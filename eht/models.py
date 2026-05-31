from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.timezone import now, timedelta

# from django.contrib.postgres.fields import JSONField  # or use TextField if DB doesn't support native JSON
from django.utils import timezone
from .heat_loss_methods import DEFAULT_HEAT_LOSS_METHOD, HEAT_LOSS_METHOD_CHOICES


# Choices should be an iterable of (value, label) tuples
MAX_CB_SIZE = [(2, 2), (4, 4), (6, 6), (10, 10), (16, 16), (20, 20), (25, 25), (32, 32), (40, 40)]
SELECT_VENDOR = [('THR', 'Thermon'), ('CHR', 'Chromalox'), ('nVN', 'nVent'), ('SST', 'SST'), ('KRZ', 'KRUS-Zapad')]
ALLOW_SPIRAL_WRAP = [(True, 'Allowed'), (False, 'Not Allowed')]
SR_PARALLEL_RUN_BASIS_CHOICES = [
    ('PIPE_SIZE_GUIDED', 'Pipe-size guided'),
    ('FIXED_PROJECT_MAXIMUM', 'Fixed project maximum'),
]
SELECT_RTD_THERMOSTAT = [('RI', 'RTD-Inline'), ('RO', 'RTD-Offline'), ('TI', 'Thermostat-Inline'), ('TO', 'Thermostat-Offline')]
CHOICE_LOCAL_ISOLATOR = [('bothSides', 'Both Sides'), ('outgoingOnly', 'Outgoing Only'), ('incomingOnly', 'Incoming Only'), ('noIsolator', 'No Isolator')]
LOCAL_ISOLATOR_REQUIREMENT = [('required', 'Required'), ('not_required', 'Not Required')]
PHASE_CHOICES = [('1PH', 'Single Phase')]
TEMPERATURE_CLASS_CHOICES = [
    ('', 'Not specified'),
    ('T1', 'T1'),
    ('T2', 'T2'),
    ('T3', 'T3'),
    ('T4', 'T4'),
    ('T5', 'T5'),
    ('T6', 'T6'),
]
GAS_GROUP_CHOICES = [
    ('', 'Not specified'),
    ('IIA', 'IIA'),
    ('IIB', 'IIB'),
    ('IIC', 'IIC'),
]
CABLE_CONDUCTOR_MATERIAL_CHOICES = [('Cu', 'Copper'), ('Al', 'Aluminium')]
CABLE_INSULATION_TYPE_CHOICES = [('XLPE', 'XLPE'), ('PVC', 'PVC')]
CABLE_STANDARD_CHOICES = [
    ('IEC_60502_1', 'IEC 60502-1 (international)'),
    ('BS_5467', 'BS 5467 (UK)'),
]
MCB_CURVE_CHOICES = [
    ('B', 'Type B (3-5x In)'),
    ('C', 'Type C (5-10x In)'),
    ('D', 'Type D (10-20x In)'),
]
MIN_CABLE_SIZE_CHOICES = [
    ('CALCULATED', 'Calculated (no minimum)'),
    ('2.5', '2.5 mm²'),
    ('4', '4 mm²'),
    ('6', '6 mm²'),
    ('10', '10 mm²'),
]
CABLE_INSTALL_METHOD_CHOICES = [
    ('E', 'E - Multi-core on open cable tray or ladder'),
    ('B2', 'B2 - Multi-core in conduit in wall or enclosure'),
    ('C', 'C - Clipped direct to surface'),
    ('D1', 'D1 - In duct in ground, single cable'),
    ('D2', 'D2 - Direct buried in ground'),
]
CABLE_GROUPING_DERATING_MIN = 0.25
CABLE_GROUPING_DERATING_MAX = 1.0
DEFAULT_PROJECT_ID = 'default_project'


def is_default_project_id(proj_id):
    return (proj_id or '').strip().casefold() == DEFAULT_PROJECT_ID.casefold()


class ManagedProject(models.Model):
    proj_id = models.CharField(max_length=20, unique=True, verbose_name='Project ID')
    description = models.CharField(max_length=255, blank=True)
    assigned_users = models.ManyToManyField(User, blank=True, related_name='eht_managed_projects')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['proj_id']

    @classmethod
    def available_to_user(cls, user):
        projects = cls.objects.filter(is_active=True)
        if getattr(user, 'is_authenticated', False) and not (
            getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)
        ):
            return projects.filter(assigned_users=user)
        return projects

    @property
    def display_name(self):
        if self.description:
            return f"{self.proj_id} - {self.description}"
        return self.proj_id

    def __str__(self):
        return self.display_name


