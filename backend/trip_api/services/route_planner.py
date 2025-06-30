# trip_api/services/route_planner.py

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from decimal import Decimal
from django.core.cache import cache, caches
import logging
from ..models import Trip, Route, Stops, HOSPeriod
from .hos_calculator import HOSCalculatorService
from .external_apis import ExternalAPIService
from users.models import DriverCycleStatus
import polyline


logger = logging.getLogger(__name__)


class RoutePlannerService:
    """
    Service class for planning HOS-compliant routes with automatic break insertion.
    Coordinates with HOS calculator to ensure regulatory compliance.
    """
    
    def __init__(self):
        self.hos_calculator = HOSCalculatorService()
        self.external_api = ExternalAPIService()

        # Default speeds and constants
        self.average_highway_speed_mph = 65
        self.average_city_speed_mph = 35
        self.fuel_stop_duration_minutes = 45
        self.mandatory_break_duration_minutes = 30
        self.daily_reset_duration_hours = 10

        self.max_fuel_distance_default = 1000
        self.break_location_buffer_miles = 50 # Miles around calculated break points
    
    def _get_cache(self, cache_name='default'):
        """Get cache instance with fallback"""
        try:
            if hasattr(caches, cache_name) and cache_name in caches:
                return caches[cache_name]
            else:
                return cache
        except Exception:
            return cache
    
    def calculate_trip_feasibility(self, trip: Trip) -> Dict[str, any]:
        """
        Analyze trip feasibility and returns Dict with feasibility analysis and route plan
        """
        try:
            # Get driver's current cycle status
            try:
                driver_status = trip.driver.cycle_status
                has_cycle_data = True
            except DriverCycleStatus.DoesNotExist:
                driver_status = None
                has_cycle_data = False

            # Current location → Pickup location (DEADHEAD)
            deadhead_route = self.external_api.get_route_data(
                origin=(float(trip.current_latitude), float(trip.current_longitude)),
                destination=(float(trip.pickup_latitude), float(trip.pickup_longitude))
            )

            if not deadhead_route['success']:
                return {
                    'success': False,
                    'error': 'Unable to calculate deadhead route',
                    'details': deadhead_route.get('error', 'Unknown routing error')
                }
            
            # Pickup location → Delivery location (LOADED)
            loaded_route = self.external_api.get_route_data(
                origin=(float(trip.pickup_latitude), float(trip.pickup_longitude)),
                destination=(float(trip.delivery_latitude), float(trip.delivery_longitude))
            )

            if not loaded_route['success']:
                return {
                    'success': False,
                    'error': 'Unable to calculate loaded route',
                    'details': loaded_route.get('error', 'Unknown routing error')
                }
            
            # Combine deadhead and loaded routes
            combined_route_data = self._combine_route_legs(deadhead_route, loaded_route)
            
            # Extract total route information
            total_distance_miles = deadhead_route['distance_miles'] + loaded_route['distance_miles']

            total_driving_hours = deadhead_route['duration_hours'] + loaded_route['duration_hours']

            total_distance_miles = Decimal(str(total_distance_miles))
            total_driving_hours = Decimal(str(total_driving_hours))

            # Update trip with calculated values
            trip.deadhead_distance_miles = Decimal(str(deadhead_route['distance_miles']))
            trip.loaded_distance_miles = Decimal(str(loaded_route['distance_miles']))
            trip.total_distance_miles = total_distance_miles
            
            trip.deadhead_driving_time = Decimal(str(deadhead_route['duration_hours']))
            trip.loaded_driving_time = Decimal(str(loaded_route['duration_hours']))
            trip.total_driving_time = total_driving_hours


            # Check feasibility with HOS calculator
            if has_cycle_data:
                feasibility_report = self.hos_calculator.validate_trip_feasibility_with_current_status(
                    trip,
                    total_driving_hours,
                    driver_status
                )
            else:
                # Fallback to basic feasibility without current status
                feasibility_report = self.hos_calculator.validate_trip_feasibility(
                    trip,
                    total_driving_hours
                )
                feasibility_report['warning'] = 'No current HOS status provided - using basic validation only'


            # Generate detailed route plan with stops and breaks
            route_plan = self._generate_three_location_route_plan_with_status(
                trip, 
                deadhead_route, 
                loaded_route, 
                feasibility_report,
                driver_status
            )

            return {
                'success': True,
                'feasibility': feasibility_report,
                'route_plan': route_plan,
                'route_data': combined_route_data,
                'leg_details': {
                    'deadhead': deadhead_route,
                    'loaded': loaded_route
                },
                'current_status_considered': has_cycle_data
            }
            
        except Exception as e:
            logger.error(f"Error calculating trip feasibility for trip {trip.trip_id}: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to calculate trip feasibility',
                'details': str(e)
            }
    
    def _combine_route_legs(self, deadhead_route: Dict, loaded_route: Dict) -> Dict:
        """
        Combine deadhead and loaded route data into a single route representation
        """
        return {
            'success': True,
            'provider': 'openrouteservice',
            'route_id': f"combined_{deadhead_route.get('route_id', '')}_{loaded_route.get('route_id', '')}",
            
            # Combined totals
            'distance_meters': deadhead_route['distance_meters'] + loaded_route['distance_meters'],
            'distance_miles': deadhead_route['distance_miles'] + loaded_route['distance_miles'],
            'duration_seconds': deadhead_route['duration_seconds'] + loaded_route['duration_seconds'],
            'duration_hours': deadhead_route['duration_hours'] + loaded_route['duration_hours'],
            
            # Route structure
            'legs': [
                {
                    'leg_type': 'deadhead',
                    'origin_lat': deadhead_route['origin_lat'],
                    'origin_lng': deadhead_route['origin_lng'],
                    'destination_lat': deadhead_route['destination_lat'],
                    'destination_lng': deadhead_route['destination_lng'],
                    'distance_miles': deadhead_route['distance_miles'],
                    'duration_hours': deadhead_route['duration_hours'],
                    'geometry': deadhead_route['geometry'],
                    'instructions': deadhead_route['instructions'],
                    'waypoints': deadhead_route['waypoints'],
                },
                {
                    'leg_type': 'loaded',
                    'origin_lat': loaded_route['origin_lat'],
                    'origin_lng': loaded_route['origin_lng'],
                    'destination_lat': loaded_route['destination_lat'],
                    'destination_lng': loaded_route['destination_lng'],
                    'distance_miles': loaded_route['distance_miles'],
                    'duration_hours': loaded_route['duration_hours'],
                    'geometry': loaded_route['geometry'],
                    'instructions': loaded_route['instructions'],
                    'waypoints': loaded_route['waypoints'],
                }
            ],
            
            # Combined geometry
            'combined_geometry': {
                'type': 'combined_polylines',
                'deadhead_polyline': deadhead_route['geometry'],
                'loaded_polyline': loaded_route['geometry']
            }
        }
    
    def _generate_three_location_route_plan_with_status(
        self, 
        trip: Trip, 
        deadhead_route: Dict, 
        loaded_route: Dict, 
        feasibility_report: Dict,
        driver_status: 'DriverCycleStatus' = None
    ) -> Dict[str, any]:
        """
        Generate detailed route plan for three-location trip structure 
        WITH automatic break insertion, fuel stops, AND HOS periods
        """
        route_plan = {
            'stops': [],
            'hos_periods': [],
            'total_duration_hours': 0,
            'estimated_pickup_time': None,
            'estimated_arrival': None,
            'optimization_notes': [],
            'current_status_impact': {}
        }

        current_time = trip.departure_datetime
        current_distance = Decimal('0')
        stop_sequence = 1

        # Handle driver status context
        if driver_status:
            route_plan['current_status_impact'] = {
                'cycle_hours_used': driver_status.total_cycle_hours,
                'remaining_cycle_hours': driver_status.remaining_cycle_hours,
                'today_driving_hours': driver_status.today_driving_hours,
                'remaining_driving_today': driver_status.remaining_driving_hours_today,
                'today_on_duty_hours': driver_status.today_on_duty_hours,
                'remaining_on_duty_today': driver_status.remaining_on_duty_hours_today,
                'current_duty_status': driver_status.current_duty_status,
                'needs_immediate_break': driver_status.needs_immediate_break,
                'needs_daily_reset': driver_status.needs_daily_reset,
                'needs_cycle_reset': driver_status.needs_cycle_reset,
                'compliance_warnings': driver_status.compliance_warnings
            }

            # Critical warning for immediate break
            if driver_status.needs_immediate_break:
                route_plan['optimization_notes'].append(
                    "CRITICAL: Driver must take 30-minute break immediately before starting trip"
                )

        # ===== STEP 1: Create basic route stops =====
        
        # 1. Trip start location
        route_plan['stops'].append({
            'type': 'trip_start',
            'sequence_order': stop_sequence,
            'address': trip.current_address,
            'latitude': float(trip.current_latitude),
            'longitude': float(trip.current_longitude),
            'arrival_time': current_time.isoformat(),
            'departure_time': current_time.isoformat(),
            'duration_minutes': 0,
            'distance_from_origin': 0,
            'is_required_for_compliance': False,
            'break_reason': None
        })
        stop_sequence += 1

        # 2. Pickup location
        deadhead_duration = timedelta(hours=deadhead_route['duration_hours'])
        pickup_arrival = current_time + deadhead_duration
        current_distance += Decimal(str(deadhead_route['distance_miles']))

        route_plan['stops'].append({
            'type': 'pickup',
            'sequence_order': stop_sequence,
            'address': trip.pickup_address,
            'latitude': float(trip.pickup_latitude),
            'longitude': float(trip.pickup_longitude),
            'arrival_time': pickup_arrival.isoformat(),
            'departure_time': (pickup_arrival + timedelta(minutes=trip.pickup_duration_minutes)).isoformat(),
            'duration_minutes': trip.pickup_duration_minutes,
            'distance_from_origin': float(current_distance),
            'is_required_for_compliance': False,
            'break_reason': None
        })
        stop_sequence += 1

        # 3. Delivery location
        pickup_departure = pickup_arrival + timedelta(minutes=trip.pickup_duration_minutes)
        loaded_duration = timedelta(hours=loaded_route['duration_hours'])
        delivery_arrival = pickup_departure + loaded_duration
        current_distance += Decimal(str(loaded_route['distance_miles']))

        route_plan['stops'].append({
            'type': 'delivery',
            'sequence_order': stop_sequence,
            'address': trip.delivery_address,
            'latitude': float(trip.delivery_latitude),
            'longitude': float(trip.delivery_longitude),
            'arrival_time': delivery_arrival.isoformat(),
            'departure_time': (delivery_arrival + timedelta(minutes=trip.delivery_duration_minutes)).isoformat(),
            'duration_minutes': trip.delivery_duration_minutes,
            'distance_from_origin': float(current_distance),
            'is_required_for_compliance': False,
            'break_reason': None
        })

        # ===== STEP 1.5: CALCULATE AND INSERT FUEL STOPS =====
        
        total_driving_hours = deadhead_route['duration_hours'] + loaded_route['duration_hours']
        total_distance_miles = float(current_distance)
        
        # Check if fuel stops are needed based on max fuel distance
        max_fuel_distance = trip.max_fuel_distance_miles or 1000
        
        logger.info(f"⛽ Checking fuel stops: max distance = {max_fuel_distance} miles, total trip = {total_distance_miles:.1f} miles")
        
        if total_distance_miles > max_fuel_distance:
            fuel_stops_needed = int(total_distance_miles // max_fuel_distance)
            logger.info(f"⛽ Fuel stops needed: {fuel_stops_needed}")
            
            # Generate fuel stops
            for i in range(1, fuel_stops_needed + 1):
                fuel_distance = i * max_fuel_distance
                
                # Don't add fuel stop if it's too close to pickup or delivery (within 100 miles)
                pickup_distance = deadhead_route['distance_miles']
                delivery_distance = total_distance_miles
                
                too_close_to_pickup = abs(fuel_distance - pickup_distance) < 100
                too_close_to_delivery = abs(fuel_distance - delivery_distance) < 100
                
                if not too_close_to_pickup and not too_close_to_delivery and fuel_distance < total_distance_miles:
                    # Find location for this fuel stop
                    fuel_location = self._find_break_location_with_coordinates(
                        trip, fuel_distance, deadhead_route, loaded_route
                    )
                    
                    # Calculate fuel stop timing (rough estimate)
                    fuel_timing = self._calculate_break_timing(
                        current_time, fuel_distance, total_distance_miles,
                        deadhead_duration, loaded_duration, trip.pickup_duration_minutes
                    )
                    
                    # Create fuel stop
                    fuel_stop = {
                        'type': 'fuel',
                        'sequence_order': 0,  # Will be updated when we re-sort
                        'address': fuel_location['address'].replace('Rest Area', 'Fuel Station & Truck Stop'),
                        'latitude': fuel_location['latitude'],
                        'longitude': fuel_location['longitude'],
                        'arrival_time': fuel_timing['arrival_time'].isoformat(),
                        'departure_time': (fuel_timing['arrival_time'] + timedelta(minutes=45)).isoformat(),
                        'duration_minutes': 45,  # Standard fuel stop duration
                        'distance_from_origin': fuel_distance,
                        'is_required_for_compliance': False,
                        'break_reason': f'Fuel stop #{i} - refueling after {fuel_distance:.0f} miles'
                    }
                    
                    # Add fuel stop to route plan
                    route_plan['stops'].append(fuel_stop)
                    
                    logger.info(f"⛽ Added fuel stop #{i} at mile {fuel_distance:.1f}")
                    
                    # Add optimization note
                    route_plan['optimization_notes'].append(
                        f"Added fuel stop #{i} at mile {fuel_distance:.1f} for refueling"
                    )
            
            logger.info(f"⛽ Total fuel stops added: {len([s for s in route_plan['stops'] if s['type'] == 'fuel'])}")
        else:
            logger.info(f"⛽ No fuel stops needed: trip distance {total_distance_miles:.1f} miles < max fuel distance {max_fuel_distance} miles")

        # ===== STEP 2: HOS COMPLIANCE CHECK AND BREAK INSERTION =====
        
        logger.info(f"🔍 HOS compliance check: {total_driving_hours:.2f} hours driving, {total_distance_miles:.1f} miles")
        
        # Check if 30-minute break is required (8+ hours driving without break)
        if total_driving_hours > 8.0:
            logger.info(f"⚠️ Break required: {total_driving_hours:.2f} hours exceeds 8-hour limit")
            
            # Calculate optimal break location (after 8 hours of driving)
            break_after_hours = 8.0
            break_distance = self._calculate_break_distance(
                break_after_hours, 
                total_driving_hours, 
                deadhead_route, 
                loaded_route
            )
            
            logger.info(f"📍 Calculated break location: mile {break_distance:.1f}")
            
            # Check if we can combine with existing fuel stop
            existing_fuel_stops = [s for s in route_plan['stops'] if s['type'] == 'fuel']
            combined_with_fuel = False
            
            for fuel_stop in existing_fuel_stops:
                distance_diff = abs(fuel_stop['distance_from_origin'] - break_distance)
                if distance_diff < 50:  # Within 50 miles, combine them
                    logger.info(f"🔄 Combining break with fuel stop at mile {fuel_stop['distance_from_origin']:.1f}")
                    
                    # Convert fuel stop to combined stop
                    fuel_stop['type'] = 'fuel_and_break'
                    fuel_stop['duration_minutes'] = max(45, 30)  # Take longer of fuel or break time
                    fuel_stop['is_required_for_compliance'] = True
                    fuel_stop['break_reason'] = 'Combined fuel and mandatory 30-minute break'
                    fuel_stop['address'] = fuel_stop['address'].replace('Fuel Station', 'Fuel & Rest Stop')
                    
                    route_plan['optimization_notes'].append(
                        f"Combined mandatory break with fuel stop at mile {fuel_stop['distance_from_origin']:.1f}"
                    )
                    
                    combined_with_fuel = True
                    break
            
            # If not combined with fuel stop, create separate break
            if not combined_with_fuel:
                # Find actual location coordinates and address
                break_location = self._find_break_location_with_coordinates(
                    trip, break_distance, deadhead_route, loaded_route
                )
                
                # Calculate break timing
                break_timing = self._calculate_break_timing(
                    current_time, break_distance, total_distance_miles,
                    deadhead_duration, loaded_duration, trip.pickup_duration_minutes
                )
                
                # Create mandatory break stop
                break_stop = {
                    'type': 'mandatory_break',
                    'sequence_order': 0,  # Will be updated when we re-sort
                    'address': break_location['address'],
                    'latitude': break_location['latitude'],
                    'longitude': break_location['longitude'],
                    'arrival_time': break_timing['arrival_time'].isoformat(),
                    'departure_time': break_timing['departure_time'].isoformat(),
                    'duration_minutes': 30,
                    'distance_from_origin': break_distance,
                    'is_required_for_compliance': True,
                    'break_reason': f'DOT required 30-minute break after {break_after_hours} hours of driving'
                }
                
                # Insert break into route plan
                route_plan['stops'].append(break_stop)
                
                # Add success note
                route_plan['optimization_notes'].append(
                    f"Inserted mandatory 30-minute break at mile {break_distance:.1f} for HOS compliance"
                )
                
                logger.info(f"🛑 Break stop inserted: {break_location['address']} at mile {break_distance:.1f}")
            
            # Adjust subsequent stop timings for 30-minute delay
            break_delay = timedelta(minutes=30)
            delivery_stop = next((s for s in route_plan['stops'] if s['type'] == 'delivery'), None)
            if delivery_stop:
                original_arrival = datetime.fromisoformat(delivery_stop['arrival_time'].replace('Z', '+00:00'))
                new_arrival = original_arrival + break_delay
                new_departure = new_arrival + timedelta(minutes=delivery_stop['duration_minutes'])
                
                delivery_stop['arrival_time'] = new_arrival.isoformat()
                delivery_stop['departure_time'] = new_departure.isoformat()
        
        else:
            logger.info(f"✅ No break required: {total_driving_hours:.2f} hours is under 8-hour limit")

        # ===== STEP 3: GENERATE HOS PERIODS =====
        
        # Generate HOS periods based on the stops
        route_plan['hos_periods'] = self._generate_hos_periods_for_route_plan(trip, route_plan)
        
        # ===== STEP 4: FINALIZE ROUTE PLAN =====
        
        # Sort stops by distance and update sequence
        route_plan['stops'].sort(key=lambda x: x['distance_from_origin'])
        for i, stop in enumerate(route_plan['stops']):
            stop['sequence_order'] = i + 1
        
        # Calculate final totals
        final_arrival = datetime.fromisoformat(route_plan['stops'][-1]['departure_time'].replace('Z', '+00:00'))
        total_duration = final_arrival - current_time
        route_plan['total_duration_hours'] = total_duration.total_seconds() / 3600
        
        # Set estimated times
        pickup_stop = next((s for s in route_plan['stops'] if s['type'] == 'pickup'), None)
        delivery_stop = next((s for s in route_plan['stops'] if s['type'] == 'delivery'), None)
        
        route_plan['estimated_pickup_time'] = pickup_stop['arrival_time'] if pickup_stop else None
        route_plan['estimated_arrival'] = delivery_stop['arrival_time'] if delivery_stop else None
        
        # ===== STEP 5: RECALCULATE COMPLIANCE =====
        self._recalculate_compliance_with_breaks(trip, route_plan)
        
        # Final summary
        stops_summary = {}
        for stop in route_plan['stops']:
            stop_type = stop['type']
            stops_summary[stop_type] = stops_summary.get(stop_type, 0) + 1
        
        logger.info(f"🎯 Final route plan complete:")
        logger.info(f"   📍 Total stops: {len(route_plan['stops'])}")
        logger.info(f"   🛑 Stop breakdown: {stops_summary}")
        logger.info(f"   ⏰ Total trip time: {route_plan['total_duration_hours']:.2f} hours")
        logger.info(f"   📋 HOS periods: {len(route_plan['hos_periods'])}")
        logger.info(f"   📝 Optimization notes: {len(route_plan['optimization_notes'])}")
        
        return route_plan
    

    def _generate_hos_periods_for_route_plan(self, trip: Trip, route_plan: Dict) -> List[Dict]:
        """
        Generate HOS periods based on the route plan stops WITH CORRECT SEQUENTIAL TIMING.
        This creates the driving, on-duty, and off-duty periods needed for compliance calculation.
        """
        hos_periods = []
        stops = route_plan['stops']
        
        if len(stops) < 2:
            logger.warning("Not enough stops to generate HOS periods")
            return hos_periods
        
        # Start with the trip departure time
        current_time = trip.departure_datetime
        
        logger.info(f"🕐 Starting HOS period generation at {current_time}")
        
        # Process each stop sequentially
        for i in range(len(stops)):
            current_stop = stops[i]
            
            logger.info(f"📍 Processing stop {i+1}: {current_stop['type']} at mile {current_stop['distance_from_origin']}")
            
            # 1. DRIVING period TO this stop (except for trip start)
            if i > 0:  # Skip driving to trip start
                previous_stop = stops[i-1]
                
                # Calculate driving distance and time
                distance_traveled = current_stop['distance_from_origin'] - previous_stop['distance_from_origin']
                
                if distance_traveled > 0:
                    # Calculate actual driving time based on distance and average speed
                    average_speed_mph = 60  # Highway speed
                    driving_time_hours = distance_traveled / average_speed_mph
                    driving_time_minutes = int(driving_time_hours * 60)
                    
                    # Driving period starts when we leave previous stop
                    driving_start_time = current_time
                    driving_end_time = current_time + timedelta(minutes=driving_time_minutes)
                    
                    # Create driving period
                    driving_period = {
                        'duty_status': 'driving',
                        'start_datetime': driving_start_time.isoformat(),
                        'end_datetime': driving_end_time.isoformat(),
                        'duration_minutes': driving_time_minutes,
                        'start_location': previous_stop['address'],
                        'end_location': current_stop['address'],
                        'distance_traveled_miles': distance_traveled,
                        'leg_type': 'driving'
                    }
                    
                    hos_periods.append(driving_period)
                    
                    # Update current time to arrival at this stop
                    current_time = driving_end_time
                    
                    logger.info(f"  🚛 Driving period: {driving_time_minutes} min ({distance_traveled:.1f} miles)")
                    logger.info(f"  🕐 Arrived at {current_stop['type']} at {current_time}")
            
            # 2. STOP period AT this location (except trip start which has 0 duration)
            if current_stop['duration_minutes'] > 0:
                # Stop period starts when we arrive
                stop_start_time = current_time
                stop_end_time = current_time + timedelta(minutes=current_stop['duration_minutes'])
                
                # Determine duty status based on stop type
                if current_stop['type'] == 'mandatory_break':
                    duty_status = 'off_duty'  # Break is off-duty
                elif current_stop['type'] in ['pickup', 'delivery']:
                    duty_status = 'on_duty_not_driving'  # Loading/unloading
                else:
                    duty_status = 'on_duty_not_driving'  # Default for other stops
                
                # Create stop period
                stop_period = {
                    'duty_status': duty_status,
                    'start_datetime': stop_start_time.isoformat(),
                    'end_datetime': stop_end_time.isoformat(),
                    'duration_minutes': current_stop['duration_minutes'],
                    'start_location': current_stop['address'],
                    'end_location': current_stop['address'],
                    'distance_traveled_miles': 0,  # No travel during stop
                    'leg_type': current_stop['type']
                }
                
                hos_periods.append(stop_period)
                
                # Update current time to when we leave this stop
                current_time = stop_end_time
                
                logger.info(f"  ⏱️  {duty_status} period: {current_stop['duration_minutes']} min")
                logger.info(f"  🕐 Departed {current_stop['type']} at {current_time}")
        
        # Calculate and log totals for verification
        driving_periods = [p for p in hos_periods if p['duty_status'] == 'driving']
        on_duty_periods = [p for p in hos_periods if p['duty_status'] in ['driving', 'on_duty_not_driving']]
        off_duty_periods = [p for p in hos_periods if p['duty_status'] in ['off_duty', 'sleeper_berth']]
        
        total_driving_minutes = sum(p['duration_minutes'] for p in driving_periods)
        total_on_duty_minutes = sum(p['duration_minutes'] for p in on_duty_periods)
        total_off_duty_minutes = sum(p['duration_minutes'] for p in off_duty_periods)
        
        logger.info(f"📊 HOS Periods Summary:")
        logger.info(f"  📍 Total periods: {len(hos_periods)}")
        logger.info(f"  🚛 Driving time: {total_driving_minutes/60:.2f} hours ({len(driving_periods)} periods)")
        logger.info(f"  ⏰ On-duty time: {total_on_duty_minutes/60:.2f} hours")
        logger.info(f"  😴 Off-duty time: {total_off_duty_minutes/60:.2f} hours")
        
        return hos_periods
    

    def _recalculate_compliance_with_breaks(self, trip: Trip, route_plan: Dict) -> None:
        """
        Recalculate compliance after breaks are inserted to ensure accurate reporting.
        """
        try:
            # Calculate totals from route plan HOS periods
            driving_periods = [p for p in route_plan['hos_periods'] if p['duty_status'] == 'driving']
            on_duty_periods = [p for p in route_plan['hos_periods'] if p['duty_status'] in ['driving', 'on_duty_not_driving']]
            off_duty_periods = [p for p in route_plan['hos_periods'] if p['duty_status'] in ['off_duty', 'sleeper_berth']]
            
            total_driving_minutes = sum(p['duration_minutes'] for p in driving_periods)
            total_on_duty_minutes = sum(p['duration_minutes'] for p in on_duty_periods)
            total_off_duty_minutes = sum(p['duration_minutes'] for p in off_duty_periods)
            
            # Count scheduled breaks
            mandatory_breaks = len([s for s in route_plan['stops'] if s['type'] == 'mandatory_break'])
            
            # Update trip fields for compliance calculation
            trip.total_driving_time = total_driving_minutes / 60.0
            trip.total_on_duty_time = total_on_duty_minutes / 60.0
            
            # Also update the individual leg driving times for consistency
            # Find deadhead and loaded driving periods
            deadhead_driving = sum(
                p['duration_minutes'] for p in driving_periods 
                if p.get('leg_type') == 'driving' and 'pickup' in p.get('end_location', '').lower()
            )
            loaded_driving = sum(
                p['duration_minutes'] for p in driving_periods 
                if p.get('leg_type') == 'driving' and 'delivery' in p.get('end_location', '').lower()
            )
            
            # Update individual leg times if we can identify them
            if deadhead_driving > 0:
                trip.deadhead_driving_time = deadhead_driving / 60.0
            if loaded_driving > 0:
                trip.loaded_driving_time = loaded_driving / 60.0
            
            logger.info(f"✅ Compliance recalculated:")
            logger.info(f"  🚛 Total driving: {total_driving_minutes/60:.2f}h")
            logger.info(f"  ⏰ Total on-duty: {total_on_duty_minutes/60:.2f}h")
            logger.info(f"  😴 Total off-duty: {total_off_duty_minutes/60:.2f}h")
            logger.info(f"  🛑 Mandatory breaks: {mandatory_breaks}")
            
        except Exception as e:
            logger.error(f"Error recalculating compliance: {str(e)}")
    

    def _calculate_break_distance(
            self, break_after_hours: float, total_driving_hours: float, deadhead_route: Dict, loaded_route: Dict
        ) -> float:
        """
        Calculate the distance where break should occur based on driving time.
        """
        # Calculate cumulative driving time to find where 8 hours occurs
        deadhead_hours = deadhead_route['duration_hours']
        deadhead_miles = deadhead_route['distance_miles']
        loaded_miles = loaded_route['distance_miles']
        
        if break_after_hours <= deadhead_hours:
            # Break occurs during deadhead leg
            ratio = break_after_hours / deadhead_hours
            return deadhead_miles * ratio
        else:
            # Break occurs during loaded leg
            remaining_hours = break_after_hours - deadhead_hours
            loaded_hours = loaded_route['duration_hours']
            ratio = remaining_hours / loaded_hours if loaded_hours > 0 else 0
            return deadhead_miles + (loaded_miles * ratio)
    

    def _find_break_location_with_coordinates(self, trip: Trip, break_distance: float, deadhead_route: Dict, loaded_route: Dict) -> Dict:
        """
        Find actual GPS coordinates and address for break location using route geometry.
        """
        try:
            # Determine which route leg contains the break
            deadhead_miles = deadhead_route['distance_miles']
            
            if break_distance <= deadhead_miles:
                # Break is in deadhead leg
                leg_distance = break_distance
                leg_total_distance = deadhead_miles
                route_geometry = deadhead_route.get('geometry')
                leg_type = 'deadhead'
                start_coords = (float(trip.current_latitude), float(trip.current_longitude))
                end_coords = (float(trip.pickup_latitude), float(trip.pickup_longitude))
            else:
                # Break is in loaded leg
                leg_distance = break_distance - deadhead_miles
                leg_total_distance = loaded_route['distance_miles']
                route_geometry = loaded_route.get('geometry')
                leg_type = 'loaded'
                start_coords = (float(trip.pickup_latitude), float(trip.pickup_longitude))
                end_coords = (float(trip.delivery_latitude), float(trip.delivery_longitude))
            
            # Get coordinates from route geometry
            if route_geometry and isinstance(route_geometry, str):
                # Decode polyline to get route points
                coordinates = self._interpolate_from_polyline(
                    route_geometry, 
                    leg_distance, 
                    leg_total_distance
                )
            else:
                # Fallback: linear interpolation between start and end
                ratio = leg_distance / leg_total_distance if leg_total_distance > 0 else 0
                coordinates = self._linear_interpolate_coordinates(start_coords, end_coords, ratio)
            
            # Generate appropriate address
            mile_marker = int(break_distance)
            if leg_type == 'deadhead':
                address = f"Rest Area & Truck Stop (Mile {mile_marker}) - Deadhead Route"
            else:
                address = f"Truck Stop & Rest Area (Mile {mile_marker}) - Loaded Route"
            
            return {
                'latitude': coordinates[0],
                'longitude': coordinates[1],
                'address': address
            }
            
        except Exception as e:
            logger.error(f"Error finding break location coordinates: {str(e)}")
            # Fallback to simple interpolation
            return self._fallback_break_location(trip, break_distance)


    def _interpolate_from_polyline(self, encoded_polyline: str, target_distance: float, total_distance: float) -> Tuple[float, float]:
        """
        Interpolate coordinates from encoded polyline geometry.
        """
        try:
            # Decode the polyline
            decoded_points = polyline.decode(encoded_polyline)
            
            if len(decoded_points) < 2:
                raise ValueError("Invalid polyline data")
            
            # Calculate target ratio along the route
            target_ratio = target_distance / total_distance if total_distance > 0 else 0
            target_ratio = max(0, min(1, target_ratio))  # Clamp between 0 and 1
            
            # Find the appropriate segment in the polyline
            num_segments = len(decoded_points) - 1
            segment_index = int(target_ratio * num_segments)
            segment_index = min(segment_index, num_segments - 1)
            
            # Interpolate within the segment
            segment_ratio = (target_ratio * num_segments) - segment_index
            
            start_point = decoded_points[segment_index]
            end_point = decoded_points[segment_index + 1]
            
            # Linear interpolation between two points
            lat = start_point[0] + (end_point[0] - start_point[0]) * segment_ratio
            lng = start_point[1] + (end_point[1] - start_point[1]) * segment_ratio
            
            return (lat, lng)
            
        except Exception as e:
            logger.error(f"Error interpolating from polyline: {str(e)}")
            # Fallback to simple calculation
            return (32.5, -96.5)  # Default coordinates for Texas


    def _linear_interpolate_coordinates(
            self, start_coords: Tuple[float, float], end_coords: Tuple[float, float], ratio: float
        ) -> Tuple[float, float]:
        """
        Simple linear interpolation between two coordinate points.
        """
        lat = start_coords[0] + (end_coords[0] - start_coords[0]) * ratio
        lng = start_coords[1] + (end_coords[1] - start_coords[1]) * ratio
        return (lat, lng)


    def _fallback_break_location(self, trip: Trip, break_distance: float) -> Dict:
        """
        Fallback method for break location when geometry interpolation fails.
        """
        # Simple midpoint calculation
        start_lat = float(trip.current_latitude)
        start_lng = float(trip.current_longitude)
        end_lat = float(trip.delivery_latitude)
        end_lng = float(trip.delivery_longitude)
        
        # Use simple ratio based on distance
        total_distance = float(trip.total_distance_miles) if trip.total_distance_miles else 400
        ratio = break_distance / total_distance
        
        lat = start_lat + (end_lat - start_lat) * ratio
        lng = start_lng + (end_lng - start_lng) * ratio
        
        return {
            'latitude': lat,
            'longitude': lng,
            'address': f"Rest Area & Truck Stop (Mile {int(break_distance)})"
        }

    def _calculate_break_timing(
            self, start_time: datetime, break_distance: float, total_distance: float, deadhead_duration: timedelta, loaded_duration: timedelta, pickup_duration: int
        ) -> Dict:
        """
        Calculate when the break should start and end based on timing.
        """
        # Calculate time ratio to break location
        distance_ratio = break_distance / total_distance if total_distance > 0 else 0
        
        # Calculate total driving time to break point
        total_driving_time = deadhead_duration + loaded_duration
        driving_time_to_break = total_driving_time * distance_ratio
        
        # Add pickup time if break is after pickup
        deadhead_miles = total_distance * (deadhead_duration.total_seconds() / total_driving_time.total_seconds())
        
        if break_distance > deadhead_miles:
            # Break is after pickup, so include pickup time
            time_to_break = deadhead_duration + timedelta(minutes=pickup_duration) + (driving_time_to_break - deadhead_duration)
        else:
            # Break is during deadhead
            time_to_break = driving_time_to_break
        
        break_arrival = start_time + time_to_break
        break_departure = break_arrival + timedelta(minutes=30)
        
        return {
            'arrival_time': break_arrival,
            'departure_time': break_departure
        }

    def _adjust_stop_timings_for_break(self, stops: List[Dict], break_departure_time: datetime) -> None:
        """
        Adjust the timing of subsequent stops to account for the 30-minute break.
        """
        break_delay = timedelta(minutes=30)
        
        for stop in stops:
            if stop['type'] in ['delivery'] and stop.get('distance_from_origin', 0) > 0:
                # Only adjust stops that come after the break
                current_arrival = datetime.fromisoformat(stop['arrival_time'].replace('Z', '+00:00'))
                if current_arrival > break_departure_time:
                    new_arrival = current_arrival + break_delay
                    new_departure = new_arrival + timedelta(minutes=stop['duration_minutes'])
                    
                    stop['arrival_time'] = new_arrival.isoformat()
                    stop['departure_time'] = new_departure.isoformat()
    

    def _calculate_leg_stops_with_status(
        self, 
        trip: Trip, 
        leg_route: Dict, 
        leg_type: str,
        start_sequence: int,
        start_distance: Decimal,
        driver_status: 'DriverCycleStatus' = None,
        accumulated_driving_today: float = 0
    ) -> List[Dict]:
        """
        Enhanced stop calculation that considers driver's current HOS status
        """
        leg_stops = []
        leg_distance = Decimal(str(leg_route['distance_miles']))
        leg_driving_hours = leg_route['duration_hours']
        max_fuel_distance = trip.max_fuel_distance_miles or self.max_fuel_distance_default
        
        current_leg_distance = Decimal('0')
        fuel_stop_number = 1
        
        while current_leg_distance + max_fuel_distance < leg_distance:
            fuel_distance = current_leg_distance + max_fuel_distance
            absolute_distance = start_distance + fuel_distance
            
            leg_proportion = float(fuel_distance / leg_distance)
            fuel_location = self._interpolate_leg_location(leg_route, leg_proportion)
            
            leg_stops.append({
                'type': 'fuel',
                'address': fuel_location['address'],
                'latitude': fuel_location['latitude'],
                'longitude': fuel_location['longitude'],
                'duration_minutes': self.fuel_stop_duration_minutes,
                'distance_from_origin': float(absolute_distance),
                'sequence_order': start_sequence + len(leg_stops),
                'fuel_stop_number': fuel_stop_number,
                'leg_type': leg_type,
                'is_required_for_compliance': False
            })
            
            current_leg_distance = fuel_distance
            fuel_stop_number += 1
        
        # Enhanced break calculation considering current status
        if driver_status:
            # Check if 30-min break is needed during this leg
            total_driving_after_leg = accumulated_driving_today + leg_driving_hours
            hours_since_last_break = driver_status.hours_since_last_break if driver_status.continuous_driving_since else 0
            combined_continuous_driving = hours_since_last_break + leg_driving_hours
            
            # Break after 8 hours of continuous driving
            if combined_continuous_driving > 8:
                hours_until_break_needed = max(0, 8 - hours_since_last_break)
                
                if hours_until_break_needed < leg_driving_hours:
                    # Break needed during this leg
                    break_proportion = hours_until_break_needed / leg_driving_hours
                    break_distance = start_distance + (leg_distance * Decimal(str(break_proportion)))
                    break_location = self._interpolate_leg_location(leg_route, break_proportion)
                    
                    leg_stops.append({
                        'type': 'mandatory_break',
                        'address': break_location['address'],
                        'latitude': break_location['latitude'],
                        'longitude': break_location['longitude'],
                        'duration_minutes': self.mandatory_break_duration_minutes,
                        'distance_from_origin': float(break_distance),
                        'sequence_order': start_sequence + len(leg_stops),
                        'leg_type': leg_type,
                        'is_required_for_compliance': True,
                        'break_reason': f'HOS 30-minute break requirement (continuous driving: {combined_continuous_driving:.1f} hours)'
                    })
            
            # Check if daily reset will be needed
            total_on_duty_after_leg = driver_status.today_on_duty_hours + leg_driving_hours + (trip.pickup_duration_minutes + trip.delivery_duration_minutes) / 60
            
            if total_on_duty_after_leg > 14:
                reset_proportion = 0.8
                reset_distance = start_distance + (leg_distance * Decimal(str(reset_proportion)))
                reset_location = self._interpolate_leg_location(leg_route, reset_proportion)
                
                leg_stops.append({
                    'type': 'daily_reset',
                    'address': reset_location['address'],
                    'latitude': reset_location['latitude'],
                    'longitude': reset_location['longitude'],
                    'duration_minutes': 10 * 60,
                    'distance_from_origin': float(reset_distance),
                    'sequence_order': start_sequence + len(leg_stops),
                    'leg_type': leg_type,
                    'is_required_for_compliance': True,
                    'break_reason': f'HOS 10-hour daily reset requirement (total on-duty: {total_on_duty_after_leg:.1f} hours)'
                })
        
        else:
            if leg_driving_hours > 8:
                break_distance = start_distance + (leg_distance * Decimal('0.6'))
                break_proportion = 0.6
                break_location = self._interpolate_leg_location(leg_route, break_proportion)
                
                leg_stops.append({
                    'type': 'mandatory_break',
                    'address': break_location['address'],
                    'latitude': break_location['latitude'],
                    'longitude': break_location['longitude'],
                    'duration_minutes': self.mandatory_break_duration_minutes,
                    'distance_from_origin': float(break_distance),
                    'sequence_order': start_sequence + len(leg_stops),
                    'leg_type': leg_type,
                    'is_required_for_compliance': True,
                    'break_reason': 'HOS 30-minute break requirement (basic calculation)'
                })
        
        leg_stops.sort(key=lambda x: x['distance_from_origin'])
        for i, stop in enumerate(leg_stops):
            stop['sequence_order'] = start_sequence + i
        
        return leg_stops
   
    def _interpolate_leg_location(self, leg_route: Dict, proportion: float) -> Dict:
        """
        Interpolate location along a specific leg route
        """
        origin_lat = leg_route['origin_lat']
        origin_lng = leg_route['origin_lng']
        dest_lat = leg_route['destination_lat']
        dest_lng = leg_route['destination_lng']
        
        # Linear interpolation
        interpolated_lat = origin_lat + (dest_lat - origin_lat) * proportion
        interpolated_lng = origin_lng + (dest_lng - origin_lng) * proportion
        
        # Try to use waypoints for more accuracy if available
        waypoints = leg_route.get('waypoints', [])
        if waypoints and len(waypoints) > 2:
            interpolated_location = self._interpolate_from_waypoints(waypoints, proportion)
            if interpolated_location:
                interpolated_lat = interpolated_location['latitude']
                interpolated_lng = interpolated_location['longitude']
        
        distance_miles = int(leg_route['distance_miles'] * proportion)
        return {
            'address': f"Highway Location (Mile {distance_miles})",
            'latitude': interpolated_lat,
            'longitude': interpolated_lng
        }
    
    def _generate_leg_periods(
        self,
        trip: Trip,
        leg_route: Dict,
        start_time: datetime,
        start_location: str,
        end_location: str,
        leg_stops: List[Dict],
        leg_type: str
    ) -> Tuple[List[Dict], datetime]:
        """
        Generate HOS periods for a specific leg including driving and stops
        """
        periods = []
        current_time = start_time
        leg_distance = Decimal(str(leg_route['distance_miles']))
        current_distance = Decimal('0')
        
        # Sort stops by distance for this leg
        sorted_stops = sorted(leg_stops, key=lambda x: x['distance_from_origin'])
        
        for stop in sorted_stops:
            # Calculate driving distance to this stop
            stop_distance_in_leg = stop['distance_from_origin'] - current_distance
            if stop_distance_in_leg > 0:
                # Calculate driving time to this stop
                proportion_to_stop = float(stop_distance_in_leg / leg_distance)
                driving_time_hours = leg_route['duration_hours'] * proportion_to_stop
                driving_time_minutes = int(driving_time_hours * 60)
                
                if driving_time_minutes > 0:
                    # Add driving period to this stop
                    driving_end_time = current_time + timedelta(minutes=driving_time_minutes)
                    periods.append({
                        'duty_status': 'driving',
                        'start_datetime': current_time,
                        'end_datetime': driving_end_time,
                        'duration_minutes': driving_time_minutes,
                        'distance_traveled_miles': float(stop_distance_in_leg),
                        'start_location': start_location if current_distance == 0 else 'Highway',
                        'end_location': stop['address'],
                        'leg_type': leg_type
                    })
                    
                    current_time = driving_end_time
                    current_distance = Decimal(str(stop['distance_from_origin']))
            
            # Add stop period
            stop_end_time = current_time + timedelta(minutes=stop['duration_minutes'])
            stop_duty_status = self._get_stop_duty_status(stop['type'])
            
            periods.append({
                'duty_status': stop_duty_status,
                'start_datetime': current_time,
                'end_datetime': stop_end_time,
                'duration_minutes': stop['duration_minutes'],
                'start_location': stop['address'],
                'end_location': stop['address'],
                'leg_type': leg_type
            })
            
            current_time = stop_end_time
        
        # Add final driving period to end of leg
        remaining_distance = leg_distance - current_distance
        if remaining_distance > 0:
            proportion_remaining = float(remaining_distance / leg_distance)
            final_driving_hours = leg_route['duration_hours'] * proportion_remaining
            final_driving_minutes = int(final_driving_hours * 60)
            
            if final_driving_minutes > 0:
                final_driving_end = current_time + timedelta(minutes=final_driving_minutes)
                periods.append({
                    'duty_status': 'driving',
                    'start_datetime': current_time,
                    'end_datetime': final_driving_end,
                    'duration_minutes': final_driving_minutes,
                    'distance_traveled_miles': float(remaining_distance),
                    'start_location': 'Highway' if leg_stops else start_location,
                    'end_location': end_location,
                    'leg_type': leg_type
                })
                current_time = final_driving_end
        
        return periods, current_time

    
    def _generate_route_plan(self, trip: Trip, route_data: Dict, feasibility_report: Dict) -> Dict[str,any]:
        """
        Generate detailed route plan with stops, breaks, and timing
        Return dictionary with route plan details
        """
        route_plan = {
            'stops': [],
            'hos_periods': [],
            'total_duration_hours': 0,
            'estimated_arrival': None,
            'optimization_notes': [],
        }

        current_time = trip.departure_datetime
        current_distance = Decimal('0')
        total_distance = trip.total_distance_miles

        # Add pickup stop
        pickup_stop = {
            'type': 'pickup',
            'address': trip.current_address,
            'latitude': trip.current_latitude,
            'longitude': trip.current_longitude,
            'arrival_time': current_time,
            'duration_minutes': trip.pickup_duration_minutes,
            'distance_from_origin': 0,
            'sequence_order': 1
        }

        route_plan['stops'].append(pickup_stop)

        # Add pickup hos period
        pickup_end_time = current_time + timedelta(minutes=trip.pickup_duration_minutes)
        route_plan['hos_periods'].append({
            'duty_status': 'on_duty_not_driving',
            'start_datetime': current_time,
            'end_datetime': pickup_end_time,
            'duration_minutes': trip.pickup_duration_minutes,
            'start_location': trip.current_address,
            'end_location': trip.current_address,
        })

        current_time = pickup_end_time
        stop_sequence = 2

        # fuel stops based on max fuel distance
        fuel_stops = self._calculate_fuel_stops(trip, route_data)

        required_breaks = feasibility_report.get('required_breaks', [])

        break_stops = self._convert_breaks_to_stops(required_breaks, trip, route_data)

        # Comebine and sort all intermediate stops by distance
        all_intermediate_stops = fuel_stops + break_stops
        all_intermediate_stops.sort(key=lambda x: x['distance_from_origin'])

        optimized_stops = self._optimize_stop_placement(all_intermediate_stops, trip)

        route_plan['optimization_notes'].extend(self._get_optimization_notes(optimized_stops, all_intermediate_stops))

        # Add intermediate stops and corresponding driving periods
        accumulated_driving_time = Decimal('0')

        for stop in optimized_stops:
            # Calculate driving time to this stop
            distance_to_stop = stop['distance_from_origin'] - current_distance
            driving_time_hours = distance_to_stop / self.average_highway_speed_mph
            driving_time_minutes = int(driving_time_hours * 60)

            if driving_time_minutes > 0:
                # Add driving period to this stop
                driving_end_time = current_time + timedelta(minutes=driving_time_minutes)
                route_plan['hos_periods'].append({
                    'duty_status': 'driving',
                    'start_datetime': current_time,
                    'end_datetime': driving_end_time,
                    'duration_minutes': driving_time_minutes,
                    'distance_traveled_miles': float(distance_to_stop),
                    'start_location': route_plan['stops'][-1]['address'],
                    'end_location': stop['address']
                })
                
                accumulated_driving_time += Decimal(str(driving_time_minutes))
                current_time = driving_end_time
                current_distance = Decimal(str(stop['distance_from_origin']))

            # Add the stop to the route plan
            stop['sequence_order'] = stop_sequence
            stop['arrival_time'] = current_time
            stop['departure_time'] = current_time + timedelta(minutes=stop['duration_minutes'])
            route_plan['stops'].append(stop)

            stop_duty_status = self._get_stop_duty_status(stop['type'])
            route_plan['hos_periods'].append({
                    'duty_status': stop_duty_status,
                    'start_datetime': current_time,
                    'end_datetime': stop['departure_time'],
                    'duration_minutes': stop['duration_minutes'],
                    'start_location': stop['address'],
                    'end_location': stop['address']
                })

            current_time = stop['departure_time']
            stop_sequence += 1

        # Add final driving period to destination
        remaining_distance = total_distance - current_distance
        if remaining_distance > 0:
            final_driving_hours = remaining_distance / self.average_highway_speed_mph
            final_driving_minutes = int(final_driving_hours * 60)

            if final_driving_minutes > 0:
                final_driving_end = current_time + timedelta(minutes=final_driving_minutes)
                route_plan['hos_periods'].append({
                    'duty_status': 'driving',
                    'start_datetime': current_time,
                    'end_datetime': final_driving_end,
                    'duration_minutes': final_driving_minutes,
                    'distance_traveled_miles': float(remaining_distance),
                    'start_location': route_plan['stops'][-1]['address'],
                    'end_location': trip.destination_address
                })
                current_time = final_driving_end

        # Add destination stop
        delivery_stop = {
            'type': 'delivery',
            'address': trip.destination_address,
            'latitude': float(trip.destination_latitude),
            'longitude': float(trip.destination_longitude),
            'arrival_time': current_time,
            'duration_minutes': trip.delivery_duration_minutes,
            'distance_from_origin': float(total_distance),
            'sequence_order': stop_sequence
        }

        route_plan['stops'].append(delivery_stop)

        # Add delivery hos period
        delivery_end_time = current_time + timedelta(minutes=trip.delivery_duration_minutes)
        route_plan['hos_periods'].append({
            'duty_status': 'on_duty_not_driving',
            'start_datetime': current_time,
            'end_datetime': delivery_end_time,
            'duration_minutes': trip.delivery_duration_minutes,
            'start_location': trip.destination_address,
            'end_location': trip.destination_address
        })

        # Calculate totals
        total_trip_time = delivery_end_time - trip.departure_datetime
        route_plan['total_duration_hours'] = total_trip_time.total_seconds() / 3600
        route_plan['estimated_arrival'] = delivery_end_time

        return route_plan
    
    def _calculate_fuel_stops(self, trip: Trip, route_data: Dict) -> List[Dict]:
        """
        Calculation for required fuel stops based on max fuel distance
        """
        fuel_stops = []
        total_distance = trip.total_distance_miles
        max_fuel_distance = trip.max_fuel_distance_miles or self.max_fuel_distance_default

        current_distance = Decimal('0')
        fuel_stop_number = 1

        while current_distance + max_fuel_distance < total_distance:
            fuel_distance = current_distance + max_fuel_distance

            # Find appropriate fuel stop location using route interpolation
            fuel_location = self._interpolate_route_location(route_data, fuel_distance, total_distance)

            fuel_stops.append({
                'type': 'fuel',
                'address': fuel_location['address'],
                'latitude': fuel_location['latitude'],
                'longitude': fuel_location['longitude'],
                'duration_minutes': self.fuel_stop_duration_minutes,
                'distance_from_origin': float(fuel_distance),
                'fuel_stop_number': fuel_stop_number,
                'is_required_for_compliance': False
            })

            current_distance = fuel_distance
            fuel_stop_number += 1
        
        return fuel_stops
    
    def _convert_breaks_to_stops(self, required_breaks: List[Dict], trip: Trip, route_data: Dict) -> List[Dict]:
        """
        Convert HOS required breaks into stop objects.
        
        Args:
            required_breaks: List of required breaks from HOS calculator
            trip: Trip instance
        """
        break_stops = []

        for break_info in required_breaks:
            if break_info['type'] == 'mandatory_break':
                # Calculate distance where break should occur
                break_distance = (break_info['after_driving_hours'] * self.average_highway_speed_mph)

                # Ensure break distance does not exceed trip distance
                break_distance = min(break_distance, float(trip.total_distance_miles * Decimal('0.9')))

                break_location = self._interpolate_route_location(route_data, Decimal(str(break_distance)), trip.total_distance_miles)
                
                break_stops.append({
                    'type': 'mandatory_break',
                    'address': break_location['address'],
                    'latitude': break_location['latitude'],
                    'longitude': break_location['longitude'],
                    'duration_minutes': break_info['duration_minutes'],
                    'distance_from_origin': break_distance,
                    'is_required_for_compliance': True,
                    'break_reason': 'HOS 30-minute break requirement'
                })
            
            elif break_info['type'] == 'daily_reset':
                reset_distance = (break_info.get('after_hours', 0) / 14 * float(trip.total_distance_miles))
                reset_distance = min(reset_distance, float(trip.total_distance_miles * Decimal('0.8')))
                
                reset_location = self._interpolate_route_location(route_data, Decimal(str(reset_distance)), trip.total_distance_miles)

                break_stops.append({
                    'type': 'daily_reset',
                    'address': reset_location['address'],
                    'latitude': reset_location['latitude'],
                    'longitude': reset_location['longitude'],
                    'duration_minutes': break_info['duration_minutes'],
                    'distance_from_origin': reset_distance,
                    'is_required_for_compliance': True,
                    'break_reason': 'HOS 10-hour daily reset requirement'
                })
        
        return break_stops
    
    def _interpolate_route_location(self, route_data: Dict, target_distance: Decimal, total_distance: Decimal) -> Dict:
        """
        Interpolate approximate location along route at target distance
        """
        # calculate proportion along route
        proportion = float(target_distance / total_distance)
        proportion = max(0.0, min(1.0, proportion))  # Clamp between 0 and 1

        origin_lat = route_data.get('origin_lat', 0)
        origin_lng = route_data.get('origin_lng', 0)
        dest_lat = route_data.get('destination_lat', 0)
        dest_lng = route_data.get('destination_lng', 0)
        
        # Linear interpolation (basic approximation)
        interpolated_lat = origin_lat + (dest_lat - origin_lat) * proportion
        interpolated_lng = origin_lng + (dest_lng - origin_lng) * proportion
        
        # Trying to use waypoints for more accurate interpolation if available
        waypoints = route_data.get('waypoints', [])
        if waypoints and len(waypoints) > 2:
            interpolated_location = self._interpolate_from_waypoints(waypoints, proportion)
            if interpolated_location:
                interpolated_lat = interpolated_location['latitude']
                interpolated_lng = interpolated_location['longitude']
        
        return {
            'address': f"Highway Location (Mile {int(target_distance)})",
            'latitude': interpolated_lat,
            'longitude': interpolated_lng
        }

    def _interpolate_from_waypoints(self, waypoints: List[Dict], proportion: float) -> Optional[Dict]:
        """
        Interpolate location from route waypoints for better accuracy
        """
        try:
            if not waypoints or len(waypoints) < 2:
                return None
            
            # Find the segment that contains the target proportion
            target_index = proportion * (len(waypoints) - 1)
            lower_index = int(target_index)
            upper_index = min(lower_index + 1, len(waypoints) - 1)

            if lower_index == upper_index:
                return waypoints[lower_index]
            
            # Interpolate between two waypoints
            segment_proportion = target_index - lower_index
            lower_point = waypoints[lower_index]
            upper_point = waypoints[upper_index]

            interpolated_lat = lower_point['latitude'] + (upper_point['latitude'] - lower_point['latitude']) * segment_proportion
            interpolated_lng = lower_point['longitude'] + (upper_point['longitude'] - lower_point['longitude']) * segment_proportion
            
            return {
                'latitude': interpolated_lat,
                'longitude': interpolated_lng
            }
            
        except Exception as e:
            logger.warning(f"Error interpolating from waypoints: {str(e)}")
            return None
    
    def _get_stop_duty_status(self, stop_type: str) -> str:
        """Get HOS duty status based on stop type"""

        duty_status_mapping = {
            'pickup': 'on_duty_not_driving',
            'delivery': 'on_duty_not_driving',
            'fuel': 'off_duty',
            'mandatory_break': 'off_duty',
            'daily_reset': 'sleeper_berth',
            'rest': 'off_duty',
            'fuel_and_break': 'off_duty'
        }

        return duty_status_mapping.get(stop_type, 'off_duty')
    
    def _optimize_stop_placement(self, stops: List[Dict], trip: Trip) -> List[Dict]:
        """
        Optimize stop placement to reduce overlaps and improve efficiency
        """
        if not stops:
            return stops
        
        optimized_stops = []
        buffer_distance = self.break_location_buffer_miles
        
        for stop in stops:
            # Check if this stop can be combined with nearby stops
            combined_stop = self._find_combinable_stop(stop, optimized_stops, buffer_distance)
            
            if combined_stop:
                # Combine the stops
                self._combine_stops(combined_stop, stop)
            else:
                # Add as new stop
                optimized_stops.append(stop.copy())
        
        return optimized_stops
    
    def _find_combinable_stop(self, new_stop: Dict, existing_stops: List[Dict], buffer_distance: float) -> Optional[Dict]:
        """
        Find an existing stop that can be combined with the new stop
        """
        new_distance = new_stop['distance_from_origin']

        for existing_stop in existing_stops:
            existing_distance = existing_stop['distance_from_origin']
            distance_difference = abs(new_distance - existing_distance)

            if distance_difference <= buffer_distance:
                # Check if stop types are compatible for combining
                if self._are_stops_combinable(new_stop['type'], existing_stop['type']):
                    return existing_stop
            
        return None
    
    def _are_stops_combinable(self, type1: str, type2: str) -> bool:
        """
        Check if two stop types can be combined
        """
        # Fuel stops can be combined with mandatory breaks
        combinable_pairs = [
            ('fuel', 'mandatory_break'),
            ('mandatory_break', 'fuel'),
        ]
        
        return (type1, type2) in combinable_pairs
    
    def _combine_stops(self, existing_stop: Dict, new_stop: Dict) -> None:
        """
        Combine two compatible stops into one optimized stop
        """
        existing_stop['duration_miutes'] = max(
            existing_stop['duration_minutes'],
            new_stop['duration_minutes']
        )

        # Combine stop types
        if existing_stop['type'] == 'fuel' and new_stop['type'] == 'mandatory_break':
            existing_stop['type'] = 'fuel_and_break'
            existing_stop['is_required_for_compliance'] = True
            existing_stop['combined_functions'] = ['fuel', 'mandatory_break']
        elif existing_stop['type'] == 'mandatory_break' and new_stop['type'] == 'fuel':
            existing_stop['type'] = 'fuel_and_break'
            existing_stop['is_required_for_compliance'] = True
            existing_stop['combined_functions'] = ['mandatory_break', 'fuel']
        
        # Update address to reflect combined purpose
        if 'fuel_and_break' in existing_stop['type']:
            mile_marker = int(existing_stop['distance_from_origin'])
            existing_stop['address'] = f"Fuel & Rest Stop (Mile {mile_marker})"
    
    def _get_optimization_notes(self, original_stops: List[Dict], optimized_stops: List[Dict]) -> List[str]:
        """
        Generate notes about optimizations made to the route
        """
        notes = []
        
        if len(optimized_stops) < len(original_stops):
            saved_stops = len(original_stops) - len(optimized_stops)
            notes.append(f"Combined {saved_stops} stop(s) to optimize route efficiency")
        
        combined_stops = [stop for stop in optimized_stops if 'combined_functions' in stop]
        if combined_stops:
            notes.append(f"Created {len(combined_stops)} combined fuel/break stop(s)")
        
        return notes
    
    def save_route_plan(self, trip: Trip, route_plan: Dict, route_data: Dict) -> Tuple[Route, List[Stops], List[HOSPeriod]]:
        """
        Save calculated route plan to database
        """
        try:
            route_geometry = route_data.get('combined_geometry', {})
            
            # Extract instructions from legs data
            route_instructions = []
            legs_data = route_data.get('legs', [])
            for leg in legs_data:
                if 'instructions' in leg:
                    route_instructions.extend(leg['instructions'])
            
            # If legs don't have instructions, try to get from route_data directly
            if not route_instructions:
                route_instructions = route_data.get('instructions', [])
            
            # Create Route object with correct data
            route = Route.objects.create(
                trip=trip,
                route_geometry=route_geometry,
                route_instructions=route_instructions,
                total_distance_meters=int(route_data.get('distance_meters', 0)),
                total_duration_seconds=int(route_data.get('duration_seconds', 0)),
                external_route_id=route_data.get('route_id', ''),
                api_provider=route_data.get('provider', 'openrouteservice'),
                calculated_by=trip.driver 
            )
            
            logger.info(f"Route saved with geometry: {bool(route_geometry)} and instructions: {len(route_instructions)} steps")

            # Create Stops objects
            stops_created = []
            for stop_data in route_plan['stops']:
                stop = Stops.objects.create(
                    trip=trip,
                    stop_type=stop_data['type'],
                    sequence_order=stop_data['sequence_order'],
                    address=stop_data['address'],
                    latitude=Decimal(str(stop_data['latitude'])) if stop_data['latitude'] else None,
                    longitude=Decimal(str(stop_data['longitude'])) if stop_data['longitude'] else None,
                    arrival_time=stop_data['arrival_time'],
                    departure_time=stop_data.get('departure_time', stop_data['arrival_time']),
                    duration_minutes=stop_data['duration_minutes'],
                    distance_from_origin_miles=Decimal(str(stop_data['distance_from_origin'])),
                    distance_to_next_stop_miles=self._calculate_distance_to_next_stop(
                        stop_data, route_plan['stops']
                    ),
                    is_required_for_compliance=stop_data.get('is_required_for_compliance', False)
                )
                stops_created.append(stop)
            
            # Create HOSPeriod objects
            hos_periods_created = []
            for period_data in route_plan['hos_periods']:
                related_stop = self._find_related_stop(period_data, stops_created)

                hos_period = HOSPeriod.objects.create(
                    trip=trip,
                    duty_status=period_data['duty_status'],
                    start_datetime=period_data['start_datetime'],
                    end_datetime=period_data['end_datetime'],
                    duration_minutes=period_data['duration_minutes'],
                    start_location=period_data.get('start_location', ''),
                    end_location=period_data.get('end_location', ''),
                    distance_traveled_miles=Decimal(str(period_data.get('distance_traveled_miles', 0))),
                    is_compliant=True,
                    related_stop=related_stop
                )
                hos_periods_created.append(hos_period)
            
            # Update trip with calculated values
            trip.estimated_arrival_time = route_plan['estimated_arrival']
            trip.is_hos_compliant = True
            trip.save()

            return route, stops_created, hos_periods_created
            
        except Exception as e:
            logger.error(f"Error saving route plan for trip {trip.trip_id}: {str(e)}")
            raise

    def _calculate_distance_to_next_stop(self, current_stop: Dict, all_stops: List[Dict]) -> Optional[Decimal]:
        current_sequence = current_stop['sequence_order']
        next_stop = next(
            (stop for stop in all_stops if stop['sequence_order'] == current_sequence + 1),
            None
        )

        if next_stop:
            distance_difference = next_stop['distance_from_origin'] - current_stop['distance_from_origin']
            return Decimal(str(max(0, distance_difference)))
        
        return None
    
    def _find_related_stop(self, period_data: Dict, stops: List[Stops]) -> Optional[Stops]:
        """
        Args:
            period_data: HOS period data
            stops: List of created stop objects
        """
        period_start = period_data['start_datetime']
        period_end = period_data['end_datetime']
        
        for stop in stops:
            # Check if period overlaps with stop time
            if (stop.arrival_time <= period_start <= stop.departure_time or 
                stop.arrival_time <= period_end <= stop.departure_time or
                (period_start <= stop.arrival_time and period_end >= stop.departure_time)):
                return stop
        
        return None
    
    def optimize_route_for_compliance(self, trip: Trip) -> Dict[str, any]:
        """
        Optimize route to ensure HOS compliance with minimal impact on delivery time
        """
        # Get initial route calculation
        initial_calculation = self.calculate_trip_feasibility(trip)

        if not initial_calculation['success']:
            return initial_calculation
        
        feasibility = initial_calculation['feasibility']

        # If already compliant, return as-is
        if feasibility['is_feasible'] and len(feasibility['violations']) == 0:
            return {
                'success': True,
                'optimized': False,
                'message': 'Route is already HOS compliant',
                'route_plan': initial_calculation['route_plan']
            }
        
        # Apply optimization strategies
        optimization_strategies = [
            self._optimize_break_placement,
            self._optimize_fuel_stop_timing,
            self._optimize_daily_reset_placement
        ]

        optimized_plan = initial_calculation['route_plan']
        optimizations_applied = []

        for strategy in optimization_strategies:
            try:
                strategy_result = strategy(trip, optimized_plan, feasibility)
                if strategy_result['improved']:
                    optimized_plan = strategy_result['route_plan']
                    optimizations_applied.append(strategy_result['optimization_type'])
            except Exception as e:
                logger.warning(f"Optimization strategy failed: {str(e)}")
                continue
        
        # Recalculate compliance after optimizations
        if optimizations_applied:
            # Update trip with optimized data for recalculation
            trip.save()
            
            final_feasibility = self.hos_calculator.validate_trip_feasibility(
                trip,
                trip.total_driving_time
            )
        else:
            final_feasibility = feasibility

        return {
            'success': True,
            'optimized': len(optimizations_applied) > 0,
            'route_plan': optimized_plan,
            'feasibility': final_feasibility,
            'optimizations_applied': optimizations_applied,
            'message': f'Route optimized with {len(optimizations_applied)} improvement(s)' if optimizations_applied else 'No optimization improvements possible'
        }
    
    def _optimize_break_placement(self, trip: Trip, route_plan: Dict, feasibility: Dict) -> Dict[str, any]:
        """
        Optimize placement of mandatory breaks to minimize total trip time
        """
        # Look for opportunities to move breaks to more optimal locations
        mandatory_breaks = [stop for stop in route_plan['stops'] if stop['type'] == 'mandatory_break']

        if not mandatory_breaks:
            return {
                'improved': False,
                'route_plan': route_plan,
                'optimization_type': 'break_placement',
                'message': 'No mandatory breaks to optimize'
            }
        
        # Check if breaks can be moved to align with fuel stops or other breaks
        improved = False
        fuel_stops = [stop for stop in route_plan['stops'] if stop['type'] == 'fuel']

        for break_stop in mandatory_breaks:
            # Find nearest fuel stop
            nearest_fuel = None
            min_distance = float('inf')

            for fuel_stop in fuel_stops:
                distance = abs(fuel_stop['distance_from_origin'] - break_stop['distance_from_origin'])
                if distance < min_distance and distance <= self.break_location_buffer_miles:
                    min_distance = distance
                    nearest_fuel = fuel_stop
            
            # If nearby fuel stop is found, combine them
            if nearest_fuel and min_distance <= 25:  # Within 25 miles
                # Update break location to fuel stop location
                break_stop['distance_from_origin'] = nearest_fuel['distance_from_origin']
                break_stop['latitude'] = nearest_fuel['latitude']
                break_stop['longitude'] = nearest_fuel['longitude']
                break_stop['address'] = f"Combined Fuel & Break Stop (Mile {int(nearest_fuel['distance_from_origin'])})"
                
                # Extend duration to accommodate both fuel and break
                break_stop['duration_minutes'] = max(break_stop['duration_minutes'], nearest_fuel['duration_minutes'])
                break_stop['type'] = 'fuel_and_break'
                break_stop['combined_functions'] = ['fuel', 'mandatory_break']
                
                # Remove the separate fuel stop
                route_plan['stops'].remove(nearest_fuel)
                improved = True
        
        return {
            'improved': improved,
            'route_plan': route_plan,
            'optimization_type': 'break_placement',
            'message': 'Optimized break placement by combining with fuel stops' if improved else 'Break placement already optimal'
        }
    
    def _optimize_fuel_stop_timing(self, trip: Trip, route_plan: Dict, feasibility: Dict) -> Dict[str, any]:
        """
        Optimize fuel stop timing to align with mandatory breaks
        """
        fuel_stops = [stop for stop in route_plan['stops'] if stop['type'] == 'fuel']
        mandatory_breaks = [stop for stop in route_plan['stops'] if stop['type'] == 'mandatory_break']
        
        if not fuel_stops or not mandatory_breaks:
            return {
                'improved': False,
                'route_plan': route_plan,
                'optimization_type': 'fuel_timing',
                'message': 'No fuel stops or breaks to optimize'
            }
        
        improved = False
        
        # Try to move fuel stops closer to mandatory breaks
        for fuel_stop in fuel_stops[:]:  # Copy list to avoid modification during iteration
            for break_stop in mandatory_breaks:
                distance = abs(fuel_stop['distance_from_origin'] - break_stop['distance_from_origin'])
                
                # If fuel stop is within reasonable distance of a break
                if 10 <= distance <= 50:  # Between 10-50 miles
                    # Move fuel stop to break location
                    fuel_stop['distance_from_origin'] = break_stop['distance_from_origin']
                    fuel_stop['latitude'] = break_stop['latitude']
                    fuel_stop['longitude'] = break_stop['longitude']
                    fuel_stop['address'] = break_stop['address'].replace('Rest Area', 'Fuel & Rest Area')
                    
                    # Combine the stops
                    combined_duration = max(fuel_stop['duration_minutes'], break_stop['duration_minutes'])
                    fuel_stop['duration_minutes'] = combined_duration
                    fuel_stop['type'] = 'fuel_and_break'
                    fuel_stop['is_required_for_compliance'] = True
                    fuel_stop['combined_functions'] = ['fuel', 'mandatory_break']
                    
                    # Remove the separate break stop
                    route_plan['stops'].remove(break_stop)
                    mandatory_breaks.remove(break_stop)
                    improved = True
                    break
        
        return {
            'improved': improved,
            'route_plan': route_plan,
            'optimization_type': 'fuel_timing',
            'message': 'Optimized fuel stop timing with mandatory breaks' if improved else 'Fuel stop timing already optimal'
        }
    
    def _optimize_daily_reset_placement(self, trip: Trip, route_plan: Dict, feasibility: Dict) -> Dict[str, any]:
        """
        Optimize daily reset placement for multi-day trips
        """
        daily_resets = [stop for stop in route_plan['stops'] if stop['type'] == 'daily_reset']
        
        if not daily_resets:
            return {
                'improved': False,
                'route_plan': route_plan,
                'optimization_type': 'daily_reset',
                'message': 'No daily resets required'
            }
        
        improved = False
        
        # Optimize reset placement to be at reasonable stopping points
        for reset_stop in daily_resets:
            # Check if reset is already at an optimal location
            current_distance = reset_stop['distance_from_origin']
            
            # Look for better placement within +/- 30 miles
            better_location = self._find_optimal_reset_location(
                trip, current_distance, route_plan.get('route_data', {})
            )
            
            if better_location:
                reset_stop['distance_from_origin'] = better_location['distance']
                reset_stop['latitude'] = better_location['latitude']
                reset_stop['longitude'] = better_location['longitude']
                reset_stop['address'] = better_location['address']
                improved = True
        
        return {
            'improved': improved,
            'route_plan': route_plan,
            'optimization_type': 'daily_reset',
            'message': 'Optimized daily reset placement' if improved else 'Daily reset placement already optimal'
        }
    
    def _find_optimal_reset_location(self, trip: Trip, target_distance: float, route_data: Dict) -> Optional[Dict]:
        """
        Find optimal location for daily reset within a reasonable range.
        
        Args:
            trip: Trip instance
            target_distance: Target distance for reset
            route_data: Route data from external API
            
        Returns:
            Dict with optimal location or None
        """
        # This is a simplified implementation
        # In a real implementation, you might query for truck stops, rest areas, etc.
        
        search_radius = 30  # miles
        optimal_distances = [
            target_distance - search_radius,
            target_distance,
            target_distance + search_radius
        ]
        
        for distance in optimal_distances:
            if 0 <= distance <= float(trip.total_distance_miles):
                location = self._interpolate_route_location(
                    route_data, 
                    Decimal(str(distance)), 
                    trip.total_distance_miles
                )
                
                # Prefer locations that sound like truck stops or rest areas
                location['address'] = f"Truck Stop & Rest Area (Mile {int(distance)})"
                location['distance'] = distance
                
                return location
        
        return None
    
    def generate_route_summary(self, trip: Trip, route_plan: Dict) -> Dict[str, any]:
        """
        Generate a comprehensive summary of the route plan
        """
        stops = route_plan.get('stops', [])
        hos_periods = route_plan.get('hos_periods', [])
        
        # Calculate statistics
        total_stops = len(stops)
        fuel_stops = len([s for s in stops if 'fuel' in s['type']])
        mandatory_breaks = len([s for s in stops if 'mandatory_break' in s['type']])
        combined_stops = len([s for s in stops if 'combined_functions' in s])
        
        driving_periods = [p for p in hos_periods if p['duty_status'] == 'driving']
        total_driving_time = sum(p['duration_minutes'] for p in driving_periods) / 60
        total_distance = float(trip.total_distance_miles or 0)
        
        return {
            'trip_id': str(trip.trip_id),
            'origin': trip.current_address,
            'destination': trip.destination_address,
            'departure_time': trip.departure_datetime.isoformat(),
            'estimated_arrival': route_plan.get('estimated_arrival').isoformat() if route_plan.get('estimated_arrival') else None,
            'total_distance_miles': total_distance,
            'total_driving_hours': round(total_driving_time, 2),
            'total_trip_hours': round(route_plan.get('total_duration_hours', 0), 2),
            'statistics': {
                'total_stops': total_stops,
                'fuel_stops': fuel_stops,
                'mandatory_breaks': mandatory_breaks,
                'combined_stops': combined_stops,
                'optimization_savings': combined_stops
            },
            'hos_compliance': {
                'total_driving_periods': len(driving_periods),
                'average_speed_mph': round(total_distance / total_driving_time, 1) if total_driving_time > 0 else 0,
                'breaks_scheduled': mandatory_breaks,
                'compliance_notes': route_plan.get('optimization_notes', [])
            }
        }