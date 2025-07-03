# trip_api/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from users.models import SpotterCompany, DriverVehicleAssignment
import uuid
from django.utils import timezone


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

    total_on_duty_time = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Total on-duty time (driving + pickup/delivery time) in hours"
    )

    estimated_arrival_time = models.DateTimeField(
        null=True, blank=True,
        help_text="Estimated arrival time at the destination"
    )
    estimated_pickup_time = models.DateTimeField(
        null=True, blank=True,
        help_text="Estimated arrival time at pickup location"
    )

    starting_cycle_hours = models.FloatField(
        null=True, blank=True,
        help_text="Driver's cycle hours when trip started"
    )
    starting_driving_hours = models.FloatField(
        null=True, blank=True,
        help_text="Driver's daily driving hours when trip started"
    )
    starting_on_duty_hours = models.FloatField(
        null=True, blank=True,
        help_text="Driver's daily on-duty hours when trip started"
    )
    starting_duty_status = models.CharField(
        max_length=20,
        null=True, blank=True,
        choices=[
            ('off_duty', 'Off Duty'),
            ('sleeper_berth', 'Sleeper Berth'),
            ('driving', 'Driving'),
            ('on_duty_not_driving', 'On Duty (Not Driving)'),
        ],
        help_text="Driver's duty status when trip started"
    )

    completed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When trip was completed"
    )
    hos_updated = models.BooleanField(
        default=False,
        help_text="Whether driver cycle status has been updated for this trip"
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
    
    def complete_trip(self):
        """Mark trip as completed and update driver HOS status"""
        if self.status != 'completed':
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save()

            # Update driver cycle status
            if not self.hos_updated:
                from .services.DriverCycleStatusService import DriverCycleStatusService
                
                DriverCycleStatusService.update_status_for_trip_completion(self)
                self.hos_updated = True
                self.save()
    
    def get_trip_hours_summary(self):
        """Get summary of hours used in a trip"""
        total_driving = 0.0
        total_on_duty = 0.0

        for period in self.hos_periods.all():
            # conver duration_minutes to hours
            period_duration_hours = period.duration_minutes / 60.0

            if period.duty_status == 'driving':
                total_driving += period_duration_hours
                total_on_duty += period_duration_hours
            elif period.duty_status == 'on_duty_not_driving':
                total_on_duty += period_duration_hours
        
        return {
            'driving_hours': total_driving,
            'on_duty_hours': total_on_duty,
            'started_with_cycle_hours': self.starting_cycle_hours or 0,
            'started_with_driving_hours': self.starting_driving_hours or 0,
            'started_with_on_duty_hours': self.starting_on_duty_hours or 0
        }

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


class ELDDailyLog(models.Model):
    """
    Represents a single day's ELD log
    Auto-populated from trip data and HOS periods for DOT compliance
    """
    log_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='eld_daily_logs',
        help_text="The trip associated with this ELD log"
    )

    log_date = models.DateField()

    driver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='eld_daily_logs'
    )
    driver_name = models.CharField(
        max_length=100,
        help_text="Driver's full name (auto-populated)",
    )
    driver_license_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Driver's CDL number (auto-populated)"
    )
    driver_license_state = models.CharField(
        max_length=2,
        blank=True,
        help_text="Driver's CDL state (auto-populated)"
    )
    employee_id = models.CharField(
        max_length=50,
        blank=True,
        help_text="Driver's employee ID (auto-populated)"
    )

    # Auto-populated company information
    carrier_name = models.CharField(
        max_length=200,
        help_text="Carrier company name (auto-populated)"
    )
    carrier_address = models.TextField(
        help_text="Carrier company address (auto-populated)"
    )
    dot_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="DOT number (auto-populated)"
    )
    mc_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="MC number (auto-populated)"
    )
    
    # Auto-populated vehicle information
    vehicle_id = models.CharField(
        max_length=50,
        help_text="Vehicle identification (auto-populated)"
    )
    license_plate = models.CharField(
        max_length=20,
        blank=True,
        help_text="Vehicle license plate (auto-populated)"
    )
    vin = models.CharField(
        max_length=17,
        blank=True,
        help_text="Vehicle VIN (auto-populated)"
    )
    vehicle_make_model = models.CharField(
        max_length=100,
        blank=True,
        help_text="Vehicle make and model (auto-populated)"
    )
    
    # Daily totals (auto-calculated from log entries)
    total_off_duty_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
        help_text="Total off-duty hours for the day"
    )
    total_sleeper_berth_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
        help_text="Total sleeper berth hours for the day"
    )
    total_driving_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(11)],
        help_text="Total driving hours for the day"
    )
    total_on_duty_not_driving_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(14)],
        help_text="Total on-duty (not driving) hours for the day"
    )
    total_on_duty_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(14)],
        help_text="Total on-duty hours (driving + not driving)"
    )
    total_distance_miles = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total distance driven for the day"
    )
    
    # Shipping documents (auto-populated from trip)
    bill_of_lading = models.CharField(
        max_length=100,
        blank=True,
        help_text="Bill of lading number"
    )
    manifest_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Manifest number"
    )
    pickup_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Pickup number"
    )
    delivery_receipt = models.CharField(
        max_length=100,
        blank=True,
        help_text="Delivery receipt number"
    )
    commodity_description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Description of cargo/commodity"
    )
    cargo_weight = models.CharField(
        max_length=50,
        blank=True,
        help_text="Weight of cargo"
    )
    is_hazmat = models.BooleanField(
        default=False,
        help_text="Whether cargo contains hazardous materials"
    )
    
    # Compliance and validation
    is_compliant = models.BooleanField(
        default=True,
        help_text="Whether this log meets HOS compliance requirements"
    )
    compliance_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Compliance score (0-100)"
    )
    violation_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of HOS violations detected"
    )
    warning_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of HOS warnings detected"
    )
    
    # Driver certification
    is_certified = models.BooleanField(
        default=False,
        help_text="Whether driver has certified this log"
    )
    certified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When driver certified this log"
    )
    certification_signature = models.TextField(
        blank=True,
        help_text="Digital signature data for certification"
    )
    certification_statement = models.TextField(
        default="I hereby certify that my data entries and my record of duty status for this 24-hour period are true and correct.",
        help_text="Certification statement text"
    )
    
    # Administrative fields
    auto_generated = models.BooleanField(
        default=True,
        help_text="Whether this log was auto-generated from trip data"
    )
    manual_edits_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of manual edits made to auto-generated data"
    )
    last_edited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='eld_logs_edited',
        help_text="Last user to edit this log"
    )
    last_edited_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this log was last edited"
    )
    
    generated_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this log was initially generated"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this log was last updated"
    )
    
    class Meta:
        ordering = ['-log_date', '-generated_at']
        unique_together = ('trip', 'log_date')
        indexes = [
            models.Index(fields=['driver', '-log_date']),
            models.Index(fields=['trip', 'log_date']),
            models.Index(fields=['log_date', 'driver']),
            models.Index(fields=['is_certified', '-log_date']),
            models.Index(fields=['is_compliant', '-log_date']),
        ]
        
        verbose_name = "ELD Daily Log"
        verbose_name_plural = "ELD Daily Logs"
    
    def __str__(self):
        return f"ELD Log - {self.driver_name} - {self.log_date} (Trip: {self.trip.trip_id})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Recalculate totals from log entries
        if hasattr(self, 'log_entries'):
            self.recalculate_daily_totals()
    
    def recalculate_daily_totals(self):
        """Recalculate daily totals from associated log entries"""
        entries = self.log_entries.all()

        totals = {
            'off_duty': 0,
            'sleeper_berth': 0,
            'driving': 0,
            'on_duty_not_driving': 0,
            'distance': 0
        }

        for entry in entries:
            duty_status = entry.duty_status
            hours = entry.duration_hours

            if duty_status in totals:
                totals[duty_status] += hours
            
            totals['distance'] += entry.vehicle_miles or 0
        
        # Update fields
        self.total_off_duty_hours = totals['off_duty']
        self.total_sleeper_berth_hours = totals['sleeper_berth']
        self.total_driving_hours = totals['driving']
        self.total_on_duty_not_driving_hours = totals['on_duty_not_driving']
        self.total_on_duty_hours = totals['driving'] + totals['on_duty_not_driving']
        self.total_distance_miles = totals['distance']
        
        self.save(update_fields=[
            'total_off_duty_hours', 'total_sleeper_berth_hours',
            'total_driving_hours', 'total_on_duty_not_driving_hours',
            'total_on_duty_hours', 'total_distance_miles'
        ])
    
    def certify_log(self, signature_data: str = None):
        """Certify the log with driver signature"""
        self.is_certified = True
        self.certified_at = timezone.now()
        if signature_data:
            self.certification_signature = signature_data
        self.save(update_fields=['is_certified', 'certified_at', 'certification_signature'])
    
    def get_compliance_grade(self):
        """Get letter grade based on compliance score"""
        if self.compliance_score >= 95:
            return 'A+'
        elif self.compliance_score >= 90:
            return 'A'
        elif self.compliance_score >= 85:
            return 'B+'
        elif self.compliance_score >= 80:
            return 'B'
        elif self.compliance_score >= 75:
            return 'C+'
        elif self.compliance_score >= 70:
            return 'C'
        elif self.compliance_score >= 65:
            return 'D'
        else:
            return 'F'