class ProjectData(models.Model):
    id = models.BigAutoField(primary_key=True)
    proj_id = models.CharField(max_length=20, unique=True, verbose_name='Project ID')
    min_amb_t = models.DecimalField(max_digits=5, decimal_places=2)
    max_amb_t = models.DecimalField(max_digits=5, decimal_places=2)
    startup_t = models.DecimalField(max_digits=5, decimal_places=2)
    area_class = models.CharField(max_length=20)
    temp_class = models.CharField(max_length=20)
    voltage = models.DecimalField(max_digits=5, decimal_places=2)
    max_cb_size = models.IntegerField(choices=MAX_CB_SIZE, default=10)
    restrict_cb_current = models.DecimalField(max_digits=5, decimal_places=2)
    vendor = models.CharField(max_length=30, choices=SELECT_VENDOR, default='THR')
    spiral_wrap_allowed = models.BooleanField(choices=ALLOW_SPIRAL_WRAP, default=True)
    spiral_factor = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    sr_parallel_run_basis = models.CharField(
        max_length=30,
        choices=SR_PARALLEL_RUN_BASIS_CHOICES,
        default='PIPE_SIZE_GUIDED',
    )
    sr_max_parallel_runs = models.PositiveSmallIntegerField(default=4)
    valve_factor = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    flange_factor = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    support_factor = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    margin_on_tracer_lengths = models.DecimalField(max_digits=5, decimal_places=2)
    voltage_var_factor = models.DecimalField(max_digits=5, decimal_places=2)
    res_tol = models.DecimalField(max_digits=5, decimal_places=2)
    termination_margin = models.DecimalField(max_digits=8, decimal_places=2)
    heat_loss_sf = models.DecimalField(max_digits=5, decimal_places=2)
    heat_loss_method = models.CharField(max_length=40, choices=HEAT_LOSS_METHOD_CHOICES, default=DEFAULT_HEAT_LOSS_METHOD)
    rtd_thrm = models.CharField(max_length=50, choices=SELECT_RTD_THERMOSTAT, default='TI')
    wind_speed = models.DecimalField(max_digits=8, decimal_places=2)
    req_local_isolator = models.CharField(max_length=30, choices=LOCAL_ISOLATOR_REQUIREMENT, default='required')
    caution_label_interval = models.DecimalField(max_digits=5, decimal_places=2)
    k_factor_ccons = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    isolator_location = models.CharField(max_length=20, choices=CHOICE_LOCAL_ISOLATOR, default='noIsolator')
    ckt_ln = models.DecimalField(max_digits=5, decimal_places=2)
    loop_ln = models.DecimalField(max_digits=5, decimal_places=2)
    acc_power_density = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    tracer_temp_factor = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    alpha_for_res = models.DecimalField(max_digits=6, decimal_places=4, default=1)
    allowablevdrop = models.DecimalField(max_digits=5, decimal_places=2)
    cable_standard = models.CharField(max_length=20, choices=CABLE_STANDARD_CHOICES, default='IEC_60502_1')
    cable_conductor_material = models.CharField(max_length=5, choices=CABLE_CONDUCTOR_MATERIAL_CHOICES, default='Cu')
    cable_insulation_type = models.CharField(max_length=10, choices=CABLE_INSULATION_TYPE_CHOICES, default='XLPE')
    cable_install_method = models.CharField(max_length=5, choices=CABLE_INSTALL_METHOD_CHOICES, default='E')
    cable_grouping_derating = models.DecimalField(max_digits=4, decimal_places=3, default=1.0)
    min_cold_cable_size_mm2 = models.CharField(max_length=15, choices=MIN_CABLE_SIZE_CHOICES, default='CALCULATED')
    mcb_curve = models.CharField(max_length=5, choices=MCB_CURVE_CHOICES, default='C')
    gfep_provided = models.BooleanField(default=True)
    udf1 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    udf2 = models.CharField(max_length=30, null=True, blank=True)
    udf3 = models.CharField(max_length=30, null=True, blank=True)    

    def clean(self):
        errors = {}
        if self.min_amb_t is not None and self.max_amb_t is not None and self.min_amb_t > self.max_amb_t:
            errors['min_amb_t'] = 'Minimum ambient temperature cannot exceed maximum ambient temperature.'
        for field in ['voltage', 'spiral_factor', 'caution_label_interval', 'ckt_ln']:
            if getattr(self, field) is not None and getattr(self, field) <= 0:
                errors[field] = 'Value must be greater than zero.'
        for field in ['margin_on_tracer_lengths', 'voltage_var_factor', 'res_tol', 'termination_margin', 'wind_speed', 'loop_ln', 'allowablevdrop']:
            if getattr(self, field) is not None and getattr(self, field) < 0:
                errors[field] = 'Value cannot be negative.'
        if self.restrict_cb_current is not None and not (0 < self.restrict_cb_current <= 100):
            errors['restrict_cb_current'] = 'Circuit breaker loading must be greater than 0 and no more than 100 percent.'
        if self.cable_grouping_derating is not None and not (
            CABLE_GROUPING_DERATING_MIN <= self.cable_grouping_derating <= CABLE_GROUPING_DERATING_MAX
        ):
            errors['cable_grouping_derating'] = (
                f'Cable grouping derating must be between {CABLE_GROUPING_DERATING_MIN:g} '
                f'and {CABLE_GROUPING_DERATING_MAX:g}.'
            )
        if self.sr_max_parallel_runs is not None and not (1 <= self.sr_max_parallel_runs <= 4):
            errors['sr_max_parallel_runs'] = 'SR maximum parallel runs must be between 1 and 4.'
        if self.heat_loss_sf is not None and self.heat_loss_sf < 1:
            errors['heat_loss_sf'] = 'Heat loss safety factor must be at least 1.0.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.proj_id:
            self.proj_id = self.proj_id.strip()
        self.req_local_isolator = 'not_required' if self.isolator_location == 'noIsolator' else 'required'
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.proj_id
    


class HeatTracingInput(models.Model):
    # Core fields
    uid = models.AutoField(primary_key=True)  # Unique ID for each entry
    proj_id = models.CharField(max_length=50, blank=True, null=True)  # Project ID
    is_deleted = models.BooleanField(default=False)  # Logical deletion flag
    line_id = models.CharField(max_length=100)  # pipeline ID
    pid_no = models.CharField(max_length=50, blank=True, null=True)  # Piping & Instrumentation Drawing Number
    area = models.CharField(max_length=10, blank=True, null=True)  # Plant Area
    train = models.CharField(max_length=10, blank=True, null=True)  # Train
    service_type = models.CharField(max_length=20)  # Mandatory field
    line_size = models.DecimalField(max_digits=10, decimal_places=4)  # Pipeline Diameter
    line_length = models.DecimalField(max_digits=10, decimal_places=4)  # Pipeline Length

    xlid = models.PositiveIntegerField(blank=True, null=True)  # user excel input row number

    # Accessories
    valve_qty = models.PositiveIntegerField(default=0, blank=True, null=True)  # Number of valves
    flange_qty = models.PositiveIntegerField(default=0, blank=True, null=True)  # Number of flanges
    support_qty = models.PositiveIntegerField(default=0, blank=True, null=True)  # Number of supports

    # Material and temperature details
    pipe_mat_class = models.CharField(max_length=50, blank=True, null=True)  # Pipe Material Class
    ins_mat_type = models.CharField(max_length=20)  # Insulation Material Type
    insul_thick = models.DecimalField(max_digits=5, decimal_places=2)  # Insulation Thickness
    maint_temp = models.DecimalField(max_digits=5, decimal_places=2)  # Maintenance Temperature
    oper_temp = models.DecimalField(max_digits=5, decimal_places=2)  # Operating Temperature
    design_temp = models.DecimalField(max_digits=5, decimal_places=2)  # Design Temperature

    # Additional fields
    phase = models.CharField(max_length=10, choices=PHASE_CHOICES, default='1PH', blank=True)  # MI MVP is single-phase only.
    emergency_supply = models.BooleanField(default=False)  # Emergency Power Supply Requirement
    discipline = models.CharField(max_length=20, blank=True, null=True)  # Responsible Discipline
    remarks = models.TextField(blank=True, null=True)  # Additional remarks  
    status = models.CharField(                                          # Ststus 'pending' or 'confirmed' depending on user confirmation
        max_length=20,
        choices=[('pending', 'Pending'), ('confirmed', 'Confirmed')],
        default='pending',  # Default to 'pending'
    )

    def __str__(self):
        return f"{self.proj_id} - {self.line_id}"

    class Meta:
        verbose_name = "Heat Tracing Input"
        verbose_name_plural = "Heat Tracing Inputs"
        indexes = [
            models.Index(fields=['proj_id']),
            models.Index(fields=['proj_id', 'status']),
        ]

