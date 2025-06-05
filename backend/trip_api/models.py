# trip_api/models.py

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class Trip(models.Model):
    trip_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    current_address = models.CharField(max_length=500)
    current_latitude = models.DecimalField(max_digits=10, decimal_places=7)
    current_longitude = models.DecimalField(max_digits=10, decimal_places=7)

    destination_address = models.CharField(max_length=500)
    destination_latitude = models.DecimalField(max_digits=10, decimal_places=7)
    destination_longitude = models.DecimalField(max_digits=10, decimal_places=7)

    departure_datetime = models.DateTimeField()

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

    total_distance_miles = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Total distance of the trip in miles"
    )
    total_driving_time = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Total driving time for the trip in hours"
    )
    estimated_arrival_time = models.DateTimeField(
        null=True, blank=True,
        help_text="Estimated arrival time at the destination"
    )
    is_hos_compliant = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Trip {self.trip_id} from {self.current_address} to {self.destination_address}"
    

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

    # external api route data
    route_geometry = models.JSONField(help_text="GeoJSON LineString geometry")
    route_instructions = models.JSONField(help_text="Turn-by-turn directions")

    total_distance_meters = models.PositiveBigIntegerField()
    total_duration_seconds = models.PositiveBigIntegerField()

    external_route_id = models.CharField(max_length=100, blank=True)
    api_provider = models.CharField(max_length=50, default='openrouteservice')

    created_at = models.DateTimeField(auto_now_add=True)

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
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)

    arrival_time = models.DateTimeField()
    departure_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(help_text="Duration of the stop in minutes")

    distance_from_origin_miles = models.DecimalField(max_digits=8, decimal_places=2)
    distance_to_next_stop_miles = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    is_required_for_compliance = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['trip', 'sequence_order']
        unique_together = ('trip', 'sequence_order')
    
    def __str__(self):
        return f"{self.get_stop_type_display()} - {self.address}"


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
    
    related_stop = models.ForeignKey(Stops, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['trip', 'start_datetime']
    
    def __str__(self):
        return f"{self.get_duty_status_display()} - {self.start_datetime} to {self.end_datetime}"


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
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Compliance Report for {self.trip} - {'Compliant' if self.is_compliant else 'Non-Compliant'}"