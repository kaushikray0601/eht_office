import pandas as pd
from .models import ElecEHT_ASMEB36, ElecEHT_ThermalConductivity, ElecEHT_Vendor, HeatTracingInput, ProjectData
from .models import HeatLoss, SelectedTracer, AlternateTracer, PowerDistribution, BOQ, ProcessLineCalculation

from django.db.models.functions import Cast
from django.db.models import FloatField

from django.shortcuts import render
from django.http import JsonResponse, HttpResponse



def fetch_asme_b36_table():
    """Fetch ASME B36 table data from the database and return as a DataFrame."""
    data = ElecEHT_ASMEB36.objects.values('Nominal_Pipe_Size', 'Outside_Diameter_mm')
    return pd.DataFrame.from_records(data)


def fetch_thermal_conductivity_data():
    """Fetch thermal conductivity data from the database and return as a DataFrame."""
    data = ElecEHT_ThermalConductivity.objects.values('Ins_Mat_Type', 'K_factor_A', 'K_factor_B', 'K_factor_C')
    return pd.DataFrame.from_records(data)


def fetch_process_lines(project_id):
    """Fetch process lines for the given project ID and return as a DataFrame."""
    data = HeatTracingInput.objects.filter(proj_id=project_id).values()
    return pd.DataFrame(data)


def fetch_vendor_data(selected_vendor, project_voltage):
    """Fetch vendor data filtered by vendor and voltage and return as a DataFrame."""
    data = ElecEHT_Vendor.objects.filter(
        Vendor=selected_vendor,
        Voltage__gte=float(project_voltage)
    ).annotate(
        Voltage_Float=Cast('Voltage', FloatField())  # Convert to float at DB level
    ).values(
        'V_UID', 'Voltage_Float', 'A_Coeff', 'B_Coeff', 'C_Coeff',
        'Power_at_Startup_T', 'Ohm_per_km', 'Res_corrFactor_Mica', 'Tracer_Family'
    ).distinct()
    return pd.DataFrame(data)


def fetch_project_data(project_id):
    """Fetch project-specific settings from the database."""
    project_data = ProjectData.objects.get(proj_id=project_id)
    return {
        "id": project_data.id,
        "proj_id": project_data.proj_id,
        "min_amb_t": float(project_data.min_amb_t),
        "max_amb_t": float(project_data.max_amb_t),
        "startup_t": float(project_data.startup_t),
        "area_class": project_data.area_class,
        "temp_class": project_data.temp_class,
        "voltage": float(project_data.voltage),
        "max_cb_size": float(project_data.max_cb_size),
        "restrict_cb_current": float(project_data.restrict_cb_current),
        "vendor": project_data.vendor,
        "spiral_wrap_allowed": project_data.spiral_wrap_allowed,
        "spiral_factor": float(project_data.spiral_factor),
        "margin_on_tracer_lengths": float(project_data.margin_on_tracer_lengths),
        "voltage_var_factor": float(project_data.voltage_var_factor),
        "res_tol": float(project_data.res_tol),
        "termination_margin": float(project_data.termination_margin),
        "heat_loss_sf": float(project_data.heat_loss_sf),
        "rtd_thrm": project_data.rtd_thrm,
        "wind_speed": float(project_data.wind_speed),
        "caution_label_interval": float(project_data.caution_label_interval),
        "isolator_location": project_data.isolator_location,
        "ckt_ln": float(project_data.ckt_ln),
        "loop_ln": float(project_data.loop_ln),
        "allowablevdrop": float(project_data.allowablevdrop),
    }


# Store calculated data in the database

# Function to store aggregated_results into the database
def store_calculated_results(project_id, aggregated_results):
    # Storing Heat Loss Data
    for item in aggregated_results['heat_loss']:
        HeatLoss.objects.update_or_create(
            uid=item['uid'],
            defaults={
                'heat_loss': item['heat_loss'],
                'tracer_adder': item['tracer_adder']
            }
        )
    field_mapping = {
    'A_Coeff': 'a_coeff',
    'B_Coeff': 'b_coeff',
    'C_Coeff': 'c_coeff',
    'Ohm_per_km': 'ohm_per_km',
    'Power_Output': 'power_output',
    'Power_at_Startup_T': 'power_at_startup_t',
    'Res_corrFactor_Mica': 'res_corrFactor_mica',
    'Spiral_Factor': 'spiral_factor',
    'Tracer_Family': 'tracer_family',
    'Tracer_Length': 'tracer_length',
    'Tracer_With_Margin': 'tracer_with_margin',
    'V_UID': 'v_uid',
    'Voltage_Correction_Factor': 'voltage_correction_factor',
    'Voltage_Float': 'voltage_float',
}
    # Storing Selected Tracers Data
    for item in aggregated_results['selected_tracers']:
        item['Res_corrFactor_Mica']=float(item['Res_corrFactor_Mica'])
        item['Ohm_per_km']=float(item['Ohm_per_km'])
        item['Power_at_Startup_T'] = float(item['Power_at_Startup_T'])
        transformed_item = {field_mapping[key]: value for key, value in item.items()}
        SelectedTracer.objects.update_or_create(
            v_uid=item['V_UID'],
            defaults=transformed_item
        )
    
    # Storing Alternate Tracers Data
    for item in aggregated_results['alternate_tracers']:
        AlternateTracer.objects.update_or_create(
            v_uid=item['V_UID'],
            defaults=transformed_item
        )
    
    # Storing Power Distribution Data
    for item in aggregated_results['power_distribution']:
        branches = item.pop('branches')
        power_distribution, _ = PowerDistribution.objects.update_or_create(
            uid=item['uid'],
            defaults=item
        )
        for branch in branches:
            power_distribution.branches.create(**branch)
    
    # Storing BOQ Data
    for item in aggregated_results['boq_per_line']:
        BOQ.objects.update_or_create(
            uid=item['uid'],
            defaults=item
        )
    
    # Storing Consolidated Power Data
    for item in aggregated_results['tracer_power_param']:
        ProcessLineCalculation.objects.update_or_create(
            uid=item['uid'],
            defaults=item        )
    
    return True



# TODO : make sure the temp folder is deleted after the file is 
# downloaded and file pointer is reset to the start of the file

# Function to export all reports in an Excel file with multiple sheets
def export_full_report_excel(request):
    boq_data = list(BOQ.objects.all().values())
    calculation_data = list(ProcessLineCalculation.objects.all().values())
    cable_schedule_data = list(ProcessLineCalculation.objects.all().values())
    
    with pd.ExcelWriter('/tmp/full_report.xlsx', engine='xlsxwriter') as writer:
        if boq_data:
            pd.DataFrame(boq_data).to_excel(writer, sheet_name="BOQ Summary", index=False)
        if calculation_data:
            pd.DataFrame(calculation_data).to_excel(writer, sheet_name="Calculation Results", index=False)
        if cable_schedule_data:
            pd.DataFrame(cable_schedule_data).to_excel(writer, sheet_name="Cable Schedule", index=False)
    
    with open('/tmp/full_report.xlsx', 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="full_report.xlsx"'
    
    return response
