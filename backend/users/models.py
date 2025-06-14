# users/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.auth.models import Group
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class User(AbstractUser):
    """
    Custom user model for Spotter's HOS compliance system.
    All users are Spotter employees with different role levels.
    """

    # Driver info
    driver_license_number = models.CharField(
        max_length=50,
        blank=True, 
        null=True
    )
    driver_license_state = models.CharField(
        max_length=2,
        blank=True, 
        null=True
    )
    driver_license_expiration = models.DateField(
        blank=True, 
        null=True,
        help_text=_("Expiration date of the driver's license")
    )

    # Contact info
    phone_number = models.CharField(
        max_length=20,
        blank=True, 
        null=True,
    )
    emergency_contact_name = models.CharField(
        max_length=100,
        blank=True, 
        null=True,
    )
    emergency_contact_phone = models.CharField(
        max_length=20,
        blank=True, 
        null=True,
    )

    is_driver = models.BooleanField(
        default=True, 
        help_text="Can log hours and view own logs"
    )
    is_fleet_manager = models.BooleanField(
        default=False,
        help_text="Can manage drivers and vehicles"
    )
    is_super_admin = models.BooleanField(
        default=False,
        help_text="System administrator"
    )
    
    # Employee Information
    employee_id = models.CharField(
        max_length=50, 
        unique=True, 
        blank=True, 
        null=True,
        help_text="This field will be auto-generated."
    )
    hire_date = models.DateField(
        blank=True, 
        null=True
    )
    is_active_driver = models.BooleanField(
        default=True, 
        help_text="Currently active driver status"
    )

    # Audit fields
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_users',
        help_text="Manager who created this account"
    )

    class Meta:
        verbose_name = "Staffs"
        verbose_name_plural = "Staffs"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def role_display(self):
        if self.is_super_admin:
            return "HR Admin"
        elif self.is_fleet_manager:
            return "Fleet Manager"
        elif self.is_driver:
            return "Driver"
        return "Unknown Role"
    
    def has_fleet_management_access(self):
        return self.is_fleet_manager or self.is_super_admin
    
    def can_manage_drivers(self):
        return self.is_fleet_manager or self.is_super_admin
    
    def has_admin_panel_access(self):
        return self.is_staff and (self.is_fleet_manager or self.is_super_admin)
    
    @classmethod
    def generate_employee_id(cls):
        with transaction.atomic():
            # Get highest existing employee ID
            existing_ids = cls.objects.filter(
                employee_id__startswith='SPT'
            ).values_list('employee_id', flat=True)

            # Find highest numeric suffix
            max_number = 0
            for employee_id in existing_ids:
                if employee_id and len(employee_id) > 3:
                    try:
                        number_part = int(employee_id[3:])
                        max_number = max(max_number, number_part)
                    except ValueError:
                        continue
            
            # Generate new employee ID
            new_number = max_number + 1
            return f"SPT{new_number:03d}"
    

    def save(self, *args, **kwargs):
        if not self.employee_id:
            self.employee_id = self.generate_employee_id()
        
        if self.is_fleet_manager or self.is_super_admin:
            self.is_staff = True
        elif self.is_driver and not self.is_fleet_manager:
            self.is_staff = False
        
        super().save(*args, **kwargs)

        if self.is_fleet_manager and not self.is_super_admin:
            self._assign_to_fleet_manager_group()
    

    def _assign_to_fleet_manager_group(self):
        try:
            fleet_manager_group, created = Group.objects.get_or_create(name='Fleet Managers')
            if not self.groups.filter(name='Fleet Managers').exists():
                self.groups.add(fleet_manager_group)
        except Exception:
            pass


class SpotterCompany(models.Model):
    name = models.CharField(max_length=255, default="Spotter")
    usdot_number = models.CharField(max_length=50, unique=True)
    mc_number = models.CharField(max_length=50, unique=True)

    # Address info
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    zip_code = models.CharField(max_length=10)

    # Contact info
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.URLField(blank=True, null=True)

    # System settings
    default_duty_cycle = models.CharField(
        max_length=10,
        choices=[('60_7', '60 hours / 7 days'), ('70_8', '70 hours / 8 days')],
        default='70_8'
    )
    timezone = models.CharField(max_length=50, default='America/Chicago')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Spotter Administrator"
        verbose_name_plural = "Spotter Administrator"
    
    def __str__(self):
        return f"{self.name} (USDOT: {self.usdot_number})"
    
    @classmethod
    def get_company_instance(cls):
         """Get the single Spotter company"""
         company, created = cls.objects.get_or_create(
             name="Spotter",
             defaults={
                'usdot_number': 'PENDING',
                'mc_number': 'PENDING',
                'address': 'To be configured',
                'city': 'To be configured',
                'state': 'TX',
                'zip_code': '00000',
                'phone_number': '000-000-0000',
                'email': 'admin@spotter.com'
             }
         )
         return company


