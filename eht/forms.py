from decimal import Decimal, InvalidOperation

from django import forms

from .models import (
    CABLE_GROUPING_DERATING_MAX,
    CABLE_GROUPING_DERATING_MIN,
    ManagedProject,
    ProjectData,
    is_default_project_id,
)
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, Field, Row, Column

PROJECT_FORM_INSTALL_METHOD_CHOICES = [
    ('E', 'E - Multi-core on open cable tray or ladder'),
    ('D2', 'D2 - Direct buried in ground (coming soon)'),
]

EHT_DB_FAULT_RATING_PRESET_CHOICES = [
    ('10', '10 kA'),
    ('15', '15 kA'),
    ('25', '25 kA'),
    ('40', '40 kA'),
    ('50', '50 kA'),
    ('OTHER', 'Other'),
]

PROJECT_FORM_COLD_CABLE_DEFAULTS = {
    'cable_standard': 'IEC_60502_1',
    'cable_conductor_material': 'Cu',
    'cable_insulation_type': 'XLPE',
    'cable_install_method': 'E',
    'cable_grouping_derating': 1.0,
    'min_cold_cable_size_mm2': 'CALCULATED',
    'mcb_curve': 'C',
    'rcd_provided': True,
}


class ColdCableInstallMethodSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if option['value'] == 'D2':
            option['attrs']['disabled'] = 'disabled'
            option['attrs']['class'] = 'text-muted'
        return option


