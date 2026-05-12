from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.timezone import now, timedelta

# from django.contrib.postgres.fields import JSONField  # or use TextField if DB doesn't support native JSON
from django.utils import timezone


# Choices should be an iterable of (value, label) tuples
MAX_CB_SIZE = [(2, 2), (4, 4), (6, 6), (10, 10), (16, 16), (20, 20), (25, 25), (32, 32), (40, 40)]
SELECT_VENDOR = [('THR', 'Thermon'), ('CHR', 'Chromalox'), ('nVN', 'nVent'), ('SST', 'SST'), ('KRZ', 'KRUS-Zapad')]
ALLOW_SPIRAL_WRAP = [(True, 'Allowed'), (False, 'Not Allowed')]
SELECT_RTD_THERMOSTAT = [('RI', 'RTD-Inline'), ('RO', 'RTD-Offline'), ('TI', 'Thermostat-Inline'), ('TO', 'Thermostat-Offline')]
CHOICE_LOCAL_ISOLATOR = [('bothSides', 'Both Sides'), ('outgoingOnly', 'Outgoing Only'), ('incomingOnly', 'Incoming Only'), ('noIsolator', 'No Isolator')]
LOCAL_ISOLATOR_REQUIREMENT = [('required', 'Required'), ('not_required', 'Not Required')]
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
    spiral_factor = models.DecimalField(max_digits=5, decimal_places=2)
    valve_factor = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    flange_factor = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    support_factor = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    margin_on_tracer_lengths = models.DecimalField(max_digits=5, decimal_places=2)
    voltage_var_factor = models.DecimalField(max_digits=5, decimal_places=2)
    res_tol = models.DecimalField(max_digits=5, decimal_places=2)
    termination_margin = models.DecimalField(max_digits=8, decimal_places=2)
    heat_loss_sf = models.DecimalField(max_digits=5, decimal_places=2)
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
    wind_correction = models.FloatField(default=1)
    accessory_adders = models.JSONField(default=dict, blank=True)
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
    remarks = models.TextField(null=True, blank=True)  # Placeholder for future

    class Meta:
        ordering = ['line']

# ------ STORE CALCULATED DATA -------------------------------------------------------




# ------ MI CABLE MODELS -----------------------------------------------------------

class MICableFamily(models.Model):
    vendor = models.CharField(max_length=30, choices=SELECT_VENDOR)
    family_name = models.CharField(max_length=50) # e.g., 'MIQ', 'XMI-A'
    alloy_type = models.CharField(max_length=50) # e.g., 'Alloy 825', 'Stainless Steel'
    max_voltage = models.FloatField(default=600.0)
    max_sheath_temp_c = models.FloatField() # e.g., 600.0
    max_maintain_temp_c = models.FloatField() # e.g., 500.0
    max_watt_density_w_m = models.FloatField() # e.g., 250.0 W/m limit

    class Meta:
        unique_together = ('vendor', 'family_name')
        verbose_name_plural = "MI Cable Families"

    def __str__(self):
        return f"{self.get_vendor_display()} {self.family_name}"

class MICableHeater(models.Model):
    family = models.ForeignKey(MICableFamily, on_delete=models.CASCADE, related_name='heaters')
    part_number = models.CharField(max_length=100, unique=True) # e.g., '61XMI2100' or 'MIQ-2500'
    conductors = models.IntegerField(default=1) # 1 for Single Core, 2 for Dual Core
    base_resistance_ohms_km = models.FloatField() # Ohms per km at 20°C
    max_ampacity = models.FloatField() # e.g., 60A

    class Meta:
        ordering = ['base_resistance_ohms_km']

    def __str__(self):
        return f"{self.part_number} ({self.base_resistance_ohms_km} ohms/km)"

class MIAlloyTempFactor(models.Model):
    alloy_type = models.CharField(max_length=50)
    temperature_c = models.FloatField()
    resistance_multiplier = models.FloatField() # e.g., 1.04 at 200°C

    class Meta:
        unique_together = ('alloy_type', 'temperature_c')
        ordering = ['alloy_type', 'temperature_c']

    def __str__(self):
        return f"{self.alloy_type} at {self.temperature_c}°C: {self.resistance_multiplier}x"


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
