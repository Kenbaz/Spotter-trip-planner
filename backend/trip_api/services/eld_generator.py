# trip_api/services/eld_generator.py

from datetime import datetime, timedelta
from typing import List, Dict
from django.utils import timezone
from ..models import Trip, HOSPeriod


class ELDGeneratorService:
    """
    Service class for generating ELD (Electronic Logging Device) compliant logs.
    Creates formatted log data for regulatory compliance and export.
    """

    def __init__(self):
        # ELD Log formatting constants
        self.log_grid_height = 11
        self.minutes_per_grid_line = 15
        self.hours_per_grid_row = 2
        self.total_minutes_per_day = 24 * 60

         # Duty status symbols for ELD logs
        self.duty_status_symbols = {
            'off_duty': 1,
            'sleeper_berth': 2,
            'driving': 3,
            'on_duty_not_driving': 4
        }
        
        # Duty status colors for visual representation
        self.duty_status_colors = {
            'off_duty': '#000000',
            'sleeper_berth': '#808080',
            'driving': '#FF0000',
            'on_duty_not_driving': '#0000FF'
        }
    
    def generate_eld_log_data(self, trip: Trip) -> Dict[str, any]:
        """Generate complete ELD log data for a trip"""

        try:
            print(f"Generating ELD logs for trip: {trip.trip_id}")
            hos_periods = trip.hos_periods.all().order_by('start_datetime')
            print(f"Found {len(hos_periods)} HOS periods")

            if not hos_periods:
                print("No HOS periods found - this is the issue!")
                return {
                    'success': False,
                    'error': 'No HOS periods found for trip',
                    'details': 'Cannot generate ELD log without duty status periods'
                }
            
            print("HOS periods found, continuing with ELD generation...")
            
            # Group periods by day
            daily_logs = self._group_periods_by_day(hos_periods)
            print(f"Grouped into {len(daily_logs)} daily logs")

            # Generate log data for each day
            eld_logs = []
            for log_date, periods in daily_logs.items():
                print(f"Processing day: {log_date} with {len(periods)} periods")
                daily_log = self._generate_daily_log(trip, log_date, periods)
                eld_logs.append(daily_log)

            # Generate summary data
            summary = self._generate_log_summary(trip, hos_periods)

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
                'generated_at': timezone.now().isoformat()
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
    
    def _group_periods_by_day(self, hos_periods: List[HOSPeriod]) -> Dict[datetime.date, List[HOSPeriod]]:
        """
        Group HOS periods by calendar day
        """
        daily_periods = {}

        for period in hos_periods:
            log_date = period.start_datetime.date()

            if log_date not in daily_periods:
                daily_periods[log_date] = []
            
            daily_periods[log_date].append(period)

            # Handle end of day periods
            if period.end_datetime.date() > log_date:
                next_date = period.end_datetime.date()
                if next_date not in daily_periods:
                    daily_periods[next_date] = []
                
                # Split period at midnight
                midnight = datetime.combine(next_date, datetime.min.time())
                midnight = timezone.make_aware(midnight)

                # Create period for next day
                next_day_period = HOSPeriod(
                    trip=period.trip,
                    duty_status=period.duty_status,
                    start_datetime=midnight,
                    end_datetime=period.end_datetime,
                    duration_minutes=int((period.end_datetime - midnight).total_seconds() / 60),
                    start_location=period.start_location,
                    end_location=period.end_location,
                    distance_traveled_miles=period.distance_traveled_miles,
                    is_compliant=period.is_compliant,
                    related_stop=period.related_stop
                )
                
                daily_periods[next_date].append(next_day_period)
                
                # Adjust original period to end at midnight
                period.end_datetime = midnight
                period.duration_minutes = int((midnight - period.start_datetime).total_seconds() / 60)
        
        return daily_periods
    
    def _generate_daily_log(self, trip: Trip, log_date: datetime.date, periods: List[HOSPeriod]) -> Dict[str, any]:
        """
        Generate ELD log data for a single day
        """
        # sort periods by start time
        sorted_periods = sorted(periods, key=lambda p: p.start_datetime)

        # Generate grid data
        grid_data = self._generate_time_grid(log_date, sorted_periods)

        daily_totals = self._calculate_daily_totals(sorted_periods)

        # Generate location remarks
        location_remarks = self._generate_location_remarks(sorted_periods)

        # Create log entries for each period
        log_entries = []
        for period in sorted_periods:
            entry = {
                'start_time': period.start_datetime.strftime('%H:%M'),
                'end_time': period.end_datetime.strftime('%H:%M'),
                'duty_status': period.duty_status,
                'duty_status_symbol': self.duty_status_symbols.get(period.duty_status, 1),
                'duration_minutes': period.duration_minutes,
                'location': period.start_location or 'Unknown',
                'odometer_start': 0,
                'odometer_end': float(period.distance_traveled_miles or 0),
                'vehicle_miles': float(period.distance_traveled_miles or 0),
                'remarks': self._generate_period_remarks(period)
            }
            log_entries.append(entry)
        
        return {
            'log_date': log_date.isoformat(),
            'driver_name': 'Driver',  # Would come from user data
            'carrier_name': 'Carrier',  # Would come from company data
            'vehicle_id': 'Vehicle-001',  # Would come from vehicle data
            'grid_data': grid_data,
            'log_entries': log_entries,
            'daily_totals': daily_totals,
            'location_remarks': location_remarks,
            'certification': {
                'driver_signature': None,
                'certification_date': None,
                'is_certified': False
            }
        }

    def _generate_time_grid(self, log_data: datetime.date, periods: List[HOSPeriod]) -> List[Dict]:
        """
        Generate time grid data for ELD log visualization
        """

        grid_data = []

        # Create 24-hour timeline ine 15-minute increments
        day_start = datetime.combine(log_data, datetime.min.time())
        day_start = timezone.make_aware(day_start)

        for minute in range(0, self.total_minutes_per_day, self.minutes_per_grid_line):
            current_time = day_start + timedelta(minutes=minute)

            # Find which duty status is applied at this time
            duty_status = self._get_duty_status_at_time(current_time, periods)

            grid_point = {
                'time': current_time.strftime('%H:%M'),
                'minute_of_day': minute,
                'duty_status': duty_status,
                'duty_status_symbol': self.duty_status_symbols.get(duty_status, 1),
                'grid_row': minute // (self.hours_per_grid_row * 60),  # 0-10 (11 rows)
                'grid_column': (minute % (self.hours_per_grid_row * 60)) // self.minutes_per_grid_line
            }
            grid_data.append(grid_point)
        
        return grid_data
    
    def _get_duty_status_at_time(self, target_time: datetime, periods: List[HOSPeriod]) -> str:
        """
        Get the duty status at a specific time.
        """
        for period in periods:
            if period.start_datetime <= target_time < period.end_datetime:
                return period.duty_status
        
        return 'off_duty'
    
    def _calculate_daily_totals(self, periods: List[HOSPeriod]) -> Dict[str, float]:
        """
        Calculate total time in each duty status for the day
        """
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
            totals[key] = round(value, 2)  # Round to 2 decimal places
        
        return totals
    
    def _generate_location_remarks(self, periods: List[HOSPeriod]) -> List[Dict]:
        """ Generate location remarks for the log """

        remarks = []

        for period in periods:
            if period.start_location and period.start_location != 'Unknown':
                remark = {
                    'time': period.start_datetime.strftime('%H:%M'),
                    'location': period.start_location,
                    'type': 'duty_status_change',
                    'duty_status': period.duty_status,
                    'odometer': float(period.distance_traveled_miles or 0)
                }
                remarks.append(remark)
        
        return remarks
    
    def _generate_period_remarks(self, period: HOSPeriod) -> str:
        remarks = []
        
        # Add duty status change remark
        status_descriptions = {
            'off_duty': 'Off Duty',
            'sleeper_berth': 'Sleeper Berth',
            'driving': 'Driving',
            'on_duty_not_driving': 'On Duty (Not Driving)'
        }

        status_desc = status_descriptions.get(period.duty_status, period.duty_status)
        remarks.append(f"Status: {status_desc}")

        # Add location if available
        if period.start_location:
            remarks.append(f"Location: {period.start_location}")
        
        if period.duty_status == 'driving' and period.distance_traveled_miles:
            remarks.append(f"Distance: {period.distance_traveled_miles} miles")
        
        if period.compliance_notes:
            remarks.append(f"Compliance Notes: {period.compliance_notes}")
        
        return "; ".join(remarks)
    
    def _generate_log_summary(self, trip: Trip, hos_periods: List[HOSPeriod]) -> Dict[str, any]:
        """
        Generate summary data for the entire trip
        """
        # Calculate overall totals
        total_driving_time = sum(
            period.duration_minutes for period in hos_periods if period.duty_status == 'driving'
        ) / 60.0

        total_on_duty_time = sum(
            period.duration_minutes for period in hos_periods if period.duty_status in ['driving', 'on_duty_not_driving']
        ) / 60.0

        total_distance = sum(
            float(period.distance_traveled_miles or 0) for period in hos_periods
        )

        # Get trip duration
        if hos_periods:
            trip_start = min(period.start_datetime for period in hos_periods)
            trip_end = max(period.end_datetime for period in hos_periods)
            trip_duration_hours = (trip_end - trip_start).total_seconds() / 3600
        else:
            trip_duration_hours = 0
        
        return {
            'trip_id': str(trip.trip_id),
            'origin': trip.current_address,
            'destination': trip.destination_address,
            'departure_time': trip.departure_datetime.isoformat(),
            'estimated_arrival': trip.estimated_arrival_time.isoformat() if trip.estimated_arrival_time else None,
            'total_distance_miles': float(trip.total_distance_miles or 0),
            'total_driving_hours': round(total_driving_time, 2),
            'total_on_duty_hours': round(total_on_duty_time, 2),
            'trip_duration_hours': round(trip_duration_hours, 2),
            'calculated_distance_miles': round(total_distance, 2),
            'number_of_stops': trip.stops.count(),
            'number_of_duty_periods': len(hos_periods),
            'hos_compliance_status': trip.is_hos_compliant
        }
    
    def export_log_to_pdf_data(self, trip: Trip) -> Dict[str, any]:
        """
        Generate PDF-ready data for ELD logs.
        """
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

        # Create a page for each daily log
        for daily_log in eld_data['daily_logs']:
            page = {
                'log_date': daily_log['log_date'],
                'driver_info': {
                    'name': daily_log['driver_name'],
                    'license_number': 'CDL-123456',
                    'carrier': daily_log['carrier_name']
                },
                'vehicle_info': {
                    'vehicle_id': daily_log['vehicle_id'],
                    'license_plate': 'TRK-001',
                    'vin': 'VIN123456789'
                },
                'grid_visualization': self._format_grid_for_pdf(daily_log['grid_data']),
                'duty_periods': daily_log['log_entries'],
                'daily_totals': daily_log['daily_totals'],
                'location_remarks': daily_log['location_remarks'],
                'certification_section': daily_log['certification']
            }
            pdf_data['page_data'].append(page)

        # Add summary data
        pdf_data['summary_page'] = eld_data['summary']

        return pdf_data
    
    def _format_grid_for_pdf(self, grid_data: List[Dict]) -> Dict[str, any]:
        """
        Format grid data for PDF visualization.
        """
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
        Validate ELD log compliance with federal regulations.
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
        Validate compliance for a single daily log.
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
                'limit': 11
            })
        
        # Check 14-hour on-duty limit
        if totals['total_on_duty'] > 14:
            violations.append({
                'type': 'daily_on_duty_limit',
                'description': f"On-duty time ({totals['total_on_duty']} hours) exceeds 14-hour limit",
                'actual': totals['total_on_duty'],
                'limit': 14
            })
        
        # Check for required off-duty time (10 hours minimum)
        total_off_duty = totals['off_duty'] + totals['sleeper_berth']
        if total_off_duty < 10:
            violations.append({
                'type': 'insufficient_off_duty',
                'description': f"Off-duty time ({total_off_duty} hours) is less than required 10 hours",
                'actual': total_off_duty,
                'required': 10
            })
        
        # Add warnings for approaching limits
        if 9 <= totals['total_driving'] <= 10.5:
            warnings.append({
                'type': 'approaching_driving_limit',
                'description': f"Driving time ({totals['total_driving']} hours) is approaching 11-hour limit"
            })
        
        if 12 <= totals['total_on_duty'] <= 13.5:
            warnings.append({
                'type': 'approaching_on_duty_limit',
                'description': f"On-duty time ({totals['total_on_duty']} hours) is approaching 14-hour limit"
            })
        
        return {
            'log_date': daily_log['log_date'],
            'is_compliant': len(violations) == 0,
            'violations': violations,
            'warnings': warnings,
            'totals_checked': totals
        }
