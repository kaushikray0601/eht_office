from django import forms

from .models import ManagedProject, ProjectData, is_default_project_id
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, Field, Row, Column

class ProjectDataForm(forms.ModelForm):
    proj_id = forms.ChoiceField(label="Project ID")

    class Meta:
        model = ProjectData
        fields = [
            'proj_id',
            'vendor',
            'startup_t',
            'min_amb_t',
            'max_amb_t',
            'voltage',
            'max_cb_size',
            'restrict_cb_current',
            'allowablevdrop',
            'spiral_factor',
            'spiral_wrap_allowed',
            'margin_on_tracer_lengths',
            'voltage_var_factor',
            'res_tol',
            'termination_margin',
            'heat_loss_sf',
            'heat_loss_method',
            'rtd_thrm',
            'wind_speed',
            'caution_label_interval',
            'isolator_location',
            'ckt_ln',
            'loop_ln',
            'area_class',
            'temp_class',
        ]
        labels = {
            'proj_id': 'Project ID',
            'vendor':'Select Vendor',
            'min_amb_t': 'Min. ambient Temp. (°C)',
            'max_amb_t': 'Max. ambient Temp. (°C)',
            'startup_t': 'Startup Temp. (°C)',
            'area_class':'Area Class',
            'temp_class':'Temp. Class',
            'voltage':'System Voltage (V)',
            'max_cb_size':'Max. circuit breaker size (A)',            
            'restrict_cb_current':'Max. circuit breaker loading (%)',
            'allowablevdrop':'Allowed voltage drop for cold cable (%)',
            'spiral_factor':'Allowed Spiral Factor',
            'spiral_wrap_allowed':'Installation with spiral wrap',
            'margin_on_tracer_lengths':'Margin on tracer length (%)',
            'voltage_var_factor':'Design margin for voltage variation (%)',
            'res_tol':'Tracer resistance tolerance (%)',
            'termination_margin':'Termination margin (in mm)',
            'heat_loss_sf':'Safety Factor on Heat Loss (> 1.0)',
            'heat_loss_method':'Heat loss calculation method',
            'rtd_thrm':'Select RTD/Thermostat type',
            'wind_speed':'Wind speed (kmph)',
            'caution_label_interval':'Caution Label Interval (m)',
            'isolator_location':'Local Isolator Location',
            'ckt_ln':'Cable Length (DB to JB) (m)',
            'loop_ln':'	Loop Length (JB to JB) (m)'
        }
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(ProjectDataForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()  
        self.helper.form_method = 'post'
        # self.helper.add_input(Submit('submit', 'Save Project Data'))

        available_projects = [
            project
            for project in ManagedProject.available_to_user(user)
            if not is_default_project_id(project.proj_id)
        ]
        self.fields['proj_id'].choices = [('', 'Select a project')] + [
            (project.proj_id, project.display_name)
            for project in available_projects
        ]
        if available_projects:
            self.fields['proj_id'].help_text = "Projects are managed in Django admin."
        else:
            self.fields['proj_id'].help_text = "No active projects are available yet. Add or assign one in Django admin."
            self.fields['proj_id'].disabled = True

        self.fields['min_amb_t'].widget.attrs.update({'placeholder': 'Min. ambient temperature (°C)'})
        self.fields['max_amb_t'].widget.attrs.update({'placeholder': 'Max. ambient temperature (°C)'})
        self.fields['startup_t'].widget.attrs.update({'placeholder': 'Startup temperature (°C)'})
        self.fields['heat_loss_method'].widget.attrs.update({'title': (
            'Mean temperature is active by default. Table, integrated k(T), and fixed-basis methods are placeholders for future releases.'
        )})

        for name, field in self.fields.items():
            self._apply_bootstrap_widget_classes(name, field)

    def _apply_bootstrap_widget_classes(self, name, field):
        widget = field.widget
        existing_classes = widget.attrs.get('class', '')
        class_tokens = existing_classes.split()

        def ensure_class(value):
            if value not in class_tokens:
                class_tokens.append(value)

        if isinstance(widget, forms.Select):
            ensure_class('form-select')
        else:
            ensure_class('form-control')

        if name in {'proj_id', 'vendor', 'heat_loss_method'}:
            ensure_class('project-hero-field')

        widget.attrs['class'] = ' '.join(token for token in class_tokens if token)
