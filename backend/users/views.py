# users/views.py

from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django_filters.rest_framework import DjangoFilterBackend

from .serializers import (
    UserSerializer, CreateDriverSerializer, UpdateDriverSerializer,
    SpotterCompanySerializer, VehicleSerializer, DriverVehicleAssignmentSerializer,
    DriverSummarySerializer, VehicleSummarySerializer, LoginUserSerializer
)
from .models import SpotterCompany, Vehicle, DriverVehicleAssignment
from .permissions import IsFleetManagerOrSuperAdmin, IsOwnerOrFleetManager
from datetime import datetime, date


User = get_user_model()


class UserPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        
        user_serializer = LoginUserSerializer(self.user)
        data['user'] = user_serializer.data
        
        return data

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user management.
    - Drivers can view/update their own profile
    - Fleet managers can manage all drivers
    - Super admins have full access
    """
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UserPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_driver', 'is_fleet_manager', 'is_active_driver']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'employee_id']
    ordering_fields = ['username', 'first_name', 'last_name', 'date_joined']
    ordering = ['first_name', 'last_name']


    def get_serializer_class(self):
        if self.action == 'create':
            return CreateDriverSerializer
        elif self.action in ['update', 'partial_update']:
            return UpdateDriverSerializer
        elif self.action in ['driver_summary', 'available_drivers']:
            return DriverSummarySerializer
        
        return UserSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [IsFleetManagerOrSuperAdmin]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsOwnerOrFleetManager]
        else:
            permission_classes = [permissions.IsAuthenticated]

        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filter queryset based on user roles and permissions."""

        queryset = super().get_queryset()
        user = self.request.user

        if not user.has_fleet_management_access():
            queryset = queryset.filter(id=user.id)

        return queryset
    
    @action(detail=False, methods=['get'])
    def current_user(self, request):
        """
        Get the current authenticated user
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """
        Logout the user by blacklisting the refresh token
        """
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({"detail": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"message": "Successfully logged out"}, 
                status=status.HTTP_205_RESET_CONTENT
            )
        except Exception as e:
             return Response(
                {"error": "Invalid refresh token"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsFleetManagerOrSuperAdmin])
    def deactivate_driver(self, request, pk=None):
        """
        Deactivate a driver account
        """
        driver = self.get_object()
        if not driver.is_driver:
            return Response(
                {"error": "This user is not a driver."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        driver.is_active_driver = False
        driver.save()

        # deactivate all vehicle assignments for this driver
        DriverVehicleAssignment.objects.filter(
            driver=driver,
            is_active=True
        ).update(is_active=False)

        return Response({"message": f"Driver {driver.full_name} deactivated successfully."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsFleetManagerOrSuperAdmin])
    def activate_driver(self, request, pk=None):
        driver = self.get_object()
        if not driver.is_driver:
            return Response(
                {"error": "User is not a driver"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        driver.is_active_driver = True
        driver.save()
        
        return Response({"message": f"Driver {driver.full_name} activated successfully"})


    @action(detail=False, methods=['get'], permission_classes=[IsFleetManagerOrSuperAdmin])
    def drivers_summary(self, request):
        drivers = self.get_queryset().filter(is_driver=True)
        serializer = self.get_serializer(drivers, many=True)
        return Response(serializer.data)
    

    @action(detail=False, methods=['get'], permission_classes=[IsFleetManagerOrSuperAdmin])
    def available_drivers(self, request):
        # Drivers who are active and don't have an active vehicle assignment
        drivers = self.get_queryset().filter(
            is_driver=True,
            is_active_driver=True
        ).exclude(
            vehicle_assignments__is_active=True
        )
        serializer = self.get_serializer(drivers, many=True)
        return Response(serializer.data)
    

class SpotterCompanyViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Spotter company information.
    """
    queryset = SpotterCompany.objects.all()
    serializer_class = SpotterCompanySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        """
        Only super admins can create, update, or delete company info.
        Everyone can view.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsFleetManagerOrSuperAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['get'])
    def company_info(self, request):
        """
        Get the company information.
        """
        company = SpotterCompany.get_company_instance()
        serializer = self.get_serializer(company)
        return Response(serializer.data)


class VehicleViewSet(viewsets.ModelViewSet):
    """
    API endpoint for vehicle fleet management.
    """
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UserPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'maintenance_status', 'vehicle_type', 'year', 'make']
    search_fields = ['unit_number', 'vin', 'license_plate', 'make', 'model']
    ordering_fields = ['unit_number', 'year', 'make', 'model', 'created_at']
    ordering = ['unit_number']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsFleetManagerOrSuperAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        if self.action in ['vehicles_summary', 'available_vehicles']:
            return VehicleSummarySerializer
        return VehicleSerializer
    
    @action(detail=False, methods=['get'])
    def vehicles_summary(self, request):
        """
        Get a summary of all vehicles in the fleet.
        """
        vehicles = self.get_queryset()
        serializer = self.get_serializer(vehicles, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def available_vehicles(self, request):
        available_vehicles = self.get_queryset().filter(
            is_active=True,
            maintenance_status='active',
        ).exclude(driver_assignments__is_active=True)
        serializer = self.get_serializer(available_vehicles, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsFleetManagerOrSuperAdmin])
    def set_maintenance(self, request, pk=None):
        """Set a vehicle to maintenance status."""
        vehicle = self.get_object()
        maintenance_status = request.data.get('maintenance_status')

        if maintenance_status not in ['active', 'maintenance', 'out of service']:
            return Response(
                {"error": "Invalid maintenance status."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        vehicle.maintenance_status = maintenance_status
        vehicle.save()

        # if vehicle goes into maintenance, end active assignments
        if maintenance_status in ['maintenance', 'out of service']:
            DriverVehicleAssignment.objects.filter(
                vehicle=vehicle,
                is_active=True
            ).update(is_active=False)
        
        return Response({"message": f"Vehicle {vehicle.unit_number} status updated to {maintenance_status}."}, status=status.HTTP_200_OK)


class DriverVehicleAssignmentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for driver-vehicle assignments.
    """
    queryset = DriverVehicleAssignment.objects.all()
    serializer_class = DriverVehicleAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UserPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['driver', 'vehicle', 'is_active', 'assignment_type']
    ordering_fields = ['start_date', 'end_date', 'created_at']
    ordering = ['-start_date']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsFleetManagerOrSuperAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """
        Filter assignments based on user role.
        """
        queryset = super().get_queryset()
        user = self.request.user

        if not user.has_fleet_management_access():
            queryset = queryset.filter(driver=user)

        # Allow filtering by driver_id and vehicle_id via query params
        driver_id = self.request.query_params.get('driver_id')
        vehicle_id = self.request.query_params.get('vehicle_id')
        active_only = self.request.query_params.get('active_only')

        if driver_id:
            queryset = queryset.filter(driver__id=driver_id)
        if vehicle_id:
            queryset = queryset.filter(vehicle__id=vehicle_id)
        if active_only and active_only.lower() == 'true':
            queryset = queryset.filter(is_active=True)

        return queryset
    
    @action(detail=True, methods=['post'], permission_classes=[IsFleetManagerOrSuperAdmin])
    def end_assignment(self, request, pk=None):
        """
        End an active driver-vehicle assignment.
        """
        assignment = self.get_object()
        if not assignment.is_active:
            return Response(
                {"error": "This assignment is already inactive."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        end_date = request.data.get('end_date')
        if not end_date:
            try:
                assignment.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"error": "Invalid end date format. Use YYYY-MM-DD."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            assignment.end_date = date.today()
        
        assignment.is_active = False
        assignment.save()

        serializer = self.get_serializer(assignment)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def current_assignments(self, request):
        """Get all currently active assignments."""
        active_assignments = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(active_assignments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def my_current_assignments(self, request):
        """Get current user's active vehicle assignments."""
        if not request.user.is_driver:
            return Response(
                {"error": "User is not a driver"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        assignment = DriverVehicleAssignment.objects.filter(
            driver=request.user,
            is_active=True
        ).first()

        if assignment:
            serializer = self.get_serializer(assignment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"message": "No active assignments found for this driver."}, 
                status=status.HTTP_404_NOT_FOUND
            )