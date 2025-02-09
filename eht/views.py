import os
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.http import JsonResponse, FileResponse
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings

from .models import ProjectData, UserAttempt
from .forms import ProjectDataForm
from .sanatize_input import * #sanitize_file
from .calculations import * # Calculation

from django.utils.timezone import now, timedelta

from django.urls import reverse

COOLDOWN_PERIOD_MINUTES = 30
MAX_FAILED_ATTEMPTS = 3

from eht.cal import parent_calculation_func
from eht.models import ProjectData, HeatTracingInput, ElecEHT_ThermalConductivity, ElecEHT_ASMEB36, ElecEHT_Vendor, SELECT_VENDOR # import required models


import logging
logger = logging.getLogger(__name__)

# Create your views here.
def index(request):
    context = {'key1': 'value1','key2': 'value2' }
    return render (request, 'eht/home.html', context)


# --------------Create project data--------------------------------------------------
def create_project_data(request, project_id=None,):  
    form = handle_project_data(request)
    return render(request, 'eht/project_data.html', {'form': form})
# --------------Edit project data--------------------------------------------------
def update_project_data(request, project_id=None, *arg, **kwarg):
    form = handle_project_data(request, project_id)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        form_html = render_to_string('eht/partials/project_data_form.html', {'form': form, 'project_id': project_id}, request)
        return JsonResponse({'form_html': form_html})    
    return render (request, 'eht/project_data.html', {'form': form, 'project_id': project_id})

# --------------Download Input data Template--------------------------------------------------
@login_required
def download_template(request):
    file_path = os.path.join('file_storage', os.path.basename('EHT_Input_template.xlsx'))    
    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename=file_path)
        return response
    else:
        messages.error(request, "The file could not be found.")
        return redirect('some_error_page')

@login_required
def upload_input(request, project_id=None, *arg, **kwarg):
    project_id = project_id or request.GET.get('project_id') or request.POST.get('project_id')
    if request.method == 'POST':
        file = request.FILES.get('file')
        if not file: return JsonResponse({'error': 'No file uploaded'}, status=400)

        try:
            # Sanitize the file
            valid_data, invalid_data, error_file_path = sanitize_file(file, request.session, request.user)

            # Save valid data to the database with a "pending" status
            if valid_data:
                upload_inputData_in_DB(valid_data, project_id)

            # If invalid data exists, send the error file and ask for user confirmation            
            if invalid_data:
                error_file_name = os.path.basename(error_file_path)
                error_file_url = reverse('download_error_file', args=[error_file_name])  # A dedicated endpoint for file download

                # Return JSON metadata with the download URL
                return JsonResponse({
                    'valid_data_with_error': True,
                    'error_file_url': error_file_url,
                    'success': 'Partial valid data uploaded. Download the error file.',
                }, status=200)


                        
            # If all data is valid, proceed directly to the calculation stage                    
            status_ok, valid_data, updated_count = update_pending_status(project_id)     

            if status_ok:                
                Calculation_result = parent_calculation_func(project_id, valid_data)

            return JsonResponse({'success': 'Data processed successfully. Proceeding to calculations.'}, status=200)  
        
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'error': f"An unexpected error occurred: {str(e)}"}, status=500)

    return JsonResponse({'error': 'Invalid request method.'}, status=405)

# -------------Download error File -------------------------------------------------------

def download_error_file(request, file_name):
    file_path = os.path.join(settings.BASE_DIR, 'file_storage','error_file', file_name)  
    try:
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=file_name)
    except FileNotFoundError:
        return JsonResponse({'error': 'File not found.'}, status=404)

# --------------Process the valid data --------------------------------------------------
@login_required
def confirm_valid_data(request):
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        if not project_id:
            return JsonResponse({'error': 'Project ID is required.'}, status=400)

        try:            
            status_ok, valid_data, updated_count = update_pending_status(project_id)
            if status_ok:
                calculation_result = parent_calculation_func(project_id)

                logger.info(f"Project ID: {project_id} - File uploaded and processed successfully.")                  
                return JsonResponse({'success': 'File uploaded and processed successfully.'}, status=200)
            else:                
                return JsonResponse({"error': 'Internal server error."}, status=500)
        except Exception as e:
            logger.error(f"Project ID: {project_id} - Failed to confirm 'EHT Input data': {str(e)}", exc_info=True)
            return JsonResponse({'error': f"Failed to confirm valid data: {str(e)}"}, status=500)
        
    return JsonResponse({'error': 'Invalid request method.'}, status=405)





