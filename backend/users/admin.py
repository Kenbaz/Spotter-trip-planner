# users/admin.py

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import SpotterCompany, Vehicle, DriverVehicleAssignment, DriverCycleStatus, DailyDrivingRecord

User = get_user_model()


@admin.register(User)
class SpotterUserAdmin(BaseUserAdmin):
    list_display = (
        'username', 'full_name', 'email', 'role_display', 
        'employee_id', 'is_active_driver', 'hire_date', 'created_by'
    )
    list_filter = (
        'is_driver', 'is_fleet_manager', 'is_super_admin', 
        'is_active_driver', 'is_active', 'is_staff', 'hire_date'
    )
    search_fields = (
        'username', 'first_name', 'last_name', 'email', 'employee_id',
        'driver_license_number', 'phone_number'
    )
    ordering = ('first_name', 'last_name')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Spotter Role Information', {
            'fields': (
                'is_driver', 'is_fleet_manager', 'is_super_admin',
                'is_active_driver', 'employee_id', 'hire_date', 'created_by'
            )
        }),
        ('Driver License Information', {
            'fields': (
                'driver_license_number', 'driver_license_state', 
                'driver_license_expiration'
            ),
            'classes': ('collapse',)
        }),
        ('Contact Information', {
            'fields': (
                'phone_number', 'emergency_contact_name', 
                'emergency_contact_phone'
            ),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Spotter Information', {
            'fields': (
                'first_name', 'last_name', 'email', 'is_driver', 
                'is_fleet_manager', 'hire_date'
            )
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        
        # Only super admins can modify super admin status and Django permissions
        if not request.user.is_super_admin:
            readonly_fields.extend([
                'is_super_admin', 'is_staff', 'is_superuser', 
                'user_permissions', 'groups'
            ])
        
        readonly_fields.extend(['employee_id', 'created_by'])
        
        return readonly_fields
    
    def has_delete_permission(self, request, obj=None):
        if request.user.is_super_admin:
            return True
        return False
    
    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Super admins see all users, fleet managers see drivers only
        if not request.user.is_super_admin and request.user.is_fleet_manager:
            qs = qs.filter(is_driver=True)
        return qs


@admin.register(SpotterCompany)
class SpotterCompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'usdot_number', 'mc_number', 'city', 'state', 'phone_number', 'email')
    fields = (
        'name', 'usdot_number', 'mc_number',
        ('address', 'city', 'state', 'zip_code'),
        ('phone_number', 'email', 'website'),
        ('default_duty_cycle', 'timezone'),
        ('created_at', 'updated_at')
    )
    readonly_fields = ('created_at', 'updated_at')
    
    def has_add_permission(self, request):
        # Only allow one company instance
        return not SpotterCompany.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of company record
        return False


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        'unit_number', 'vehicle_info', 'vehicle_type', 
        'maintenance_status', 'current_driver_link', 'is_active', 'created_by'
    )
    list_filter = (
        'is_active', 'maintenance_status', 'vehicle_type', 
        'year', 'make', 'license_plate_state'
    )
    search_fields = (
        'unit_number', 'vin', 'license_plate', 'make', 'model'
    )
    ordering = ('unit_number',)
    
    fieldsets = (
        ('Vehicle Identification', {
            'fields': ('unit_number', 'vin', 'license_plate', 'license_plate_state')
        }),
        ('Vehicle Details', {
            'fields': ('year', 'make', 'model', 'vehicle_type')
        }),
        ('Status', {
            'fields': ('is_active', 'maintenance_status')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ('created_by', 'created_at', 'updated_at')
    
    def vehicle_info(self, obj):
        return f"{obj.year} {obj.make} {obj.model}"
    vehicle_info.short_description = 'Vehicle Info'
    
    def current_driver_link(self, obj):
        assignment = obj.driver_assignments.filter(is_active=True).first()
        if assignment:
            url = reverse('admin:users_user_change', args=[assignment.driver.id])
            return format_html('<a href="{}">{}</a>', url, assignment.driver.full_name)
        return 'Unassigned'
    current_driver_link.short_description = 'Current Driver'
    current_driver_link.admin_order_field = 'driver_assignments__driver__first_name'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DriverVehicleAssignment)
class DriverVehicleAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'driver_link', 'vehicle_link', 'assignment_type',
        'start_date', 'end_date', 'is_active', 'assigned_by'
    )
    list_filter = (
        'is_active', 'assignment_type', 'start_date', 'assigned_by'
    )
    search_fields = (
        'driver__username', 'driver__first_name', 'driver__last_name',
        'vehicle__unit_number', 'vehicle__vin'
    )
    ordering = ('-start_date',)
    
    fieldsets = (
        ('Assignment Details', {
            'fields': ('driver', 'vehicle', 'assignment_type')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date', 'is_active')
        }),
        ('Audit Information', {
            'fields': ('assigned_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ('assigned_by', 'created_at', 'updated_at')
    
    def driver_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.driver.id])
        return format_html('<a href="{}">{}</a>', url, obj.driver.full_name)
    driver_link.short_description = 'Driver'
    driver_link.admin_order_field = 'driver__first_name'
    
    def vehicle_link(self, obj):
        url = reverse('admin:users_vehicle_change', args=[obj.vehicle.id])
        return format_html('<a href="{}">{}</a>', url, obj.vehicle.unit_number)
    vehicle_link.short_description = 'Vehicle'
    vehicle_link.admin_order_field = 'vehicle__unit_number'
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Limit driver choices to active drivers only
        if 'driver' in form.base_fields:
            form.base_fields['driver'].queryset = User.objects.filter(
                is_driver=True, is_active_driver=True
            )
        
        # Limit vehicle choices to active vehicles only
        if 'vehicle' in form.base_fields:
            form.base_fields['vehicle'].queryset = Vehicle.objects.filter(
                is_active=True
            )
        
        return form
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Fleet managers see all assignments, drivers see only their own
        if not request.user.has_fleet_management_access() and request.user.is_driver:
            qs = qs.filter(driver=request.user)
        return qs


@admin.register(DriverCycleStatus)
class DriverCycleStatusAdmin(admin.ModelAdmin):
    list_display = (
        'driver', 'total_cycle_hours', 'remaining_cycle_hours',
        'today_driving_hours', 'today_on_duty_hours', 'current_duty_status',
        'needs_immediate_break_display', 'needs_daily_reset_display', 'updated_at'
    )
    list_filter = (
        'current_duty_status',
        'today_date', 'updated_at'
    )
    search_fields = (
        'driver__username', 'driver__first_name', 'driver__last_name'
    )
    readonly_fields = (
        'today_date', 'remaining_cycle_hours', 'remaining_driving_hours_today',
        'remaining_on_duty_hours_today', 'hours_since_last_break',
        'needs_immediate_break_display', 'needs_daily_reset_display', 'needs_cycle_reset_display',
        'compliance_warnings_display', 'updated_at'
    )
    
    fieldsets = (
        ('Driver Information', {
            'fields': ('driver',)
        }),
        ('Cycle Status (8-day period)', {
            'fields': (
                'cycle_start_date', 'total_cycle_hours', 'remaining_cycle_hours'
            )
        }),
        ('Daily Status', {
            'fields': (
                'today_date', 'today_driving_hours', 'today_on_duty_hours',
                'remaining_driving_hours_today', 'remaining_on_duty_hours_today'
            )
        }),
        ('Current Activity', {
            'fields': (
                'current_duty_status', 'current_status_start',
                'continuous_driving_since', 'last_30min_break_end'
            )
        }),
        ('Daily Reset Tracking', {
            'fields': (
                'last_daily_reset_start', 'last_daily_reset_end'
            )
        }),
        ('Compliance Status', {
            'fields': (
                'needs_immediate_break_display', 'needs_daily_reset_display', 'needs_cycle_reset_display',
                'hours_since_last_break', 'compliance_warnings_display'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        })
    )

    def needs_immediate_break_display(self, obj):
        """Display method for needs_immediate_break property"""
        return obj.needs_immediate_break
    needs_immediate_break_display.short_description = 'Needs Immediate Break'
    needs_immediate_break_display.boolean = True
    
    def needs_daily_reset_display(self, obj):
        """Display method for needs_daily_reset property"""
        return obj.needs_daily_reset
    needs_daily_reset_display.short_description = 'Needs Daily Reset'
    needs_daily_reset_display.boolean = True
    
    def needs_cycle_reset_display(self, obj):
        """Display method for needs_cycle_reset property"""
        return obj.needs_cycle_reset
    needs_cycle_reset_display.short_description = 'Needs Cycle Reset'
    needs_cycle_reset_display.boolean = True
    
    def compliance_warnings_display(self, obj):
        """Display method for compliance_warnings property"""
        warnings = obj.compliance_warnings
        if not warnings:
            return "No warnings"
        return f"{len(warnings)} warning(s)"
    compliance_warnings_display.short_description = 'Compliance Warnings'


@admin.register(DailyDrivingRecord)
class DailyDrivingRecordAdmin(admin.ModelAdmin):
    list_display = (
        'driver', 'date', 'total_driving_hours', 'total_on_duty_hours',
        'had_30min_break', 'had_daily_reset', 'is_compliant'
    )
    list_filter = (
        'date', 'had_30min_break', 'had_daily_reset', 'is_compliant'
    )
    search_fields = (
        'driver__username', 'driver__first_name', 'driver__last_name'
    )
    date_hierarchy = 'date'
    ordering = ['-date']


admin.site.site_header = "Spotter HOS Compliance Administration"
admin.site.site_title = "Spotter HOS Admin"
admin.site.index_title = "Spotter HOS Management"