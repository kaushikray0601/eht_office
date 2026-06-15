import logging
import os
from time import perf_counter
from pathlib import Path
import pandas as pd
from mimetypes import guess_type
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.utils import DatabaseError
from django.utils.timezone import now, timedelta
from django.http import JsonResponse
import math

def index(request):
    my_dictionary = {"a": 1, "b": 2}
    return JsonResponse(my_dictionary)

def index2(request):
    my_array = [("a", 1), ("b", 2)]
    return JsonResponse(my_array, safe=False)

import pandas as pd
from django.core.exceptions import ValidationError
from .models import HeatTracingInput


logger = logging.getLogger(__name__)


def emit_timing(message):
    if not getattr(settings, "EHT_TIMING_LOGS", False):
        return
    print(message, flush=True)
    logger.warning(message)

# Constants
ALLOWED_EXTENSIONS = ['.xlsx']
ALLOWED_XLSX_MIME_TYPES = {
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}
XLSX_ZIP_SIGNATURES = (b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08')
MAX_FILE_SIZE_MB = 10
ERROR_FILE_DIR = os.path.join('file_storage', 'error_file')
DEFAULT_ERROR_RETENTION_MAX_FILES = 10
DEFAULT_ERROR_FILE_MAX_SIZE_MB = 5
MAX_FAILED_ATTEMPTS = 3
LOCKOUT_THRESHOLD = 6
COOLDOWN_PERIOD_MINUTES = 30


def _read_file_start(file, byte_count=4):
    position = None
    try:
        position = file.tell()
    except (AttributeError, OSError):
        position = None
    start = file.read(byte_count)
    if position is not None:
        try:
            file.seek(position)
        except (AttributeError, OSError):
            pass
    return start


def sanitize_file_basic_check(file, session, user):   
    if file.size > MAX_FILE_SIZE_MB * 1024 * 1024:                                       # 1. Check file size
        raise ValidationError(f"File size exceeds {MAX_FILE_SIZE_MB}MB limit.")

    if file.name != os.path.basename(file.name) or '\\' in file.name or '/' in file.name:
        raise ValidationError("Invalid file name.")

    _, ext = os.path.splitext(file.name)                                                    # 2. Check file extension
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise ValidationError("Invalid file extension. Only .xlsx is allowed.")
  
    mime_type, _ = guess_type(file.name)                                                    # 3. Check MIME type
    if mime_type != 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
        raise ValidationError("File is not a valid Excel file.")
    content_type = getattr(file, 'content_type', '') or ''
    if content_type and content_type not in ALLOWED_XLSX_MIME_TYPES:
        raise ValidationError("File MIME type is not a valid Excel workbook.")
    if not _read_file_start(file).startswith(XLSX_ZIP_SIGNATURES):
        raise ValidationError("File content is not a valid XLSX workbook.")
    return True


def _error_file_retention_policy():
    try:
        from .models import ErrorFileRetentionPolicy
        policy = ErrorFileRetentionPolicy.objects.filter(is_active=True).order_by('-updated_at', '-id').first()
    except DatabaseError:
        policy = None
    if policy is None:
        return DEFAULT_ERROR_RETENTION_MAX_FILES, DEFAULT_ERROR_FILE_MAX_SIZE_MB * 1024 * 1024
    return int(policy.max_error_files), int(float(policy.max_file_size_mb) * 1024 * 1024)


def _error_file_slot_name(index):
    return f'error_file_{index:02d}.xlsx'


def _cleanup_error_file_directory(error_dir, max_files, max_file_size_bytes):
    error_path = Path(error_dir)
    error_path.mkdir(parents=True, exist_ok=True)
    allowed_names = {_error_file_slot_name(index) for index in range(1, max_files + 1)}
    for path in error_path.glob('error_file*.xlsx'):
        if not path.is_file():
            continue
        try:
            too_large = path.stat().st_size > max_file_size_bytes
        except OSError:
            continue
        if path.name not in allowed_names or too_large:
            path.unlink(missing_ok=True)


def _next_error_file_path():
    max_files, max_file_size_bytes = _error_file_retention_policy()
    error_dir = ERROR_FILE_DIR
    _cleanup_error_file_directory(error_dir, max_files, max_file_size_bytes)
    error_path = Path(error_dir)
    for index in range(1, max_files + 1):
        candidate = error_path / _error_file_slot_name(index)
        if not candidate.exists():
            return str(candidate), max_file_size_bytes
    candidates = [error_path / _error_file_slot_name(index) for index in range(1, max_files + 1)]
    oldest = min(candidates, key=lambda path: path.stat().st_mtime_ns)
    return str(oldest), max_file_size_bytes

    
def log_failed_attempt(session, user):                                          # """Track and log failed attempts."""
    attempts = session.get('failed_attempts', 0) + 1
    session['failed_attempts'] = attempts
    session.save()
    if attempts >= MAX_FAILED_ATTEMPTS:
        lock_user_account(user, session)


def lock_user_account(user, session):                                    #Lock the user account after exceeding failed attempts."""
    from .models import UserAttempt
    now_time = now()
    attempt = UserAttempt.objects.create(
        user=user,
        ip_address=session.get('user_ip'),
        failed_at=now_time,
        lockout=True,
        cooldown_expires=now_time + timedelta(minutes=COOLDOWN_PERIOD_MINUTES),
    )
    attempt.save()
    session['locked'] = True


# ---------------input validation -----------------------

def sanitize_file(file, session, user):
    overall_started = perf_counter()

    if not sanitize_file_basic_check(file, session, user):
        raise ValidationError(f"Your uploaded input file could not be processed. Check the file template.")
    
    # Read the Excel file
    try:
        read_started = perf_counter()
        df = pd.read_excel(file)
        read_duration = perf_counter() - read_started
    except Exception as e:
        raise ValidationError("Invalid Excel file. Please ensure it follows the template.")     

    #  Lets separate valid and invalid data 
    valid_rows = {}
    invalid_data = []

    # category of fields 
    mandatory_fields = ['Service_Type','Line_Size','Line_Length','Ins_Mat_Type','Insul_Thick','Maint_T','Oper_T','Design_T']
    numeric_fields = ['Line_Size', 'Line_Length', 'Insul_Thick', 'Maint_T', 'Oper_T', 'Design_T']
    other_fields = ['IsDeleted', 'PID_No', 'Area', 'Train', 'Valve_Qty', 'Flange_Qty', 'Support_Qty', 'Pipe_Mat_Class', 'Emergency_Supply', 'Discipline', 'Remarks']
    duplicate_check_fields = [
        'Line_ID', 'Area', 'Train', 'Service_Type', 'Line_Size', 'Line_Length',
        'Valve_Qty', 'Flange_Qty', 'Support_Qty', 'Pipe_Mat_Class', 'Ins_Mat_Type',
        'Insul_Thick', 'Maint_T', 'Oper_T', 'Design_T'
    ]
    
    # Use a stable row identifier even when XLID is missing or blank.
    def get_row_number(row_index, row_data=None):
        if row_data is not None:
            xlid_value = row_data.get('XLID', None)
        elif 'XLID' in df.columns:
            xlid_value = df.loc[row_index, 'XLID']
        else:
            xlid_value = None

        if pd.isna(xlid_value) or xlid_value is None:
            return row_index + 2
        if isinstance(xlid_value, str) and xlid_value.strip() == "":
            return row_index + 2
        return xlid_value

    df['_error_row_number'] = [get_row_number(idx, row) for idx, row in df.iterrows()]

    validation_started = perf_counter()
    # Validate each row    
    for idx, row in df.iterrows():
        row_number = row['_error_row_number']
        row_errors = {}
        
        # Check for mandatory fields.
        for field in mandatory_fields:
            if check_field_for_na(row, field):
                row_errors[field] = f"Missing value for {field}"

        # Numeric validations.
        numeric_values = {}
        for field in numeric_fields:
            if field in row_errors:
                continue
            try:
                value = float(row.get(field))
                numeric_values[field] = value
                if field in ['Line_Size', 'Line_Length', 'Insul_Thick'] and value < 0:
                    row_errors[field] = f"{field} must be positive."
            except (TypeError, ValueError):
                row_errors[field] = f"{field} must be numeric."

        # Set default value: If some fields are blank or none, set them to a safe default value based on the field type   
        for field in other_fields:          
            if check_field_for_na(row, field): 
                if field in ['IsDeleted', 'Emergency_Supply']:
                    row[field] = False 
                if field in ['Valve_Qty', 'Flange_Qty', 'Support_Qty']: # Numeric validations for valve_qty, flange_qty, support_qty, discipline and remarks columns     
                    row[field] = 0                    
                if field in ['PID_No', 'Area', 'Train', 'Pipe_Mat_Class', 'Discipline', 'Remarks']:
                    row[field] = 'n/A' 
        
        # Temperature constraints
        temperature_fields = ['Oper_T', 'Maint_T', 'Design_T']
        if not any(field in row_errors for field in temperature_fields) and not (
            numeric_values['Maint_T'] <= numeric_values['Oper_T'] <= numeric_values['Design_T']
        ):
            row_errors['Temperature'] = "Temperatures must satisfy Maint_T <= Oper_T <= Design_T."

        # Append to valid/invalid data
        if row_errors:
            invalid_data.append({'row_number': row_number, 'errors': row_errors})
        else:
            valid_row = row.to_dict()
            valid_row.pop('_error_row_number', None)
            valid_rows[idx] = valid_row

    # Check for duplicate rows 
    duplicates = df.duplicated(subset=duplicate_check_fields, keep=False)  # Mark all duplicates
    for idx, is_duplicate in enumerate(duplicates):
        if is_duplicate:
            row_number = df.loc[idx, '_error_row_number']
            invalid_data.append({
                'row_number': row_number,
                'errors': {
                    'Duplicate': f"Row {row_number}: Duplicate rows detected within the file."
                }
            })
            valid_rows.pop(idx, None)
        
    validation_duration = perf_counter() - validation_started

    # Write errors to Excel file
    error_file_path= ''
    if invalid_data:
        error_column = "Errors"
        df[error_column] = ""
        row_error_map = {}

        for error_entry in invalid_data:
            if isinstance(error_entry, dict):
                row_number = error_entry.get('row_number')
                errors = error_entry.get('errors', {})
                if isinstance(errors, dict):
                    row_error_messages = [str(msg) for msg in errors.values()]
                elif isinstance(errors, list):
                    row_error_messages = [str(msg) for msg in errors]
                else:
                    row_error_messages = [str(errors)]
            elif isinstance(error_entry, tuple) and len(error_entry) >= 2:
                row_number = error_entry[0]
                raw_errors = error_entry[1]
                if isinstance(raw_errors, list):
                    row_error_messages = [str(msg) for msg in raw_errors]
                else:
                    row_error_messages = [str(raw_errors)]
            else:
                continue

            row_error_map.setdefault(row_number, []).extend(row_error_messages)

        for row_number, messages in row_error_map.items():
            df.loc[df['_error_row_number'] == row_number, error_column] = "; ".join(messages)

        error_write_started = perf_counter()
        error_file_path, max_error_file_size_bytes = _next_error_file_path()
        df.drop(columns=['_error_row_number']).to_excel(error_file_path, index=False, engine='openpyxl')
        if os.path.exists(error_file_path) and os.path.getsize(error_file_path) > max_error_file_size_bytes:
            os.remove(error_file_path)
            raise ValidationError(
                'Validation error workbook exceeded the configured retention file-size limit. '
                'Reduce the upload size or ask an administrator to increase the error-file policy.'
            )
        error_write_duration = perf_counter() - error_write_started
    else:
        error_write_duration = 0.0

    valid_data = list(valid_rows.values())
    total_duration = perf_counter() - overall_started
    emit_timing(
        "EHT timing | sanitize_file | rows={rows} | read={read:.3f}s | validate={validate:.3f}s | error_write={error_write:.3f}s | total={total:.3f}s | valid_rows={valid_rows} | invalid_rows={invalid_rows}".format(
            rows=len(df.index),
            read=read_duration,
            validate=validation_duration,
            error_write=error_write_duration,
            total=total_duration,
            valid_rows=len(valid_data),
            invalid_rows=len(invalid_data),
        )
    )
    return valid_data, invalid_data, error_file_path  # Return sanitized data



# Helper functions ---
def check_field_for_na(row, field):
    value = row.get(field)
    is_value_na = pd.isna(value) or value is None or (isinstance(value, str) and value.strip() == "")  # Check for both NaN and None
    if field in ['IsDeleted', 'Emergency_Supply']: # when df gets previous value 'blank' next datatype it considers float (instead of boolean), need to force it to True/False
        if row[field] == 0:
            row[field] = False
    return True if is_value_na else False
