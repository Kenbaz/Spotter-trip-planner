# users/permissions.py

from rest_framework import permissions


class IsFleetManagerOrSuperAdmin(permissions.BasePermission):
    """
    Custom permission to only allow fleet managers or super admins to access certain views.
    """

    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.has_fleet_management_access()
        )


class IsSuperAdmin(permissions.BasePermission):
    """
    Custom permission to only allow super admins to access certain views.
    """

    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_super_admin
        )


class IsOwnerOrFleetManager(permissions.BasePermission):
    """
    Custom permission to allow users to edit their own profile,
    or fleet managers to edit any driver profile.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Read permissions for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions for the owner of the profile
        if obj == request.user:
            return True
        
        # Write permissions for fleet managers and super admins
        if request.user.has_fleet_management_access():
            return True
        
        return False


class IsDriverOrFleetManager(permissions.BasePermission):
    """
    Permission for driver-specific resources that can be accessed by:
    - The driver themselves
    - Fleet managers
    - Super admins
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # If the object has a 'driver' attribute, check if user is that driver
        if hasattr(obj, 'driver') and obj.driver == request.user:
            return True
        
        # Fleet managers and super admins have access
        if request.user.has_fleet_management_access():
            return True
        
        return False


class IsActiveDriver(permissions.BasePermission):
    """
    permission to ensure user is an active driver.
    """

    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_driver and 
            request.user.is_active_driver
        )


class CanManageDrivers(permissions.BasePermission):
    """
    Permission for actions that require driver management capabilities.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.can_manage_drivers()
        )