# This table holds thermal conductivity data for insulation materials
class ElecEHT_ThermalConductivity(models.Model):
    Ins_Mat_Type = models.CharField(max_length=60, null=True)
    K_factor_A = models.FloatField(null=True)
    K_factor_B = models.FloatField(null=True)
    K_factor_C = models.FloatField(null=True)

# This table holds vendor catalogue data
class ElecEHT_Vendor(models.Model):
    V_UID = models.CharField(max_length=50, null=True)
    Vendor = models.CharField(max_length=30, null=True)
    Tracer_Family = models.CharField(max_length=50, null=True)
    Tracer_Model = models.CharField(max_length=50, null=True)
    Tracer_Cat_No = models.CharField(max_length=50, null=True)
    Voltage = models.DecimalField(max_digits=5, decimal_places=1, null=True)
    Zone = models.CharField(max_length=30, null=True)
    Gas_Group = models.CharField(max_length=30, null=True)
    T_Rating = models.CharField(max_length=30, null=True)
    A_Coeff = models.FloatField(null=True)
    B_Coeff = models.FloatField(null=True)
    C_Coeff = models.FloatField(null=True)
    Maint_T = models.DecimalField(max_digits=4, decimal_places=1, null=True)
    Max_Op_T = models.DecimalField(max_digits=4, decimal_places=1, null=True)
    Min_Installation_T = models.DecimalField(max_digits=4, decimal_places=1, null=True)
    Max_Exp_T_On = models.DecimalField(max_digits=4, decimal_places=1, null=True)
    Max_Exp_T_Off = models.DecimalField(max_digits=4, decimal_places=1, null=True)
    Power_at_Startup_T = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    Ohm_per_km = models.DecimalField(max_digits=9, decimal_places=2, null=True)
    Res_corrFactor_Mica = models.DecimalField(max_digits=9, decimal_places=2, null=True)


# This table is used to store the TAGs of all items
class ElecEHT_TagManagement(models.Model):
    UID = models.CharField(max_length=50, null=True)
    TypeofItem = models.CharField(max_length=20, null=True)
    User_Tag = models.CharField(max_length=30, null=True)
    LineUID = models.CharField(max_length=50, null=True)
    From_Item_Tag = models.CharField(max_length=30, null=True)
    To_Item_Tag = models.CharField(max_length=30, null=True)
    Para1 = models.CharField(max_length=30, null=True)
    Para2 = models.CharField(max_length=30, null=True)
    X_Coordinate = models.DecimalField(max_digits=7, decimal_places=3, null=True)
    Y_Coordinate = models.DecimalField(max_digits=7, decimal_places=3, null=True)
    projID = models.CharField(max_length=20, null=True)


# This table is used to convert the nominal pipe size to actual OD
class ElecEHT_ASMEB36(models.Model):
    Nominal_Pipe_Size = models.FloatField(null=True)
    Outside_Diameter = models.FloatField(null=True)
    Wall_Thickness = models.FloatField(null=True)
    Plain_End_Weight = models.FloatField(null=True)
    Schedule_No = models.CharField(max_length=10, null=True)
    Nominal_Diameter = models.FloatField(null=True)
    Outside_Diameter_mm = models.FloatField(null=True)
    Wall_Thickness_mm = models.FloatField(null=True)
    Plain_end_Mass = models.FloatField(null=True)


# Track user login attempts
class UserAttempt(models.Model):
   user = models.ForeignKey(User, on_delete=models.CASCADE)
   ip_address = models.GenericIPAddressField(null=True, blank=True)
   failed_at = models.DateTimeField(auto_now_add=True)
   lockout = models.BooleanField(default=False)
   cooldown_expires = models.DateTimeField(null=True, blank=True)
   def is_locked(self):
       if self.lockout and self.cooldown_expires and self.cooldown_expires > now():
           return True
       return False
   
#########################################################################
# TODO: ADD project_id to stored it with all the below tables 

# STORE Calculated results in thebelow models
# heat_loss
# selected_tracers
# alternative_tracers
# power_distribution
# boq_per_line
# consolidated_boq
# tracer_power_param

class HeatLoss(models.Model):
    uid = models.CharField(max_length=100, primary_key=True)
    line = models.OneToOneField(HeatTracingInput, on_delete=models.CASCADE, null=True, blank=True, related_name='heat_loss_result')
    heat_loss = models.FloatField()
    base_heat_loss = models.FloatField(default=0)
    design_heat_loss = models.FloatField(default=0)
    heat_loss_sf = models.FloatField(default=1)
    pipe_size_mm = models.FloatField(default=0)
    conductivity = models.FloatField(default=0)
    conductivity_basis = models.JSONField(default=dict, blank=True)
    wind_correction = models.FloatField(default=1)
    accessory_adders = models.JSONField(default=dict, blank=True)
    selection_status = models.CharField(max_length=30, default='', blank=True)
    selection_rejection_reasons = models.JSONField(default=list, blank=True)
    tracer_adder = models.FloatField()

    class Meta:
        ordering = ['line']

