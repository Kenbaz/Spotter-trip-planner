#trip_api/admin.py

from django.contrib import admin
from .models import Trip, Route, Stops, HOSPeriod, ComplianceReport

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = [
        'trip_id', 
        'current_address',
        'pickup_address', 
        'delivery_address', 
        'departure_datetime',
        'is_hos_compliant',
        'created_at'
    ]
    list_filter = ['is_hos_compliant', 'created_at', 'status']
    search_fields = [
        'current_address', 'pickup_address', 'delivery_address', 
        'trip_id', 'driver__first_name', 'driver__last_name'
    ]
    readonly_fields = ['trip_id', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Trip Identification', {
            'fields': ('trip_id', 'driver', 'assigned_vehicle', 'company', 'status')
        }),
        ('Current Location', {
            'fields': ('current_address', 'current_latitude', 'current_longitude')
        }),
        ('Pickup Location', {
            'fields': ('pickup_address', 'pickup_latitude', 'pickup_longitude')
        }),
        ('Delivery Location', {
            'fields': ('delivery_address', 'delivery_latitude', 'delivery_longitude')
        }),
        ('Timing', {
            'fields': ('departure_datetime', 'pickup_duration_minutes', 'delivery_duration_minutes')
        }),
        ('Calculated Data', {
            'fields': (
                'total_distance_miles', 'deadhead_distance_miles', 'loaded_distance_miles',
                'total_driving_time', 'deadhead_driving_time', 'loaded_driving_time',
                'estimated_pickup_time', 'estimated_arrival_time', 'is_hos_compliant'
            ),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = [
        'trip', 
        'total_distance_meters', 
        'total_duration_seconds',
        'api_provider',
        'created_at'
    ]
    list_filter = ['api_provider', 'created_at']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(Stops)
class StopAdmin(admin.ModelAdmin):
    list_display = [
        'trip',
        'stop_type',
        'sequence_order',
        'address',
        'arrival_time',
        'duration_minutes',
        'is_required_for_compliance'
    ]
    list_filter = ['stop_type', 'is_required_for_compliance', 'trip']
    search_fields = ['address', 'trip__trip_id']
    ordering = ['trip', 'sequence_order']


@admin.register(HOSPeriod)
class HOSPeriodAdmin(admin.ModelAdmin):
    list_display = [
        'trip',
        'duty_status',
        'start_datetime',
        'end_datetime',
        'duration_minutes',
        'is_compliant'
    ]
    list_filter = ['duty_status', 'is_compliant', 'trip']
    search_fields = ['trip__trip_id', 'start_location', 'end_location']
    ordering = ['trip', 'start_datetime']


@admin.register(ComplianceReport)
class ComplianceReportAdmin(admin.ModelAdmin):
    list_display = [
        'trip',
        'is_compliant',
        'compliance_score',
        'total_driving_hours',
        'total_on_duty_hours',
        'created_at'
    ]
    list_filter = ['is_compliant', 'created_at']
    search_fields = ['trip__trip_id']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
