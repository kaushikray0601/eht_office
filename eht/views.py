import os
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.http import JsonResponse, FileResponse, Http404
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings

from .models import DEFAULT_PROJECT_ID, HeatTracingInput, ManagedProject, ProjectData, UserAttempt, is_default_project_id
from .forms import ProjectDataForm
from .sanatize_input import * #sanitize_file
# from .calculations import * # Calculation
from django.utils.timezone import now, timedelta


from django.urls import reverse

COOLDOWN_PERIOD_MINUTES = 30
MAX_FAILED_ATTEMPTS = 3

# from eht.cal import parent_calculation_func
from eht.cal import orchestrate_calculations
from eht.models import ProjectData, HeatTracingInput, ElecEHT_ThermalConductivity, ElecEHT_ASMEB36, ElecEHT_Vendor, SELECT_VENDOR # import required models


import logging
logger = logging.getLogger(__name__)

PROJECT_DATA_TEMPLATE_FIELDS = [
    'min_amb_t',
    'max_amb_t',
    'startup_t',
    'area_class',
    'temp_class',
    'voltage',
    'max_cb_size',
    'restrict_cb_current',
    'vendor',
    'spiral_wrap_allowed',
    'spiral_factor',
    'valve_factor',
    'flange_factor',
    'support_factor',
    'margin_on_tracer_lengths',
    'voltage_var_factor',
    'res_tol',
    'termination_margin',
    'heat_loss_sf',
    'rtd_thrm',
    'wind_speed',
    'req_local_isolator',
    'caution_label_interval',
    'k_factor_ccons',
    'isolator_location',
    'ckt_ln',
    'loop_ln',
    'acc_power_density',
    'tracer_temp_factor',
    'alpha_for_res',
    'allowablevdrop',
    'udf1',
    'udf2',
    'udf3',
]


def copy_project_setup(source_project, target_project):
    for field_name in PROJECT_DATA_TEMPLATE_FIELDS:
        setattr(target_project, field_name, getattr(source_project, field_name))

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

# @login_required
# def upload_input(request, project_id=None, *arg, **kwarg):
#     project_id = project_id or request.GET.get('project_id') or request.POST.get('project_id')
#     if request.method == 'POST':
#         file = request.FILES.get('file')
#         if not file: return JsonResponse({'error': 'No file uploaded'}, status=400)

#         try:
#             # Sanitize the file
#             valid_data, invalid_data, error_file_path = sanitize_file(file, request.session, request.user)

#             # Save valid data to the database with a "pending" status
#             if valid_data:
#                 upload_inputData_in_DB(valid_data, project_id)

#             # If invalid data exists, send the error file and ask for user confirmation            
#             if invalid_data:
#                 error_file_name = os.path.basename(error_file_path)
#                 error_file_url = reverse('download_error_file', args=[error_file_name])  # A dedicated endpoint for file download

#                 # Return JSON metadata with the download URL
#                 return JsonResponse({
#                     'valid_data_with_error': True,
#                     'error_file_url': error_file_url,
#                     'success': 'Partial valid data uploaded. Download the error file.',
#                 }, status=200)


                        
#             # If all data is valid, proceed directly to the calculation stage                    
#             status_ok, valid_data, updated_count = update_pending_status(project_id)     

#             if status_ok:                
#                 # Calculation_result = parent_calculation_func(project_id, valid_data)
#                 Calculation_result = orchestrate_calculations(project_id, valid_data)
                
               

#             return JsonResponse({'success': 'Data processed successfully. Proceeding to calculations.'}, status=200)  
        
#         except ValidationError as e:
#             return JsonResponse({'error': str(e)}, status=400)
#         except Exception as e:
#             return JsonResponse({'error': f"An unexpected error occurred: {str(e)}"}, status=500)

#     return JsonResponse({'error': 'Invalid request method.'}, status=405)

# ##################################################################################################
# CALCULATION Module: --------------------------------------------------------

from .cal import orchestrate_calculations
from .data_service import (
    fetch_process_lines,
    fetch_vendor_data,
    fetch_project_data,
    fetch_asme_b36_table,
    fetch_thermal_conductivity_data,
    store_calculated_results,
)


def summarize_calculation_result(calculation_result):
    return {
        'heat_loss': len(calculation_result.get('heat_loss', [])),
        'selected_tracers': len(calculation_result.get('selected_tracers', [])),
        'alternative_tracers': len(calculation_result.get('alternative_tracers', [])),
        'power_distribution': len(calculation_result.get('power_distribution', [])),
        'boq_lines': len(calculation_result.get('boq_per_line', {})),
        'consolidated_boq_items': len(calculation_result.get('consolidated_boq', {})),
        'tracer_power_param': len(calculation_result.get('tracer_power_param', [])),
    }