class ProjectDataForm(forms.ModelForm):
    proj_id = forms.ChoiceField(label="Project ID")
    eht_db_fault_rating_ka_preset = forms.ChoiceField(
        label='EHT DB fault rating',
        choices=EHT_DB_FAULT_RATING_PRESET_CHOICES,
        initial='15',
        required=True,
        help_text='Three-phase prospective short-circuit current at the EHT distribution board busbar (kA). Used to estimate source impedance for L-PE fault-loop checks.',
    )
    eht_db_fault_rating_ka_custom = forms.DecimalField(
        label='Other EHT DB fault rating (kA)',
        required=False,
        min_value=Decimal('1'),
        max_digits=6,
        decimal_places=2,
        help_text='Required only when Other is selected. Minimum accepted value is 1 kA.',
    )

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
            'cable_standard',
            'cable_conductor_material',
            'cable_insulation_type',
            'cable_install_method',
            'cable_grouping_derating',
            'min_cold_cable_size_mm2',
            'mcb_curve',
            'rcd_provided',
            'spiral_factor',
            'spiral_wrap_allowed',
            'sr_parallel_run_basis',
            'sr_max_parallel_runs',
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
            'cable_standard': 'Cold cable standard',
            'cable_conductor_material': 'Cold cable conductor material',
            'cable_insulation_type': 'Cold cable insulation type',
            'cable_install_method': 'Cold cable installation method',
            'cable_grouping_derating': 'Cable grouping derating factor',
            'min_cold_cable_size_mm2': 'Minimum cold cable size',
            'mcb_curve': 'MCB characteristic curve',
            'rcd_provided': 'RCD / earth fault protection provided',
            'spiral_factor':'Allowed Spiral Factor',
            'spiral_wrap_allowed':'Installation with spiral wrap',
            'sr_parallel_run_basis': 'SR parallel run basis',
            'sr_max_parallel_runs': 'Max. SR parallel runs',
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
        self.order_fields([
            'proj_id',
            'vendor',
            'startup_t',
            'min_amb_t',
            'max_amb_t',
            'voltage',
            'eht_db_fault_rating_ka_preset',
            'eht_db_fault_rating_ka_custom',
            'max_cb_size',
            'restrict_cb_current',
            'allowablevdrop',
            'cable_standard',
            'cable_conductor_material',
            'cable_insulation_type',
            'cable_install_method',
            'cable_grouping_derating',
            'min_cold_cable_size_mm2',
            'mcb_curve',
            'rcd_provided',
            'spiral_factor',
            'spiral_wrap_allowed',
            'sr_parallel_run_basis',
            'sr_max_parallel_runs',
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
        ])
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
        self.fields['cable_grouping_derating'].widget.attrs.update({
            'min': f'{CABLE_GROUPING_DERATING_MIN:g}',
            'max': f'{CABLE_GROUPING_DERATING_MAX:.1f}',
            'step': '0.001',
        })
        self._set_fault_rating_initials()
        self.fields['sr_parallel_run_basis'].help_text = (
            'Pipe-size guided uses 1/2/3/4 preferred straight runs for <1, <2, <3, and >=3 inch lines.'
        )
        self.fields['sr_max_parallel_runs'].help_text = (
            'Absolute SR straight-run cap for this pass. Values above the pipe-size guidance are flagged for review.'
        )
        self.fields['cable_grouping_derating'].help_text = (
            'User-entered grouping/spacing derating factor. Use 1.0 only when no grouping derating is required.'
        )
        self.fields['cable_standard'].help_text = 'Default basis for LV EHT cold-cable sizing.'
        self.fields['cable_conductor_material'].help_text = 'Used for resistance correction and conductor mass estimate.'
        self.fields['cable_insulation_type'].help_text = 'XLPE uses 90 C and PVC uses 70 C conductor temperature basis.'
        self.fields['cable_install_method'].choices = PROJECT_FORM_INSTALL_METHOD_CHOICES
        self.fields['cable_install_method'].widget = ColdCableInstallMethodSelect(choices=PROJECT_FORM_INSTALL_METHOD_CHOICES)
        self.fields['cable_install_method'].help_text = (
            'Method E is active for this phase. Method D2 direct buried is shown '
            'for planning only and is under development.'
        )
        self.fields['min_cold_cable_size_mm2'].help_text = 'Optional project minimum. Calculated allows the sizing engine to choose freely.'
        self.fields['mcb_curve'].help_text = 'Type C is the default EHT breaker curve for fault-check screening.'
        self.fields['rcd_provided'].help_text = (
            'Enabled by default for EHT circuits. If disabled, the MCB earth-loop check is a hard cold-cable sizing gate.'
        )
        self.fields['sr_parallel_run_basis'].required = False
        self.fields['sr_max_parallel_runs'].required = False
        self.fields['sr_max_parallel_runs'].choices = [(value, str(value)) for value in range(1, 5)]
        self.fields['sr_max_parallel_runs'].widget = forms.Select(choices=self.fields['sr_max_parallel_runs'].choices)
        for name, field in self.fields.items():
            self._apply_bootstrap_widget_classes(name, field)

    def _apply_bootstrap_widget_classes(self, name, field):
        widget = field.widget
        existing_classes = widget.attrs.get('class', '')
        class_tokens = existing_classes.split()

        def ensure_class(value):
            if value not in class_tokens:
                class_tokens.append(value)

        if isinstance(widget, forms.CheckboxInput):
            ensure_class('form-check-input')
        elif isinstance(widget, forms.Select):
            ensure_class('form-select')
        else:
            ensure_class('form-control')

        if name in {'proj_id', 'vendor', 'heat_loss_method', 'sr_parallel_run_basis'}:
            ensure_class('project-hero-field')

        widget.attrs['class'] = ' '.join(token for token in class_tokens if token)

    def clean_sr_parallel_run_basis(self):
        return self.cleaned_data.get('sr_parallel_run_basis') or 'PIPE_SIZE_GUIDED'

    def clean_sr_max_parallel_runs(self):
        return self.cleaned_data.get('sr_max_parallel_runs') or 4

    def clean_cable_install_method(self):
        method = self.cleaned_data.get('cable_install_method') or 'E'
        if method == 'D2':
            raise forms.ValidationError('Method D2 direct buried is under development and cannot be selected yet.')
        return method

    def _set_fault_rating_initials(self):
        if self.is_bound:
            return
        value = getattr(self.instance, 'eht_db_fault_rating_ka', None) or Decimal('15')
        try:
            normalized = Decimal(str(value)).normalize()
        except InvalidOperation:
            normalized = Decimal('15')
        preset_values = {Decimal(choice_value) for choice_value, _label in EHT_DB_FAULT_RATING_PRESET_CHOICES if choice_value != 'OTHER'}
        if normalized in preset_values:
            self.fields['eht_db_fault_rating_ka_preset'].initial = f'{normalized:g}'
            self.fields['eht_db_fault_rating_ka_custom'].initial = None
        else:
            self.fields['eht_db_fault_rating_ka_preset'].initial = 'OTHER'
            self.fields['eht_db_fault_rating_ka_custom'].initial = normalized

    def clean(self):
        cleaned_data = super().clean()
        preset = cleaned_data.get('eht_db_fault_rating_ka_preset') or '15'
        custom = cleaned_data.get('eht_db_fault_rating_ka_custom')
        if preset == 'OTHER':
            if custom is None:
                self.add_error('eht_db_fault_rating_ka_custom', 'Enter an EHT DB fault rating when Other is selected.')
                return cleaned_data
            rating = custom
        else:
            try:
                rating = Decimal(str(preset))
            except InvalidOperation:
                self.add_error('eht_db_fault_rating_ka_preset', 'Select a valid EHT DB fault rating.')
                return cleaned_data
        if rating < Decimal('1'):
            self.add_error('eht_db_fault_rating_ka_custom' if preset == 'OTHER' else 'eht_db_fault_rating_ka_preset', 'EHT DB fault rating must be at least 1 kA.')
        cleaned_data['eht_db_fault_rating_ka'] = rating
        return cleaned_data

    def save(self, commit=True):
        self.instance.eht_db_fault_rating_ka = self.cleaned_data.get('eht_db_fault_rating_ka') or Decimal('15')
        return super().save(commit=commit)
