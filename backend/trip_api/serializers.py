# trip_api/serializers.py

from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Trip, Route, Stops, HOSPeriod, ComplianceReport, ELDDailyLog, ELDLogEntry, ELDLocationRemark, ELDComplianceViolation, ELDExportRecord
from users.models import DriverVehicleAssignment, DriverCycleStatus
from users.serializers import DriverCycleStatusSerializer


User = get_user_model()


class TripCreationSerializer(serializers.ModelSerializer):
    """
    Enhanced serializer for creating new trips with current driver cycle status.
    Includes all location data, timing, and current HOS status for compliance planning.
    """
    
    # Current cycle information
    trip_start_cycle_hours = serializers.FloatField(
        min_value=0,
        max_value=70,
        help_text="Driver's cycle hours at trip start (for reference)"
    )
    trip_start_driving_hours = serializers.FloatField(
        min_value=0,
        max_value=11,
        help_text="Driver's daily driving hours at trip start (for reference)"
    )
    trip_start_on_duty_hours = serializers.FloatField(
        min_value=0,
        max_value=14,
        help_text="Driver's daily on-duty hours at trip start (for reference)"
    )
    trip_start_duty_status = serializers.ChoiceField(
        choices=[
            ('off_duty', 'Off Duty'),
            ('sleeper_berth', 'Sleeper Berth'),
            ('driving', 'Driving'),
            ('on_duty_not_driving', 'On Duty (Not Driving)'),
        ],
        help_text="Driver's duty status at trip start"
    )
    trip_start_status_time = serializers.DateTimeField(
        help_text="When driver started current duty status"
    )
    trip_start_last_break = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Driver's last 30-minute break end time (if any)"
    )
    
    class Meta:
        model = Trip
        fields = [
            # Trip locations
            'current_address', 'current_latitude', 'current_longitude',
            'pickup_address', 'pickup_latitude', 'pickup_longitude',
            'delivery_address', 'delivery_latitude', 'delivery_longitude',
            
            # Trip timing and settings
            'departure_datetime', 'pickup_duration_minutes', 'delivery_duration_minutes',
            'max_fuel_distance_miles',
            
            # Trip starting conditions
            'trip_start_cycle_hours', 'trip_start_driving_hours', 'trip_start_on_duty_hours',
            'trip_start_duty_status', 'trip_start_status_time', 'trip_start_last_break'
        ]
    
    def validate_departure_datetime(self, value):
        """Validate departure time is not in the past"""
        if value < timezone.now():
            raise serializers.ValidationError("Departure time cannot be in the past")
        return value
    
    def validate_current_latitude(self, value):
        """Validate latitude range"""
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_current_longitude(self, value):
        """Validate longitude range"""
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value
    
    def validate_pickup_latitude(self, value):
        """Validate pickup latitude range"""
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Pickup latitude must be between -90 and 90")
        return value
    
    def validate_pickup_longitude(self, value):
        """Validate pickup longitude range"""
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Pickup longitude must be between -180 and 180")
        return value
    
    def validate_delivery_latitude(self, value):
        """Validate delivery latitude range"""
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Delivery latitude must be between -90 and 90")
        return value
    
    def validate_delivery_longitude(self, value):
        """Validate delivery longitude range"""
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Delivery longitude must be between -180 and 180")
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        # Check if all three locations are different
        current_lat = attrs['current_latitude']
        current_lng = attrs['current_longitude']
        pickup_lat = attrs['pickup_latitude']
        pickup_lng = attrs['pickup_longitude']
        delivery_lat = attrs['delivery_latitude']
        delivery_lng = attrs['delivery_longitude']
        
        # Check pickup vs delivery
        if (abs(float(pickup_lat - delivery_lat)) < 0.01 and 
            abs(float(pickup_lng - delivery_lng)) < 0.01):
            raise serializers.ValidationError(
                "Pickup location and delivery location are too similar. Please ensure they are different locations."
            )
        
        # Check current vs delivery
        if (abs(float(current_lat - delivery_lat)) < 0.01 and 
            abs(float(current_lng - delivery_lng)) < 0.01):
            raise serializers.ValidationError(
                "Current location and delivery location are too similar. Please ensure they are different locations."
            )
        
        # Validate cycle data consistency
        start_cycle_hours = attrs['trip_start_cycle_hours']
        start_driving = attrs['trip_start_driving_hours']
        start_on_duty = attrs['trip_start_on_duty_hours']
        start_status_time = attrs['trip_start_status_time']
        
        if start_on_duty > start_cycle_hours:
            raise serializers.ValidationError(
                "Daily on-duty hours cannot exceed total cycle hours"
            )
        
        if start_driving > start_on_duty:
            raise serializers.ValidationError(
                "Daily driving hours cannot exceed daily on-duty hours"
            )
        
        if start_status_time > timezone.now():
            raise serializers.ValidationError(
                "Status start time cannot be in the future"
            )
        
        return attrs
    
    def create(self, validated_data):
        """Create trip and update driver cycle status"""
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Authentication required to create trips")
        
        starting_conditions = {
            'cycle_hours': validated_data.pop('trip_start_cycle_hours'),
            'driving_hours': validated_data.pop('trip_start_driving_hours'),
            'on_duty_hours': validated_data.pop('trip_start_on_duty_hours'),
            'duty_status': validated_data.pop('trip_start_duty_status'),
            'status_time': validated_data.pop('trip_start_status_time'),
            'last_break': validated_data.pop('trip_start_last_break', None),
        }
        
        # Create trip with remaining data
        trip = super().create(validated_data)
        
        # Update or create driver cycle status
        self._record_trip_starting_conditions(trip, starting_conditions)
        
        return trip
    
    def _record_trip_starting_conditions(self, trip, starting_conditions):
        """Record the driver's HOS status at the start of the trip"""
        # Store starting conditions on the trip model
        trip.starting_cycle_hours = starting_conditions['cycle_hours']
        trip.starting_driving_hours = starting_conditions['driving_hours']  
        trip.starting_on_duty_hours = starting_conditions['on_duty_hours']
        trip.starting_duty_status = starting_conditions['duty_status']
        trip.save()

        print(f"Recorded starting conditions for trip {trip.trip_id}")
        print(f"  Starting cycle hours: {trip.starting_cycle_hours}")
        print(f"  Starting driving hours: {trip.starting_driving_hours}")
        print(f"  Starting on-duty hours: {trip.starting_on_duty_hours}")


class CurrentDriverStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for retrieving driver's current HOS status.
    Used to populate trip creation forms with accurate current data.
    """
    remaining_cycle_hours = serializers.SerializerMethodField()
    remaining_driving_hours_today = serializers.SerializerMethodField()
    remaining_on_duty_hours_today = serializers.SerializerMethodField()
    needs_immediate_break = serializers.BooleanField(read_only=True)
    compliance_warnings = serializers.SerializerMethodField()

    class Meta:
        model = DriverCycleStatus
        fields = [
            'total_cycle_hours',
            'today_driving_hours',
            'today_on_duty_hours',
            'current_duty_status',
            'current_status_start',
            'last_30min_break_end',
            'today_date',

            'remaining_cycle_hours',
            'remaining_driving_hours_today',
            'remaining_on_duty_hours_today',
            'needs_immediate_break',
            'compliance_warnings'
        ]
    
    def get_remaining_cycle_hours(self, obj):
        return obj.remaining_cycle_hours
    
    def get_remaining_driving_hours_today(self, obj):
        return obj.remaining_driving_hours_today
    
    def get_remaining_on_duty_hours_today(self, obj):
        return obj.remaining_on_duty_hours_today
    
    def get_needs_immediate_break(self, obj):
        return obj.needs_immediate_break
    
    def get_compliance_warnings(self, obj):
        return obj.compliance_warnings


class TripCompletionSerializer(serializers.Serializer):
    """
    Serializer for trip completion response.
    """
    success = serializers.BooleanField()
    message = serializers.CharField()
    hours_summary = serializers.DictField()
    
    class Meta:
        fields = ['success', 'message', 'hours_summary']


class StopsSerializer(serializers.ModelSerializer):
    """
    Serializer for trip stops.
    """
    stop_type_display = serializers.CharField(source='get_stop_type_display', read_only=True)
    
    class Meta:
        model = Stops
        fields = [
            'id',
            'stop_type',
            'stop_type_display',
            'sequence_order',
            'address',
            'latitude',
            'longitude',
            'arrival_time',
            'departure_time',
            'duration_minutes',
            'distance_from_origin_miles',
            'distance_to_next_stop_miles',
            'is_required_for_compliance',
            'is_optimized_stop',
            'optimization_notes'
        ]


class HOSPeriodSerializer(serializers.ModelSerializer):
    """
    Serializer for HOS periods.
    """
    duty_status_display = serializers.CharField(source='get_duty_status_display', read_only=True)
    duration_hours = serializers.SerializerMethodField()
    
    class Meta:
        model = HOSPeriod
        fields = [
            'id',
            'duty_status',
            'duty_status_display',
            'start_datetime',
            'end_datetime',
            'duration_minutes',
            'duration_hours',
            'start_location',
            'end_location',
            'distance_traveled_miles',
            'is_compliant',
            'compliance_notes',
            'verified_by_driver'
        ]
    
    def get_duration_hours(self, obj):
        """Convert duration from minutes to hours"""
        return round(obj.duration_minutes / 60, 2)


class RouteSerializer(serializers.ModelSerializer):
    """
    Serializer for route data.
    """
    distance_miles = serializers.SerializerMethodField()
    duration_hours = serializers.SerializerMethodField()
    calculated_by_name = serializers.CharField(source='calculated_by.full_name', read_only=True)
    
    class Meta:
        model = Route
        fields = [
            'id',
            'route_geometry',
            'route_instructions',
            'total_distance_meters',
            'distance_miles',
            'total_duration_seconds',
            'duration_hours',
            'external_route_id',
            'api_provider',
            'calculated_by_name',
            'created_at'
        ]
    
    def get_distance_miles(self, obj):
        """Convert distance from meters to miles"""
        return round(obj.total_distance_meters * 0.000621371, 2)
    
    def get_duration_hours(self, obj):
        """Convert duration from seconds to hours"""
        return round(obj.total_duration_seconds / 3600, 2)


class ComplianceReportSerializer(serializers.ModelSerializer):
    """
    Serializer for compliance reports.
    """
    generated_by_name = serializers.CharField(source='generated_by.full_name', read_only=True)
    violations_count = serializers.SerializerMethodField()
    warnings_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ComplianceReport
        fields = [
            'id',
            'is_compliant',
            'compliance_score',
            'total_driving_hours',
            'total_on_duty_hours',
            'total_off_duty_hours',
            'violations',
            'warnings',
            'violations_count',
            'warnings_count',
            'required_30min_breaks',
            'scheduled_30min_breaks',
            'required_daily_resets',
            'scheduled_daily_resets',
            'generated_by_name',
            'reviewed_by_fleet_manager',
            'created_at'
        ]
    
    def get_violations_count(self, obj):
        """Count of violations"""
        return len(obj.violations) if obj.violations else 0
    
    def get_warnings_count(self, obj):
        """Count of warnings"""
        return len(obj.warnings) if obj.warnings else 0


class TripDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for trip data including all related objects.
    """
    stops = StopsSerializer(many=True, read_only=True)
    hos_periods = HOSPeriodSerializer(many=True, read_only=True)
    route = RouteSerializer(read_only=True)
    compliance_reports = ComplianceReportSerializer(many=True, read_only=True)
    
    # User context fields
    driver_name = serializers.CharField(source='driver.full_name', read_only=True)
    driver_username = serializers.CharField(source='driver.username', read_only=True)
    vehicle_info = serializers.SerializerMethodField()
    company_name = serializers.CharField(source='company.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    driver_cycle_status = DriverCycleStatusSerializer(source='driver.cycle_status')
    
    # Status and compliance
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_editable = serializers.ReadOnlyField()
    compliance_summary = serializers.ReadOnlyField()

    trip_legs = serializers.ReadOnlyField()
    
    class Meta:
        model = Trip
        fields = [
            'trip_id',
            'driver_name',
            'driver_username', 
            'vehicle_info',
            'company_name',
            'created_by_name',
            'status',
            'status_display',
            'is_editable',

            'current_address',
            'current_latitude',
            'current_longitude',

            'pickup_address',
            'pickup_latitude',
            'pickup_longitude',

            'delivery_address',
            'delivery_latitude',
            'delivery_longitude',

            'driver_cycle_status',

            'departure_datetime',
            'max_fuel_distance_miles',
            'pickup_duration_minutes',
            'delivery_duration_minutes',

            'total_distance_miles',
            'deadhead_distance_miles',
            'loaded_distance_miles',
            'total_driving_time',
            'deadhead_driving_time',
            'loaded_driving_time',
            'estimated_arrival_time',
            'estimated_pickup_time',
            'is_hos_compliant',
            'compliance_summary',

            'trip_legs',

            'created_at',
            'updated_at',

            'stops',
            'hos_periods',
            'route',
            'compliance_reports'
        ]
    
    def get_vehicle_info(self, obj):
        """Get vehicle information"""
        if obj.assigned_vehicle:
            return {
                'id': obj.assigned_vehicle.id,
                'unit_number': obj.assigned_vehicle.unit_number,
                'year': obj.assigned_vehicle.year,
                'make': obj.assigned_vehicle.make,
                'model': obj.assigned_vehicle.model,
                'vehicle_type': obj.assigned_vehicle.vehicle_type
            }
        return None


class TripListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for trip listings.
    """
    stops_count = serializers.SerializerMethodField()
    compliance_status = serializers.SerializerMethodField()
    driver_name = serializers.CharField(source='driver.full_name', read_only=True)
    vehicle_unit = serializers.CharField(source='assigned_vehicle.unit_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Trip
        fields = [
            'trip_id',
            'driver_name',
            'vehicle_unit',

            'current_address',
            'pickup_address', 
            'delivery_address',

            'departure_datetime',
            'estimated_arrival_time',
            'estimated_pickup_time',

            'total_distance_miles',
            'deadhead_distance_miles',
            'loaded_distance_miles',
            'total_driving_time',

            'status',
            'status_display',
            'is_hos_compliant',
            'stops_count',
            'compliance_status',
            'created_at'
        ]
    
    def get_stops_count(self, obj):
        """Get count of stops for this trip"""
        return obj.stops.count()
    
    def get_compliance_status(self, obj):
        """Get compliance status summary"""
        if obj.is_hos_compliant:
            return "Compliant"
        elif obj.compliance_reports.exists():
            latest_report = obj.compliance_reports.first()
            if latest_report and latest_report.violations:
                return f"Non-Compliant ({len(latest_report.violations)} violations)"
            else:
                return "Under Review"
        else:
            return "Not Analyzed"


class TripCalculationRequestSerializer(serializers.Serializer):
    """
    Serializer for trip calculation requests.
    """
    optimize_route = serializers.BooleanField(default=True)
    generate_eld_logs = serializers.BooleanField(default=False)
    include_fuel_optimization = serializers.BooleanField(default=True)
    
    def validate(self, attrs):
        """Validate calculation request parameters"""
        return attrs


class TripCalculationResponseSerializer(serializers.Serializer):
    """
    Serializer for trip calculation responses.
    """
    success = serializers.BooleanField()
    trip_id = serializers.UUIDField(read_only=True)
    feasibility = serializers.DictField()
    route_plan = serializers.DictField()
    route_data = serializers.DictField()
    optimization_applied = serializers.BooleanField(default=False)
    message = serializers.CharField(max_length=500)
    error = serializers.CharField(max_length=500, required=False)
    details = serializers.CharField(max_length=1000, required=False)


class ELDLogRequestSerializer(serializers.Serializer):
    """
    Serializer for ELD log generation requests.
    """
    export_format = serializers.ChoiceField(
        choices=[('json', 'JSON'), ('pdf_data', 'PDF Data')],
        default='json'
    )
    include_validation = serializers.BooleanField(default=True)


class ELDLogResponseSerializer(serializers.Serializer):
    """
    Serializer for ELD log responses.
    """
    success = serializers.BooleanField()
    trip_id = serializers.UUIDField()
    total_days = serializers.IntegerField()
    log_date_range = serializers.DictField()
    daily_logs = serializers.ListField()
    summary = serializers.DictField()
    validation_results = serializers.DictField(required=False)
    generated_at = serializers.DateTimeField()
    error = serializers.CharField(max_length=500, required=False)


class GeocodingRequestSerializer(serializers.Serializer):
    """
    Serializer for geocoding requests.
    """
    address = serializers.CharField(max_length=500)
    
    def validate_address(self, value):
        """Validate address is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Address cannot be empty")
        return value.strip()


class GeocodingResponseSerializer(serializers.Serializer):
    """
    Serializer for geocoding responses.
    """
    success = serializers.BooleanField()
    latitude = serializers.FloatField(required=False)
    longitude = serializers.FloatField(required=False)
    formatted_address = serializers.CharField(max_length=500, required=False)
    confidence = serializers.FloatField(required=False)
    country = serializers.CharField(max_length=100, required=False)
    region = serializers.CharField(max_length=100, required=False)
    error = serializers.CharField(max_length=500, required=False)


class RouteOptimizationRequestSerializer(serializers.Serializer):
    """
    Serializer for route optimization requests.
    """
    optimize_breaks = serializers.BooleanField(default=True)
    optimize_fuel_stops = serializers.BooleanField(default=True)
    optimize_daily_resets = serializers.BooleanField(default=True)
    max_optimization_distance = serializers.IntegerField(default=50, min_value=10, max_value=100)


class RouteOptimizationResponseSerializer(serializers.Serializer):
    """
    Serializer for route optimization responses.
    """
    success = serializers.BooleanField()
    optimized = serializers.BooleanField()
    route_plan = serializers.DictField()
    feasibility = serializers.DictField()
    optimizations_applied = serializers.ListField()
    message = serializers.CharField(max_length=500)
    error = serializers.CharField(max_length=500, required=False)


class VehicleAssignmentSerializer(serializers.ModelSerializer):
    """
    Serializer for current vehicle assignment display.
    """
    vehicle_info = serializers.SerializerMethodField()
    driver_name = serializers.CharField(source='driver.full_name', read_only=True)
    
    class Meta:
        model = DriverVehicleAssignment
        fields = [
            'id',
            'driver_name',
            'vehicle_info',
            'start_date',
            'assignment_type',
            'is_active'
        ]
    
    def get_vehicle_info(self, obj):
        """Get detailed vehicle information"""
        vehicle = obj.vehicle
        return {
            'id': vehicle.id,
            'unit_number': vehicle.unit_number,
            'year': vehicle.year,
            'make': vehicle.make,
            'model': vehicle.model,
            'vehicle_type': vehicle.vehicle_type,
            'maintenance_status': vehicle.maintenance_status
        }


class UserVehicleInfoSerializer(serializers.Serializer):
    """
    Serializer for user's current vehicle assignment info.
    """
    has_vehicle_assignment = serializers.BooleanField()
    current_assignment = VehicleAssignmentSerializer(required=False)
    available_vehicles = serializers.SerializerMethodField()
    
    def get_available_vehicles(self, obj):
        """Get list of available vehicles for assignment"""
        # This would be used by fleet managers
        from users.models import Vehicle
        available_vehicles = Vehicle.objects.filter(
            is_active=True,
            maintenance_status='active'
        ).exclude(
            driver_assignments__is_active=True
        )
        
        return [
            {
                'id': vehicle.id,
                'unit_number': vehicle.unit_number,
                'year': vehicle.year,
                'make': vehicle.make,
                'model': vehicle.model,
                'vehicle_type': vehicle.vehicle_type
            }
            for vehicle in available_vehicles
        ]


class ELDLogEntrySerializer(serializers.ModelSerializer):
    """Serializer for individual ELD log entries (duty periods)"""
    
    duty_status_label = serializers.CharField(read_only=True)
    duty_status_symbol = serializers.SerializerMethodField()
    duty_status_color = serializers.SerializerMethodField()
    
    class Meta:
        model = ELDLogEntry
        fields = [
            'id', 'start_time', 'end_time', 'duty_status', 'duty_status_label',
            'duty_status_symbol', 'duty_status_color', 'duration_minutes', 'duration_hours',
            'start_location', 'end_location', 'location_type',
             'vehicle_miles', 'remarks', 'auto_generated_remarks',
            'manual_remarks', 'grid_row', 'grid_column_start', 'grid_column_end',
            'is_compliant', 'compliance_notes', 'was_manually_edited'
        ]
        read_only_fields = [
            'duty_status_symbol', 'duty_status_color', 'duration_hours', 
            'auto_generated_remarks', 'was_manually_edited'
        ]
    
    def get_duty_status_symbol(self, obj):
        return obj.get_duty_status_symbol()
    
    def get_duty_status_color(self, obj):
        return obj.get_duty_status_color()


class ELDLocationRemarkSerializer(serializers.ModelSerializer):
    """Serializer for ELD location remarks"""
    
    location_type_display = serializers.CharField(source='get_location_type_display', read_only=True)
    duty_status_display = serializers.CharField(source='get_duty_status_display', read_only=True)
    
    class Meta:
        model = ELDLocationRemark
        fields = [
            'id', 'time', 'location', 'location_type', 'location_type_display', 'duty_status', 'duty_status_display', 'remarks', 'auto_generated', 'is_duty_status_change'
        ]
        read_only_fields = ['location_type_display', 'duty_status_display']


class ELDComplianceViolationSerializer(serializers.ModelSerializer):
    """Serializer for ELD compliance violations"""
    
    violation_type_display = serializers.CharField(source='get_violation_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.full_name', read_only=True)
    
    class Meta:
        model = ELDComplianceViolation
        fields = [
            'id', 'violation_type', 'violation_type_display', 'severity', 
            'severity_display', 'description', 'actual_value', 'limit_value',
            'violation_amount', 'is_resolved', 'resolution_notes', 'resolved_at',
            'resolved_by_name', 'detected_at'
        ]
        read_only_fields = [
            'violation_type_display', 'severity_display', 'resolved_by_name',
            'detected_at'
        ]


class ELDLocationRemarkSerializer(serializers.ModelSerializer):
    """Serializer for ELD location remarks"""
    
    location_type_display = serializers.CharField(source='get_location_type_display', read_only=True)
    duty_status_display = serializers.CharField(source='get_duty_status_display', read_only=True)
    
    class Meta:
        model = ELDLocationRemark
        fields = [
            'id', 'time', 'location', 'location_type', 'location_type_display', 'duty_status', 'duty_status_display', 'remarks',
            'auto_generated', 'is_duty_status_change'
        ]
        read_only_fields = ['location_type_display', 'duty_status_display']


class ELDComplianceViolationSerializer(serializers.ModelSerializer):
    """Serializer for ELD compliance violations"""
    
    violation_type_display = serializers.CharField(source='get_violation_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.full_name', read_only=True)
    
    class Meta:
        model = ELDComplianceViolation
        fields = [
            'id', 'violation_type', 'violation_type_display', 'severity', 
            'severity_display', 'description', 'actual_value', 'limit_value',
            'violation_amount', 'is_resolved', 'resolution_notes', 'resolved_at',
            'resolved_by_name', 'detected_at'
        ]
        read_only_fields = [
            'violation_type_display', 'severity_display', 'resolved_by_name',
            'detected_at'
        ]


class ELDDailyLogSerializer(serializers.ModelSerializer):
    """Serializer for ELD daily logs with nested entries and remarks"""
    
    log_entries = ELDLogEntrySerializer(many=True, read_only=True)
    location_remarks = ELDLocationRemarkSerializer(many=True, read_only=True)
    compliance_violations = ELDComplianceViolationSerializer(many=True, read_only=True)
    compliance_grade = serializers.SerializerMethodField()
    driver_name_display = serializers.CharField(source='driver.full_name', read_only=True)
    
    class Meta:
        model = ELDDailyLog
        fields = [
            # Basic identification
            'log_id', 'trip', 'log_date', 'driver', 'driver_name_display',
            
            # Auto-populated header info
            'driver_name', 'driver_license_number', 'driver_license_state', 'employee_id',
            'carrier_name', 'carrier_address', 'dot_number', 'mc_number',
            'vehicle_id', 'license_plate', 'vin', 'vehicle_make_model',
            
            # Daily totals
            'total_off_duty_hours', 'total_sleeper_berth_hours', 'total_driving_hours',
            'total_on_duty_not_driving_hours', 'total_on_duty_hours', 'total_distance_miles',
            
            # Shipping documents
            'bill_of_lading', 'manifest_number', 'pickup_number', 'delivery_receipt',
            'commodity_description', 'cargo_weight', 'is_hazmat',
            
            'is_compliant', 'compliance_score', 'compliance_grade', 'violation_count', 'warning_count',
            
            'is_certified', 'certified_at', 'certification_statement',
            
            'auto_generated', 'manual_edits_count', 'generated_at', 'updated_at',
            
            'log_entries', 'location_remarks', 'compliance_violations'
        ]
        read_only_fields = [
            'log_id', 'driver_name_display', 'compliance_grade', 'violation_count',
            'warning_count', 'manual_edits_count', 'generated_at', 'updated_at'
        ]
    
    def get_compliance_grade(self, obj):
        return obj.get_compliance_grade()


class ELDDailyLogSummarySerializer(serializers.ModelSerializer):
    """Simplified serializer for ELD daily log listings"""
    
    driver_name_display = serializers.CharField(source='driver.full_name', read_only=True)
    trip_id = serializers.CharField(source='trip.trip_id', read_only=True)
    compliance_grade = serializers.SerializerMethodField()
    
    class Meta:
        model = ELDDailyLog
        fields = [
            'log_id', 'log_date', 'driver_name_display', 'trip_id',
            'total_driving_hours', 'total_on_duty_hours', 'total_distance_miles',
            'is_compliant', 'compliance_score', 'compliance_grade', 'violation_count',
            'is_certified', 'certified_at', 'auto_generated'
        ]
        read_only_fields = ['compliance_grade']
    
    def get_compliance_grade(self, obj):
        return obj.get_compliance_grade()


class ELDLogGenerationRequestSerializer(serializers.Serializer):
    """Serializer for ELD log generation requests"""
    
    save_to_database = serializers.BooleanField(default=True)
    include_compliance_validation = serializers.BooleanField(default=True)
    auto_certify = serializers.BooleanField(default=False)
    export_format = serializers.ChoiceField(
        choices=[('json', 'JSON'), ('pdf_data', 'PDF Data')],
        default='json'
    )
    generate_missing_only = serializers.BooleanField(
        default=False,
        help_text="Only generate logs for days that don't already have ELD logs"
    )


class ELDLogGenerationResponseSerializer(serializers.Serializer):
    """Serializer for ELD log generation responses"""
    
    success = serializers.BooleanField()
    trip_id = serializers.UUIDField()
    logs_generated = serializers.IntegerField()
    logs_updated = serializers.IntegerField()
    total_days = serializers.IntegerField()
    log_date_range = serializers.DictField()
    daily_logs = ELDDailyLogSerializer(many=True, required=False)
    compliance_summary = serializers.DictField()
    warnings = serializers.ListField(child=serializers.CharField(), required=False)
    error = serializers.CharField(required=False)
    generated_at = serializers.DateTimeField()


class ELDLogCertificationSerializer(serializers.Serializer):
    """Serializer for ELD log certification requests"""
    
    certification_signature = serializers.CharField(
        max_length=5000,
        required=False,
        help_text="Digital signature data (base64 encoded image or signature hash)"
    )
    certification_notes = serializers.CharField(
        max_length=1000,
        required=False,
        help_text="Optional notes from driver about certification"
    )


class ELDLogEditRequestSerializer(serializers.Serializer):
    """Serializer for ELD log edit requests"""
    
    log_entry_id = serializers.IntegerField()
    field_name = serializers.ChoiceField(
        choices=[
            'start_time', 'end_time', 'duty_status', 'start_location', 
            'end_location', 'manual_remarks', 'odometer_start', 'odometer_end'
        ]
    )
    new_value = serializers.CharField(max_length=500)
    edit_reason = serializers.CharField(
        max_length=500,
        help_text="Reason for manual edit"
    )


class ELDExportRequestSerializer(serializers.Serializer):
    """Serializer for ELD log export requests"""
    
    export_format = serializers.ChoiceField(
        choices=[
            ('pdf', 'PDF Document'),
            ('csv', 'CSV Data'),
            ('json', 'JSON Data'),
            ('xml', 'XML Data'),
            ('dot_format', 'DOT Compliant Format')
        ],
        default='pdf'
    )
    export_purpose = serializers.ChoiceField(
        choices=[
            ('dot_inspection', 'DOT Inspection'),
            ('driver_record', 'Driver Personal Record'),
            ('fleet_audit', 'Fleet Management Audit'),
            ('compliance_review', 'Compliance Review'),
            ('backup', 'Data Backup'),
            ('other', 'Other Purpose')
        ],
        default='driver_record'
    )
    date_range_start = serializers.DateField(required=False)
    date_range_end = serializers.DateField(required=False)
    include_violations = serializers.BooleanField(default=True)
    include_location_remarks = serializers.BooleanField(default=True)
    inspection_reference = serializers.CharField(
        max_length=100,
        required=False,
        help_text="DOT inspection reference number (if applicable)"
    )
    notes = serializers.CharField(
        max_length=1000,
        required=False,
        help_text="Additional notes about this export"
    )


class ELDExportResponseSerializer(serializers.Serializer):
    """Serializer for ELD export responses"""
    
    success = serializers.BooleanField()
    export_id = serializers.UUIDField(required=False)
    file_name = serializers.CharField(required=False)
    file_size_bytes = serializers.IntegerField(required=False)
    download_url = serializers.URLField(required=False)
    export_format = serializers.CharField(required=False)
    logs_exported = serializers.IntegerField(required=False)
    date_range = serializers.DictField(required=False)
    error = serializers.CharField(required=False)
    expires_at = serializers.DateTimeField(required=False)