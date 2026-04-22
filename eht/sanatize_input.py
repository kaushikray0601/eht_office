import os
import pandas as pd
from mimetypes import guess_type
from django.core.exceptions import ValidationError
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

# Constants
ALLOWED_EXTENSIONS = ['.xlsx']
MAX_FILE_SIZE_MB = 10
MAX_FAILED_ATTEMPTS = 3
LOCKOUT_THRESHOLD = 6
COOLDOWN_PERIOD_MINUTES = 30


def sanitize_file_basic_check(file, session, user):   
    if file.size > MAX_FILE_SIZE_MB * 1024 * 1024:                                       # 1. Check file size
        raise ValidationError(f"File size exceeds {MAX_FILE_SIZE_MB}MB limit.")
   
    _, ext = os.path.splitext(file.name)                                                    # 2. Check file extension
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise ValidationError("Invalid file extension. Only .xlsx is allowed.")
  
    mime_type, _ = guess_type(file.name)                                                    # 3. Check MIME type
    if mime_type != 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
        raise ValidationError("File is not a valid Excel file.")
    return True

    
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

    if not sanitize_file_basic_check(file, session, user):
        raise ValidationError(f"Your uploaded input file could not be processed. Check the file template.")
    
    # Read the Excel file
    try:
        df = pd.read_excel(file)
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
            numeric_values['Oper_T'] <= numeric_values['Maint_T'] <= numeric_values['Design_T']
        ):
            row_errors['Temperature'] = "Temperatures must satisfy Oper_T <= Maint_T <= Design_T."

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

        error_file_path = os.path.join('file_storage/error_file', 'error_file.xlsx')
        df.drop(columns=['_error_row_number']).to_excel(error_file_path, index=False, engine='openpyxl')

    valid_data = list(valid_rows.values())
    return valid_data, invalid_data, error_file_path  # Return sanitized data



# Helper functions ---
def check_field_for_na(row, field):
    value = row.get(field)
    is_value_na = pd.isna(value) or value is None or (isinstance(value, str) and value.strip() == "")  # Check for both NaN and None
    if field in ['IsDeleted', 'Emergency_Supply']: # when df gets previous value 'blank' next datatype it considers float (instead of boolean), need to force it to True/False
        if row[field] == 0:
            row[field] = False
    return True if is_value_na else False
