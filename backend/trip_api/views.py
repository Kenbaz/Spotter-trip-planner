# test_api/views.py

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
import logging

from .models import Trip, Route, Stops, HOSPeriod, ComplianceReport
from .serializers import (
    TripCreationSerializer, TripDetailSerializer, TripListSerializer,
    TripCalculationRequestSerializer, TripCalculationResponseSerializer,
    ELDLogRequestSerializer, ELDLogResponseSerializer,
    GeocodingRequestSerializer, GeocodingResponseSerializer,
    RouteOptimizationRequestSerializer, RouteOptimizationResponseSerializer,
    StopsSerializer, HOSPeriodSerializer, RouteSerializer, ComplianceReportSerializer
)
from users.models import SpotterCompany
from .services.route_planner import RoutePlannerService
from .services.hos_calculator import HOSCalculatorService
from .services.eld_generator import ELDGeneratorService
from .services.external_apis import ExternalAPIService
from users.permissions import IsDriverOrFleetManager, IsActiveDriver
from users.models import DriverVehicleAssignment

logger = logging.getLogger(__name__)


class TripViewSet(viewsets.ModelViewSet):
    """ ViewSet for managing trips and trip calculations """

    queryset = Trip.objects.all()
    permission_classes = [IsAuthenticated, IsDriverOrFleetManager]
    lookup_field = 'trip_id'

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return TripCreationSerializer
        elif self.action == 'list':
            return TripListSerializer
        else:
            return TripDetailSerializer
    
    def get_queryset(self):
        queryset = Trip.objects.prefetch_related(
            'stops', 'hos_periods', 'route', 'compliance_reports'
        ).select_related('driver', 'assigned_vehicle', 'company')
        
        user = self.request.user
        
        if user.is_driver and user.is_active_driver:
            return queryset.filter(driver=user).order_by('-created_at')
        
        else:
            return queryset.none()
    
    def perform_create(self, serializer):
        user = self.request.user

        # Ensure user is an active driver
        if not (user.is_driver and user.is_active_driver):
            raise serializer.ValidationError(
                "Only active drivers can create trips"
            )
        
        # Get user's current vehicle assignment
        current_assignement = DriverVehicleAssignment.objects.filter(
            driver=user,
            is_active=True
        ).first()

        company = SpotterCompany.get_company_instance()

        trip = serializer.save(
            driver=user,
            created_by=user,
            company=company,
            assigned_vehicle=current_assignement.vehicle if current_assignement else None,
        )

        logger.info(f"Trip {trip.trip_id} created by driver {user.full_name}")
    
    def create(self, request, *args, **kwargs):
        """Create a new trip"""

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                self.perform_create(serializer)
                trip = serializer.instance

                # Return detailed trip data
                response_serializer = TripDetailSerializer(trip, context={'request': request})
                return Response(
                    {
                        'success': True,
                        'message': 'Trip created successfully',
                        'trip': response_serializer.data
                    },
                    status=status.HTTP_201_CREATED
                )
        except Exception as e:
            logger.error(f"Error creating trip: {str(e)}")
            return Response(
                {
                    'success': False,
                    'error': 'Failed to create trip',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def retrieve(self, request, *args, **kwargs):
        """ Retrieve a specific trip """
        try:
            trip = self.get_object()

            if not self._can_access_trip(request.user, trip):
                return Response(
                    {
                        'success': False,
                        'error': 'Permission denied - you can only view your own trips'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = self.get_serializer(trip)
            return Response({
                'success': True,
                'trip': serializer.data
            })
        
        except Trip.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': 'Trip not found'
                },
                status=status.HTTP_404_NOT_FOUND
            )
    
    def update(self, request, *args, **kwargs):
        """ Update an existing trip """
        try:
            trip = self.get_object()

            if not self._can_modify_trip(request.user, trip):
                return Response(
                    {
                        'success': False,
                        'error': 'Permission denied - you can only modify your own editable trips'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if not trip.is_editable:
                return Response(
                    {
                        'success': False,
                        'error': f'Trip cannot be modified in {trip.status} status'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Perform update
            partial = kwargs.pop('partial', False)
            serializer = self.get_serializer(trip, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)

            with transaction.atomic():
                serializer.save()
            
            return Response({
                'success': True,
                'message': 'Trip updated successfully',
                'trip': serializer.data
            })
        
        except Exception as e:
            logger.error(f"Error updating trip {kwargs.get('trip_id')}: {str(e)}")
            return Response(
                {
                    'success': False,
                    'error': 'Failed to update trip',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        """ Delete a trip """
        try:
            trip = self.get_object()

            if not self._can_modify_trip(request.user, trip):
                return Response(
                    {
                        'success': False,
                        'error': 'Permission denied - you can only delete your own trips'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if trip.status != 'draft':
                return Response(
                    {
                        'success': False,
                        'error': f'Trip cannot be deleted in {trip.status} status'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            trip_id = trip.trip_id
            trip.delete()

            logger.info(f"Trip {trip_id} deleted by user {request.user.username}")

            return Response({
                'success': True,
                'message': f'Trip {trip_id} deleted successfully'
            }, status=status.HTTP_204_NO_CONTENT)
        
        except Exception as e:
            logger.error(f"Error deleting trip {str(e)}")
            return Response(
                {
                    'success': False,
                    'error': 'Failed to delete trip',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsActiveDriver])
    def calculate_route(self, request, trip_id=None):
        """ Calculate route and HOS compliance for a trip """
        try:
            trip = self.get_object()

            if not self._can_modify_trip(request.user, trip):
                return Response(
                    {
                        'success': False,
                        'error': 'Permission denied - you can only calculate routes for your own trips'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Validate request data
            calc_serializer = TripCalculationRequestSerializer(data=request.data)
            calc_serializer.is_valid(raise_exception=True)
            calc_data = calc_serializer.validated_data

            # Initialize route planner service
            route_planner = RoutePlannerService()

            with transaction.atomic():
                # Calculate trip feasibility and route plan
                calc_result = route_planner.calculate_trip_feasibility(trip)

                if not calc_result['success']:
                    return Response(
                        TripCalculationResponseSerializer({
                            'success': False,
                            'trip_id': trip.trip_id,
                            'error': calc_result['error'],
                            'details': calc_result.get('details', ''),
                            'feasibility': {},
                            'route_plan': {},
                            'route_data': {},
                            'optimization_applied': False,
                            'message': 'Route calculation failed'
                        }).data,
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Apply route optimization if requested
                optimization_applied = False
                if calc_data.get('optimize_route', True):
                    optimization_result = route_planner.optimize_route_for_compliance(trip)
                    if optimization_result['success'] and optimization_result.get('optimized', False):
                        calc_result = optimization_result
                        optimization_applied = True
                
                # save route plan to db
                route, stops, hos_period = route_planner.save_route_plan(
                    trip,
                    calc_result['route_plan'],
                    calc_result['route_data'],
                )

                # Generate compliance report
                hos_calc = HOSCalculatorService()
                compliance_report = hos_calc.generate_compliance_report(trip)

                # Update trip status and compliance
                trip.status = 'Planned'
                trip.is_hos_compliant = compliance_report.is_compliant
                trip.save()

                # Generate ELD logs if requested
                eld_logs = None
                if calc_data.get('generate_eld_logs', False):
                    eld_generator = ELDGeneratorService()
                    eld_logs = eld_generator.generate_eld_log_data(trip)
                
                # Prepare response data
                response_data = {
                    'success': True,
                    'trip_id': trip.trip_id,
                    'feasibility': calc_result['feasibility'],
                    'route_plan': calc_result['route_plan'],
                    'route_data': calc_result['route_data'],
                    'optimization_applied': optimization_applied,
                    'message': 'Route calculation successful',
                }

                if eld_logs:
                    response_data['eld_logs'] = eld_logs
                
                if eld_logs:
                    response_data['eld_logs'] = eld_logs
                
                logger.info(f"Route calculated for trip {trip.trip_id} by driver {request.user.full_name}")
                
                return Response(
                    TripCalculationResponseSerializer(response_data).data,
                    status=status.HTTP_200_OK
                )
                
        except Exception as e:
            logger.error(f"Error calculating route for trip {trip_id} by user {request.user.username}: {str(e)}")
            return Response(
                TripCalculationResponseSerializer({
                    'success': False,
                    'trip_id': trip_id,
                    'error': 'Route calculation failed',
                    'details': str(e),
                    'feasibility': {},
                    'route_plan': {},
                    'route_data': {},
                    'optimization_applied': False,
                    'message': 'Internal server error'
                }).data,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsActiveDriver])
    def optimize_route(self, request, trip_id=None):
        """Optimizing an existing route for better compliance and efficiency"""
        try:
            trip = self.get_object()

            if not self._can_modify_trip(request.user, trip):
                return Response({
                    'success': False,
                    'error': 'Permission denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Validate request data
            optimize_serializer = RouteOptimizationRequestSerializer(data=request.data)
            optimize_serializer.is_valid(raise_exception=True)

            # Initialize route planner service
            route_planner = RoutePlannerService()

            # Perform route optimization
            optimization_result = route_planner.optimize_route_for_compliance(trip)

            response_data = {
                'success': optimization_result.get('success', False),
                'optimized': optimization_result.get('optimized', False),
                'route_plan': optimization_result.get('route_plan', {}),
                'feasibility': optimization_result.get('feasibility', {}),
                'optimizations_applied': optimization_result.get('optimizations_applied', []),
                'message': optimization_result.get('message', 'Optimization completed'),
                'error': optimization_result.get('error', '') if not optimization_result.get('success', False) else ''
            }
            
            if optimization_result['success'] and optimization_result.get('optimized', False):
                # Save optimized route plan
                with transaction.atomic():
                    # Clear existing route data
                    trip.stops.all().delete()
                    trip.hos_periods.all().delete()
                    if hasattr(trip, 'route'):
                        trip.route.delete()
                    
                    # Save new route plan
                    route_planner.save_route_plan(
                        trip,
                        optimization_result['route_plan'],
                        optimization_result.get('route_data', {})
                    )

                    # Update compliance
                    hos_calculator = HOSCalculatorService()
                    compliance_report = hos_calculator.generate_compliance_report(trip)
                    trip.is_hos_compliant = compliance_report.is_compliant
                    trip.save()
                
                logger.info(f"Route optimized for trip {trip.trip_id} by driver {request.user.full_name}")
            
            return Response(
                RouteOptimizationResponseSerializer(response_data).data,
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error optimizing route for trip {trip_id}: {str(e)}")
            return Response(
                RouteOptimizationResponseSerializer({
                    'success': False,
                    'optimized': False,
                    'route_plan': {},
                    'feasibility': {},
                    'optimizations_applied': [],
                    'message': 'Optimization failed',
                    'error': str(e)
                }).data,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def generate_eld_logs(self, request, trip_id=None):
        """Generate ELD logs for a trip"""
        try:
            trip = self.get_object()

            print(f"Trip status: {trip.status}")
            print(f"Trip has route: {hasattr(trip, 'route')}")
            print(f"Trip stops count: {trip.stops.count()}")
            print(f"Trip HOS periods count: {trip.hos_periods.count()}")
            print(f"Trip is HOS compliant: {trip.is_hos_compliant}")

            if not self._can_access_trip(request.user, trip):
                return Response(
                    {
                        'success': False,
                        'error': 'Permission denied - you can only generate ELD logs for your own trips'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

            # Validate request data
            eld_serializer = ELDLogRequestSerializer(data=request.data)
            eld_serializer.is_valid(raise_exception=True)
            eld_data = eld_serializer.validated_data

            # Initialize ELD generator service
            eld_generator = ELDGeneratorService()

            # Generate ELD logs
            if eld_data.get('export_format') == 'pdf_data':
                eld_result = eld_generator.export_log_to_pdf_data(trip)
            else:
                eld_result = eld_generator.generate_eld_log_data(trip)
            
            print(f"ELD result keys: {list(eld_result.keys())}")
            print(f"ELD result trip_id: {eld_result.get('trip_id', 'NOT FOUND')}")
            
            if not eld_result['success']:
                error_response = {
                    'success': False,
                    'trip_id': str(trip.trip_id),
                    'total_days': 0,
                    'log_date_range': {},
                    'daily_logs': [],
                    'summary': {},
                    'generated_at': timezone.now(),
                    'error': eld_result.get('error', 'ELD generation failed'),
                    'details': eld_result.get('details', '')
                }
                return Response(
                    ELDLogResponseSerializer(error_response).data,
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Add validation if requested
            if eld_data.get('include_validation', True):
                validation_results = eld_generator.validate_log_compliance(trip)
                eld_result['validation_results'] = validation_results
            
            success_response = {
                'success': True,
                'trip_id': str(trip.trip_id),
                'total_days': eld_result.get('total_days', 0),
                'log_date_range': eld_result.get('log_date_range', {}),
                'daily_logs': eld_result.get('daily_logs', []),
                'summary': eld_result.get('summary', {}),
                'generated_at': eld_result.get('generated_at', timezone.now()),
            }
            
            # Add validation results if present
            if 'validation_results' in eld_result:
                success_response['validation_results'] = eld_result['validation_results']
            
            logger.info(f"ELD logs generated for trip {trip.trip_id} by user {request.user.username}")
            
            return Response(
                ELDLogResponseSerializer(success_response).data,
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error generating ELD logs for trip {trip_id}: {str(e)}")
            return Response(
                ELDLogResponseSerializer({
                    'success': False,
                    'trip_id': str(trip_id),
                    'error': 'ELD log generation failed',
                    'total_days': 0,
                    'log_date_range': {},
                    'daily_logs': [],
                    'summary': {},
                    'generated_at': timezone.now(),
                    'details': str(e)
                }).data,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def compliance_report(self, request, trip_id=None):
        """Get compliance report for a trip"""
        try:
            trip = self.get_object()

            if not self._can_access_trip(request.user, trip):
                return Response(
                    {
                        'success': False,
                        'error': 'Permission denied - you can only view compliance reports for your own trips'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Generate compliance report
            hos_calculator = HOSCalculatorService()
            compliance_report = hos_calculator.generate_compliance_report(trip)

            # Update the generated_by field
            compliance_report.generated_by = request.user
            compliance_report.save()

            serializer = ComplianceReportSerializer(compliance_report)
            return Response({
                'success': True,
                'compliance_report': serializer.data
            })
        
        except Exception as e:
            logger.error(f"Error generating compliance report for trip {trip_id}: {str(e)}")
            return Response(
                {
                    'success': False,
                    'error': 'Failed to generate compliance report',
                    'details': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def my_trips(self, request):
        """Get current user's trips"""
        if not (request.user.is_driver and request.user.is_active_driver):
            return Response(
                {
                    'success': False,
                    'error': 'Only active drivers can view trips'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Filter trips by status
        status_filter = request.query_params.get('status')
        trips = Trip.objects.filter(driver=request.user)

        if status_filter:
            trips = trips.filter(status=status_filter)
        
        trips = trips.order_by('-created_at')

        # Paginate results
        page = self.paginate_queryset(trips)
        if page is not None:
            serializer = TripListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = TripListSerializer(trips, many=True, context={'request': request})
        return Response({
            'success': True,
            'trips': serializer.data,
            'count': trips.count()
        })
    
    def _can_access_trip(self, user, trip):
        """Check if user can access (view) the trip"""
        # Drivers can only access their own trips
        if user.is_driver and user.is_active_driver:
            return trip.driver == user
        
        return False
    
    def _can_modify_trip(self, user, trip):
        """Check if user can modify (edit/delete) the trip"""
        # Drivers can only modify their own trips
        if user.is_driver and user.is_active_driver:
            return trip.driver == user
        
        return False


class UtilityViewSet(viewsets.ViewSet):
    """
    ViewSet for utility functions like geocoding and API testing.
    Some endpoints require authentication, others are public.
    """

    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['geocode', 'reverse_geocode']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = []
        
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['post'])
    def geocode(self, request):
        """Geocode an address to get coordinates"""
        try:
            # Validate request data
            geocode_serializer = GeocodingRequestSerializer(data=request.data)
            geocode_serializer.is_valid(raise_exception=True)

            address = geocode_serializer.validated_data['address']

            # Initialize external API service
            external_api = ExternalAPIService()

            # Perform geocoding
            geocode_result = external_api.geocode_address(address)

            logger.info(f"Geocoding request for '{address}' by user {request.user.username}")

            return Response(
                GeocodingResponseSerializer(geocode_result).data,
                status=status.HTTP_200_OK if geocode_result['success'] else status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            logger.error(f"Error geocoding address: {str(e)}")
            return Response(
                GeocodingResponseSerializer({
                    'success': False,
                    'error': 'Geocoding failed',
                }).data,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def reverse_geocode(self, request):
        """Reverse geocode coordinates to get address"""
        try:
            latitude = float(request.data.get('latitude'))
            longitude = float(request.data.get('longitude'))

            if not (-90 <= latitude <= 90):
                raise ValueError("Invalid latitude")
            if not (-180 <= longitude <= 180):
                raise ValueError("Invalid longitude")
            
            # Initialize external API service
            external_api = ExternalAPIService()

            # Perform reverse geocoding
            reverse_result = external_api.reverse_geocode(latitude, longitude)

            logger.info(f"Reverse geocoding request for ({latitude}, {longitude}) by user {request.user.username}")

            return Response(
                GeocodingResponseSerializer(reverse_result).data,
                status=status.HTTP_200_OK if reverse_result['success'] else status.HTTP_400_BAD_REQUEST
            )

        except (ValueError, TypeError) as e:
            return Response(
                GeocodingResponseSerializer({
                    'success': False,
                    'error': 'Invalid coordinates provided'
                }).data,
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error reverse geocoding coordinates: {str(e)}")
            return Response(
                GeocodingResponseSerializer({
                    'success': False,
                    'error': 'Reverse geocoding failed'
                }).data,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def api_status(self, request):
        """Check the status of external APIs"""
        try:
            external_api = ExternalAPIService()
            status_result = external_api.get_api_status()

            return Response({
                'success': True,
                'api_status': status_result,
                'timestamp': timezone.now().isoformat()
            })
        
        except Exception as e:
            logger.error(f"Error checking API status: {str(e)}")
            return Response(
                {
                    'success': False,
                    'error': 'Failed to check API status',
                    'details': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def test_route_calculation(self, request):
        """Test route calculation between two points (public for testing)"""
        try:
            origin_lat = float(request.data.get('origin_latitude'))
            origin_lng = float(request.data.get('origin_longitude'))
            dest_lat = float(request.data.get('destination_latitude'))
            dest_lng = float(request.data.get('destination_longitude'))
            
            # Validate coordinates
            if not all(-90 <= lat <= 90 for lat in [origin_lat, dest_lat]):
                raise ValueError("Invalid latitude values")
            if not all(-180 <= lng <= 180 for lng in [origin_lng, dest_lng]):
                raise ValueError("Invalid longitude values")
            
            # Initialize external API service
            external_api = ExternalAPIService()
            
            # Calculate route
            route_result = external_api.get_route_data(
                origin=(origin_lat, origin_lng),
                destination=(dest_lat, dest_lng)
            )
            
            return Response({
                'success': route_result['success'],
                'route_data': route_result,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK if route_result['success'] else status.HTTP_400_BAD_REQUEST)
            
        except (ValueError, TypeError) as e:
            return Response(
                {
                    'success': False,
                    'error': 'Invalid coordinate data provided'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error testing route calculation: {str(e)}")
            return Response(
                {
                    'success': False,
                    'error': 'Route calculation test failed',
                    'details': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