class ELDLogEntry(models.Model):
    """
    Represents individual duty status periods within an ELD daily log
    Auto-populated from HOS periods with enhanced location and timing data
    """
    
    DUTY_STATUS_CHOICES = [
        ('off_duty', 'Off Duty'),
        ('sleeper_berth', 'Sleeper Berth'),
        ('driving', 'Driving'),
        ('on_duty_not_driving', 'On Duty (Not Driving)'),
    ]
    
    daily_log = models.ForeignKey(
        ELDDailyLog,
        on_delete=models.CASCADE,
        related_name='log_entries',
        help_text="The daily log this entry belongs to"
    )
    
    hos_period = models.ForeignKey(
        HOSPeriod,
        on_delete=models.CASCADE,
        related_name='eld_log_entries',
        help_text="The HOS period this entry was generated from"
    )
    
    # Time and duty status
    start_time = models.TimeField(
        help_text="Start time of this duty period (24-hour format)"
    )
    end_time = models.TimeField(
        help_text="End time of this duty period (24-hour format)"
    )
    duty_status = models.CharField(
        max_length=20,
        choices=DUTY_STATUS_CHOICES,
        help_text="Duty status for this period"
    )
    duration_minutes = models.PositiveIntegerField(
        help_text="Duration of this period in minutes"
    )
    duration_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        help_text="Duration of this period in hours (calculated)"
    )
    
    # Location information (auto-populated from route)
    start_location = models.CharField(
        max_length=500,
        blank=True,
        help_text="Starting location for this period"
    )
    end_location = models.CharField(
        max_length=500,
        blank=True,
        help_text="Ending location for this period"
    )
    location_type = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('trip_start', 'Trip Start'),
            ('pickup', 'Pickup Location'),
            ('delivery', 'Delivery Location'),
            ('fuel_stop', 'Fuel Stop'),
            ('rest_area', 'Rest Area'),
            ('intermediate_stop', 'Intermediate Stop'),
            ('unknown', 'Unknown Location'),
        ],
        help_text="Type of location for this period"
    )
    
    vehicle_miles = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Miles driven during this period"
    )
    
    remarks = models.TextField(
        blank=True,
        help_text="Remarks for this duty period (auto-generated + manual)"
    )
    auto_generated_remarks = models.TextField(
        blank=True,
        help_text="Auto-generated remarks based on trip context"
    )
    manual_remarks = models.TextField(
        blank=True,
        help_text="Manual remarks added by driver"
    )
    
    # Grid positioning for ELD visualization
    grid_row = models.PositiveIntegerField(
        help_text="Grid row for ELD visualization (0-10)"
    )
    grid_column_start = models.PositiveIntegerField(
        help_text="Starting grid column for ELD visualization"
    )
    grid_column_end = models.PositiveIntegerField(
        help_text="Ending grid column for ELD visualization"
    )
    
    is_compliant = models.BooleanField(
        default=True,
        help_text="Whether this entry meets HOS compliance"
    )
    compliance_notes = models.TextField(
        blank=True,
        help_text="Notes about compliance issues with this entry"
    )

    was_manually_edited = models.BooleanField(
        default=False,
        help_text="Whether this entry has been manually edited"
    )
    original_auto_data = models.JSONField(
        default=dict,
        help_text="Original auto-generated data for audit purposes"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this entry was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this entry was last updated"
    )
    
    class Meta:
        ordering = ['daily_log', 'start_time']
        indexes = [
            models.Index(fields=['daily_log', 'start_time']),
            models.Index(fields=['duty_status', 'start_time']),
            models.Index(fields=['daily_log', 'duty_status']),
        ]
        
        verbose_name = "ELD Log Entry"
        verbose_name_plural = "ELD Log Entries"
    
    def __str__(self):
        return f"{self.get_duty_status_display()} - {self.start_time} to {self.end_time} ({self.daily_log.log_date})"
    
    def save(self, *args, **kwargs):
        """Override save to calculate duration in hours and update grid positions"""
        # Calculate duration in hours
        self.duration_hours = round(self.duration_minutes / 60.0, 2)
        
        # Store original data for audit trail if this is a manual edit
        if self.pk and not self.was_manually_edited:
            # Check if any fields were manually changed
            original = ELDLogEntry.objects.get(pk=self.pk)
            manual_edit_fields = ['start_time', 'end_time', 'duty_status', 'location', 'remarks']
            
            for field in manual_edit_fields:
                if getattr(self, field) != getattr(original, field):
                    self.was_manually_edited = True
                    self.original_auto_data = {
                        'start_time': str(original.start_time),
                        'end_time': str(original.end_time),
                        'duty_status': original.duty_status,
                        'start_location': original.start_location,
                        'remarks': original.remarks
                    }
                    # Update parent log's edit count
                    self.daily_log.manual_edits_count += 1
                    self.daily_log.save(update_fields=['manual_edits_count'])
                    break
        
        super().save(*args, **kwargs)
        
        # Update parent log totals
        if hasattr(self.daily_log, 'recalculate_daily_totals'):
            self.daily_log.recalculate_daily_totals()
    
    def get_duty_status_symbol(self):
        """Get DOT-compliant duty status symbol"""
        symbols = {
            'off_duty': 1,
            'sleeper_berth': 2,
            'driving': 3,
            'on_duty_not_driving': 4
        }
        return symbols.get(self.duty_status, 1)
    
    def get_duty_status_color(self):
        """Get color for duty status visualization"""
        colors = {
            'off_duty': '#000000',
            'sleeper_berth': '#808080',
            'driving': '#FF0000',
            'on_duty_not_driving': '#0000FF'
        }
        return colors.get(self.duty_status, '#000000')


