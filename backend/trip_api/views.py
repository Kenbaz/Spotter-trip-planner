# trip_api/views.py

from rest_framework import viewsets, status, generics, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
import logging
from datetime import datetime, date, timedelta
from django.db import models

from .models import Trip, ELDDailyLog, ELDLogEntry, ELDLocationRemark, ELDExportRecord
from .serializers import (
    TripCreationSerializer, TripDetailSerializer, TripListSerializer,
    TripCalculationRequestSerializer, TripCalculationResponseSerializer,
    ELDLogRequestSerializer, ELDLogResponseSerializer,
    GeocodingRequestSerializer, GeocodingResponseSerializer,
    RouteOptimizationRequestSerializer, RouteOptimizationResponseSerializer, ComplianceReportSerializer, CurrentDriverStatusSerializer, ELDDailyLogSerializer, ELDDailyLogSummarySerializer,
    ELDLogGenerationRequestSerializer, ELDLogGenerationResponseSerializer,
    ELDLogCertificationSerializer, ELDLogEditRequestSerializer,
    ELDExportRequestSerializer, ELDExportResponseSerializer
)
from users.models import SpotterCompany
from .services.route_planner import RoutePlannerService
from .services.hos_calculator import HOSCalculatorService
from .services.eld_generator import ELDGeneratorService
from .services.external_apis import ExternalAPIService
from .services.DriverCycleStatusService import DriverCycleStatusService
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

        print(f"Trip {trip.trip_id} created by driver {user.full_name}")
        print(f"  Starting conditions recorded: {trip.starting_cycle_hours}h cycle, {trip.starting_driving_hours}h driving")
    
    @action(detail=False, methods=['get'])
    def current_driver_status(self, request):
        """Get current driver's HOS status"""
        if not request.user.is_driver:
            return Response(
                {'error': 'Only drivers can access HOS status'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Get current status which also resets daily hours if its a new day
            status_data = DriverCycleStatusService.get_driver_status_for_trip_planning(request.user)

            return Response({
                'success': True,
                'current_status': status_data,
                'last_updated': timezone.now().isoformat()
            })
        except Exception as e:
            print(f"Error getting driver status for {request.user.username}: {str(e)}")
            return Response(
                {'error': f'Failed to get driver status: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def complete_trip(self, request, trip_id=None):
        """Mark trip as completed and update driver HOS status"""
        try:
            trip = self.get_object()

            if not self._can_modify_trip(request.user, trip):
                return Response(
                    {'error': 'You can only completed your own trips'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if trip.status == 'completed':
                return Response(
                    {'message': 'Trip is already completed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not trip.hos_periods.exists():
                return Response(
                    {'error': 'Trip must have calculated route and HOS periods before completion'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                trip.complete_trip()

                hours_summary = trip.get_trip_hours_summary()

                updated_status = DriverCycleStatusService.get_driver_status_for_trip_planning(request.user)

                print(f"Trip {trip.trip_id} completed by {request.user.full_name}")
                print(f"  Hours added: {hours_summary['driving_hours']}h driving, {hours_summary['on_duty_hours']}h on-duty")
                
                return Response({
                    'success': True,
                    'message': 'Trip completed successfully',
                    'hours_summary': hours_summary,
                    'updated_driver_status': updated_status
                })
                
        except Exception as e:
            logger.error(f"Error completing trip {trip_id}: {str(e)}")
            return Response(
                {'error': f'Failed to complete trip: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
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
            
            # Get current driver HOS status for route planning
            try:
                driver_status = DriverCycleStatusService.get_or_create_current_status(request.user)
                current_status = DriverCycleStatusService.get_driver_status_for_trip_planning(request.user)

            except Exception as e:
                logger.warning(f"Could not get driver status for route calculation: {str(e)}")
                driver_status = None
                current_status = None
            
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
                route_planner.save_route_plan(
                    trip,
                    calc_result['route_plan'],
                    calc_result['route_data'],
                )

                # Generate compliance report
                print(f"Generated trip planning compliance report for route calculation")
                hos_calc = HOSCalculatorService()
                compliance_report = hos_calc.generate_trip_planning_compliance_report(trip)
                

                # Update trip status and compliance
                print("Trip status being updated to 'Planned'")
                trip.status = 'Planned'
                print(f"Trip {trip.trip_id} status updated to 'Planned'")
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

                if current_status:
                    response_data['driver_status_impact'] = current_status

                if eld_logs:
                    response_data['eld_logs'] = eld_logs
                
                print(f"Route calculated for trip {trip.trip_id} by driver {request.user.full_name}")
                print(f"Final compliance status: {compliance_report.is_compliant}")
                
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
        
    @action(detail=False, methods=['patch'])
    def update_driver_status(self, request):
        """Manually update driver duty status"""
        if not request.user.is_driver:
            return Response(
                {'error': 'Only drivers can update their status'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_status = request.data.get('current_duty_status')
        status_start_time = request.data.get('current_status_start')
        
        if not new_status:
            return Response(
                {'error': 'current_duty_status is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            start_time = None
            if status_start_time:
                start_time = timezone.datetime.fromisoformat(status_start_time.replace('Z', '+00:00'))
            
            # update status
            updated_status = DriverCycleStatusService.manual_status_update(
                request.user, 
                new_status, 
                start_time
            )

            # Get formatted status for response
            status_data = DriverCycleStatusService.get_driver_status_for_trip_planning(request.user)
            
            return Response({
                'success': True,
                'message': f'Status updated to {new_status}',
                'current_status': status_data
            })
            
        except Exception as e:
            logger.error(f"Error updating status for {request.user.username}: {str(e)}")
            return Response(
                {'error': f'Failed to update status: {str(e)}'}, 
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
            
            if hasattr(trip, 'route') and trip.route:
                print(f"Trip has route with distance: {trip.route.total_distance_meters} meters")
            else:
                print("Trip has no associated route")

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
            
            logs_created = []
            logs_updated = []
            
            print("DEBUG: Saving ELD logs to database...")
            with transaction.atomic():
                for daily_log_data in eld_result['daily_logs']:
                    try:
                        log_date = datetime.fromisoformat(daily_log_data['log_date']).date()
                        
                        # Check if log already exists
                        existing_log = ELDDailyLog.objects.filter(
                            trip=trip,
                            log_date=log_date
                        ).first()
                        
                        if existing_log:
                            print(f"DEBUG: Updating existing log for {log_date}")
                            # Update existing log
                            updated_log = self._update_eld_log_from_data(existing_log, daily_log_data, trip)
                            logs_updated.append(updated_log)
                        else:
                            new_log = self._create_eld_log_from_data(daily_log_data, trip)
                            logs_created.append(new_log)
                            
                    except Exception as save_error:
                        print(f"DEBUG: Error saving daily log: {save_error}")
                        logger.error(f"Error saving daily log for {trip.trip_id}: {save_error}")
                        continue
            
            success_response = {
                'success': True,
                'trip_id': str(trip.trip_id),
                'total_days': eld_result.get('total_days', 0),
                'log_date_range': eld_result.get('log_date_range', {}),
                'daily_logs': eld_result.get('daily_logs', []),
                'summary': eld_result.get('summary', {}),
                'generated_at': eld_result.get('generated_at', timezone.now()),
                # Add database save info
                'database_saved': True,
                'logs_created': len(logs_created),
                'logs_updated': len(logs_updated)
            }
            
            if 'validation_results' in eld_result:
                success_response['validation_results'] = eld_result['validation_results']
            
            logger.info(f"ELD logs generated and saved for trip {trip.trip_id} by user {request.user.username}. Created: {len(logs_created)}, Updated: {len(logs_updated)}")
            
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
    def eld_logs(self, request, trip_id=None):
        """Get all ELD logs for a trip"""
        try:
            trip = self.get_object()

            if not self._can_access_trip(request.user, trip):
                return Response(
                    {'error': 'Permission denied - you can only view ELD logs for your own trips'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Fetch ELD logs for the trip
            eld_logs = ELDDailyLog.objects.filter(trip=trip).order_by('log_date')

            if not eld_logs.exists():
                return Response(
                    {
                        'success': False,
                        'trip_id': str(trip.trip_id),
                        'message': 'No ELD logs found for this trip. Generate logs first.',
                        'logs': []
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = ELDDailyLogSerializer(eld_logs, many=True)

            # Calculate summary statistics
            total_driving_hours = sum(log.total_driving_hours for log in eld_logs)
            total_on_duty_hours = sum(log.total_on_duty_hours for log in eld_logs)
            total_distance = sum(log.total_distance_miles for log in eld_logs)
            compliant_logs = sum(1 for log in eld_logs if log.is_compliant)
            certified_logs = sum(1 for log in eld_logs if log.is_certified)
            
            return Response(
                {
                    'success': True,
                    'trip_id': str(trip.trip_id),
                    'total_days': len(eld_logs),
                    'logs': serializer.data,
                    'summary': {
                        'total_driving_hours': float(total_driving_hours),
                        'total_on_duty_hours': float(total_on_duty_hours),
                        'total_distance_miles': float(total_distance),
                        'compliance_rate': round((compliant_logs / len(eld_logs)) * 100, 1),
                        'certification_rate': round((certified_logs / len(eld_logs)) * 100, 1),
                        'compliant_logs': compliant_logs,
                        'certified_logs': certified_logs
                    }
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error retrieving ELD logs for trip {trip_id}: {str(e)}")
            return Response(
                {'error': f'Failed to retrieve ELD logs: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def export_trip_eld_logs(self, request, trip_id=None):
        """Export all ELD logs for a trip"""
        try:
            trip = self.get_object()
            
            # Check permissions
            if not self._can_access_trip(request.user, trip):
                return Response(
                    {'error': 'Permission denied - you can only export ELD logs for your own trips'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Validate request data
            serializer = ELDExportRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            export_data = serializer.validated_data
            
            # Get ELD logs for this trip
            eld_logs = ELDDailyLog.objects.filter(trip=trip).order_by('log_date')
            
            if not eld_logs.exists():
                return Response(
                    {'error': 'No ELD logs found for this trip. Generate logs first.'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Apply date filtering if specified
            if export_data.get('date_range_start'):
                eld_logs = eld_logs.filter(log_date__gte=export_data['date_range_start'])
            
            if export_data.get('date_range_end'):
                eld_logs = eld_logs.filter(log_date__lte=export_data['date_range_end'])
            
            # Create export record
            export_record = ELDExportRecord.objects.create(
                trip=trip,
                export_format=export_data['export_format'],
                export_purpose=export_data['export_purpose'],
                date_range_start=eld_logs.first().log_date,
                date_range_end=eld_logs.last().log_date,
                file_name=f"trip_{trip.trip_id}_eld_logs.{export_data['export_format']}",
                exported_by=request.user,
                is_for_dot_inspection=export_data['export_purpose'] == 'dot_inspection',
                inspection_reference=export_data.get('inspection_reference', ''),
                notes=export_data.get('notes', '')
            )
            
            # Add logs to export record
            export_record.daily_logs.set(eld_logs)
            
            # Generate export data
            eld_generator = ELDGeneratorService()
            
            if export_data['export_format'] == 'pdf':
                export_result = eld_generator.export_log_to_pdf_data(trip)
            else:
                export_result = {
                    'trip_eld_export': {
                        'trip_id': str(trip.trip_id),
                        'export_metadata': {
                            'export_id': str(export_record.export_id),
                            'exported_at': export_record.exported_at.isoformat(),
                            'exported_by': request.user.full_name,
                            'export_purpose': export_data['export_purpose']
                        },
                        'daily_logs': ELDDailyLogSerializer(eld_logs, many=True).data
                    }
                }
            
            logger.info(f"Trip {trip.trip_id} ELD logs exported by {request.user.full_name} for {export_data['export_purpose']}")
            
            return Response(
                ELDExportResponseSerializer({
                    'success': True,
                    'export_id': export_record.export_id,
                    'file_name': export_record.file_name,
                    'export_format': export_data['export_format'],
                    'logs_exported': len(eld_logs),
                    'date_range': {
                        'start': str(eld_logs.first().log_date),
                        'end': str(eld_logs.last().log_date)
                    }
                }).data,
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error exporting trip ELD logs for {trip_id}: {str(e)}")
            return Response(
                ELDExportResponseSerializer({
                    'success': False,
                    'error': f'Failed to export trip ELD logs: {str(e)}'
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
            compliance_report = hos_calculator.generate_trip_planning_compliance_report(trip)

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

        # Get current driver status for context
        try:
            current_status = DriverCycleStatusService.get_driver_status_for_trip_planning(request.user)
        except Exception as e:
            logger.warning(f"Could not get driver status: {str(e)}")
            current_status = None

        # Paginate results
        page = self.paginate_queryset(trips)
        if page is not None:
            serializer = TripListSerializer(page, many=True, context={'request': request})
            response_data = self.get_paginated_response(serializer.data).data
            if current_status:
                response_data['driver_status'] = current_status
            return Response(response_data)
        
        serializer = TripListSerializer(trips, many=True, context={'request': request})
        response_data = {
            'success': True,
            'trips': serializer.data,
            'count': trips.count()
        }

        if current_status:
            response_data['driver_status'] = current_status
            
        return Response(response_data)
    
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
    
    def _create_eld_log_from_data(
        self,
        daily_log_data: dict,
        trip: Trip
        ) -> ELDDailyLog:
        """Create ELD log from generated data - WITH PROPER LINKING"""
        
        print("DEBUG: Creating ELD log with all related data...")
        
        # Get all HOS periods for this trip for matching
        hos_periods = list(trip.hos_periods.all().order_by('start_datetime'))
        print(f"DEBUG: Found {len(hos_periods)} HOS periods for matching")
        
        # Create the daily log with our perfect pre-calculated totals
        eld_log = ELDDailyLog.objects.create(
            trip=trip,
            log_date=datetime.fromisoformat(daily_log_data['log_date']).date(),
            driver=trip.driver,
            
            # Auto-populated header info
            driver_name=daily_log_data['driver_name'],
            driver_license_number=daily_log_data.get('driver_license', ''),
            driver_license_state=daily_log_data.get('driver_license_state', ''),
            employee_id=daily_log_data.get('employee_id', ''),
            
            carrier_name=daily_log_data['carrier_name'],
            carrier_address=daily_log_data.get('carrier_address', ''),
            dot_number=daily_log_data.get('dot_number', ''),
            mc_number=daily_log_data.get('mc_number', ''),
            
            vehicle_id=daily_log_data['vehicle_id'],
            license_plate=daily_log_data.get('license_plate', ''),
            vin=daily_log_data.get('vin', ''),
            vehicle_make_model=daily_log_data.get('vehicle_make_model', ''),
            
            # Our perfectly calculated daily totals
            total_off_duty_hours=daily_log_data['daily_totals']['off_duty'],
            total_sleeper_berth_hours=daily_log_data['daily_totals']['sleeper_berth'],
            total_driving_hours=daily_log_data['daily_totals']['driving'],
            total_on_duty_not_driving_hours=daily_log_data['daily_totals']['on_duty_not_driving'],
            total_on_duty_hours=daily_log_data['daily_totals']['total_on_duty'],
            total_distance_miles=sum(
                entry['vehicle_miles'] for entry in daily_log_data['log_entries']
            ),
            
            # Shipping documents
            bill_of_lading=daily_log_data.get('shipping_documents', {}).get('bill_of_lading', ''),
            manifest_number=daily_log_data.get('shipping_documents', {}).get('manifest_number', ''),
            pickup_number=daily_log_data.get('shipping_documents', {}).get('pickup_number', ''),
            delivery_receipt=daily_log_data.get('shipping_documents', {}).get('delivery_receipt', ''),
            commodity_description=daily_log_data.get('shipping_documents', {}).get('commodity_description', ''),
            
            # Metadata
            is_compliant=True,
            is_certified=False,
            auto_generated=True,
            manual_edits_count=0
        )
        
        print("DEBUG: ELD log created successfully")
        
        # Create log entries with HOS period links and store them for location remark linking
        print("DEBUG: Creating log entries with HOS period matching...")
        created_log_entries = []
        
        for i, entry_data in enumerate(daily_log_data['log_entries']):
            # Find the corresponding HOS period
            matching_hos_period = None
            
            try:
                # Try to match by start time and duty status
                entry_start_time = datetime.strptime(entry_data['start_time'], '%H:%M').time()
                entry_duty_status = entry_data['duty_status']
                
                for hos_period in hos_periods:
                    hos_start_time = hos_period.start_datetime.time()
                    
                    # Match by time (within 5 minutes) and duty status
                    if (abs((datetime.combine(datetime.today(), entry_start_time) - 
                            datetime.combine(datetime.today(), hos_start_time)).total_seconds()) <= 300 and
                        hos_period.duty_status == entry_duty_status):
                        matching_hos_period = hos_period
                        print(f"DEBUG: Matched entry {i+1} to HOS period {hos_period.id}")
                        break
                
                # If no exact match, try to match by sequence order
                if not matching_hos_period and i < len(hos_periods):
                    matching_hos_period = hos_periods[i]
                    print(f"DEBUG: Matched entry {i+1} to HOS period {matching_hos_period.id} by sequence")
                    
            except (ValueError, IndexError, AttributeError) as e:
                print(f"DEBUG: Error matching entry {i+1}: {e}")
                # Use the first available HOS period as fallback
                if hos_periods:
                    matching_hos_period = hos_periods[0]
                    print(f"DEBUG: Using fallback HOS period {matching_hos_period.id} for entry {i+1}")
            
            # Create the log entry
            log_entry = ELDLogEntry.objects.create(
                daily_log=eld_log,
                hos_period=matching_hos_period,  # REQUIRED FIELD
                start_time=datetime.strptime(entry_data['start_time'], '%H:%M').time(),
                end_time=datetime.strptime(entry_data['end_time'], '%H:%M').time(),
                duty_status=entry_data['duty_status'],
                duration_minutes=entry_data['duration_minutes'],
                duration_hours=entry_data['duration_hours'],
                start_location=entry_data.get('location', ''),
                end_location=entry_data.get('location', ''),
                vehicle_miles=entry_data.get('vehicle_miles', 0),
                remarks=entry_data.get('remarks', ''),
                
                # Grid positioning for ELD visualization
                grid_row=self._calculate_grid_row(entry_data['start_time']),
                grid_column_start=self._calculate_grid_column(entry_data['start_time']),
                grid_column_end=self._calculate_grid_column(entry_data['end_time']),
                
                is_compliant=True
            )
            
            # Store for location remark linking
            created_log_entries.append(log_entry)
        
        print(f"DEBUG: Created {len(daily_log_data['log_entries'])} log entries")
        
        # Create location remarks with proper log entry links
        print("DEBUG: Creating location remarks with log entry linking...")
        for remark_data in daily_log_data.get('location_remarks', []):
            # Find the best matching log entry for this remark
            matching_log_entry = None
            
            try:
                remark_time = datetime.strptime(remark_data['time'], '%H:%M').time()
                
                # Find the log entry that this remark time falls within
                for log_entry in created_log_entries:
                    if log_entry.start_time <= remark_time <= log_entry.end_time:
                        matching_log_entry = log_entry
                        print(f"DEBUG: Matched remark at {remark_data['time']} to log entry {log_entry.id}")
                        break
                
                # If no exact match, find the closest log entry by time
                if not matching_log_entry and created_log_entries:
                    closest_entry = min(created_log_entries, 
                                    key=lambda entry: abs((datetime.combine(datetime.today(), entry.start_time) - 
                                                            datetime.combine(datetime.today(), remark_time)).total_seconds()))
                    matching_log_entry = closest_entry
                    print(f"DEBUG: Matched remark at {remark_data['time']} to closest log entry {closest_entry.id}")
                    
            except (ValueError, AttributeError) as e:
                print(f"DEBUG: Error matching remark: {e}")
                # Use the first log entry as fallback
                if created_log_entries:
                    matching_log_entry = created_log_entries[0]
                    print(f"DEBUG: Using fallback log entry {matching_log_entry.id} for remark")
            
            # Create the location remark
            ELDLocationRemark.objects.create(
                daily_log=eld_log,
                log_entry=matching_log_entry,  # REQUIRED FIELD - now properly linked
                time=datetime.strptime(remark_data['time'], '%H:%M').time(),
                location=remark_data['location'],
                location_type=remark_data.get('location_type', 'duty_status_change'),
                duty_status=remark_data.get('duty_status', 'off_duty'),
                remarks=remark_data.get('remarks', ''),
                auto_generated=True,
                is_duty_status_change=remark_data.get('duty_status_change', True)
            )
        
        print(f"DEBUG: Created {len(daily_log_data.get('location_remarks', []))} location remarks")
        print("DEBUG: Complete ELD log created with all related data and proper linking")
        
        return eld_log
    
    def _calculate_grid_row(self, time_str: str) -> int:
        """Calculate grid row from time (0-10 for 24-hour period)"""
        try:
            time_obj = datetime.strptime(time_str, '%H:%M').time()
            hour = time_obj.hour
            # Each row represents 2 hours and 24 minutes (144 minutes)
            return min(hour // 2, 10)
        except:
            return 0

    def _calculate_grid_column(self, time_str: str) -> int:
        """Calculate grid column from time (0-7 for 15-minute increments)"""
        try:
            time_obj = datetime.strptime(time_str, '%H:%M').time()
            minute = time_obj.minute
            # Each column represents 15 minutes
            return min(minute // 15, 7)
        except:
            return 0
        
    def _update_eld_log_from_data(self, eld_log: ELDDailyLog, daily_log_data: dict, trip: Trip):
            """Update existing ELD log with new data"""
            
            # Only update if not certified
            if eld_log.is_certified:
                return eld_log
            
            # Update daily totals
            eld_log.total_off_duty_hours = daily_log_data['daily_totals']['off_duty']
            eld_log.total_sleeper_berth_hours = daily_log_data['daily_totals']['sleeper_berth']
            eld_log.total_driving_hours = daily_log_data['daily_totals']['driving']
            eld_log.total_on_duty_not_driving_hours = daily_log_data['daily_totals']['on_duty_not_driving']
            eld_log.total_on_duty_hours = daily_log_data['daily_totals']['total_on_duty']
            eld_log.total_distance_miles = sum(
                entry['vehicle_miles'] for entry in daily_log_data['log_entries']
            )
            eld_log.save()
            
            # Clear and recreate log entries
            eld_log.log_entries.all().delete()
            eld_log.location_remarks.all().delete()
            
            # Recreate entries (use same logic as create)
            for entry_data in daily_log_data['log_entries']:
                ELDLogEntry.objects.create(
                    daily_log=eld_log,
                    start_time=datetime.strptime(entry_data['start_time'], '%H:%M').time(),
                    end_time=datetime.strptime(entry_data['end_time'], '%H:%M').time(),
                    duty_status=entry_data['duty_status'],
                    duration_minutes=entry_data['duration_minutes'],
                    duration_hours=entry_data['duration_hours'],
                    start_location=entry_data.get('location', ''),
                    vehicle_miles=entry_data.get('vehicle_miles', 0),
                    remarks=entry_data.get('remarks', ''),
                    auto_generated_remarks=entry_data.get('remarks', ''),
                    grid_row=self._calculate_grid_row(entry_data['start_time']),
                    grid_column_start=self._calculate_grid_column(entry_data['start_time']),
                    grid_column_end=self._calculate_grid_column(entry_data['end_time'])
                )
            
            return eld_log
    
    def _determine_location_type(self, location: str) -> str:
        """Determine location type from location string"""
        location_lower = location.lower()
        
        if 'pickup' in location_lower:
            return 'pickup'
        elif 'delivery' in location_lower:
            return 'delivery'
        elif 'fuel' in location_lower:
            return 'fuel_stop'
        elif 'rest' in location_lower:
            return 'rest_area'
        else:
            return 'unknown'
    
    def _calculate_grid_row(self, time_str: str) -> int:
        """Calculate grid row for time visualization"""
        try:
            time_obj = datetime.strptime(time_str, '%H:%M').time()
            hour = time_obj.hour
            return hour // 2  # Each row represents 2 hours
        except ValueError:
            return 0
    
    def _calculate_grid_column(self, time_str: str) -> int:
        """Calculate grid column for time visualization"""
        try:
            time_obj = datetime.strptime(time_str, '%H:%M').time()
            minute = time_obj.minute
            return minute // 15  # Each column represents 15 minutes
        except ValueError:
            return 0
        



class CurrentDriverStatusView(generics.RetrieveAPIView):
    """
    Dedicated view for getting current driver's HOS status.
    """
    serializer_class = CurrentDriverStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """Get current user's driver cycle status"""
        if not self.request.user.is_driver:
            raise PermissionDenied("Only drivers can access cycle status")
        
        # Reset daily hours if new day and get current status
        cycle_status = DriverCycleStatusService.reset_daily_hours_if_needed(self.request.user)
        return cycle_status
    
    def retrieve(self, request, *args, **kwargs):
        """Override to return custom response format"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return Response({
            'success': True,
            'current_status': serializer.data,
            'last_updated': timezone.now().isoformat()
        })


class DriverStatusUpdateView(generics.UpdateAPIView):
    """
    View for manually updating driver duty status.
    Use this for status changes outside of trip completion.
    """
    serializer_class = CurrentDriverStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """Get current user's driver cycle status"""
        if not self.request.user.is_driver:
            raise PermissionDenied("Only drivers can update their status")
        
        return DriverCycleStatusService.get_or_create_current_status(self.request.user)
    
    def patch(self, request, *args, **kwargs):
        """Update only the current duty status"""
        cycle_status = self.get_object()
        
        new_status = request.data.get('current_duty_status')
        status_start_time = request.data.get('current_status_start')
        
        if not new_status:
            return Response(
                {'error': 'current_duty_status is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Parse status start time if provided
            start_time = None
            if status_start_time:
                start_time = timezone.datetime.fromisoformat(status_start_time.replace('Z', '+00:00'))
            
            # Update status using service
            updated_status = DriverCycleStatusService.manual_status_update(
                self.request.user, 
                new_status, 
                start_time
            )
            
            serializer = self.get_serializer(updated_status)
            
            return Response({
                'success': True,
                'message': f'Status updated to {new_status}',
                'current_status': serializer.data
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to update status: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

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


class ELDLogViewSet(viewsets.ModelViewSet):
    """ViewSet for managing ELD daily logs"""

    permission_classes = [IsAuthenticated]
    lookup_field = 'log_id'

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return ELDDailyLogSummarySerializer
        else:
            return ELDDailyLogSerializer
    
    def get_queryset(self):
        """Filter logs by driver"""
        user = self.request.user

        if user.is_driver and user.is_active_driver:
            queryset = ELDDailyLog.objects.filter(driver=user)
        else:
            queryset = ELDDailyLog.objects.none()
        
        # Add filtering by date range if provided
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(log_date__gte=date_from)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(log_date__lte=date_to)
            except ValueError:
                pass
        
        # Add filtering by compliance status
        compliance_filter = self.request.query_params.get('compliance')
        if compliance_filter == 'compliant':
            queryset = queryset.filter(is_compliant=True)
        elif compliance_filter == 'non_compliant':
            queryset = queryset.filter(is_compliant=False)
        
        # Add filtering by certification status
        certified_filter = self.query_params.get('certified')
        if certified_filter == 'certified':
            queryset = queryset.filter(is_certified=True)
        elif certified_filter == 'uncertified':
            queryset = queryset.filter(is_certified=False)
        
        return queryset.select_related('trip', 'driver').prefetch_related(
            'log_entries', 'location_remarks', 'compliance_violations'
        ).order_by('-log_date')
    
    def create(self, request, *args, **kwargs):
        """No direct creation of ELD logs"""
        return Response(
            {
                'error': 'ELD logs cannot be created directly. Use the generate_eld_logs action on trips instead'
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def destroy(self, request, *args, **kwargs):
        """Prevent deletion of certified logs"""
        log = self.get_object()
        
        if log.is_certified:
            return Response(
                {
                    'error': 'Cannot delete certified ELD logs'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        if log.driver != request.user and not request.user.is_fleet_manager:
            return Response(
                {
                    'error': 'You can only delete your own ELD logs.'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def certify_log(self, request, log_id=None):
        try:
            log = self.get_object()

            if log.driver != request.user:
                return Response(
                    {'error': 'You can only certify your own logs'},
                    status=status.HTTP_403_FORBIDDEN
                )

            if log.is_certified:
                return Response(
                    {'error': 'This log is already certified'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = ELDLogCertificationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Certify the log
            log.certify_log(
                signature_data=serializer.validated_data.get('certification_signature'),
            )

            return Response(
                {
                    'success': True,
                    'message': 'ELD log certified successfully',
                    'certified_at': log.certified_at.isoformat(),
                    'log_id': str(log.log_id)
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error certifying ELD log {log_id}: {str(e)}")
            return Response(
                {'error': f'Failed to certify log: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def edit_log_entry(self, request, log_id=None):
        try:
            log = self.get_object()

            if log.driver != request.user:
                return Response(
                    {'error': 'You can only edit your own log'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if log.is_certified:
                return Response(
                    {'error': 'Cannot edit certified logs'},
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = ELDLogEditRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Get log entry to edit
            try:
                log_entry = log.log_entries.get(id=serializer.validated_data['log_entry_id'])
            except ELDLogEntry.DoesNotExist:
                return Response(
                    {'error': 'Log entry not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Update the field
            field_name = serializer.validated_data['field_name']
            new_value = serializer.validated_data['new_value']
            edit_reason = serializer.validated_data['edit_reason']

            if not log_entry.was_manually_edited:
                log_entry.original_auto_data = {
                    field_name: str(getattr(log_entry, field_name))
                }
            
            # Apply edit
            setattr(log_entry, field_name, new_value)
            log_entry.manual_remarks = f"{log_entry.manual_remarks}\nEdit: {edit_reason}".strip()
            log_entry.was_manually_edited = True
            log_entry.save()

            logger.info(f"ELD log entry {log_entry.id} edited by driver {request.user.full_name}: {field_name} = {new_value}")
            
            return Response(
                {
                    'success': True,
                    'message': 'Log entry updated successfully',
                    'log_entry_id': log_entry.id,
                    'field_updated': field_name,
                    'new_value': new_value
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error editing ELD log entry: {str(e)}")
            return Response(
                {'error': f'Failed to edit log entry: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def export_log(self, request, log_id=None):
        try:
            log = self.get_object()

            # Check permissions
            if log.driver != request.user:
                return Response(
                    {'error': 'You can only export your own logs'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = ELDExportRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            export_data = serializer.validated_data

            # Create export record
            export_record = ELDExportRecord.objects.create(
                export_format=export_data['export_format'],
                export_purpose=export_data['export_purpose'],
                date_range_start=log.log_date,
                date_range_end=log.log_date,
                file_name=f"eld_log_{log.log_date}_{log.driver.username}.{export_data['export_format']}",
                exported_by=request.user,
                is_for_dot_inspection=export_data['export_purpose'] == 'dot_inspection',
                inspection_reference=export_data.get('inspection_reference', ''),
                notes=export_data.get('notes', '')
            )
            
            # Add the log to the export record
            export_record.daily_logs.add(log)
            
            # Generate export data based on format
            eld_generator = ELDGeneratorService()
            
            if export_data['export_format'] == 'pdf':
                # Generate PDF export data
                export_result = eld_generator.export_log_to_pdf_data(log.trip)
            else:
                # Generate JSON/other format
                export_result = {
                    'daily_log': ELDDailyLogSerializer(log).data,
                    'export_metadata': {
                        'export_id': str(export_record.export_id),
                        'exported_at': export_record.exported_at.isoformat(),
                        'exported_by': request.user.full_name,
                        'export_purpose': export_data['export_purpose']
                    }
                }
            
            logger.info(f"ELD log {log.log_id} exported by {request.user.full_name} for {export_data['export_purpose']}")
            
            return Response(
                ELDExportResponseSerializer({
                    'success': True,
                    'export_id': export_record.export_id,
                    'file_name': export_record.file_name,
                    'export_format': export_data['export_format'],
                    'logs_exported': 1,
                    'date_range': {
                        'start': str(log.log_date),
                        'end': str(log.log_date)
                    }
                }).data,
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error exporting ELD log {log_id}: {str(e)}")
            return Response(
                ELDExportResponseSerializer({
                    'success': False,
                    'error': f'Failed to export log: {str(e)}'
                }).data,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def compliance_summary(self, request):
        """Get compliance summary for driver's ELD logs"""
        user = request.user
        
        if not (user.is_driver and user.is_active_driver):
            return Response(
                {'error': 'Only active drivers can access compliance summary.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get date range from query params (default to last 30 days)
        try:
            date_to = date.today()
            date_from = date_to - timedelta(days=30)
            
            if request.query_params.get('date_from'):
                date_from = datetime.strptime(request.query_params['date_from'], '%Y-%m-%d').date()
            
            if request.query_params.get('date_to'):
                date_to = datetime.strptime(request.query_params['date_to'], '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get logs in date range
        logs = ELDDailyLog.objects.filter(
            driver=user,
            log_date__gte=date_from,
            log_date__lte=date_to
        ).prefetch_related('compliance_violations')
        
        # Calculate summary statistics
        total_logs = logs.count()
        compliant_logs = logs.filter(is_compliant=True).count()
        certified_logs = logs.filter(is_certified=True).count()
        total_violations = sum(log.violation_count for log in logs)
        
        avg_compliance_score = logs.aggregate(
            avg_score=models.Avg('compliance_score')
        )['avg_score'] or 0
        
        # Violation breakdown
        violation_types = {}
        for log in logs:
            for violation in log.compliance_violations.all():
                v_type = violation.get_violation_type_display()
                if v_type not in violation_types:
                    violation_types[v_type] = 0
                violation_types[v_type] += 1
        
        summary = {
            'date_range': {
                'start': str(date_from),
                'end': str(date_to)
            },
            'statistics': {
                'total_logs': total_logs,
                'compliant_logs': compliant_logs,
                'compliance_rate': round((compliant_logs / total_logs * 100) if total_logs > 0 else 0, 1),
                'certified_logs': certified_logs,
                'certification_rate': round((certified_logs / total_logs * 100) if total_logs > 0 else 0, 1),
                'total_violations': total_violations,
                'average_compliance_score': round(avg_compliance_score, 1)
            },
            'violation_breakdown': violation_types,
            'recent_logs': ELDDailyLogSummarySerializer(
                logs.order_by('-log_date')[:10], many=True
            ).data
        }
        
        return Response(summary, status=status.HTTP_200_OK)
            
