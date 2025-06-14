# trip_api/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from users.models import SpotterCompany, DriverVehicleAssignment
import uuid

User = get_user_model()


class Trip(models.Model):
    trip_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    driver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='trips',
        limit_choices_to={'is_driver': True, 'is_active_driver': True},
        help_text="Driver who owns this trip"
    )
    
    assigned_vehicle = models.ForeignKey(
        'users.Vehicle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trips',
        help_text="Vehicle assigned for this trip"
    )
    
    company = models.ForeignKey(
        'users.SpotterCompany',
        on_delete=models.CASCADE,
        related_name='trips',
        help_text="Company this trip belongs to."
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('planned', 'Planned'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        help_text="Current status of the trip"
    )

    # Existing location fields
    current_address = models.CharField(
        max_length=500, 
        help_text="Driver's current location"
    )
    current_latitude = models.DecimalField(max_digits=10, decimal_places=7)
    current_longitude = models.DecimalField(max_digits=10, decimal_places=7)

    pickup_address = models.CharField(
        max_length=500,
        help_text="Where to pick up cargo"
    )
    pickup_latitude = models.DecimalField(max_digits=10, decimal_places=7)
    pickup_longitude = models.DecimalField(max_digits=10, decimal_places=7)

    delivery_address = models.CharField(
        max_length=500,
        help_text="Final delivery location"
    )
    delivery_latitude = models.DecimalField(max_digits=10, decimal_places=7)
    delivery_longitude = models.DecimalField(max_digits=10, decimal_places=7)

    destination_address = models.CharField(max_length=500)
    destination_latitude = models.DecimalField(max_digits=10, decimal_places=7)
    destination_longitude = models.DecimalField(max_digits=10, decimal_places=7)

    departure_datetime = models.DateTimeField()

    # Vehicle-specific settings - UPDATED with defaults from vehicle
    max_fuel_distance_miles = models.PositiveBigIntegerField(
        default=1000,
        validators=[MinValueValidator(200), MaxValueValidator(1200)],
        help_text="Maximum distance between fuel stops in miles"
    )
    pickup_duration_minutes = models.PositiveIntegerField(
        default=60,
        validators=[MinValueValidator(15), MaxValueValidator(240)],
        help_text="Estimated pickup duration in minutes"
    )
    delivery_duration_minutes = models.PositiveIntegerField(
        default=60,
        validators=[MinValueValidator(15), MaxValueValidator(240)],
        help_text="Estimated delivery duration in minutes"
    )

    # Calculated fields
    total_distance_miles = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Total distance of the trip in miles"
    )
    deadhead_distance_miles = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Distance from current location to pickup in miles"
    )
    loaded_distance_miles = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Distance from pickup to delivery in miles"
    )

    total_driving_time = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Total driving time for the trip in hours"
    )
    deadhead_driving_time = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Driving time for deadhead leg in hours"
    )
    loaded_driving_time = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Driving time for loaded leg in hours"
    )

    estimated_arrival_time = models.DateTimeField(
        null=True, blank=True,
        help_text="Estimated arrival time at the destination"
    )
    estimated_pickup_time = models.DateTimeField(
        null=True, blank=True,
        help_text="Estimated arrival time at pickup location"
    )

    is_hos_compliant = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trips_created',
        help_text="User who created this trip"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['driver', '-created_at']),
            models.Index(fields=['company', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['assigned_vehicle', '-created_at']),
        ]

    def __str__(self):
        return f"Trip {self.trip_id} - {self.driver.full_name} ({self.current_address} → {self.destination_address})"
    
    def save(self, *args, **kwargs):
        """Override save to set company and default vehicle assignment"""
        # Ensure company is set if not specified
        if not self.company:
            self.company = SpotterCompany.get_company_instance()
        
        # Handle backward compatibility for destination fields
        if self.delivery_address and not self.destination_address:
            self.destination_address = self.delivery_address
            self.destination_latitude = self.delivery_latitude
            self.destination_longitude = self.delivery_longitude
        
        # Auto-assign driver's current vehicle if not specified
        if not self.assigned_vehicle and self.driver:
            current_assignment = DriverVehicleAssignment.objects.filter(
                driver=self.driver,
                is_active=True
            ).first()
            if current_assignment:
                self.assigned_vehicle = current_assignment.vehicle
        
        # Set created_by to driver if not specified
        if not self.created_by and self.driver:
            self.created_by = self.driver
        
        super().save(*args, **kwargs)
    
    @property
    def trip_legs(self):
        """Get trip legs information"""
        return {
            'deadhead': {
                'origin': self.current_address,
                'destination': self.pickup_address,
                'distance_miles': float(self.deadhead_distance_miles or 0),
                'driving_time_hours': float(self.deadhead_driving_time or 0),
            },
            'loaded': {
                'origin': self.pickup_address,
                'destination': self.delivery_address,
                'distance_miles': float(self.loaded_distance_miles or 0),
                'driving_time_hours': float(self.loaded_driving_time or 0),
            }
        }
    
    @property
    def driver_name(self):
        """Get driver's full name"""
        return self.driver.full_name if self.driver else "Unknown Driver"
    
    @property
    def vehicle_info(self):
        """Get vehicle information"""
        if self.assigned_vehicle:
            return f"{self.assigned_vehicle.unit_number} ({self.assigned_vehicle.year} {self.assigned_vehicle.make})"
        return "No Vehicle Assigned"
    
    @property
    def is_editable(self):
        """Check if trip can be edited"""
        return self.status in ['draft', 'planned']
    
    @property
    def compliance_summary(self):
        """Get compliance summary"""
        latest_report = self.compliance_reports.first()
        if latest_report:
            return {
                'is_compliant': latest_report.is_compliant,
                'score': latest_report.compliance_score,
                'violations_count': len(latest_report.violations)
            }
        return {
            'is_compliant': False,
            'score': 0,
            'violations_count': 0
        }