class ELDComplianceViolation(models.Model):
    """
    Represents HOS compliance violations detected in ELD logs.
    Auto-generated during log validation process.
    """
    
    VIOLATION_TYPES = [
        ('daily_driving_limit', 'Daily Driving Limit Exceeded'),
        ('daily_on_duty_limit', 'Daily On-Duty Limit Exceeded'),
        ('insufficient_off_duty', 'Insufficient Off-Duty Time'),
        ('missing_30min_break', 'Missing 30-Minute Break'),
        ('weekly_driving_limit', 'Weekly Driving Limit Exceeded'),
        ('daily_time_accounting', 'Daily Time Accounting Error'),
        ('missing_location_change', 'Missing Location Change'),
        ('invalid_duty_status', 'Invalid Duty Status Sequence'),
    ]
    
    SEVERITY_LEVELS = [
        ('critical', 'Critical'),
        ('major', 'Major'),
        ('minor', 'Minor'),
        ('warning', 'Warning'),
    ]
    
    daily_log = models.ForeignKey(
        ELDDailyLog,
        on_delete=models.CASCADE,
        related_name='compliance_violations',
        help_text="The daily log this violation belongs to"
    )
    
    log_entry = models.ForeignKey(
        ELDLogEntry,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='compliance_violations',
        help_text="The specific log entry with violation (if applicable)"
    )
    
    # Violation details
    violation_type = models.CharField(
        max_length=50,
        choices=VIOLATION_TYPES,
        help_text="Type of HOS violation"
    )
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_LEVELS,
        default='major',
        help_text="Severity level of the violation"
    )
    description = models.TextField(
        help_text="Detailed description of the violation"
    )
    
    # Violation metrics
    actual_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Actual value that caused violation"
    )
    limit_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Legal limit value"
    )
    violation_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount by which limit was exceeded"
    )
    
    is_resolved = models.BooleanField(
        default=False,
        help_text="Whether this violation has been resolved"
    )
    resolution_notes = models.TextField(
        blank=True,
        help_text="Notes about how violation was resolved"
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When violation was resolved"
    )
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='eld_violations_resolved',
        help_text="User who resolved this violation"
    )
    
    detected_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this violation was detected"
    )
    
    class Meta:
        ordering = ['-detected_at', 'severity']
        indexes = [
            models.Index(fields=['daily_log', 'violation_type']),
            models.Index(fields=['severity', '-detected_at']),
            models.Index(fields=['is_resolved', '-detected_at']),
        ]
        
        verbose_name = "ELD Compliance Violation"
        verbose_name_plural = "ELD Compliance Violations"
    
    def __str__(self):
        return f"{self.get_violation_type_display()} - {self.daily_log.log_date} ({self.get_severity_display()})"
    
    # def resolve_violation(self, resolved_by: User, notes: str = ""):
    #     """Mark violation as resolved"""
    #     self.is_resolved = True
    #     self.resolved_at = timezone.now()
    #     self.resolved_by = resolved_by
    #     self.resolution_notes = notes
    #     self.save(update_fields=['is_resolved', 'resolved_at', 'resolved_by', 'resolution_notes'])
        
    #     # Update parent log compliance score
    #     if hasattr(self.daily_log, 'recalculate_compliance_score'):
    #         self.daily_log.recalculate_compliance_score()


