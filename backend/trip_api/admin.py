#trip_api/admin.py

from django.contrib import admin
from .models import Trip, Route, Stops, HOSPeriod, ComplianceReport
from users.models import DriverCycleStatus, DailyDrivingRecord
from .services.DriverCycleStatusService import DriverCycleStatusService
from django.utils.html import format_html


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = [
        'trip_id', 
        'current_address',
        'pickup_address', 
        'delivery_address', 
        'departure_datetime',
        'status',
        'starting_cycle_hours',
        'completed_at',
        'hos_updated',
        'trip_hours_summary',
        'is_hos_compliant',
        'created_at'
    ]
    list_filter = ['is_hos_compliant', 'hos_updated', 'departure_datetime', 'starting_duty_status', 'created_at', 'status']
    date_hierarchy = 'departure_datetime'
    search_fields = [
        'current_address', 'pickup_address', 'delivery_address', 
        'trip_id', 'driver__first_name', 'driver__last_name'
    ]
    readonly_fields = ['trip_id', 'created_at', 'updated_at', 'completed_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic information', {
            'fields': ('trip_id', 'driver', 'assigned_vehicle', 'company', 'status', 'completed_at')
        }),
        ('Locations', {
            'fields': [
                'current_address', 'pickup_address', 'delivery_address'
            ]
        }),
        ('Starting HOS Conditions', {
            'fields': [
                'starting_cycle_hours', 'starting_driving_hours', 
                'starting_on_duty_hours', 'starting_duty_status'
            ],
            'description': 'Driver HOS status when trip started (for compliance tracking)'
        }),
        ('HOS Management', {
            'fields': ['hos_updated'],
            'description': 'Track whether driver cycle status was updated'
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

    actions = ['mark_completed', 'recalculated_hos', 'force_hos_update']

    def trip_hours_summary(self, obj):
        """Display trip hours summary in admin"""
        if obj.status == 'completed' and obj.hos_updated:
            summary = obj.get_trip_hours_summary()
            return format_html(
                "Driving: {}h | On-duty: {}h",
                round(summary['driving_hours'], 1),
                round(summary['on_duty_hours'], 1)
            )
        return "Not completed"
    
    def mark_completed(self, request, queryset):
        """Admin action to mark trips as completed"""
        completed_count = 0
        for trip in queryset:
            if trip.status != 'completed':
                trip.complete_trip()
                completed_count += 1
        
        self.message_user(
            request, 
            f"Successfully completed {completed_count} trip(s) and updated driver HOS status."
        )
    mark_completed.short_description = "Mark selected trips as completed"
    
    def recalculate_hos(self, request, queryset):
        """Admin action to recalculate HOS for trips"""
        recalculated_count = 0
        for trip in queryset:
            if trip.status == 'completed':
                trip.hos_updated = False
                trip.save()
                DriverCycleStatusService.update_status_for_trip_completion(trip)
                recalculated_count += 1
        
        self.message_user(
            request, 
            f"Recalculated HOS status for {recalculated_count} trip(s)."
        )
    recalculate_hos.short_description = "Recalculate HOS for selected completed trips"
    
    def force_hos_update(self, request, queryset):
        """Force HOS update for selected trips"""
        updated_count = 0
        for trip in queryset:
            if trip.status == 'completed':
                DriverCycleStatusService.update_status_for_trip_completion(trip)
                trip.hos_updated = True
                trip.save()
                updated_count += 1
        
        self.message_user(
            request,
            f"Force updated HOS for {updated_count} trip(s)."
        )
    force_hos_update.short_description = "Force HOS update for selected trips"


@admin.register(DriverCycleStatus)
class DriverCycleStatusAdmin(admin.ModelAdmin):
    list_display = [
        'driver', 'today_date', 'today_driving_hours', 'today_on_duty_hours',
        'total_cycle_hours', 'current_duty_status', 'compliance_status'
    ]
    list_filter = ['current_duty_status', 'today_date']
    search_fields = ['driver__username', 'driver__first_name', 'driver__last_name']
    date_hierarchy = 'today_date'
    
    readonly_fields = [
        'remaining_cycle_hours', 'remaining_driving_hours_today', 
        'remaining_on_duty_hours_today', 'needs_immediate_break',
        'compliance_warnings_display'
    ]
    
    fieldsets = [
        ('Driver Information', {
            'fields': ['driver']
        }),
        ('Cycle Status', {
            'fields': [
                'cycle_start_date', 'total_cycle_hours', 'remaining_cycle_hours'
            ]
        }),
        ('Daily Status', {
            'fields': [
                'today_date', 'today_driving_hours', 'remaining_driving_hours_today',
                'today_on_duty_hours', 'remaining_on_duty_hours_today'
            ]
        }),
        ('Current Status', {
            'fields': [
                'current_duty_status', 'current_status_start',
                'needs_immediate_break', 'last_30min_break_end'
            ]
        }),
        ('Compliance', {
            'fields': ['compliance_warnings_display']
        })
    ]
    
    actions = ['reset_daily_hours', 'manual_status_update']
    
    def compliance_status(self, obj):
        """Display compliance status with color coding"""
        if obj.needs_immediate_break:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠️ Break Required</span>'
            )
        elif obj.remaining_driving_hours_today < 2:
            return format_html(
                '<span style="color: orange;">⚠️ Low Hours</span>'
            )
        else:
            return format_html(
                '<span style="color: green;">✅ Compliant</span>'
            )
    compliance_status.short_description = "Compliance"
    
    def compliance_warnings_display(self, obj):
        """Display compliance warnings in admin"""
        warnings = obj.compliance_warnings
        if not warnings:
            return "No warnings"
        
        warning_list = []
        for warning in warnings:
            warning_list.append(f"• {warning['message']}")
        
        return format_html("<br>".join(warning_list))
    compliance_warnings_display.short_description = "Compliance Warnings"
    
    def reset_daily_hours(self, request, queryset):
        """Reset daily hours for selected drivers"""
        reset_count = 0
        for cycle_status in queryset:
            DriverCycleStatusService.reset_daily_hours_if_needed(cycle_status.driver)
            reset_count += 1
        
        self.message_user(
            request,
            f"Reset daily hours for {reset_count} driver(s)."
        )
    reset_daily_hours.short_description = "Reset daily hours if new day"
    
    def manual_status_update(self, request, queryset):
        """Manually update status to off_duty"""
        updated_count = 0
        for cycle_status in queryset:
            DriverCycleStatusService.manual_status_update(
                cycle_status.driver, 
                'off_duty'
            )
            updated_count += 1
        
        self.message_user(
            request,
            f"Updated {updated_count} driver(s) to off_duty status."
        )
    manual_status_update.short_description = "Set status to off_duty"


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


@admin.register(DailyDrivingRecord)
class DailyDrivingRecordAdmin(admin.ModelAdmin):
    list_display = [
        'driver', 'date', 'total_driving_hours', 'total_on_duty_hours',
        'is_compliant', 'had_30min_break', 'had_daily_reset'
    ]
    list_filter = ['is_compliant', 'had_30min_break', 'had_daily_reset', 'date']
    search_fields = ['driver__username', 'driver__first_name', 'driver__last_name']
    date_hierarchy = 'date'
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['driver', 'date', 'is_compliant']
        }),
        ('Hours Tracking', {
            'fields': [
                'total_driving_hours', 'total_on_duty_hours', 'total_off_duty_hours'
            ]
        }),
        ('Break Tracking', {
            'fields': [
                'had_30min_break', 'break_start_time', 'break_end_time'
            ]
        }),
        ('Daily Reset Tracking', {
            'fields': [
                'had_daily_reset', 'reset_start_time', 'reset_end_time'
            ]
        }),
        ('Violations', {
            'fields': ['violations']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at']
        })
    ]
