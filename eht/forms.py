from django import forms
from .models import ProjectData
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, Field, Row, Column

valve_factor = 0
flange_factor = 0
support_factor = 0
project_ID = 'P001'

class ProjectDataForm(forms.ModelForm):

    # Define a non-model field just to display to user but will not be stored anywhere
    readonly_info = forms.CharField(
        initial="Refer Note-1",  # Set a default value
        required=False,
        disabled=True,  # Make the field read-only (grayed out)
        label="Factor for valve/flange/support"
    )

    class Meta:
        model = ProjectData
        # fields = '__all__'  # Or list specific fields you want to include
        fields = ['proj_id', 'min_amb_t', 'max_amb_t', 'startup_t', 'area_class', 'temp_class', 'voltage', 
                  'max_cb_size', 'restrict_cb_current', 'vendor', 'allowablevdrop', 'spiral_factor', 
                  'spiral_wrap_allowed', 'margin_on_tracer_lengths', 'voltage_var_factor', 'res_tol', 
                  'termination_margin', 'heat_loss_sf', 'rtd_thrm', 'wind_speed', 'caution_label_interval', 
                  'isolator_location', 'ckt_ln', 'loop_ln'
                  ]
        labels = {
            'proj_id': 'Project ID',
            'min_amb_t': 'Min. ambient Temp. (°C)',
            'max_amb_t': 'Max. ambient Temp. (°C)',
            'startup_t': 'Startup Temp. (°C)',
            'area_class':'Area Class',
            'temp_class':'Temp. Class',
            'voltage':'System Voltage (V)',
            'max_cb_size':'Max. circuit breaker size (A)',            
            'restrict_cb_current':'Max. circuit breaker loading (%)',
            'vendor':'Select Vendor',
            'allowablevdrop':'Allowed voltage drop for cold cable (%)',
            'spiral_factor':'Allowed Spiral Factor',
            'spiral_wrap_allowed':'Installation with spiral wrap',
            'margin_on_tracer_lengths':'Margin on tracer length (%)',
            'voltage_var_factor':'Design margin for voltage variation (%)',
            'res_tol':'Tracer resistance tolerance (%)',
            'termination_margin':'Termination margin (in mm)',
            'heat_loss_sf':'Safety Factor on Heat Loss (> 1.0)',
            'rtd_thrm':'Select RTD/Thermostat type',
            'wind_speed':'Wind speed (kmph)',
            'caution_label_interval':'Caution Label Interval (m)',
            'isolator_location':'Local Isolator Location',
            'ckt_ln':'Cable Length (DB to JB) (m)',
            'loop_ln':'	Loop Length (JB to JB) (m)'
        }
    
    def clean_proj_id(self):
        proj_id = self.cleaned_data.get('proj_id')
        if ProjectData.objects.filter(proj_id=proj_id).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A project with this ID already exists.")
        return proj_id
      
    def __init__(self, *args, **kwargs):
        super(ProjectDataForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()  
        self.helper.form_method = 'post'
        # self.helper.add_input(Submit('submit', 'Save Project Data'))

        # Get Choice fields from database or from environment variables; e.g. 
        # self.fields['proj_id'].choices = [(x.code, x.name) for x in Project.objects.all()]

        # Helper text (this code shows the text within the input field)
        self.fields['proj_id'].widget.attrs.update({'placeholder': 'Select Project ID'})
        self.fields['min_amb_t'].widget.attrs.update({'placeholder': 'Min. ambient temperature (°C)'})
        self.fields['max_amb_t'].widget.attrs.update({'placeholder': 'Max. ambient temperature (°C)'})
        self.fields['startup_t'].widget.attrs.update({'placeholder': 'Startup temperature (°C)'})

        # self.fields['proj_id'].widget.attrs.update({'placeholder': 'Select Project ID'})
        # self.fields['min_amb_t'].widget.attrs.update({'placeholder': 'Min. ambient temperature (°C)'})
        # self.fields['max_amb_t'].widget.attrs.update({'placeholder': 'Max. ambient temperature (°C)'})
        # self.fields['startup_t'].widget.attrs.update({'placeholder': 'Startup temperature (°C)'})

        #  below helper text code to show the helper text below the field (it take more space
        help_texts = {
            # 'min_amb_t': 'Enter the minimum ambient temperature in °C.', # Add more help texts as needed
        }
