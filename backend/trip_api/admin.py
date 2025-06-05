#trip_api/admin.py

from django.contrib import admin
from .models import Trip, Route, Stops, HOSPeriod, ComplianceReport

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = [
        'trip_id', 
        'current_address', 
        'destination_address', 
        'departure_datetime',
        'is_hos_compliant',
        'created_at'
    ]
    list_filter = ['is_hos_compliant', 'created_at']
    search_fields = ['current_address', 'destination_address', 'trip_id']
    readonly_fields = ['trip_id', 'created_at', 'updated_at']
    ordering = ['-created_at']


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