class Vehicle(models.Model):
    unit_number = models.CharField(max_length=50, unique=True)
    vin = models.CharField(max_length=17, unique=True)
    license_plate = models.CharField(max_length=15, unique=True)
    license_plate_state = models.CharField(max_length=2, default='TX')

    year = models.PositiveIntegerField()
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    vehicle_type = models.CharField(
        max_length=20,
        choices=[
            ('truck', 'Truck'),
            ('trailer', 'Trailer'),
            ('truck_trailer', 'Truck with Trailer'),

        ],
        default='truck'
    )

    is_active = models.BooleanField(default=True)
    maintenance_status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('maintenance', 'In Maintenance'),
            ('out of service', 'Out of Service'),
        ],
        default='active'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vehicles_created',
        help_text="Fleet manager who created this vehicle record"
    )

    class Meta:
        ordering = ['unit_number']
        verbose_name = 'Vehicle'
        verbose_name_plural = 'Vehicles'
    
    def __str__(self):
        return f"{self.unit_number} - ({self.year} {self.make}, {self.model})"
    
    @property
    def is_available_for_assignment(self):
        return self.is_active and self.maintenance_status == 'active'


class DriverVehicleAssignment(models.Model):
    """
    Model representing assignment of drivers to vehicles.
    """
    driver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vehicle_assignments',
        limit_choices_to={'is_driver': True, 'is_active_driver': True},
        help_text="Driver assigned to vehicle"
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='driver_assignments',
    )

    # Assignment Details
    start_date = models.DateField()
    end_date = models.DateField(
        blank=True, 
        null=True,
    )
    is_active = models.BooleanField(default=True,)

    # Assigment type
    assignment_type = models.CharField(
        max_length=20,
        choices=[
            ('permanent', 'Permanent Assignment'),
            ('temporary', 'Temporary Assignment'),
        ],
        default='permanent'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assignments_made',
        limit_choices_to={'is_fleet_manager': True},
    )

    class Meta:
        ordering = ['-start_date']
        unique_together = ['driver', 'vehicle', 'start_date']
        verbose_name = 'Driver-Vehicle Assignment'
        verbose_name_plural = 'Driver-Vehicle Assignments'
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.driver.full_name} - {self.vehicle.unit_number} ({status})"
    
    def clean(self):
        if self.end_date and self.start_date and self.end_date <= self.start_date:
            raise ValidationError("End date must be after start date.")
        
        if self.is_active:
            overlapping_assignments = DriverVehicleAssignment.objects.filter(
                driver=self.driver,
                is_active=True
            ).exclude(pk=self.pk)

            if self.end_date:
                overlapping_assignments = overlapping_assignments.filter(
                    start_date__lte=self.end_date,
                    end_date__gte=self.start_date
                )
            else:
                overlapping_assignments = overlapping_assignments.filter(
                    start_date__lte=self.start_date
                )
            
            if overlapping_assignments.exists():
                raise ValidationError(
                    "This driver already has an active assignment that overlaps with the selected dates."
                )
        
        def save(self, *args, **kwargs):
            self.full_clean()
            super().save(*args, **kwargs)


