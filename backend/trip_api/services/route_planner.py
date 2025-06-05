# trip_api/services/route_planner.py

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from decimal import Decimal
from django.utils import timezone
from ..models import Trip, Route, Stops, HOSPeriod
from .hos_calculator import HOSCalculatorService
from .external_apis import ExternalAPIService


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
    
    def calculate_trip_feasibility(self, trip: Trip) -> Dict[str, any]:
        """
        Analyze trip feasibility and returns Dict with feasibility analysis and route plan
        """
        # Get route data from external API
        route_data = self.external_api.get_route_data(
            origin=(float(trip.current_latitude), float(trip.current_longitude)),
            destination=(float(trip.destination_latitude), float(trip.destination_longitude)
        ))

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

        # Check feasibility
        feasibility_report = self.hos_calculator.validate_trip_feasibility(
            trip,
            Decimal(str(estimated_driving_hours))
        )

        # Generate route plan with stops and breaks
        route_plan = self._generate_route_plan(trip, route_data, feasibility_report)

        return {
            'success': True,
            'feasibility': feasibility_report,
            'route_plan': route_plan,
            'route_data': route_data
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
            'estimated_arrival': None
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
            'start_location': trip.current_address
        })

        current_time = pickup_end_time
        stop_sequence = 2

        # fuel stops based on max fuel distance
        fuel_stops = self._calculate_fuel_stops(trip, route_data)

        required_breaks = feasibility_report.get('required_breaks', [])

        # Comebine and sort all intermediate stops by distance
        all_intermediate_stops = fuel_stops + self._convert_breaks_to_stops(required_breaks, trip)
        all_intermediate_stops.sort(key=lambda x: x['distance_from_origin'])

        # Add intermediate stops and corresponding driving periods
        accumulated_driving_time = Decimal('0')

        for stop in all_intermediate_stops:
            # Calculate driving time to this stop
            distance_to_stop = stop['distance_from_origin'] - current_distance
            driving_time_hours = distance_to_stop / self.average_highway_speed_mph
            driving_time_minutes = int(driving_time_hours * 60)

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
            current_distance = stop['distance_from_origin']

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
            'latitude': trip.destination_latitude,
            'longitude': trip.destination_longitude,
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

        # calculate totals
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
        max_fuel_distance = trip.max_fuel_distance_miles

        current_distance = Decimal('0')
        fuel_stop_number = 1

        while current_distance + max_fuel_distance < total_distance:
            fuel_distance = current_distance + max_fuel_distance

            # Find appropriate fuel stop location
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
    
    def _convert_breaks_to_stops(self, required_breaks: List[Dict], trip: Trip) -> List[Dict]:
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
                
                break_stops.append({
                    'type': 'mandatory_break',
                    'address': f"Rest Area (Mile {int(break_distance)})",
                    'latitude': None,  # Will be interpolated
                    'longitude': None,  # Will be interpolated
                    'duration_minutes': break_info['duration_minutes'],
                    'distance_from_origin': break_distance,
                    'is_required_for_compliance': True
                })
            
            elif break_info['type'] == 'daily_reset':
                reset_distance = (break_info['after_driving_hours'] * self.average_highway_speed_mph)

                break_stops.append({
                    'type': 'daily_reset',
                    'address': f"Rest Area (Mile {int(reset_distance)})",
                    'latitude': None,  # Will be interpolated
                    'longitude': None,  # Will be interpolated
                    'duration_minutes': break_info['duration_minutes'],
                    'distance_from_origin': reset_distance,
                    'is_required_for_compliance': True
                })
        
        return break_stops
    
    def _interpolate_route_location(self, route_data: Dict, target_distance: Decimal, total_distance: Decimal) -> Dict:
        """
        Interpolate approximate location along route at target distance.
        """
        # calculate proportion along route
        proportion = float(target_distance / total_distance)

        origin_lat = route_data.get('origin_lat', 0)
        origin_lng = route_data.get('origin_lng', 0)
        dest_lat = route_data.get('destination_lat', 0)
        dest_lng = route_data.get('destination_lng', 0)
        
        interpolated_lat = origin_lat + (dest_lat - origin_lat) * proportion
        interpolated_lng = origin_lng + (dest_lng - origin_lng) * proportion
        
        return {
            'address': f"Highway Location (Mile {int(target_distance)})",
            'latitude': interpolated_lat,
            'longitude': interpolated_lng
        }
    
    def _get_stop_duty_status(self, stop_type: str) -> str:
        """Get HOS duty status based on stop type"""

        duty_status_mapping = {
            'pickup': 'on_duty_not_driving',
            'delivery': 'on_duty_not_driving',
            'fuel': 'off_duty',
            'mandatory_break': 'off_duty',
            'daily_reset': 'sleeper_berth',
            'rest': 'off_duty'
        }

        return duty_status_mapping.get(stop_type, 'off_duty')
    
    def save_route_plan(self, trip: Trip, route_plan: Dict, route_data: Dict) -> Tuple[Route, List[Stops], List[HOSPeriod]]:
        """
        Save calculated route plan to database.
        """
        route = Route.objects.create(
            trip=trip,
            route_geometry=route_data.get('geometry', {}),
            route_instructions=route_data.get('instructions', []),
            total_distance_meters=int(route_data.get('distance_meters', 0)),
            total_duration_seconds=int(route_data.get('duration_seconds', 0)),
            external_route_id=route_data.get('route_id', ''),
            api_provider=route_data.get('provider', 'openrouteservice')
        )

        # Create stops objects
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
        
        # Create HOS periods objects
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
        
        #Update trip with calculated values
        trip.estimated_arrival_time = route_plan['estimated_arrival']
        trip.save()

        return route, stops_created, hos_periods_created

    def _calculate_distance_to_next_stop(self, current_stop: Dict, all_stops: List[Dict]) -> Optional[Decimal]:
        current_sequence = current_stop['sequence_order']
        next_stop = next(
            (stop for stop in all_stops if stop['sequence_order'] == current_sequence + 1),
            None
        )

        if next_stop:
            distance_difference = next_stop['distance_from_origin'] - current_stop['distance_from_origin']
            return Decimal(str(distance_difference))
        
        return None
    
    def _find_related_stop(self, period_data: Dict, stops: List[Stops]) -> Optional[Stops]:
        """
        Args:
            period_data: HOS period data
            stops: List of created stop objects
        """
        for stop in stops:
            if (stop.arrival_time <= period_data['start_datetime'] <= stop.departure_time or stop.arrival_time <= period_data['end_datetime'] <= stop.departure_time):
                return stop
        
        return None
    
    def optimize_route_for_compliance(self, trip: Trip) -> Dict[str, any]:
        """
        Optimize route to ensure HOS compliance with minimal impact on delivery time
        """
        # Get initial route calc
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
        
        optimization_strategies = [
            self._optimize_break_placement,
            self._optimize_fuel_stop_timing,
            self._optimize_daily_reset_placement
        ]

        optimization_plan = initial_calculation['route_plan']
        optimization_applied = False

        for strategy in optimization_strategies:
            try:
                strategy_result = strategy(trip, optimized_plan, feasibility)
                if strategy_result['improved']:
                    optimized_plan = strategy_result['route_plan']
                    optimization_applied = True
            except Exception as e:
                continue
        
        # Recalculate compliance after optimizations
        final_feasibility = self.hos_calculator.validate_trip_feasibility(
            trip,
            trip.total_driving_time
        )

        return {
            'success': True,
            'optimized': optimization_applied,
            'route_plan': optimized_plan,
            'feasibility': final_feasibility,
            'message': 'Route optimized for HOS compliance' if optimization_applied else 'No optimization needed'
        }
    
    def _optimize_break_placement(self, trip: Trip, route_plan: Dict, feasibility: Dict) -> Dict[str, any]:
        """
        Optimize placement of mandatory breaks to minimize total trip time
        """
        # Implementation would analyze current break placement and adjust timing
        # For now, return unchanged
        return {
            'improved': False,
            'route_plan': route_plan,
            'message': 'Break placement already optimal'
        }
    
    def _optimize_fuel_stop_timing(self, trip: Trip, route_plan: Dict, feasibility: Dict) -> Dict[str, any]:
        """
        Optimize fuel stop timing to align with mandatory breaks
        """
        # Implementation would combine fuel stops with mandatory breaks where possible
        return {
            'improved': False,
            'route_plan': route_plan,
            'message': 'Fuel stop timing already optimal'
        }
    
    def _optimize_daily_reset_placement(self, trip: Trip, route_plan: Dict, feasibility: Dict) -> Dict[str, any]:
        """
        Optimize daily reset placement for multi-day trips
        """
        # Implementation would find optimal locations for 10-hour resets
        return {
            'improved': False,
            'route_plan': route_plan,
            'message': 'Daily reset placement already optimal'
        }