class Route(models.Model):
    """
    Represents a route for a trip, including waypoints and fuel stops.
    """
    trip = models.OneToOneField(
        Trip,
        on_delete=models.CASCADE,
        related_name='route',
        help_text="The trip associated with this route"
    )

    # External API route data
    route_geometry = models.JSONField(help_text="GeoJSON LineString geometry")
    route_instructions = models.JSONField(help_text="Turn-by-turn directions")

    total_distance_meters = models.PositiveBigIntegerField()
    total_duration_seconds = models.PositiveBigIntegerField()

    external_route_id = models.CharField(max_length=100, blank=True)
    api_provider = models.CharField(max_length=50, default='openrouteservice')

    calculated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='routes_calculated',
        help_text="User who calculated this route"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['trip', '-created_at']),
        ]

    def __str__(self):
        return f"Route for {self.trip}"


class Stops(models.Model):
    """
    Represents stops along the route, (fuel, rest, pickup, delivery)
    """
    STOP_TYPES = [
        ('pickup', 'Pickup'),
        ('delivery', 'Delivery'),
        ('fuel', 'Fuel Stop'),
        ('rest', 'Rest Break'),
        ('mandatory_break', 'Mandatory 30-min Break'),
        ('daily_reset', 'Daily 10-hour Reset'),
        ('fuel_and_break', 'Combined Fuel & Break'),
    ]

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='stops',
        help_text="The trip associated with these stops"
    )

    stop_type = models.CharField(max_length=20, choices=STOP_TYPES)
    sequence_order = models.PositiveIntegerField()

    address = models.CharField(max_length=500)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    arrival_time = models.DateTimeField()
    departure_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(help_text="Duration of the stop in minutes")

    distance_from_origin_miles = models.DecimalField(max_digits=8, decimal_places=2)
    distance_to_next_stop_miles = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # Compliance and optimization fields
    is_required_for_compliance = models.BooleanField(default=False)
    is_optimized_stop = models.BooleanField(
        default=False,
        help_text="Whether this stop was created through route optimization"
    )
    optimization_notes = models.TextField(
        blank=True,
        help_text="Notes about optimizations applied to this stop"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['trip', 'sequence_order']
        unique_together = ('trip', 'sequence_order')
        indexes = [
            models.Index(fields=['trip', 'sequence_order']),
            models.Index(fields=['trip', 'stop_type']),
        ]
    
    def __str__(self):
        return f"{self.get_stop_type_display()} - {self.address} (Trip: {self.trip.trip_id})"


class HOSPeriod(models.Model):
    """
    Represents periods of duty status for HOS Compliance tracking
    """
    DUTY_STATUS_CHOICES = [
        ('off_duty', 'Off Duty'),
        ('sleeper_berth', 'Sleeper Berth'),
        ('driving', 'Driving'),
        ('on_duty_not_driving', 'On Duty (Not Driving)'),
    ]

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='hos_periods',
        help_text="The trip associated with this HOS period"
    )

    duty_status = models.CharField(max_length=20, choices=DUTY_STATUS_CHOICES)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField()

    start_location = models.CharField(max_length=500, blank=True)
    end_location = models.CharField(max_length=500, blank=True)
    start_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    start_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    distance_traveled_miles = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Distance traveled during this HOS period in miles"
    )

    is_compliant = models.BooleanField(default=True)
    compliance_notes = models.TextField(blank=True)
    
    related_stop = models.ForeignKey(
        Stops, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='hos_periods'
    )
    
    verified_by_driver = models.BooleanField(
        default=False,
        help_text="Whether this period has been verified by the driver"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['trip', 'start_datetime']
        indexes = [
            models.Index(fields=['trip', 'start_datetime']),
            models.Index(fields=['trip', 'duty_status']),
            models.Index(fields=['duty_status', 'start_datetime']),
        ]
    
    def __str__(self):
        return f"{self.get_duty_status_display()} - {self.start_datetime} to {self.end_datetime} (Trip: {self.trip.trip_id})"


class ComplianceReport(models.Model):
    """Stores HOS compliance reports for a trip"""

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='compliance_reports',
        help_text="The trip associated with this compliance report"
    )

    is_compliant = models.BooleanField(default=False)
    compliance_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Compliance score as percentage"
    )

    total_driving_hours = models.DecimalField(max_digits=5, decimal_places=2)
    total_on_duty_hours = models.DecimalField(max_digits=5, decimal_places=2)
    total_off_duty_hours = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Violation tracking
    violations = models.JSONField(default=list, help_text="List of HOS violations found")
    warnings = models.JSONField(default=list, help_text="List of potential compliance issues")
    
    # Break requirements
    required_30min_breaks = models.PositiveIntegerField(default=0)
    scheduled_30min_breaks = models.PositiveIntegerField(default=0)
    
    # Daily reset requirements
    required_daily_resets = models.PositiveIntegerField(default=0)
    scheduled_daily_resets = models.PositiveIntegerField(default=0)
    
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compliance_reports_generated',
        help_text="User who generated this report"
    )
    reviewed_by_fleet_manager = models.BooleanField(
        default=False,
        help_text="Whether this report has been reviewed by fleet management"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['trip', '-created_at']),
            models.Index(fields=['is_compliant', '-created_at']),
        ]
    
    def __str__(self):
        return f"Compliance Report for {self.trip} - {'Compliant' if self.is_compliant else 'Non-Compliant'}"