class DriverCycleStatus(models.Model):
    """Track driver's current HOS cycle status"""
    driver = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cycle_status',
        limit_choices_to={'is_driver': True},
    )

    # 8-day cycle tracking
    cycle_start_date = models.DateTimeField(
        help_text="Start of current 8-day cycle"
    )
    total_cycle_hours = models.FloatField(
        default=0.0,
        help_text="Total on-duty hours used in current 8-day cycle"
    )

    # Daily status tracking
    last_daily_reset_start = models.DateTimeField(
        blank=True, 
        null=True,
        help_text="When current daily reset (10-hour break) started"
    )
    last_daily_reset_end = models.DateTimeField(
        null=True, blank=True,
        help_text="When current daily reset ended"
    )

    # Current status
    current_duty_status = models.CharField(
        max_length=20,
        choices=[
            ('off_duty', 'Off Duty'),
            ('sleeper_berth', 'Sleeper Berth'),
            ('driving', 'Driving'),
            ('on_duty_not_driving', 'On Duty (Not Driving)'),
        ],
        default='off_duty'
    )
    current_status_start = models.DateTimeField(
        help_text="When current duty status started"
    )

    # Today's totals
    today_driving_hours = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(11)],
        help_text="Hours driven TODAY (out of 11 allowed)"
    )
    today_on_duty_hours = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(14)],
        help_text="Hours on-duty TODAY (out of 14 allowed)"
    )
    today_date = models.DateField(
        auto_now_add=True,
        help_text="Date these daily totals apply to"
    )

    # Last break info
    last_30min_break_end = models.DateTimeField(
        null=True, blank=True,
        help_text="Time the driver's last 30-minute break ended"
    )
    continuous_driving_since = models.DateTimeField(
        null=True, blank=True,
        help_text="Start time of current continuous driving period"
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Driver Cycle Status"
        verbose_name_plural = "Driver Cycle Status"
    
    def __str__(self):
        return f"{self.driver.full_name} - Cycle: {self.total_cycle_hours}/70 hrs"
    
    @property
    def remaining_cycle_hours(self):
        return max(0, 70 - self.total_cycle_hours)
    
    @property
    def remaining_driving_hours_today(self):
        return max(0, 11 - self.today_driving_hours)
    
    @property
    def remaining_on_duty_hours_today(self):
        return max(0, 14 - self.today_on_duty_hours)
    
    @property
    def hours_since_last_break(self):
        """Hours since last 30-minute break"""
        if not self.continuous_driving_since:
            return 0
        
        time_diff = timezone.now() - self.continuous_driving_since
        return time_diff.total_seconds() / 3600
    
    @property
    def needs_immediate_break(self):
        """Does driver need 30-min break RIGHT NOW?"""
        return (self.current_duty_status == 'driving' and 
                self.hours_since_last_break >= 8)
    
    @property
    def needs_daily_reset(self):
        """Does driver need 10-hour daily reset?"""
        return (self.today_on_duty_hours >= 14 or 
                self.today_driving_hours >= 11)
    
    @property
    def needs_cycle_reset(self):
        """Does driver need 34-hour cycle reset?"""
        return self.total_cycle_hours >= 70
    
    @property
    def compliance_warnings(self):
        """Get list of current compliance warnings"""
        warnings = []
        
        if self.needs_immediate_break:
            warnings.append({
                'type': 'immediate_break_required',
                'message': f'Must take 30-min break NOW (driving {self.hours_since_last_break:.1f} hours)',
                'severity': 'critical'
            })
        
        if self.remaining_driving_hours_today <= 1:
            warnings.append({
                'type': 'approaching_daily_driving_limit',
                'message': f'Only {self.remaining_driving_hours_today:.1f} hours driving time left today',
                'severity': 'warning'
            })
        
        if self.remaining_on_duty_hours_today <= 2:
            warnings.append({
                'type': 'approaching_daily_on_duty_limit',
                'message': f'Only {self.remaining_on_duty_hours_today:.1f} hours on-duty time left today',
                'severity': 'warning'
            })
        
        if self.remaining_cycle_hours <= 10:
            warnings.append({
                'type': 'approaching_cycle_limit',
                'message': f'Only {self.remaining_cycle_hours:.1f} hours left in 8-day cycle',
                'severity': 'warning'
            })
        
        return warnings
    
    def can_start_trip(self, estimated_trip_hours):
        """Check if driver can start a trip of given duration"""
        if self.needs_immediate_break:
            return False, "Must take 30-minute break before starting trip"
        
        if estimated_trip_hours > self.remaining_driving_hours_today:
            return False, f"Trip requires {estimated_trip_hours} hours but only {self.remaining_driving_hours_today} hours remain today"
        
        if estimated_trip_hours > self.remaining_cycle_hours:
            return False, f"Trip requires {estimated_trip_hours} hours but only {self.remaining_cycle_hours} hours remain in cycle"
        
        return True, "Driver can start trip"


class DailyDrivingRecord(models.Model):
    """Track daily driving records for the 8-day cycle"""
    driver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='daily_records'
    )
    date = models.DateField()
    
    # Daily totals
    total_driving_hours = models.FloatField(default=0.0)
    total_on_duty_hours = models.FloatField(default=0.0)
    total_off_duty_hours = models.FloatField(default=0.0)
    
    # Break tracking
    had_30min_break = models.BooleanField(default=False)
    break_start_time = models.DateTimeField(null=True, blank=True)
    break_end_time = models.DateTimeField(null=True, blank=True)
    
    # Daily reset tracking
    had_daily_reset = models.BooleanField(default=False)
    reset_start_time = models.DateTimeField(null=True, blank=True)
    reset_end_time = models.DateTimeField(null=True, blank=True)
    
    # Compliance
    is_compliant = models.BooleanField(default=True)
    violations = models.JSONField(default=list, help_text="List of HOS violations for this day")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('driver', 'date')
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.driver.full_name} - {self.date} - {self.total_driving_hours}h driving"

