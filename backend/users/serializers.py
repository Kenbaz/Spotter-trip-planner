# users/serializers.py

from rest_framework import serializers
from .models import SpotterCompany, Vehicle, DriverVehicleAssignment
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class LoginUserSerializer(serializers.ModelSerializer):
    """
    Simplified user serializer for login responses.
    No dynamic field filtering to avoid authentication issues.
    """
    full_name = serializers.ReadOnlyField()
    role_display = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'role_display', 'is_driver', 'is_fleet_manager', 
            'is_super_admin', 'is_active_driver', 'employee_id', 'date_joined'
        ]
        read_only_fields = [
            'id', 'date_joined', 'full_name', 'role_display'
        ]
        

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for viewing user information.
    Different fields are shown based on the requesting user's role.
    """
    full_name = serializers.ReadOnlyField()
    role_display = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = User
        exclude = ('password', 'groups', 'user_permissions')
        read_only_fields = (
            'id', 'date_joined', 'last_login', 'is_staff', 'is_superuser',
            'created_by', 'full_name', 'role_display', 'created_by_name'
        )
    
    def get_fields(self):
        """
        Dynamically adjust fields based on requesting user's permissions
        """
        fields = super().get_fields()
        request = self.context.get('request')

        if request and request.user and request.user.is_authenticated:
            # For authenticated users
            if hasattr(request.user, 'has_fleet_management_access') and request.user.has_fleet_management_access():
                allowed_fields = {
                    'id', 'username', 'email', 'first_name', 'last_name',
                    'phone_number', 'emergency_contact_name', 'emergency_contact_phone',
                    'full_name', 'role_display', 'date_joined' 
                }
                fields = {key: field for key, field in fields.items() if key in allowed_fields}
            else:
                # For unauthenticated users
                safe_fields = {
                    'id', 'username', 'first_name', 'last_name', 'full_name', 
                    'role_display', 'is_driver', 'is_fleet_manager', 'is_super_admin',
                    'is_active_driver', 'employee_id', 'date_joined'
                }
                fields = {key: field for key, field in fields.items() if key in safe_fields}
        return fields


class CreateDriverSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new driver accounts.
    Only accessible by fleet managers and super admins.
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'username', 'password', 'confirm_password', 'email', 'first_name', 'last_name',
            'driver_license_number', 'driver_license_state', 'driver_license_expiration',
            'phone_number', 'emergency_contact_name', 'emergency_contact_phone',
            'employee_id', 'hire_date', 'is_driver', 'is_fleet_manager'
        ]

    def validate(self, data):
        """Validate password confirmation and role assignments"""
        if data['password'] != data.pop('confirm_password'):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        
        if 'is_driver' not in data:
            data['is_driver'] = True
        
        if data.get('is_super_admin', False):
            raise serializers.ValidationError({"is_super_admin": "Cannot create super admin through this endpoint."})
        
        return data
    
    def create(self, validated_data):
        """Create a new driver user"""
        request = self.context.get('request')
        
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            driver_license_number=validated_data.get('driver_license_number'),
            driver_license_state=validated_data.get('driver_license_state'),
            driver_license_expiration=validated_data.get('driver_license_expiration'),
            phone_number=validated_data.get('phone_number'),
            emergency_contact_name=validated_data.get('emergency_contact_name'),
            emergency_contact_phone=validated_data.get('emergency_contact_phone'),
            hire_date=validated_data.get('hire_date'),
            is_driver=validated_data.get('is_driver', True),
            is_fleet_manager=validated_data.get('is_fleet_manager', False),
            is_active_driver=False,
            created_by=request.user if request else None
        )
        return user


class UpdateDriverSerializer(serializers.ModelSerializer):
    """
    Serializer for updating existing driver accounts.
    Accessible by fleet managers and super admins.
    """

    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name',
            'driver_license_number', 'driver_license_state', 'driver_license_expiration',
            'phone_number', 'emergency_contact_name', 'emergency_contact_phone', 'hire_date', 'is_active_driver', 'is_driver', 'is_fleet_manager'
        ]

    def get_fields(self):
        """Adjust editable fields based on user permissions"""
        fields = super().get_fields()
        request = self.context.get('request')

        if request and request.user:
            if not request.user.has_fleet_management_access():
                allowed_fields = {
                    'email', 'first_name', 'last_name', 'phone_number',
                    'emergency_contact_name', 'emergency_contact_phone'
                }
                fields = {key: field for key, field in fields.items() if key in allowed_fields}
        
        return fields
    

class SpotterCompanySerializer(serializers.ModelSerializer):
    """
    Serializer for Spotter company information.
    Only super admins can modify this.
    """
    
    class Meta:
        model = SpotterCompany
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'created_by')

    def get_current_driver(self, obj):
        """Get the current driver assigned to this vehicle"""
        current_assignment = obj.driver_assignments.filter(is_active=True).first()
        if current_assignment:
            return {
                'id': current_assignment.driver.id,
                'full_name': current_assignment.driver.full_name,
                'username': current_assignment.driver.username
            }
        return None
    
    def create(self, validated_data):
        """Set created_by field when creating vehicle"""
        request = self.context.get('request')
        if request:
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class DriverVehicleAssignmentSerializer(serializers.ModelSerializer):
    """
    Serializer for driver-vehicle assignments.
    """
    driver_name = serializers.CharField(source='driver.full_name', read_only=True)
    vehicle_unit = serializers.CharField(source='vehicle.unit_number', read_only=True)
    vehicle_info = serializers.CharField(source='vehicle.__str__', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.full_name', read_only=True)

    class Meta:
        model = DriverVehicleAssignment
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'assigned_by')
    
    def validate(self, data):
        """Validate assignment business rules"""
        driver = data.get('driver')
        vehicle = data.get('vehicle')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        is_active = data.get('is_active', True)

        if driver and not driver.is_driver:
            raise serializers.ValidationError({"driver": "Selected user is not a driver."})
        
        if driver and not driver.is_active_driver:
            raise serializers.ValidationError({"driver": "Selected driver is not active."})
        
        if vehicle and not vehicle.is_available_for_assignment:
            raise serializers.ValidationError({"vehicle": "Selected vehicle is not available."})
        
        # Check for conflicting assignments
        if is_active and driver and start_date:
            conflicting_assignments = DriverVehicleAssignment.objects.filter(
                driver=driver,
                is_active=True
            )

            if self.instance:
                conflicting_assignments = conflicting_assignments.exclude(pk=self.instance.pk)
            
            if end_date:
                conflicting_assignments = conflicting_assignments.filter(
                    start_date__lte=end_date,
                    end_date__gte=start_date
                )
            else:
                conflicting_assignments = conflicting_assignments.filter(
                    start_date__lte=start_date
                )
            
            if conflicting_assignments.exists():
                raise serializers.ValidationError(
                    {"driver": "This driver already has an active assignment during the specified period."}
                )
        
        return data
    
    def create(self, validated_data):
        """Set assigned_by field when creating assignment"""
        request = self.context.get('request')
        if request:
            validated_data['assigned_by'] = request.user
        return super().create(validated_data)


class DriverSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for driver summary information.
    Used in lists and dropdowns.
    """
    full_name = serializers.ReadOnlyField()
    current_vehicle = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'employee_id', 'is_active_driver', 'current_vehicle']
    
    def get_current_vehicle(self, obj):
        """Get currently assigned vehicle"""
        assignment = obj.vehicle_assignments.filter(is_active=True).first()
        if assignment:
            return {
                'id': assignment.vehicle.id,
                'unit_number': assignment.vehicle.unit_number
            }
        return None


class VehicleSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for vehicle summary information.
    """
    current_driver = serializers.SerializerMethodField()
    is_available_for_assignment = serializers.ReadOnlyField()
    
    class Meta:
        model = Vehicle
        fields = ['id', 'unit_number', 'year', 'make', 'model', 'is_active', 'maintenance_status', 'current_driver', 'is_available_for_assignment']
    
    def get_current_driver(self, obj):
        """Get currently assigned driver"""
        assignment = obj.driver_assignments.filter(is_active=True).first()
        if assignment:
            return {
                'id': assignment.driver.id,
                'name': assignment.driver.full_name,
                'username': assignment.driver.username
            }
        return None
