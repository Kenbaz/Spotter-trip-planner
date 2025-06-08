# trip_api/services/route_planner.py

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from decimal import Decimal
from django.utils import timezone
from django.core.cache import cache, caches
import hashlib
import json
import logging
from ..models import Trip, Route, Stops, HOSPeriod
from .hos_calculator import HOSCalculatorService
from .external_apis import ExternalAPIService


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
            # Get route data from external API
            route_data = self.external_api.get_route_data(
                origin=(float(trip.current_latitude), float(trip.current_longitude)),
                destination=(float(trip.destination_latitude), float(trip.destination_longitude))
            )

            if not route_data['success']:
                return {
                    'success': False,
                    'error': 'Unable to calculate route',
                    'details': route_data.get('error', 'Unknown routing error')
                }
            
            # Extract route information
            total_distance_miles = route_data['distance_miles']
            estimated_driving_hours = route_data['duration_hours']

            # Update trip with calculated values
            trip.total_distance_miles = Decimal(str(total_distance_miles))
            trip.total_driving_time = Decimal(str(estimated_driving_hours))

            # Check feasibility with HOS calculator
            feasibility_report = self.hos_calculator.validate_trip_feasibility(
                trip,
                Decimal(str(estimated_driving_hours))
            )

            # Generate detailed route plan with stops and breaks
            route_plan = self._generate_route_plan(trip, route_data, feasibility_report)

            return {
                'success': True,
                'feasibility': feasibility_report,
                'route_plan': route_plan,
                'route_data': route_data
            }
            
        except Exception as e:
            logger.error(f"Error calculating trip feasibility for trip {trip.trip_id}: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to calculate trip feasibility',
                'details': str(e)
            }
    
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
            # Create Route object
            route = Route.objects.create(
                trip=trip,
                route_geometry=route_data.get('geometry', {}),
                route_instructions=route_data.get('instructions', []),
                total_distance_meters=int(route_data.get('distance_meters', 0)),
                total_duration_seconds=int(route_data.get('duration_seconds', 0)),
                external_route_id=route_data.get('route_id', ''),
                api_provider=route_data.get('provider', 'openrouteservice')
            )

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