class SelectedTracer(models.Model):
    line = models.OneToOneField(HeatTracingInput, on_delete=models.CASCADE, null=True, blank=True, related_name='selected_tracer_result')
    v_uid = models.CharField(max_length=100)
    a_coeff = models.FloatField()
    b_coeff = models.FloatField()
    c_coeff = models.FloatField()
    power_at_startup_t = models.FloatField()
    ohm_per_km = models.FloatField()
    res_corrFactor_mica = models.FloatField()
    tracer_family = models.CharField(max_length=50)
    voltage_float = models.FloatField()
    voltage_correction_factor = models.FloatField()
    power_output = models.FloatField()
    spiral_factor = models.FloatField()
    sr_parallel_run_count = models.PositiveSmallIntegerField(default=1)
    sr_parallel_run_basis = models.CharField(max_length=50, default='', blank=True)
    sr_constructability_warning = models.CharField(max_length=255, default='', blank=True)
    sr_per_run_tracer_length = models.FloatField(default=0)
    tracer_length = models.FloatField()
    tracer_with_margin = models.FloatField()

    class Meta:
        ordering = ['line']

class AlternateTracer(models.Model):
    line = models.ForeignKey(HeatTracingInput, on_delete=models.CASCADE, null=True, blank=True, related_name='alternate_tracer_results')
    option_rank = models.PositiveIntegerField(default=0)
    v_uid = models.CharField(max_length=100)
    a_coeff = models.FloatField()
    b_coeff = models.FloatField()
    c_coeff = models.FloatField()
    power_at_startup_t = models.FloatField()
    ohm_per_km = models.FloatField()
    res_corrFactor_mica = models.FloatField()
    tracer_family = models.CharField(max_length=50)
    voltage_float = models.FloatField()
    voltage_correction_factor = models.FloatField()
    power_output = models.FloatField()
    spiral_factor = models.FloatField()
    sr_parallel_run_count = models.PositiveSmallIntegerField(default=1)
    sr_parallel_run_basis = models.CharField(max_length=50, default='', blank=True)
    sr_constructability_warning = models.CharField(max_length=255, default='', blank=True)
    sr_per_run_tracer_length = models.FloatField(default=0)
    tracer_length = models.FloatField()
    tracer_with_margin = models.FloatField()

    class Meta:
        ordering = ['line', 'option_rank']
        constraints = [
            models.UniqueConstraint(fields=['line', 'option_rank'], name='unique_alternate_tracer_rank_per_line'),
        ]

class PowerDistribution(models.Model):
    uid = models.CharField(max_length=100, primary_key=True)
    line = models.OneToOneField(HeatTracingInput, on_delete=models.CASCADE, null=True, blank=True, related_name='power_distribution_result')
    total_circuits = models.IntegerField()

    class Meta:
        ordering = ['line']
    
class PowerDistributionBranch(models.Model):
    distribution = models.ForeignKey(PowerDistribution, related_name='branches', on_delete=models.CASCADE)
    branch_index = models.PositiveIntegerField(default=0)
    branch_type = models.CharField(max_length=50)
    circuit_count = models.IntegerField()
    connected_to = models.CharField(max_length=100)
    cable_length_db_to_jb = models.FloatField()
    cable_length_jb_to_jb = models.FloatField(null=True, blank=True)
    tagged_components = models.JSONField(default=dict)

    class Meta:
        ordering = ['distribution', 'branch_index']
        constraints = [
            models.UniqueConstraint(fields=['distribution', 'branch_index'], name='unique_branch_index_per_distribution'),
        ]


class CableScheduleOverride(models.Model):
    project = models.ForeignKey(
        ProjectData,
        to_field='proj_id',
        db_column='project_id',
        on_delete=models.CASCADE,
        related_name='cable_schedule_overrides',
    )
    component_id = models.CharField(max_length=255)
    component_uid = models.CharField(max_length=32, blank=True, default='')
    display_tag = models.CharField(max_length=100)
    component_type = models.CharField(max_length=50)
    line_id = models.CharField(max_length=100, blank=True, default='')
    line_uid = models.CharField(max_length=100, blank=True, default='')
    branch_index = models.PositiveIntegerField(default=0)
    circuit_index = models.PositiveIntegerField(null=True, blank=True)
    generated_length_m = models.FloatField(null=True, blank=True)
    manual_length_m = models.FloatField(null=True, blank=True)
    generated_cable_size = models.CharField(max_length=50, blank=True, default='')
    manual_cable_size = models.CharField(max_length=50, blank=True, default='')
    remarks = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='created_cable_overrides')
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='updated_cable_overrides')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['project', 'line_id', 'branch_index', 'display_tag']
        constraints = [
            models.UniqueConstraint(fields=['project', 'component_id'], name='unique_cable_override_component_per_project'),
        ]
        indexes = [
            models.Index(fields=['project', 'line_id']),
            models.Index(fields=['component_uid']),
            models.Index(fields=['display_tag']),
            models.Index(fields=['is_active']),
        ]