# # Success page when form is created successfully
# def success(request):
#     return render(request, 'eht/success.html')



# ----------Helper functions--------------------

#  Get the validated instance of forms
def handle_project_data(request, project_id=None):
    instance = get_object_or_404(ProjectData, proj_id=project_id) if project_id else ProjectData()
    form = ProjectDataForm(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Project data saved successfully.")
    return form


#  Logic for userAtempt and limit invalid attempts.
def log_failed_attempt(user, ip_address):
    # Check if a user is already locked
    attempt = UserAttempt.objects.filter(user=user).first()
    if attempt and attempt.is_locked():
        return {'locked': True, 'cooldown_expires': attempt.cooldown_expires}

    # Create or update an attempt entry
    if not attempt:
        attempt = UserAttempt.objects.create(
            user=user,
            ip_address=ip_address,
            failed_at=now(),
            lockout=False,
            cooldown_expires=None
        )
    else:
        attempt.failed_at = now()

    # Increment failed attempts and check for lockout
    attempts_count = UserAttempt.objects.filter(user=user, lockout=False).count()
    if attempts_count >= MAX_FAILED_ATTEMPTS:
        attempt.lockout = True
        attempt.cooldown_expires = now() + timedelta(minutes=COOLDOWN_PERIOD_MINUTES)

    attempt.save()
    return {'locked': attempt.lockout, 'cooldown_expires': attempt.cooldown_expires}


# Bulk upload valid/sanitized input data into database
def upload_inputData_in_DB(valid_data, project_id):
    try:
        if project_id:
            deleted_count, _ = HeatTracingInput.objects.filter(proj_id=project_id).delete()
            print(f"{deleted_count} rows deleted")

        valid_rows = [
            HeatTracingInput(               
                proj_id=project_id,
                xlid=row['XLID'],
                line_id=row['Line_ID'],
                service_type=row['Service_Type'],
                line_size=row['Line_Size'],
                line_length=row['Line_Length'],
                ins_mat_type=row['Ins_Mat_Type'],
                insul_thick=row['Insul_Thick'],
                maint_temp=row['Maint_T'],
                oper_temp=row['Oper_T'],
                design_temp=row['Design_T'],
                is_deleted=row['IsDeleted'],
                pid_no=row['PID_No'],
                area=row['Area'],
                train=row['Train'],
                valve_qty=row['Valve_Qty'],
                flange_qty=row['Flange_Qty'],
                support_qty=row['Support_Qty'],
                pipe_mat_class=row['Pipe_Mat_Class'],
                emergency_supply=row['Emergency_Supply'],
                discipline=row['Discipline'],
                remarks=row['Remarks'],
                status='pending',
            )
            for row in valid_data
        ]
        HeatTracingInput.objects.bulk_create(valid_rows)

    except Exception as e:
        # Log the error or handle it as needed
        print(f"An error occurred: {e}")

# Update input data status from 'pending' to confirm

def update_pending_status(project_id):
    # Update the status of valid data for the given project ID
    try:
        updated_count = HeatTracingInput.objects.filter(proj_id=project_id, status='pending').update(status='confirmed')
        valid_data = HeatTracingInput.objects.filter(proj_id=project_id, status='confirmed').values()
        logger.info(f"Project ID: {project_id} -  'EHT input data' Status updated successfully. Updated {updated_count} records.")
        return True, valid_data, updated_count
    except Exception as e:
        logger.error(f"Project ID: {project_id} - Failed to update pending status: {str(e)}", exc_info=True)
        return False, None, None



# test Base template

# --------------Create project data--------------------------------------------------
def base(request):  
    form = ProjectDataForm()
    return render(request, 'eht/base.html', {'form': form})

def my_login(request):    
    return render(request, 'eht/my_login.html')

def my_logout(request):    
    return render(request, 'eht/my_logout.html')

def my_register(request):    
    return render(request, 'eht/my_register.html')