class ELDExportRecord(models.Model):
    """
    Tracks ELD log exports for DOT compliance and audit purposes.
    """
    
    EXPORT_FORMATS = [
        ('pdf', 'PDF Document'),
        ('csv', 'CSV Data'),
        ('json', 'JSON Data'),
        ('xml', 'XML Data'),
        ('dot_format', 'DOT Compliant Format'),
    ]
    
    EXPORT_PURPOSES = [
        ('dot_inspection', 'DOT Inspection'),
        ('driver_record', 'Driver Personal Record'),
        ('fleet_audit', 'Fleet Management Audit'),
        ('compliance_review', 'Compliance Review'),
        ('backup', 'Data Backup'),
        ('other', 'Other Purpose'),
    ]
    
    export_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this export"
    )
    
    daily_logs = models.ManyToManyField(
        ELDDailyLog,
        related_name='export_records',
        help_text="Daily logs included in this export"
    )
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='eld_export_records',
        help_text="Trip associated with exported logs"
    )
    
    # Export details
    export_format = models.CharField(
        max_length=20,
        choices=EXPORT_FORMATS,
        help_text="Format of the exported data"
    )
    export_purpose = models.CharField(
        max_length=20,
        choices=EXPORT_PURPOSES,
        help_text="Purpose of this export"
    )
    date_range_start = models.DateField(
        help_text="Start date of exported logs"
    )
    date_range_end = models.DateField(
        help_text="End date of exported logs"
    )
    
    # File information
    file_name = models.CharField(
        max_length=255,
        help_text="Name of exported file"
    )
    file_size_bytes = models.PositiveIntegerField(
        default=0,
        help_text="Size of exported file in bytes"
    )
    file_checksum = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA-256 checksum of exported file"
    )
    
    exported_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='eld_exports_created',
        help_text="User who created this export"
    )
    exported_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this export was created"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this export"
    )
    
    # Compliance tracking
    is_for_dot_inspection = models.BooleanField(
        default=False,
        help_text="Whether this export is for DOT inspection purposes"
    )
    inspection_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="DOT inspection reference number (if applicable)"
    )
    
    class Meta:
        ordering = ['-exported_at']
        indexes = [
            models.Index(fields=['exported_by', '-exported_at']),
            models.Index(fields=['export_purpose', '-exported_at']),
            models.Index(fields=['trip', '-exported_at']),
            models.Index(fields=['is_for_dot_inspection', '-exported_at']),
        ]
        
        verbose_name = "ELD Export Record"
        verbose_name_plural = "ELD Export Records"
    
    def __str__(self):
        return f"ELD Export - {self.file_name} ({self.exported_at.strftime('%Y-%m-%d %H:%M')})"