class ColdCableCatalogue(models.Model):
    """Validated LV cold-cable catalogue row used by the cold cable module."""
    CORE_COUNT_CHOICES = [(2, '2C'), (3, '3C'), (4, '4C')]

    vendor = models.CharField(max_length=60, blank=True, default='')
    cable_standard = models.CharField(max_length=20, choices=CABLE_STANDARD_CHOICES)
    catalogue_ref = models.CharField(max_length=100, blank=True, default='')
    cable_type_code = models.CharField(max_length=50)
    voltage_grade = models.CharField(max_length=20, default='0.6/1kV')
    conductor_material = models.CharField(max_length=5, choices=CABLE_CONDUCTOR_MATERIAL_CHOICES)
    insulation_type = models.CharField(max_length=10, choices=CABLE_INSULATION_TYPE_CHOICES)
    core_count = models.IntegerField(choices=CORE_COUNT_CHOICES)
    conductor_size_mm2 = models.FloatField()
    installation_method = models.CharField(max_length=5, choices=CABLE_INSTALL_METHOD_CHOICES)
    ampacity_a = models.FloatField()
    ampacity_temp_ref_c = models.FloatField(default=30.0)
    max_conductor_temp_c = models.FloatField(default=90.0)
    resistance_mohm_per_m = models.FloatField()
    reactance_mohm_per_m = models.FloatField(default=0.08)
    source_document = models.CharField(max_length=200, blank=True, default='')
    source_date = models.DateField(null=True, blank=True)
    is_validated = models.BooleanField(default=False)

    class Meta:
        ordering = ['conductor_material', 'insulation_type', 'core_count', 'conductor_size_mm2']
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'cable_standard',
                    'conductor_material',
                    'insulation_type',
                    'core_count',
                    'conductor_size_mm2',
                    'installation_method',
                ],
                name='unique_cold_cable_catalogue_row',
            ),
        ]
        indexes = [
            models.Index(fields=['conductor_material', 'insulation_type', 'core_count', 'installation_method']),
            models.Index(fields=['is_validated']),
        ]

    def __str__(self):
        return f"{self.cable_type_code} {self.core_count}C x {self.conductor_size_mm2:g} mm²"


class TracerSelectionOverride(models.Model):
    project = models.ForeignKey(
        ProjectData,
        to_field='proj_id',
        db_column='project_id',
        on_delete=models.CASCADE,
        related_name='tracer_selection_overrides',
    )
    line = models.ForeignKey(
        HeatTracingInput,
        on_delete=models.CASCADE,
        related_name='tracer_selection_overrides',
    )
    selected_v_uid = models.CharField(max_length=100)
    selected_option_rank = models.PositiveIntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='created_tracer_overrides')
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='updated_tracer_overrides')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['project', 'line__line_id']
        constraints = [
            models.UniqueConstraint(fields=['project', 'line'], name='unique_tracer_override_line_per_project'),
        ]
        indexes = [
            models.Index(fields=['project', 'line']),
            models.Index(fields=['selected_v_uid']),
            models.Index(fields=['is_active']),
        ]


class SLDNodeLayout(models.Model):
    project = models.ForeignKey(
        ProjectData,
        to_field='proj_id',
        db_column='project_id',
        on_delete=models.CASCADE,
        related_name='sld_node_layouts',
    )
    component_id = models.CharField(max_length=255)
    component_uid = models.CharField(max_length=32, blank=True, default='')
    display_tag = models.CharField(max_length=100, blank=True, default='')
    component_type = models.CharField(max_length=50)
    line_id = models.CharField(max_length=100, blank=True, default='')
    line_uid = models.CharField(max_length=100, blank=True, default='')
    branch_index = models.PositiveIntegerField(default=0)
    circuit_index = models.PositiveIntegerField(null=True, blank=True)
    x_position = models.FloatField()
    y_position = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['project', 'line_id', 'branch_index', 'component_type', 'display_tag']
        constraints = [
            models.UniqueConstraint(fields=['project', 'component_id'], name='unique_sld_layout_component_per_project'),
        ]
        indexes = [
            models.Index(fields=['project', 'line_id']),
            models.Index(fields=['project', 'branch_index']),
            models.Index(fields=['component_uid']),
        ]


class SLDTopologyEdit(models.Model):
    EDIT_TYPES = [
        ('combine_feeders', 'Combine Feeders'),
        ('split_circuits', 'Split Circuits'),
        ('downstream_jb', 'Downstream 3PH JB'),
        ('attach_to_jb', 'Attach Feeder to 3PH JB'),
        ('move_branch_to_jb', 'Move Branch to 3PH JB'),
    ]
    STATUSES = [
        ('draft', 'Draft'),
        ('applied', 'Applied'),
        ('superseded', 'Superseded'),
        ('reset', 'Reset'),
        ('needs_review', 'Needs Review'),
    ]

    project = models.ForeignKey(
        ProjectData,
        to_field='proj_id',
        db_column='project_id',
        on_delete=models.CASCADE,
        related_name='sld_topology_edits',
    )
    edit_type = models.CharField(max_length=30, choices=EDIT_TYPES)
    status = models.CharField(max_length=20, choices=STATUSES, default='draft')
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sld_topology_edits',
    )
    remarks = models.TextField(blank=True, default='')
    baseline_fingerprint = models.CharField(max_length=64, blank=True, default='')
    generated_snapshot = models.JSONField(default=dict, blank=True)
    edit_payload = models.JSONField(default=dict, blank=True)
    validation_summary = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['project', 'edit_type']),
            models.Index(fields=['baseline_fingerprint']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['project'],
                condition=models.Q(status='applied'),
                name='unique_active_sld_topology_edit_per_project',
            ),
        ]

    def __str__(self):
        return f"{self.project_id} {self.edit_type} {self.status}"


class BOQ(models.Model):
    uid = models.CharField(max_length=100, blank=True, default='')
    project = models.ForeignKey(ProjectData, to_field='proj_id', db_column='project_id', on_delete=models.CASCADE, related_name='boq_items', null=True, blank=True)
    line = models.ForeignKey(HeatTracingInput, null=True, blank=True, on_delete=models.CASCADE, related_name='boq_items')
    scope = models.CharField(max_length=20, choices=[('line', 'Line'), ('consolidated', 'Consolidated')], default='line')
    item_code = models.CharField(max_length=100, blank=True, default='')
    item_description = models.CharField(max_length=255, blank=True)
    quantity = models.FloatField()
    unit = models.CharField(max_length=50, blank=True, default='EA')
    cost = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ['scope', 'line', 'item_code']
        indexes = [
            models.Index(fields=['project', 'scope']),
            models.Index(fields=['line', 'scope']),
            models.Index(fields=['item_code']),
        ]