def run_project_calculations(project_id):
    project_specific_data = fetch_project_data(project_id)
    selected_vendor = next(
        (vendor_name for code, vendor_name in SELECT_VENDOR if code == project_specific_data['vendor']),
        None,
    )
    if not selected_vendor:
        raise ValidationError("Selected vendor could not be resolved for this project.")

    process_lines = fetch_process_lines(project_id)
    if process_lines.empty:
        raise ValidationError("No confirmed input data found for this project.")

    vendor_data = fetch_vendor_data(selected_vendor, project_specific_data['voltage'])
    asme_b36_table = fetch_asme_b36_table()
    thermal_conductivity_data = fetch_thermal_conductivity_data()

    calculation_result = orchestrate_calculations(
        project_id=project_id,
        process_lines=process_lines,
        vendor_data=vendor_data,
        project_settings=project_specific_data,
        asme_b36_table=asme_b36_table,
        thermal_cond_data=thermal_conductivity_data,
    )
    store_calculated_results(project_id, calculation_result)
    return calculation_result, summarize_calculation_result(calculation_result)


@login_required
def calculate_view(request, project_id=None):
    project_id = project_id or request.GET.get('project_id') or request.POST.get('project_id')

    if request.method == 'POST':
        file = request.FILES.get('file')
        if not file: return JsonResponse({'error': 'No file uploaded'}, status=400)

        try:
            # Step 1: Sanitize the file
            valid_process_line_data, invalid_data, error_file_path = sanitize_file(file, request.session, request.user)         
            # Save valid data to the database with a "pending" status
            if valid_process_line_data:
                upload_inputData_in_DB(valid_process_line_data, project_id)

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

            if not status_ok:
                return JsonResponse({'error': 'Failed to confirm uploaded data.'}, status=500)

            if updated_count == 0:
                return JsonResponse({'error': 'No valid uploaded data was available to process.'}, status=400)

            calculation_result, result_counts = run_project_calculations(project_id)
            return JsonResponse({
                'success': 'Input file processed and calculations completed successfully.',
                'project_id': project_id,
                'confirmed_rows': updated_count,
                'result_counts': result_counts,
                'calculation_result': calculation_result,
            })           
        
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return JsonResponse({'error': f"An unexpected error occurred: {str(e)}"}, status=500)
    return JsonResponse({'error': 'Invalid request method.'}, status=405)

# View to render the calculation results page
'''
def boq_view(request):
    boq_data = list(BOQ.objects.all().values())
    calculation_data = list(ProcessLineCalculation.objects.all().values())
    cable_schedule_data = list(ProcessLineCalculation.objects.all().values())
    return render(request, 'boq.html', {
        'boq': boq_data,
        'calculations': calculation_data,
        'cable_schedule': cable_schedule_data
    })'''

# -------------------helper functions for calculate_view:-------------------------------------------------------
# def get_project_id(request):
#     return request.GET.get('project_id') or request.POST.get('project_id')

# def fetch_asme_b36_table_from_db():
#     df_asme_b36 = ElecEHT_ASMEB36.objects.values('Nominal_Pipe_Size', 'Outside_Diameter_mm')
#     return pd.DataFrame.from_records(df_asme_b36)

# def fetch_ther_conductivity_data_from_db():
#     thermal_conductivity_data = ElecEHT_ThermalConductivity.objects.values('Ins_Mat_Type', 'K_factor_A', 'K_factor_B', 'K_factor_C')
#     return pd.DataFrame.from_records(thermal_conductivity_data)

# def fetch_process_lines_from_db(project_id):
#     """Fetch process lines from the database for a given project ID."""
#     process_lines = HeatTracingInput.objects.filter(project_id=project_id).values()
#     return pd.DataFrame(process_lines)

# def fetch_vendor_data_from_db(selected_vendor, project_voltage):
#     """
#     Fetch vendor data from the database for a given project ID.    
#     """
#     # vendor_dict = dict(SELECT_VENDOR)
#     vendor_data_query = list(ElecEHT_Vendor.objects.filter(
#             Vendor=selected_vendor,
#             Voltage__gte=float(project_voltage)
#             ).annotate(
#                 Voltage_Float= Cast('Voltage', FloatField())  # Convert to float at DB level
#                 ).values(
#                     'V_UID', 'Voltage_Float', 'A_Coeff', 'B_Coeff', 'C_Coeff', 
#                     'Power_at_Startup_T', 'Ohm_per_km', 'Res_corrFactor_Mica', 'Tracer_Family'
#                 ).distinct())   
#     return pd.DataFrame(vendor_data_query)

