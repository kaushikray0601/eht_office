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
    valid_data = []
    invalid_data = []

    # category of fields 
    mandatory_fields = ['Service_Type','Line_Size','Line_Length','Ins_Mat_Type','Insul_Thick','Maint_T','Oper_T','Design_T']
    numeric_fields = ['Line_Size', 'Line_Length', 'Insul_Thick', 'Maint_T', 'Oper_T', 'Design_T']
    other_fields = ['IsDeleted', 'PID_No', 'Area', 'Train', 'Valve_Qty', 'Flange_Qty', 'Support_Qty', 'Pipe_Mat_Class', 'Emergency_Supply', 'Discipline', 'Remarks']
    
    # Validate each row    
    for idx, row in df.iterrows():
        row_number = row.get('XLID', idx + 2)  # Default to Excel row + 2 for 1-based index
        row_errors = {}
        
        # Check for mandatory fields & Numeric validations 
        for field in mandatory_fields:
            if check_field_for_na(row, field):                                          # Validation for Mandatory fields
                row_errors[field] = f"Missing value for {field}"
            else:                                                                         # Validation for Numeric 
                for field in numeric_fields:
                    try:
                        value = float(row.get(field))
                        if field in ['Line_Size', 'Line_Length', 'Insul_Thick']:
                            if value < 0:
                                row_errors[field] = f"{field} must be positive."
                    except ValueError:
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
        if not (row['Oper_T']  <= row['Maint_T'] <= row['Design_T']):
            row_errors[field] = f"Temperatures must satisfy Oper_T <= Maint_T <= Design_T."

        # Append to valid/invalid data
        if row_errors:
            invalid_data.append({'row_number': row_number, 'errors': row_errors})
        else:
            valid_data.append(row.to_dict())

    # Check for duplicate rows 
    duplicates = df.duplicated(subset=mandatory_fields, keep=False)  # Mark all duplicates
    for idx, is_duplicate in enumerate(duplicates):
        if is_duplicate:
            row_number = df.loc[idx, 'XLID'] or idx + 2
            invalid_data.append((row_number, [f"Row {row_number}: Duplicate rows detected within the file."]))
        
    # Write errors to Excel file
    error_file_path= ''
    if invalid_data:
        error_column = "Errors"
        df[error_column] = ""
        for error_entry in invalid_data:
            row_number = error_entry['row_number']
            row_error_messages = "; ".join([msg for msg in error_entry['errors'].values()])          
            df.loc[df['XLID'] == row_number, error_column] = row_error_messages            

        error_file_path = os.path.join('file_storage/error_file', 'error_file.xlsx')
        df.to_excel(error_file_path, index=False, engine='openpyxl')       

    return valid_data, invalid_data, error_file_path  # Return sanitized data



# Helper functions ---
def check_field_for_na(row, field):
    value = row.get(field)
    is_value_na = pd.isna(value) or value is None or (isinstance(value, str) and value.strip() == "")  # Check for both NaN and None
    if field in ['IsDeleted', 'Emergency_Supply']: # when df gets previous value 'blank' next datatype it considers float (instead of boolean), need to force it to True/False
        if row[field] == 0:
            row[field] = False
    return True if is_value_na else False