class ProcessLineCalculation(models.Model):
    uid = models.CharField(max_length=100, primary_key=True)
    line = models.OneToOneField(HeatTracingInput, on_delete=models.CASCADE, null=True, blank=True, related_name='process_line_calculation')
    line_size = models.FloatField()
    line_length = models.FloatField()
    operating_temp = models.FloatField()
    heat_loss = models.FloatField()
    selected_tracer = models.CharField(max_length=100)  # Store Tracer Name
    breaker_size = models.FloatField(default=0)
    total_circuits = models.IntegerField(default=0)
    starting_current = models.FloatField()
    operating_current = models.FloatField()
    total_power_consumption = models.FloatField()
    total_tracer_length = models.FloatField(default=0)
    pipe_size_mm = models.FloatField(default=0)
    spiral_factor = models.FloatField()
    sr_parallel_run_count = models.PositiveSmallIntegerField(default=1)
    sr_parallel_run_basis = models.CharField(max_length=50, default='', blank=True)
    sr_constructability_warning = models.CharField(max_length=255, default='', blank=True)
    remarks = models.TextField(null=True, blank=True)  # Placeholder for future

    class Meta:
        ordering = ['line']


class ColdCableResult(models.Model):
    SIZING_STATUS_CHOICES = [
        ('selected', 'Selected'),
        ('review_required', 'Review Required'),
        ('unsizeable', 'Unsizeable - no feasible cable found'),
        ('length_missing', 'Length Basis Missing'),
    ]
    VD_STATUS_CHOICES = [
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('review_required', 'Review Required'),
        ('not_calculated', 'Not Calculated'),
    ]
    FAULT_STATUS_CHOICES = [
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('review_required', 'Review Required'),
        ('not_calculated', 'Not Calculated'),
    ]

    project = models.ForeignKey(
        ProjectData,
        to_field='proj_id',
        db_column='project_id',
        on_delete=models.CASCADE,
        related_name='cold_cable_results',
    )
    distribution = models.ForeignKey(PowerDistribution, on_delete=models.CASCADE, related_name='cold_cable_results')
    branch = models.ForeignKey(PowerDistributionBranch, on_delete=models.CASCADE, related_name='cold_cable_results', null=True, blank=True)
    branch_index = models.PositiveIntegerField()
    line_id = models.CharField(max_length=100)
    line_uid = models.CharField(max_length=100)
    heating_cable_type = models.CharField(max_length=10, default='SR')

    per_circuit_operating_current_a = models.FloatField(default=0.0)
    line_operating_current_a = models.FloatField(default=0.0)
    breaker_size_a = models.FloatField(default=0.0)
    circuit_count = models.IntegerField(default=0)
    mcb_curve = models.CharField(max_length=5, choices=MCB_CURVE_CHOICES, default='C')
    gfep_provided = models.BooleanField(default=True)

    length_4c_m = models.FloatField(null=True, blank=True)
    length_3c_m = models.FloatField(null=True, blank=True)
    length_basis = models.CharField(max_length=30, default='project_default')

    site_ambient_temp_c = models.FloatField(default=0.0)
    catalogue_temp_ref_c = models.FloatField(default=30.0)
    k_temp = models.FloatField(null=True, blank=True)
    k_group = models.FloatField(default=1.0)
    k_total = models.FloatField(null=True, blank=True)
    install_method = models.CharField(max_length=5, choices=CABLE_INSTALL_METHOD_CHOICES, default='E')

    cable_4c_size_mm2 = models.FloatField(null=True, blank=True)
    cable_4c_catalogue = models.ForeignKey(ColdCableCatalogue, null=True, blank=True, on_delete=models.SET_NULL, related_name='results_4c')
    cable_4c_ampacity_derated_a = models.FloatField(null=True, blank=True)
    cable_4c_ampacity_margin_pct = models.FloatField(null=True, blank=True)
    cable_4c_conductor_temp_c = models.FloatField(null=True, blank=True)
    cable_4c_conductor_mass_mt = models.FloatField(null=True, blank=True)
    cable_4c_vd_v = models.FloatField(null=True, blank=True)
    cable_4c_vd_pct = models.FloatField(null=True, blank=True)

    cable_3c_size_mm2 = models.FloatField(null=True, blank=True)
    cable_3c_catalogue = models.ForeignKey(ColdCableCatalogue, null=True, blank=True, on_delete=models.SET_NULL, related_name='results_3c')
    cable_3c_ampacity_derated_a = models.FloatField(null=True, blank=True)
    cable_3c_ampacity_margin_pct = models.FloatField(null=True, blank=True)
    cable_3c_conductor_temp_c = models.FloatField(null=True, blank=True)
    cable_3c_conductor_mass_mt = models.FloatField(null=True, blank=True)
    cable_3c_vd_v = models.FloatField(null=True, blank=True)
    cable_3c_vd_pct = models.FloatField(null=True, blank=True)

    vd_total_pct = models.FloatField(null=True, blank=True)
    vd_allowable_pct = models.FloatField(default=0.0)
    vd_status = models.CharField(max_length=20, choices=VD_STATUS_CHOICES, default='not_calculated')
    load_end_voltage_v = models.FloatField(null=True, blank=True)

    optimization_run = models.BooleanField(default=False)
    conductor_volume_proxy = models.FloatField(null=True, blank=True)
    conductor_material_density_kg_m3 = models.FloatField(null=True, blank=True)
    conductor_mass_total_mt = models.FloatField(null=True, blank=True)

    fault_current_4c_phase_to_phase_a = models.FloatField(null=True, blank=True)
    fault_protection_4c_status = models.CharField(max_length=20, choices=FAULT_STATUS_CHOICES, default='not_calculated')
    fault_current_3c_line_to_neutral_a = models.FloatField(null=True, blank=True)
    fault_protection_3c_status = models.CharField(max_length=20, choices=FAULT_STATUS_CHOICES, default='not_calculated')

    sizing_status = models.CharField(max_length=20, choices=SIZING_STATUS_CHOICES)
    review_notes = models.JSONField(default=list, blank=True)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['project', 'line_id', 'branch_index']
        constraints = [
            models.UniqueConstraint(fields=['distribution', 'branch_index'], name='unique_cold_cable_result_per_branch'),
        ]
        indexes = [
            models.Index(fields=['project', 'sizing_status']),
            models.Index(fields=['line_id', 'branch_index']),
        ]