# def fetch_project_data_from_db(project_id):
#     """
#     Fetch project-specific settings from the database for a given project ID.
#     """
#     project_data = ProjectData.objects.get(proj_id=project_id)
#     # TODO: commented out 9 nos parameters are not currently in use, revisit and update model if not finally used.
#     # Project data being limited data set, we can directly return the dictionary without converting to DataFrame
#     return {
#         "id":project_data.id,
#         "proj_id":project_data.proj_id,
#         "min_amb_t":float(project_data.min_amb_t),
#         "max_amb_t":float(project_data.max_amb_t),
#         "startup_t":float(project_data.startup_t),
#         "area_class":project_data.area_class,
#         "temp_class":project_data.temp_class,
#         "voltage":float(project_data.voltage),
#         "max_cb_size":float(project_data.max_cb_size),
#         "restrict_cb_current":float(project_data.restrict_cb_current),
#         "vendor":project_data.vendor,
#         # "tracer_family":project_data.tracer_family,
#         "spiral_wrap_allowed":project_data.spiral_wrap_allowed,
#         "spiral_factor":float(project_data.spiral_factor),
#         #"valve_factor":float(project_data.valve_factor),                                # not used default value 5
#         #"flange_factor":float(project_data.flange_factor),                              # not used default value 5
#         #"support_factor":float(project_data.support_factor),                            # not used default value 5
#         "margin_on_tracer_lengths":float(project_data.margin_on_tracer_lengths),
#         "voltage_var_factor":float(project_data.voltage_var_factor),
#         "res_tol":float(project_data.res_tol),
#         "termination_margin":float(project_data.termination_margin),
#         "heat_loss_sf":float(project_data.heat_loss_sf),
#         "rtd_thrm":project_data.rtd_thrm,
#         "wind_speed":float(project_data.wind_speed),
#         # "req_local_isolator":project_data.req_local_isolator,
#         "caution_label_interval":float(project_data.caution_label_interval),
#         # "k_factor_ccons":float(project_data.k_factor_ccons),
#         "isolator_location":project_data.isolator_location,
#         "ckt_ln":float(project_data.ckt_ln),
#         "loop_ln":float(project_data.loop_ln),
#         # "acc_power_density":project_data.acc_power_density,
#         # "tracer_temp_factor":project_data.tracer_temp_factor,
#         # "alpha_for_res":float(project_data.alpha_for_res),
#         "allowablevdrop":float(project_data.allowablevdrop)      
#     }








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
            if not status_ok:
                return JsonResponse({'error': 'Failed to confirm valid uploaded data.'}, status=500)

            if updated_count == 0:
                return JsonResponse({'error': 'No valid uploaded data is pending confirmation.'}, status=400)

            calculation_result, result_counts = run_project_calculations(project_id)
            logger.info(
                "Project ID: %s - Pending rows confirmed and calculations completed for %s row(s).",
                project_id,
                updated_count,
            )
            return JsonResponse({
                'success': 'Valid data confirmed and calculations completed successfully.',
                'project_id': project_id,
                'confirmed_rows': updated_count,
                'result_counts': result_counts,
                'calculation_result': calculation_result,
            }, status=200)
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
    selected_project_id = request.POST.get('proj_id') or project_id or request.GET.get('project_id')
    available_projects = ManagedProject.available_to_user(getattr(request, 'user', None))
    available_project_ids = set(available_projects.values_list('proj_id', flat=True))

    if selected_project_id and not available_projects.filter(proj_id=selected_project_id).exists() and request.method != 'POST':
        raise Http404("Project not found.")

    instance = ProjectData.objects.filter(proj_id=selected_project_id).first() if selected_project_id else None
    if instance is None:
        instance = ProjectData(proj_id=selected_project_id) if selected_project_id else ProjectData()

    if request.method == 'POST' and request.POST.get('action') == 'load_defaults':
        if not selected_project_id:
            messages.error(request, "Select a project before loading the default project data.")
        elif selected_project_id not in available_project_ids:
            messages.error(request, "The selected project is not available for this user.")
        else:
            default_project = ProjectData.objects.filter(proj_id__iexact=DEFAULT_PROJECT_ID).first()
            if default_project is None:
                messages.error(request, "Default project data is not configured yet.")
            elif is_default_project_id(selected_project_id):
                messages.error(request, "Select a working project before loading the default project data.")
            else:
                copy_project_setup(default_project, instance)
                instance.proj_id = selected_project_id
                try:
                    instance.full_clean()
                    instance.save()
                    messages.success(request, "Default project data loaded successfully. Review and adjust any project-specific values.")
                except ValidationError as exc:
                    for field_errors in exc.message_dict.values():
                        for message in field_errors:
                            messages.error(request, message)
        return ProjectDataForm(instance=instance, user=getattr(request, 'user', None))

    form = ProjectDataForm(request.POST or None, instance=instance, user=getattr(request, 'user', None))
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
    form = ProjectDataForm(user=getattr(request, 'user', None))
    return render(request, 'eht/base.html', {'form': form})

def my_login(request):    
    return render(request, 'eht/my_login.html')

def my_logout(request):    
    return render(request, 'eht/my_logout.html')

def my_register(request):    
    return render(request, 'eht/my_register.html')

#  generate SLD
def sld(request):      
    return render(request, 'eht/sld.html', {})