class ELDLocationRemark(models.Model):
    """
    Represents location change remarks in ELD logs.
    Auto-populated from route data and HOS period locations.
    """
    
    daily_log = models.ForeignKey(
        ELDDailyLog,
        on_delete=models.CASCADE,
        related_name='location_remarks',
        help_text="The daily log this remark belongs to"
    )
    
    log_entry = models.ForeignKey(
        ELDLogEntry,
        on_delete=models.CASCADE,
        related_name='location_remarks',
        help_text="The log entry this remark is associated with"
    )
    
    time = models.TimeField(
        help_text="Time of location change"
    )
    location = models.CharField(
        max_length=500,
        help_text="Location description"
    )
    location_type = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('trip_start', 'Trip Start'),
            ('pickup', 'Pickup Location'),
            ('delivery', 'Delivery Location'),
            ('fuel_stop', 'Fuel Stop'),
            ('rest_area', 'Rest Area'),
            ('state_line', 'State Line Crossing'),
            ('weigh_station', 'Weigh Station'),
            ('intermediate_stop', 'Intermediate Stop'),
            ('duty_status_change', 'Duty Status Change'),
        ],
        help_text="Type of location change"
    )
    
    duty_status = models.CharField(
        max_length=20,
        choices=ELDLogEntry.DUTY_STATUS_CHOICES,
        help_text="Duty status at this location"
    )
    remarks = models.TextField(
        blank=True,
        help_text="Additional remarks about this location change"
    )
    
    auto_generated = models.BooleanField(
        default=True,
        help_text="Whether this remark was auto-generated"
    )
    is_duty_status_change = models.BooleanField(
        default=True,
        help_text="Whether this remark represents a duty status change"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this remark was created"
    )
    
    class Meta:
        ordering = ['daily_log', 'time']
        indexes = [
            models.Index(fields=['daily_log', 'time']),
            models.Index(fields=['location_type', 'time']),
        ]
        
        verbose_name = "ELD Location Remark"
        verbose_name_plural = "ELD Location Remarks"
    
    def __str__(self):
        return f"{self.time} - {self.location} ({self.get_location_type_display()})"