# ------ STORE CALCULATED DATA -------------------------------------------------------




# ------ MI CABLE MODELS -----------------------------------------------------------

class MICableFamily(models.Model):
    """Catalogue-level MI product family limits.

    MI data is safety-sensitive. `is_validated` stays false until the row has
    been checked against a real vendor document recorded in `source_document`.
    """
    vendor = models.CharField(max_length=30, choices=SELECT_VENDOR)
    family_name = models.CharField(max_length=50) # e.g., 'MIQ', 'XMI-A'
    alloy_type = models.CharField(max_length=50) # e.g., 'Alloy 825', 'Stainless Steel'
    max_voltage = models.FloatField(default=600.0)
    max_sheath_temp_c = models.FloatField() # e.g., 600.0
    max_maintain_temp_c = models.FloatField() # e.g., 500.0
    max_exposure_temp_c = models.FloatField(default=0.0) # Used to reject line design temperatures above vendor limits.
    max_watt_density_w_m = models.FloatField() # e.g., 250.0 W/m limit
    min_circuit_length_m = models.FloatField(default=0.0)
    max_circuit_length_m = models.FloatField(default=0.0)
    temp_class_rating = models.CharField(max_length=10, choices=TEMPERATURE_CLASS_CHOICES, blank=True, default='')
    gas_group = models.CharField(max_length=10, choices=GAS_GROUP_CHOICES, blank=True, default='')
    zone_approval = models.CharField(max_length=60, blank=True, default='')
    source_document = models.CharField(max_length=200, blank=True, default='')
    is_validated = models.BooleanField(default=False)

    class Meta:
        unique_together = ('vendor', 'family_name')
        verbose_name_plural = "MI Cable Families"

    def __str__(self):
        return f"{self.get_vendor_display()} {self.family_name}"

class MICableHeater(models.Model):
    """Specific MI heater resistance code within a family."""
    family = models.ForeignKey(MICableFamily, on_delete=models.CASCADE, related_name='heaters')
    part_number = models.CharField(max_length=100, unique=True) # e.g., '61XMI2100' or 'MIQ-2500'
    conductors = models.IntegerField(default=1) # 1 for Single Core, 2 for Dual Core
    resistance_ohms_m = models.FloatField() # Ohms per metre at catalogue reference temperature, usually 20°C.
    tcr_per_degree_c = models.FloatField(null=True, blank=True, default=None) # Linear resistance coefficient per °C, keyed to conductor alloy.
    max_current_a = models.FloatField() # Catalogue maximum heater current.
    cold_lead_resistance_ohms_m = models.FloatField(default=0.0)
    cold_lead_max_ampacity_a = models.FloatField(default=0.0)
    sheath_material = models.CharField(max_length=50, blank=True, default='')
    conductor_material = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        ordering = ['resistance_ohms_m']

    def __str__(self):
        return f"{self.part_number} ({self.resistance_ohms_m} ohms/m)"


class MIColdLeadOption(models.Model):
    """Selectable MI cold-lead length tied to a heater resistance code."""
    heater = models.ForeignKey(MICableHeater, on_delete=models.CASCADE, related_name='cold_lead_options')
    option_code = models.CharField(max_length=20)
    length_m = models.FloatField()

    class Meta:
        ordering = ['heater', 'length_m', 'option_code']
        constraints = [
            models.UniqueConstraint(fields=['heater', 'option_code'], name='unique_mi_cold_lead_option_per_heater'),
        ]

    def __str__(self):
        return f"{self.heater.part_number} {self.option_code} ({self.length_m} m)"

class MIAlloyTempFactor(models.Model):
    alloy_type = models.CharField(max_length=50)
    temperature_c = models.FloatField()
    resistance_multiplier = models.FloatField() # e.g., 1.04 at 200°C

    class Meta:
        unique_together = ('alloy_type', 'temperature_c')
        ordering = ['alloy_type', 'temperature_c']

    def __str__(self):
        return f"{self.alloy_type} at {self.temperature_c}°C: {self.resistance_multiplier}x"


class SelectedMIHeater(models.Model):
    """Persisted MI selection snapshot for one process line.

    The result stores both catalogue references and calculated snapshot values
    so reports remain traceable even if catalogue rows are later revised. Rejected
    MI selections also use this table, with blank catalogue references and the
    reason payload kept beside the line for review.
    """
    T_CLASS_VERDICTS = [
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('review', 'Review Required'),
    ]

    line = models.OneToOneField(
        HeatTracingInput,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='selected_mi_heater_result',
    )
    heater = models.ForeignKey(MICableHeater, on_delete=models.SET_NULL, null=True, blank=True)
    cold_lead_option = models.ForeignKey(MIColdLeadOption, on_delete=models.SET_NULL, null=True, blank=True)
    selection_status = models.CharField(max_length=30, default='', blank=True)
    selection_rejection_reasons = models.JSONField(default=list, blank=True)

    heated_length_m = models.FloatField(default=0.0)
    cold_lead_option_code = models.CharField(max_length=20, blank=True, default='')
    cold_lead_length_m = models.FloatField(default=0.0)

    heater_resistance_ohms = models.FloatField(default=0.0)
    cold_lead_resistance_total_ohms = models.FloatField(default=0.0)
    power_nominal_w = models.FloatField(default=0.0)
    power_density_w_m = models.FloatField(default=0.0)
    current_nominal_a = models.FloatField(default=0.0)
    current_cold_start_a = models.FloatField(default=0.0)

    max_sheath_temp_published_c = models.FloatField(null=True, blank=True)
    project_t_class_limit_c = models.FloatField(default=0.0)
    t_class_verdict = models.CharField(max_length=20, choices=T_CLASS_VERDICTS, default='review')
    selection_basis = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['line']


# ######################### OLD Models for reference #####################################


