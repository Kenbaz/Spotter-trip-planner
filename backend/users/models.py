# users/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.auth.models import Group


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

