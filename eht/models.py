from django.db import models, IntegrityError
from django.contrib.auth.models import User
from django.utils.timezone import now, timedelta


# Choices should be an iterable of (value, label) tuples
SELECT_PROJECT_ID = [('p1', 'P001'), ('p2', 'P002')]
MAX_CB_SIZE = [(10, 10), (16, 16), (20, 20), (25, 25),(32, 32), (40, 40)]
SELECT_VENDOR = [('THR', 'Thermon'), ('CHR', 'Chromalox'), ('nVN', 'nVent'), ('SST', 'SST'), ('KRZ', 'KRUS-Zapad')]
ALLOW_SPIRAL_WRAP = [(True, 'Allowed'), (False, 'Not Allowed')]
SELECT_RTD_THERMOSTAT = [('RI', 'RTD-Inline'), ('RO', 'RTD-Offline'), ('TI', 'Thermostat-Inline'), ('TO', 'Thermostat-Offline')]
CHOICE_LOCAL_ISOLATOR = [('bothSides', 'Both Sides'), ('outgoingOnly', 'Outgoing Only'), ('incomingOnly', 'Incoming Only'), ('noIsolator', 'No Isolator')]

class ProjectData(models.Model):
    id = models.BigAutoField(primary_key=True)
    proj_id = models.CharField(max_length=20, unique=True, choices=SELECT_PROJECT_ID, default='p1', verbose_name='Project ID')    
    min_amb_t = models.DecimalField(max_digits=5, decimal_places=2)
    max_amb_t = models.DecimalField(max_digits=5, decimal_places=2)
    startup_t = models.DecimalField(max_digits=5, decimal_places=2)
    area_class = models.CharField(max_length=20)
    temp_class = models.CharField(max_length=20)
    voltage = models.DecimalField(max_digits=5, decimal_places=2)
    max_cb_size = models.IntegerField(choices=MAX_CB_SIZE, default=5)
    restrict_cb_current = models.DecimalField(max_digits=5, decimal_places=2)
    vendor = models.CharField(max_length=30, choices=SELECT_VENDOR, default='THR')
    tracer_family = models.CharField(max_length=30)
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
    req_local_isolator = models.CharField(max_length=30)
    caution_label_interval = models.DecimalField(max_digits=5, decimal_places=2)
    k_factor_ccons = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    isolator_location = models.CharField(max_length=20, choices=CHOICE_LOCAL_ISOLATOR, default='II')
    ckt_ln = models.DecimalField(max_digits=5, decimal_places=2)
    loop_ln = models.DecimalField(max_digits=5, decimal_places=2)
    acc_power_density = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    tracer_temp_factor = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    alpha_for_res = models.DecimalField(max_digits=6, decimal_places=4, default=1)
    allowablevdrop = models.DecimalField(max_digits=5, decimal_places=2)
    udf1 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    udf2 = models.CharField(max_length=30, null=True, blank=True)
    udf3 = models.CharField(max_length=30, null=True, blank=True)    

    def save(self, *args, **kwargs):                                                                #`save()` method to check project id uniqueness
        if ProjectData.objects.filter(proj_id=self.proj_id).exclude(pk=self.pk).exists():
            raise IntegrityError("A project with this ID already exists.")
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.id)
    


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