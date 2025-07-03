# trip_api/services/eld_generator.py

from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple, Optional
from decimal import Decimal
import json
from django.utils import timezone
from django.contrib.auth import get_user_model
from ..models import Trip, HOSPeriod, Stops
from users.models import SpotterCompany, Vehicle


User = get_user_model()


class ELDGeneratorService:
    """
    Enhanced service class for generating ELD (Electronic Logging Device) compliant logs.
    Auto-populates from trip data, user profiles, and company information.
    """

    def __init__(self):
        # Log formatting constants
        self.log_grid_height = 11
        self.minutes_per_grid_line = 15
        self.hours_per_grid_row = 2
        self.total_minutes_per_day = 24 * 60

        # Duty status symbols
        self.duty_status_symbols = {
            'off_duty': 1,
            'sleeper_berth': 2,
            'driving': 3,
            'on_duty_not_driving': 4,
        }

        # Duty status colors
        self.duty_status_colors = {
            'off_duty': '#000000',
            'sleeper_berth': '#808080',
            'driving': '#FF0000',
            'on_duty_not_driving': '#0000FF',
        }

        # Duty status labels
        self.duty_status_labels = {
            'off_duty': 'Off Duty',
            'sleeper_berth': 'Sleeper Berth',
            'driving': 'Driving',
            'on_duty_not_driving': 'On Duty (Not Driving)',
        }
    
    def generate_eld_log_data(self, trip: Trip) -> Dict[str, any]:
        """Generate complete ELD log data for a trip with auto-population"""

        try:
            print(f"Generating ELD log data for trip: {trip.trip_id}")
            hos_periods = trip.hos_periods.all().order_by('start_datetime')
            print(f"Found {len(hos_periods)} HOS periods")

            if not hos_periods:
                print("No HOS periods found for this trip.")
                return {
                    'success': False,
                    'error': 'No HOS periods found for this trip',
                    'details': 'Cannot generate ELD log without duty status periods'
                }
            
            print("HOS periods found, proceeding with log generation")

            # Get trip context data for auto-population
            trip_context = self._extract_trip_context(trip)

            # Group periods by day
            daily_logs = self._group_periods_by_day(hos_periods)
            print(f"Grouped HOS periods into {len(daily_logs)} days")

            eld_logs = []
            for log_date, periods in daily_logs.items():
                print(f"Processing day: {log_date} with {len(periods)} periods")
                daily_log = self._generate_daily_log_with_context(trip, trip_context, log_date, periods)
                eld_logs.append(daily_log)
            
            summary = self._generate_enhanced_log_summary(trip, trip_context, hos_periods)

            return {
                'success': True,
                'trip_id': str(trip.trip_id),
                'total_days': len(eld_logs),
                'log_date_range': {
                    'start': min(daily_logs.keys()).isoformat(),
                    'end': max(daily_logs.keys()).isoformat()
                },
                'daily_logs': eld_logs,
                'summary': summary,
                'generated_at': timezone.now().isoformat(),
                'trip_context': trip_context
            }
        
        except Exception as e:
            print(f"Exception in generate_eld_log_data: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': 'Failed to generate ELD log data',
                'details': str(e)
            }
    
    def _extract_trip_context(self, trip: Trip) -> Dict[str, any]:
        """Extract all relevant context data from trip for auto-population"""
        context = {
            'driver_info': self._get_driver_info(trip.driver if hasattr(trip, 'driver') else None),
            'company_info': self._get_company_info(trip.driver if hasattr(trip, 'driver') else None),
            'vehicle_info': self._get_vehicle_info(trip),
            'trip_details': self._get_trip_details(trip),
            'route_locations': self._get_route_locations(trip)
        }

        return context
    
    def _get_driver_info(self, driver_user) -> Dict[str, str]:
        """Extract driver information from user profile"""
        if not driver_user:
            return {
                'name': 'Unknown Driver',
                'employee_id': 'N/A',
                'license_number': 'N/A',
                'license_state': 'N/A'
            }
        
        return {
            'name': f"{driver_user.first_name} {driver_user.last_name}".strip() or driver_user.username,
            'employee_id': driver_user.employee_id or 'N/A',
            'license_number': driver_user.driver_license_number or 'N/A',
            'license_state': driver_user.driver_license_state or 'N/A',
            'email': driver_user.email or 'N/A',
            'phone_number': driver_user.phone_number or 'N/A'
        }

    def _get_company_info(self, driver_user) -> Dict[str, str]:
        if not driver_user:
            return {
                'name': 'Unknown Company',
                'address': 'N/A',
                'dot_number': 'N/A',
                'mc_number': 'N/A'
            }
        
        # Get the single Spotter company instance
        try:
            company = SpotterCompany.get_company_instance()
        except Exception:
            return {
                'name': 'Spotter',
                'address': 'N/A',
                'dot_number': 'N/A',
                'mc_number': 'N/A'
            }
        
        return {
            'name': company.name,
            'address': f"{company.address}, {company.city}, {company.state} {company.zip_code}".strip(),
            'dot_number': company.usdot_number,
            'mc_number': company.mc_number,
            'phone': company.phone_number
        }
    
    def _get_vehicle_info(self, trip: Trip) -> Dict[str, str]:
        """Extract vehicle information from trip assignment"""
        vehicle = trip.assigned_vehicle
        
        if not vehicle:
            return {
                'vehicle_id': 'N/A',
                'license_plate': 'N/A',
                'vin': 'N/A',
                'make_model': 'N/A',
                'year': 'N/A'
            }
        
        return {
            'vehicle_id': vehicle.unit_number,
            'license_plate': vehicle.license_plate,
            'vin': vehicle.vin,
            'make_model': f"{vehicle.make} {vehicle.model}".strip(),
            'year': str(vehicle.year)
        }
    
    def _get_trip_details(self, trip: Trip) -> Dict[str, any]:
        """Extract trip-specific details for log generation"""
        return {
            'trip_id': str(trip.trip_id),
            'departure_time': trip.departure_datetime.isoformat() if trip.departure_datetime else None,
            'pickup_location': trip.pickup_address,
            'delivery_location': trip.delivery_address,
            'current_location': trip.current_address,
            'pickup_duration': trip.pickup_duration_minutes,
            'delivery_duration': trip.delivery_duration_minutes,
            'status': trip.status,
            'created_at': trip.created_at.isoformat(),
        }
    
    def _get_route_locations(self, trip: Trip) -> List[Dict[str, any]]:
        """Extract route locations from trip stops and key locations"""
        locations = []
        
        # Add trip start location
        if trip.current_address:
            locations.append({
                'type': 'trip_start',
                'location': trip.current_address,
                'description': 'Trip Start Location',
                'time_estimate': trip.departure_datetime.isoformat() if trip.departure_datetime else None
            })
        
        # Add pickup location
        if trip.pickup_address:
            pickup_time = None
            if trip.departure_datetime:
                pickup_time = trip.departure_datetime.isoformat()
            
            locations.append({
                'type': 'pickup',
                'location': trip.pickup_address,
                'description': 'Pickup Location',
                'time_estimate': pickup_time,
                'duration_minutes': trip.pickup_duration_minutes
            })
        
        # Add any intermediate stops from route planning
        stops = trip.stops.all().order_by('sequence_order') if hasattr(trip, 'stops') else []
        for stop in stops:
            locations.append({
                'type': 'fuel_stop' if 'fuel' in stop.stop_type.lower() else 'intermediate_stop',
                'location': stop.address,
                'description': stop.get_stop_type_display(),
                'time_estimate': stop.arrival_time.isoformat() if hasattr(stop, 'arrival_time') and stop.arrival_time else None,
                'duration_minutes': stop.duration_minutes
            })
        
        # Add delivery location
        if trip.delivery_address:
            locations.append({
                'type': 'delivery',
                'location': trip.delivery_address,
                'description': 'Delivery Location',
                'time_estimate': None,
                'duration_minutes': trip.delivery_duration_minutes
            })
        
        return locations
    
    def _generate_daily_log_with_context(
            self, 
            trip: Trip, 
            trip_context: Dict, 
            log_date: date, 
            periods: List[HOSPeriod]
        ) -> Dict[str, any]:
        """
        Generate ELD log data for a single day with auto-populated context
        """
        # Sort periods by start time
        sorted_periods = sorted(periods, key=lambda p: p.start_datetime)

        # Generate grid data
        grid_data = self._generate_time_grid(log_date, sorted_periods)

        # Calculate daily totals
        daily_totals = self._calculate_daily_totals(sorted_periods)

        # Generate location remarks with trip context
        location_remarks = self._generate_enhanced_location_remarks(sorted_periods, trip_context['route_locations'])

        # Generate shipping documents info
        shipping_documents = self._generate_shipping_documents(trip, trip_context)

        # Create log entries for each period with enhanced data
        log_entries = []
        for period in sorted_periods:
            entry = {
                'start_time': period.start_datetime.strftime('%H:%M'),
                'end_time': period.end_datetime.strftime('%H:%M'),
                'duty_status': period.duty_status,
                'duty_status_label': self.duty_status_labels.get(period.duty_status, 'Unknown'),
                'duty_status_symbol': self.duty_status_symbols.get(period.duty_status, 1),
                'duration_minutes': period.duration_minutes,
                'duration_hours': round(period.duration_minutes / 60.0, 2),
                'location': self._get_enhanced_location_for_period(period, trip_context['route_locations']),
                'odometer_start': getattr(period, 'odometer_start', 0),
                'odometer_end': getattr(period, 'odometer_end', 0),
                'vehicle_miles': float(period.distance_traveled_miles or 0),
                'remarks': self._generate_enhanced_period_remarks(period, trip_context)
            }
            log_entries.append(entry)
        
        return {
            'log_date': log_date.isoformat(),
            'driver_name': trip_context['driver_info']['name'],
            'driver_license': trip_context['driver_info']['license_number'],
            'driver_license_state': trip_context['driver_info']['license_state'],
            'employee_id': trip_context['driver_info']['employee_id'],
            'carrier_name': trip_context['company_info']['name'],
            'carrier_address': trip_context['company_info']['address'],
            'dot_number': trip_context['company_info']['dot_number'],
            'mc_number': trip_context['company_info']['mc_number'],
            'vehicle_id': trip_context['vehicle_info']['vehicle_id'],
            'license_plate': trip_context['vehicle_info']['license_plate'],
            'vin': trip_context['vehicle_info']['vin'],
            'vehicle_make_model': trip_context['vehicle_info']['make_model'],
            'grid_data': grid_data,
            'log_entries': log_entries,
            'daily_totals': daily_totals,
            'location_remarks': location_remarks,
            'shipping_documents': shipping_documents,
            'certification': {
                'driver_signature': None,
                'certification_date': None,
                'is_certified': False,
                'certification_statement': 'I hereby certify that my data entries and my record of duty status for this 24-hour period are true and correct.'
            }
        }
    
    def _generate_enhanced_location_remarks(
            self,
            periods: List[HOSPeriod],
            route_locations: List[Dict]
        ) -> List[Dict]:
        """Generate enhanced location remarks combining HOS periods with route data"""
        remarks = []
        location_map = {loc['location']: loc for loc in route_locations}

        for period in periods:
            location = period.start_location or 'Unknown'

            # Check if this location matches a known route location
            route_info = location_map.get(location, {})
            location_type = route_info.get('type', 'unknown')

            remark = {
                'time': period.start_datetime.strftime('%H:%M'),
                'location': location,
                'location_type': location_type,
                'description': route_info.get('description', ''),
                'duty_status': period.duty_status,
                'duty_status_change': True,
                'odometer': getattr(period, 'odometer_start', 0)
            }

            # Add specific remarks based on location type
            if location_type == 'pickup':
                remark['remarks'] = f"Arrived at pickup location - {route_info.get('description', '')}"
            elif location_type == 'delivery':
                remark['remarks'] = f"Arrived at delivery location - {route_info.get('description', '')}"
            elif location_type == 'fuel_stop':
                remark['remarks'] = f"Fuel stop - {location}"
            else:
                remark['remarks'] = f"Location - {location}"
            
            remarks.append(remark)
        
        return remarks
    
    def _generate_shipping_documents(
        self,
        trip: Trip,
        trip_context: Dict
        ) -> Dict[str, any]:
        """Generate shipping documents section based on trip data"""
        return {
            'bill_of_lading': f"BOL-{trip.trip_id}",
            'manifest_number': f"MAN-{trip.trip_id}",
            'pickup_number': f"PU-{trip.trip_id}",
            'delivery_receipt': f"DR-{trip.trip_id}",
            'commodity': getattr(trip, 'commodity_description', 'General Freight'),
            'weight': getattr(trip, 'cargo_weight', 'N/A'),
            'hazmat': getattr(trip, 'hazmat_required', False),
            'trailer_number': getattr(trip_context['vehicle_info'], 'trailer_number', 'N/A')
        }
    
    def _get_enhanced_location_for_period(
        self,
        period: HOSPeriod,
        route_locations: List[Dict]
        ) -> str:
        """Get enhanced location description for a period"""
        base_location = period.start_location or 'Unknown'

        # Find matching route location
        for route_loc in route_locations:
            if route_loc['location'] == base_location:
                if route_loc.get('description'):
                    return f"{base_location} - {route_loc['description']}"
                break
        return base_location
    
    def _generate_enhanced_period_remarks(
        self,
        period: HOSPeriod,
        trip_context: Dict
        ) -> str:
        """Generate enhanced remarks for individual periods"""
        base_remarks = getattr(period, 'remarks', '') or ''

        # Add context specific remarks based on duty status and location
        if period.duty_status == 'driving':
            if period.distance_traveled_miles:
                base_remarks += f" Drove {period.distance_traveled_miles} miles"
        
        elif period.duty_status == 'on_duty_not_driving':
            # Check if this is at pickup or delivery location
            location = period.start_location or ''
            pickup_loc = trip_context['trip_details'].get('pickup_location', '')
            delivery_loc = trip_context['trip_details'].get('delivery_location', '')

            if pickup_loc and pickup_loc in location:
                base_remarks += 'Loading/Pickup activities'
            elif delivery_loc and delivery_loc in location:
                base_remarks += 'Unloading/Delivery activities'
            else:
                base_remarks += 'On-duty activities'
        
        elif period.duty_status == 'off_duty':
            if period.duration_minutes >= 30:
                base_remarks += 'Required break'
        
        elif period.duty_status == 'sleeper_berth':
            if period.duration_minutes >= 600:
                base_remarks += 'Daily reset period'
        
        return base_remarks.strip()
    
    def _generate_enhanced_log_summary(
        self,
        trip: Trip,
        trip_context: Dict,
        hos_periods: List[HOSPeriod]
        ) -> Dict[str, any]:
        """Generate enhanced summary data with trip context"""
        base_summary = self._generate_log_summary(trip, hos_periods)

        # Add enhanced summary data
        enhanced_summary = {
            **base_summary,
            'trip_overview': {
                'trip_id': str(trip.trip_id),
                'route': f"{trip_context['trip_details']['pickup_location']} → {trip_context['trip_details']['delivery_location']}",
                'driver': trip_context['driver_info']['name'],
                'vehicle': trip_context['vehicle_info']['vehicle_id'],
                'company': trip_context['company_info']['name'],
                'total_distance': sum(float(p.distance_traveled_miles or 0) for p in hos_periods),
                'trip_duration_days': len(set(p.start_datetime.date() for p in hos_periods))
            },
            'compliance_summary': {
                'hos_compliant': True,  # Would be calculated from compliance validation
                'total_violations': 0,  # Would come from validation
                'required_breaks_taken': len([p for p in hos_periods if p.duty_status == 'off_duty' and p.duration_minutes >= 30]),
                'daily_resets_taken': len([p for p in hos_periods if p.duty_status in ['off_duty', 'sleeper_berth'] and p.duration_minutes >= 600])
            }
        }
        
        return enhanced_summary
    
    def _group_periods_by_day(
        self,
        periods: List[HOSPeriod]
        ) -> Dict[date, List[HOSPeriod]]:
        daily_periods = {}

        for period in periods:
            log_date = period.start_datetime.date()

            if log_date not in daily_periods:
                daily_periods[log_date] = []
            
            # Handle periods that cross midnight
            if period.end_datetime.date() != log_date:
                # Split the period at midnight
                midnight = datetime.combine(period.end_datetime.date(), datetime.min.time())
                midnight = timezone.make_aware(midnight)

                # First part (current day)
                current_day_period = HOSPeriod(
                    trip=period.trip,
                    start_datetime=period.start_datetime,
                    end_datetime=midnight,
                    duty_status=period.duty_status,
                    start_location=period.start_location,
                    distance_traveled_miles=period.distance_traveled_miles
                )
                current_day_period.duration_minutes = int((midnight - period.start_datetime).total_seconds() / 60)
                daily_periods[log_date].append(current_day_period)

                # Second part (next day)
                next_day = period.end_datetime.date()
                if next_day not in daily_periods:
                    daily_periods[next_day] = []
                
                next_day_period = HOSPeriod(
                    trip=period.trip,
                    start_datetime=midnight,
                    end_datetime=period.end_datetime,
                    duty_status=period.duty_status,
                    start_location=period.start_location,
                    distance_traveled_miles=0
                )
                next_day_period.duration_minutes = int((period.end_datetime - midnight).total_seconds() / 60)
                daily_periods[next_day].append(next_day_period)
            else:
                daily_periods[log_date].append(period)
        
        return daily_periods
    
    def _generate_time_grid(
        self,
        log_date: date,
        periods: List[HOSPeriod]
        ) -> List[Dict]:
        """Generate time grid data for ELD Log visualization"""
        grid_data = []

        # Create 24-hour timeline in 15-minute increments
        day_start = datetime.combine(log_date, datetime.min.time())
        day_start = timezone.make_aware(day_start)

        for minute in range(0, self.total_minutes_per_day, self.minutes_per_grid_line):
            current_time = day_start + timedelta(minutes=minute)

            # Find which duty status is applied at this time
            duty_status = self._get_duty_status_at_time(current_time, periods)

            grid_point = {
                'time': current_time.strftime('%H:%M'),
                'minute_of_day': minute,
                'duty_status': duty_status,
                'duty_status_label': self.duty_status_labels.get(duty_status, 'Unknown'),
                'duty_status_symbol': self.duty_status_symbols.get(duty_status, 1),
                'duty_status_color': self.duty_status_colors.get(duty_status, '#000000'),
                'grid_row': minute // (self.hours_per_grid_row * 60),  # 0-10 (11 rows)
                'grid_column': (minute % (self.hours_per_grid_row * 60)) // self.minutes_per_grid_line
            }
            grid_data.append(grid_point)
        
        return grid_data
    
    def _get_duty_status_at_time(
        self, 
        target_time: datetime, 
        periods: List[HOSPeriod]
        ) -> str:
        """Get the duty status at a specific time (existing method)"""
        for period in periods:
            if period.start_datetime <= target_time < period.end_datetime:
                return period.duty_status
        
        return 'off_duty'
    
    def _calculate_daily_totals(
        self,
        periods: List[HOSPeriod]
        ) -> Dict[str, float]:
        """Calculate total time in each duty status for the day"""
        totals = {
            'off_duty': 0.0,
            'sleeper_berth': 0.0,
            'driving': 0.0,
            'on_duty_not_driving': 0.0,
            'total_on_duty': 0.0,
            'total_driving': 0.0
        }

        for period in periods:
            hours = period.duration_minutes / 60.0
            duty_status = period.duty_status

            if duty_status in totals:
                totals[duty_status] += hours
            
            # Calculate combined totals
            if duty_status in ['driving', 'on_duty_not_driving']:
                totals['total_on_duty'] += hours
            
            if duty_status == 'driving':
                totals['total_driving'] += hours
        
        for key, value in totals.items():
            totals[key] = round(value, 2)
        
        daily_total = totals['off_duty'] + totals['sleeper_berth'] + totals['driving'] + totals['on_duty_not_driving']
        totals['daily_total_verification'] = round(daily_total, 2)
        
        return totals
    
    def _generate_log_summary(
        self,
        trip: Trip,
        hos_periods: List[HOSPeriod]
        ) -> Dict[str, any]:
        """Generate basic log summary"""
        total_driving = sum(
            Decimal(p.duration_minutes) / 60
            for p in hos_periods if p.duty_status == 'driving'
        )
        
        total_on_duty = sum(
            Decimal(p.duration_minutes) / 60
            for p in hos_periods if p.duty_status in ['on_duty_not_driving', 'driving']
        )

        total_distance = sum(
            Decimal(p.distance_traveled_miles or 0)
            for p in hos_periods
        )
        
        return {
            'total_driving_hours': float(total_driving),
            'total_on_duty_hours': float(total_on_duty),
            'total_distance_miles': float(total_distance),
            'trip_start': hos_periods[0].start_datetime.isoformat() if hos_periods else None,
            'trip_end': hos_periods[-1].end_datetime.isoformat() if hos_periods else None,
            'total_periods': len(hos_periods),
            'unique_locations': len(set(p.start_location for p in hos_periods if p.start_location))
        }
    
    def export_log_to_pdf_data(self, trip: Trip) -> Dict[str, any]:
        """Export log data formatted for PDF generation (existing method, will work with enhanced data)"""
        # Get the full ELD log data
        eld_data = self.generate_eld_log_data(trip)

        if not eld_data['success']:
            return eld_data
    
        pdf_data = {
            'success': True,
            'trip_id': str(trip.trip_id),
            'export_timestamp': timezone.now().isoformat(),
            'page_data': []
        }

        # Create a page for each daily log with enhanced data
        for daily_log in eld_data['daily_logs']:
            page = {
                'log_date': daily_log['log_date'],
                'driver_info': {
                    'name': daily_log['driver_name'],
                    'license_number': daily_log['driver_license'],
                    'license_state': daily_log['driver_license_state'],
                    'employee_id': daily_log['employee_id'],
                    'carrier': daily_log['carrier_name']
                },
                'vehicle_info': {
                    'vehicle_id': daily_log['vehicle_id'],
                    'license_plate': daily_log['license_plate'],
                    'vin': daily_log['vin'],
                    'make_model': daily_log['vehicle_make_model']
                },
                'company_info': {
                    'name': daily_log['carrier_name'],
                    'address': daily_log['carrier_address'],
                    'dot_number': daily_log['dot_number'],
                    'mc_number': daily_log['mc_number']
                },
                'grid_visualization': self._format_grid_for_pdf(daily_log['grid_data']),
                'duty_periods': daily_log['log_entries'],
                'daily_totals': daily_log['daily_totals'],
                'location_remarks': daily_log['location_remarks'],
                'shipping_documents': daily_log['shipping_documents'],
                'certification_section': daily_log['certification']
            }
            pdf_data['page_data'].append(page)

        # Add enhanced summary data
        pdf_data['summary_page'] = eld_data['summary']

        return pdf_data

    def _format_grid_for_pdf(self, grid_data: List[Dict]) -> Dict[str, any]:
        """Format grid data for PDF visualization (existing method, works with enhanced grid)"""
        # 11x8 grid (11 rows of 2 hours each, 8 columns of 15 minutes each)
        grid_matrix = [[0 for _ in range(8)] for _ in range(11)]

        for point in grid_data:
            row = point['grid_row']
            col = point['grid_column']
            if 0 <= row < 11 and 0 <= col < 8:
                grid_matrix[row][col] = point['duty_status_symbol']
        
        return {
            'grid_matrix': grid_matrix,
            'row_labels': [f"{i*2:02d}:00-{(i*2)+1:02d}:59" for i in range(11)],
            'column_labels': [f":{i*15:02d}" for i in range(8)],
            'legend': {
                1: {'symbol': '○', 'description': 'Off Duty', 'color': '#000000'},
                2: {'symbol': '◐', 'description': 'Sleeper Berth', 'color': '#808080'},
                3: {'symbol': '●', 'description': 'Driving', 'color': '#FF0000'},
                4: {'symbol': '◆', 'description': 'On Duty (Not Driving)', 'color': '#0000FF'}
            }
        }

    def validate_log_compliance(self, trip: Trip) -> Dict[str, any]:
        """
        Validate ELD log compliance with federal regulations (enhanced)
        """
        # Generate the log data
        eld_data = self.generate_eld_log_data(trip)
        
        if not eld_data['success']:
            return eld_data
        
        validation_results = {
            'is_compliant': True,
            'violations': [],
            'warnings': [],
            'daily_validations': []
        }

        # Validate each daily log
        for daily_log in eld_data['daily_logs']:
            daily_validation = self._validate_daily_log_compliance(daily_log)
            validation_results['daily_validations'].append(daily_validation)

            if not daily_validation['is_compliant']:
                validation_results['is_compliant'] = False
                validation_results['violations'].extend(daily_validation['violations'])
            
            validation_results['warnings'].extend(daily_validation['warnings'])
        
        return validation_results

    def _validate_daily_log_compliance(self, daily_log: Dict) -> Dict[str, any]:
        """
        Validate compliance for a single daily log (enhanced)
        """
        violations = []
        warnings = []
        totals = daily_log['daily_totals']
        
        # Check 11-hour driving limit
        if totals['total_driving'] > 11:
            violations.append({
                'type': 'daily_driving_limit',
                'description': f"Driving time ({totals['total_driving']} hours) exceeds 11-hour limit",
                'actual': totals['total_driving'],
                'limit': 11,
                'severity': 'critical'
            })
        
        # Check 14-hour on-duty limit
        if totals['total_on_duty'] > 14:
            violations.append({
                'type': 'daily_on_duty_limit',
                'description': f"On-duty time ({totals['total_on_duty']} hours) exceeds 14-hour limit",
                'actual': totals['total_on_duty'],
                'limit': 14,
                'severity': 'critical'
            })
        
        # Check for required off-duty time (10 hours minimum)
        total_off_duty = totals['off_duty'] + totals['sleeper_berth']
        if total_off_duty < 10:
            violations.append({
                'type': 'insufficient_off_duty',
                'description': f"Off-duty time ({total_off_duty} hours) is less than required 10 hours",
                'actual': total_off_duty,
                'required': 10,
                'severity': 'major'
            })
        
        # Check for 30-minute break requirement after 8 hours of driving
        if totals['total_driving'] > 8:
            # Check if there's a 30+ minute break in the log entries
            has_required_break = any(
                entry['duty_status'] in ['off_duty', 'sleeper_berth'] and 
                entry['duration_minutes'] >= 30 
                for entry in daily_log['log_entries']
            )
            
            if not has_required_break:
                violations.append({
                    'type': 'missing_30min_break',
                    'description': f"Missing required 30-minute break after {totals['total_driving']} hours of driving",
                    'severity': 'major'
                })
        
        # Check for 24-hour period accuracy
        daily_verification = totals.get('daily_total_verification', 0)
        if abs(daily_verification - 24.0) > 0.1:  # Allow small rounding differences
            violations.append({
                'type': 'daily_time_accounting',
                'description': f"Daily time periods do not sum to 24 hours (total: {daily_verification})",
                'actual': daily_verification,
                'expected': 24.0,
                'severity': 'minor'
            })
        
        # Add warnings for approaching limits
        if 9 <= totals['total_driving'] <= 10.5:
            warnings.append({
                'type': 'approaching_driving_limit',
                'description': f"Driving time ({totals['total_driving']} hours) is approaching 11-hour limit",
                'remaining_hours': 11 - totals['total_driving']
            })
        
        if 12 <= totals['total_on_duty'] <= 13.5:
            warnings.append({
                'type': 'approaching_on_duty_limit',
                'description': f"On-duty time ({totals['total_on_duty']} hours) is approaching 14-hour limit",
                'remaining_hours': 14 - totals['total_on_duty']
            })
        
        return {
            'log_date': daily_log['log_date'],
            'is_compliant': len(violations) == 0,
            'violations': violations,
            'warnings': warnings,
            'totals_checked': totals,
            'compliance_score': self._calculate_compliance_score(violations, warnings)
        }

    def _calculate_compliance_score(
        self, 
        violations: List[Dict], 
        warnings: List[Dict]
        ) -> float:
        """Calculate a compliance score based on violations and warnings"""
        base_score = 100.0
        
        # Deduct points for violations
        for violation in violations:
            severity = violation.get('severity', 'minor')
            if severity == 'critical':
                base_score -= 25.0
            elif severity == 'major':
                base_score -= 15.0
            elif severity == 'minor':
                base_score -= 5.0
        
        # Deduct smaller amounts for warnings
        for warning in warnings:
            base_score -= 2.0
        
        return max(0.0, base_score)

    def generate_compliance_report(self, trip: Trip) -> Dict[str, any]:
        """
        Generate a comprehensive compliance report for the trip
        """
        validation_results = self.validate_log_compliance(trip)
        eld_data = self.generate_eld_log_data(trip)
        
        if not eld_data['success']:
            return {
                'success': False,
                'error': 'Cannot generate compliance report without ELD data'
            }
        
        # Calculate overall statistics
        total_violations = len(validation_results['violations'])
        total_warnings = len(validation_results['warnings'])
        average_compliance_score = sum(
            daily['compliance_score'] 
            for daily in validation_results['daily_validations']
        ) / len(validation_results['daily_validations']) if validation_results['daily_validations'] else 0
        
        # Group violations by type
        violation_summary = {}
        for violation in validation_results['violations']:
            v_type = violation['type']
            if v_type not in violation_summary:
                violation_summary[v_type] = {'count': 0, 'severity': violation.get('severity', 'minor')}
            violation_summary[v_type]['count'] += 1
        
        return {
            'success': True,
            'trip_id': str(trip.trip_id),
            'report_generated_at': timezone.now().isoformat(),
            'overall_compliance': {
                'is_compliant': validation_results['is_compliant'],
                'compliance_score': round(average_compliance_score, 1),
                'total_violations': total_violations,
                'total_warnings': total_warnings,
                'grade': self._get_compliance_grade(average_compliance_score)
            },
            'violation_summary': violation_summary,
            'daily_breakdown': validation_results['daily_validations'],
            'recommendations': self._generate_compliance_recommendations(validation_results['violations']),
            'trip_summary': eld_data['summary']
        }

    def _get_compliance_grade(self, score: float) -> str:
        """Convert compliance score to letter grade"""
        if score >= 95:
            return 'A+'
        elif score >= 90:
            return 'A'
        elif score >= 85:
            return 'B+'
        elif score >= 80:
            return 'B'
        elif score >= 75:
            return 'C+'
        elif score >= 70:
            return 'C'
        elif score >= 65:
            return 'D'
        else:
            return 'F'

    def _generate_compliance_recommendations(self, violations: List[Dict]) -> List[str]:
        """Generate actionable recommendations based on violations"""
        recommendations = []
        
        violation_types = {v['type'] for v in violations}
        
        if 'daily_driving_limit' in violation_types:
            recommendations.append(
                "Plan for additional rest periods to stay within the 11-hour daily driving limit. "
                "Consider splitting long trips across multiple days."
            )
        
        if 'daily_on_duty_limit' in violation_types:
            recommendations.append(
                "Reduce on-duty time by optimizing loading/unloading procedures and minimizing delays. "
                "Plan for 10-hour reset periods when approaching the 14-hour limit."
            )
        
        if 'insufficient_off_duty' in violation_types:
            recommendations.append(
                "Ensure adequate rest periods between duty cycles. "
                "A minimum of 10 consecutive hours off-duty is required."
            )
        
        if 'missing_30min_break' in violation_types:
            recommendations.append(
                "Schedule a 30-minute break after 8 hours of driving. "
                "This break can be off-duty or sleeper berth time."
            )
        
        if 'daily_time_accounting' in violation_types:
            recommendations.append(
                "Review duty status entries to ensure all 24 hours are properly accounted for. "
                "Check for gaps or overlapping periods in the log."
            )
        
        if not recommendations:
            recommendations.append(
                "All HOS compliance requirements are met. Continue following current practices."
            )
        
        return recommendations

    def get_eld_log_metadata(self, trip: Trip) -> Dict[str, any]:
        """
        Get metadata about ELD logs without generating full log data
        """
        hos_periods = trip.hos_periods.all().order_by('start_datetime')
        
        if not hos_periods:
            return {
                'success': False,
                'error': 'No HOS periods available'
            }
        
        trip_context = self._extract_trip_context(trip)
        
        # Calculate basic statistics
        total_periods = len(hos_periods)
        date_range = {
            'start': hos_periods[0].start_datetime.date().isoformat(),
            'end': hos_periods[-1].end_datetime.date().isoformat()
        }
        
        unique_days = len(set(p.start_datetime.date() for p in hos_periods))
        total_driving_time = sum(p.duration_minutes for p in hos_periods if p.duty_status == 'driving') / 60.0
        total_distance = sum(float(p.distance_traveled_miles or 0) for p in hos_periods)
        
        return {
            'success': True,
            'trip_id': str(trip.trip_id),
            'driver_name': trip_context['driver_info']['name'],
            'vehicle_id': trip_context['vehicle_info']['vehicle_id'],
            'carrier_name': trip_context['company_info']['name'],
            'date_range': date_range,
            'total_days': unique_days,
            'total_periods': total_periods,
            'total_driving_hours': round(total_driving_time, 2),
            'total_distance_miles': round(total_distance, 2),
            'can_generate_logs': True,
            'estimated_pages': unique_days  # One page per day
        }
        