'''
# This table holds all EHT system design calculation
class ElecEHT_CalculatedTable(models.Model):
    UID = models.CharField(max_length=50, null=True)
    Heat_Loss = models.DecimalField(max_digits=7, decimal_places=3, null=True)
    Tracer_Power_Output = models.DecimalField(max_digits=4, decimal_places=2, null=True)
    User_Tracer_Cat_UID = models.CharField(max_length=50, null=True)
    Auto_Tracer_Cat_UID = models.CharField(max_length=50, null=True)
    Tracer_Length = models.DecimalField(max_digits=7, decimal_places=3, null=True)
    Spiral_Factor = models.DecimalField(max_digits=4, decimal_places=2, null=True)
    DB_No = models.CharField(max_length=20, null=True)
    CKT_No = models.TextField(null=True)
    Breaker_Size = models.IntegerField(null=True)
    Operating_Current = models.DecimalField(max_digits=7, decimal_places=3, null=True)
    Maximum_Current = models.DecimalField(max_digits=7, decimal_places=3, null=True)
    Operating_Load = models.DecimalField(max_digits=7, decimal_places=3, null=True)
    Optional_Tracer = models.TextField(null=True)
    Total_Tracer_Length = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    Last_Design = models.CharField(max_length=7, null=True)
    No_of_Ckt = models.IntegerField(null=True)
    Isolator = models.IntegerField(null=True)
    JB_3PH = models.IntegerField(null=True)
    JB_1PH = models.IntegerField(null=True)
    Splice_Connection_Box = models.IntegerField(null=True)
    Tee_Connection_Box = models.IntegerField(null=True)
    End_Connection_Box = models.IntegerField(null=True, blank=True)
    RTD = models.IntegerField(null=True, blank=True)
    Thermostat = models.IntegerField(null=True, blank=True)
    Caution_Label = models.IntegerField(null=True, blank=True)
    Aluminium_Adhesive_Tape = models.DecimalField(max_digits=9, decimal_places=3, null=True)
    Others = models.TextField(null=True)
    Pipe_Strap = models.IntegerField(null=True)
    No_of_Segment = models.IntegerField(null=True)
    IsMIQ = models.BooleanField(null=True, default=False)
    IsSeries = models.BooleanField(null=True, default=False)

# This table holds clean Input & output parameters
class ElecEHT_IO(models.Model):
    UID = models.CharField(max_length=50, unique=True)
    XLID = models.CharField(max_length=10, null=True)
    ISDeleted = models.BooleanField(default=False)
    Line_ID = models.CharField(max_length=100)
    PID_No = models.CharField(max_length=100)
    Area = models.CharField(max_length=50, null=True)
    Train = models.CharField(max_length=50, null=True)
    Service_Type = models.CharField(max_length=20)
    Line_Size = models.DecimalField(max_digits=7, decimal_places=3)
    Line_Length = models.DecimalField(max_digits=7, decimal_places=3)
    Valve_Qty = models.DecimalField(max_digits=7, decimal_places=3, null=True)
    Flange_Qty = models.DecimalField(max_digits=7, decimal_places=3, null=True)
    Support_Qty = models.DecimalField(max_digits=7, decimal_places=3, null=True)
    Pipe_Mat_Class = models.CharField(max_length=20, null=True)
    Ins_Mat_Type = models.CharField(max_length=20)
    Insul_Thick = models.DecimalField(max_digits=7, decimal_places=3)
    Maint_T = models.DecimalField(max_digits=4, decimal_places=1)
    Oper_T = models.DecimalField(max_digits=4, decimal_places=1)
    Design_T = models.DecimalField(max_digits=4, decimal_places=1)
    Emergency_Supply = models.BooleanField(null=True)
    Discipline = models.CharField(max_length=20, null=True)
    Remarks = models.CharField(max_length=200, null=True)
    Repeat_Seq = models.CharField(max_length=20, null=True)
    Heat_Loss = models.DecimalField(max_digits=7, decimal_places=3, null=True)
    Tracer_Power_Output = models.DecimalField(max_digits=7, decimal_places=2, null=True)
    User_Tracer_Cat_UID = models.CharField(max_length=50, null=True)
    Auto_Tracer_Cat_UID = models.CharField(max_length=50, null=True)
    Tracer_Length = models.DecimalField(max_digits=8, decimal_places=3, null=True)
    Spiral_Factor = models.DecimalField(max_digits=4, decimal_places=2, null=True)
    DB_No = models.CharField(max_length=20, null=True)
    CKT_No = models.TextField(null=True)
    Breaker_Size = models.IntegerField(null=True)
    Operating_Current = models.DecimalField(max_digits=7, decimal_places=3, null=True)
    Maximum_Current = models.DecimalField(max_digits=7, decimal_places=3, null=True)
    Operating_Load = models.DecimalField(max_digits=9, decimal_places=3, null=True)
    Optional_Tracer = models.TextField(null=True)
    Total_Tracer_Length = models.DecimalField(max_digits=8, decimal_places=3, null=True)
    Last_Design = models.CharField(max_length=7, null=True)
    No_of_Ckt = models.IntegerField(null=True)
    Isolator = models.IntegerField(null=True)
    JB_3PH = models.IntegerField(null=True)
    JB_1PH = models.IntegerField(null=True)
    Splice_Connection_Box = models.IntegerField(null=True)
    Tee_Connection_Box = models.IntegerField(null=True)
    End_Connection_Box = models.IntegerField(null=True)
    RTD = models.IntegerField(null=True)
    Thermostat = models.IntegerField(null=True)
    Caution_Label = models.IntegerField(null=True)
    Aluminium_Adhesive_Tape = models.DecimalField(max_digits=9, decimal_places=3, null=True)
    Others = models.TextField(null=True)
    Pipe_Strap = models.IntegerField(null=True)
    No_of_Segment = models.IntegerField(null=True)
    IsMIQ = models.BooleanField(null=True)
    IsSeries = models.BooleanField(null=True)
    projID = models.CharField(max_length=50, null=True)

'''
