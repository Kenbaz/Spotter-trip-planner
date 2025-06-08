# trip_api/serializers.py

from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Trip, Route, Stops, HOSPeriod, ComplianceReport
from users.models import DriverVehicleAssignment, Vehicle

User = get_user_model()


class TripCreationSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new trips with input validation.
    Driver and company are automatically set based on authenticated user.
    """
    
    class Meta:
        model = Trip
        fields = [
            'current_address',
            'current_latitude',
            'current_longitude',
            'destination_address',
            'destination_latitude',
            'destination_longitude',
            'departure_datetime',
            'max_fuel_distance_miles',
            'pickup_duration_minutes',
            'delivery_duration_minutes'
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
    
    def validate_destination_latitude(self, value):
        """Validate destination latitude range"""
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Destination latitude must be between -90 and 90")
        return value
    
    def validate_destination_longitude(self, value):
        """Validate destination longitude range"""
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Destination longitude must be between -180 and 180")
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        # Check if origin and destination are different
        origin_lat = attrs['current_latitude']
        origin_lng = attrs['current_longitude']
        dest_lat = attrs['destination_latitude']
        dest_lng = attrs['destination_longitude']
        
        # Calculate rough distance (simple check)
        lat_diff = abs(float(origin_lat - dest_lat))
        lng_diff = abs(float(origin_lng - dest_lng))
        
        if lat_diff < 0.01 and lng_diff < 0.01:  # Very close coordinates
            raise serializers.ValidationError(
                "Origin and destination locations are too similar. Please ensure they are different locations."
            )
        
        return attrs
    
    def create(self, validated_data):
        """Create trip with user context"""
        request = self.context.get('request')
        if request and request.user:
            return super().create(validated_data)
        else:
            raise serializers.ValidationError("Authentication required to create trips")


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
    
    # Status and compliance
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_editable = serializers.ReadOnlyField()
    compliance_summary = serializers.ReadOnlyField()
    
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
            'destination_address',
            'destination_latitude',
            'destination_longitude',
            'departure_datetime',
            'max_fuel_distance_miles',
            'pickup_duration_minutes',
            'delivery_duration_minutes',
            'total_distance_miles',
            'total_driving_time',
            'estimated_arrival_time',
            'is_hos_compliant',
            'compliance_summary',
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
            'destination_address',
            'departure_datetime',
            'estimated_arrival_time',
            'total_distance_miles',
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