# trip_api/services/hos_calculator.py

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache, caches
import hashlib
import json
from ..models import Trip, HOSPeriod, ComplianceReport
from users.models import DriverCycleStatus
import logging


logger = logging.getLogger(__name__)


class HOSCalculatorService:
    """
    Service class for calculating HOS compliance based on federal regulations.
    """

    def __init__(self):
        self.hos_settings = getattr(settings, 'HOS_SETTINGS', {})
        self.max_driving_hours = self.hos_settings.get('MAX_DRIVING_HOURS', 11)
        self.max_on_duty_hours = self.hos_settings.get('MAX_ON_DUTY_HOURS', 14)
        self.required_off_duty_hours = self.hos_settings.get('REQUIRED_OFF_DUTY_HOURS', 10)
        self.max_hours_before_break = self.hos_settings.get('MAX_HOURS_BEFORE_BREAK', 8)
        self.required_break_minutes = self.hos_settings.get('REQUIRED_BREAK_MINUTES', 30)
        self.weekly_driving_limit = self.hos_settings.get('WEEKLY_DRIVING_LIMIT', 70)
        self.cycle_days = self.hos_settings.get('CYCLE_DAYS', 8)
    
    def _get_cache(self, cache_name='default'):
        """Get cache instance with fallback"""
        try:
            if hasattr(caches, cache_name) and cache_name in caches:
                return caches[cache_name]
            else:
                return cache
        except Exception:
            return cache
    
    def validate_daily_driving_limits(self, driving_hours: Decimal) -> Dict[str, any]:
        """
        Validate daily driving hour limits (11-hour rule)
        """
        is_compliant = driving_hours <= self.max_driving_hours

        return {
            'is_compliant': is_compliant,
            'driving_hours': float(driving_hours),
            'limit': self.max_driving_hours,
            'violation_hours': float(max(0, driving_hours - self.max_driving_hours)),
            'remaining_hours': float(max(0, self.max_driving_hours - driving_hours))
        }
    
    def validate_daily_on_duty_limits(self, on_duty_hours: Decimal) -> Dict[str, any]:
        """
        Validate daily on-duty hour limits (14-hour rule)
        """
        is_compliant = on_duty_hours <= self.max_on_duty_hours

        return {
            'is_compliant': is_compliant,
            'on_duty_hours': float(on_duty_hours),
            'limit': self.max_on_duty_hours,
            'violation_hours': float(max(0, on_duty_hours - self.max_on_duty_hours)),
            'remaining_hours': float(max(0, self.max_on_duty_hours - on_duty_hours))
        }
    
    def validate_off_duty_requirements(self, off_duty_hours: Decimal) -> Dict[str, any]:
        """
        Validate off-duty time requirements (10-hour rule)
        """
        is_compliant = off_duty_hours >= self.required_off_duty_hours

        return {
            'is_compliant': is_compliant,
            'off_duty_hours': float(off_duty_hours),
            'required_hours': self.required_off_duty_hours,
            'deficit_hours': float(max(0, self.required_off_duty_hours - off_duty_hours)),
        }
    
    def validate_30_minute_break_requirement(self, driving_periods: List[HOSPeriod]) -> Dict[str, any]:
        """
        Validate 30-minute break requirement after 8 hours of driving
        """
        continuous_driving_hours = Decimal('0')
        breaks_taken = 0
        breaks_required = 0
        violations = []

        current_driving_start = None
        last_break_end = None

        for period in driving_periods:
            if period.duty_status == 'driving':
                if current_driving_start is None:
                    current_driving_start = period.start_datetime
                
                continuous_driving_hours += Decimal(period.duration_minutes) / 60

                # Check if 8 hours driving limit has been exceeded without a break
                if continuous_driving_hours > self.max_hours_before_break:
                    breaks_required += 1
                    violations.append({
                        'type': 'missing_30minute_break',
                        'period_start': current_driving_start.isoformat(),
                        'period_end': period.end_datetime.isoformat(),
                        'continuous_hours': float(continuous_driving_hours),
                        'description': f'Drove {float(continuous_driving_hours):.2f} hours without required 30-minute break'
                    })
            
            elif period.duty_status in ['off_duty', 'sleeper_berth']:
                # Check if the break is sufficient (30 minutes minimum)
                break_minutes = period.duration_minutes
                if break_minutes >= self.required_break_minutes:
                    breaks_taken += 1
                    continuous_driving_hours = Decimal('0')
                    current_driving_start = None
                    last_break_end = period.end_datetime
        
        is_compliant = len(violations) == 0

        return {
            'is_compliant': is_compliant,
            'breaks_required': breaks_required,
            'breaks_taken': breaks_taken,
            'violations': violations,
            'continuous_driving_hours': float(continuous_driving_hours),
            'last_break_end': last_break_end.isoformat() if last_break_end else None
        }
    
    def calculate_weekly_hours(self, periods: List[HOSPeriod], reference_date: datetime) -> Dict[str, any]:
        """
        Calculate weekly driving hours within the 8-day cycle
        
        Args:
            periods: List of HOS periods
            reference_date: Reference date for calculating the 8-day cycle
        """
        cycle_start = reference_date - timedelta(days=self.cycle_days-1)
        cycle_end = reference_date + timedelta(days=1)

        total_driving_hours = Decimal('0')
        driving_days = set()

        for period in periods:
            if (period.duty_status == 'driving' and 
                cycle_start <= period.start_datetime <= cycle_end):
                total_driving_hours += Decimal(period.duration_minutes) / 60
                driving_days.add(period.start_datetime.date())
        
        is_compliant = total_driving_hours <= self.weekly_driving_limit

        return {
            'is_compliant': is_compliant,
            'total_driving_hours': float(total_driving_hours),
            'limit': self.weekly_driving_limit,
            'remaining_hours': float(max(0, self.weekly_driving_limit - total_driving_hours)),
            'cycle_start': cycle_start.isoformat(),
            'cycle_end': cycle_end.isoformat(),
            'driving_days_count': len(driving_days)
        }
    
    def calculate_required_breaks(self, trip_duration_hours: Decimal, driving_hours: Decimal) -> List[Dict[str, any]]:
        """
        Calculate required breaks based on trip duration and driving time
        """
        required_breaks = []
        accumulated_driving = Decimal('0')
        break_count = 0

        # 30-minute break every 8 hours of driving
        while accumulated_driving + self.max_hours_before_break < driving_hours:
            accumulated_driving += self.max_hours_before_break
            break_count += 1

            required_breaks.append({
                'type': 'mandatory_break',
                'duration_minutes': self.required_break_minutes,
                'after_driving_hours': float(accumulated_driving),
                'break_number': break_count,
                'description': f'30-minute break required after {float(accumulated_driving)} hours of driving'
            })
        
        # Daily resets for multi-day trips (when exceeding 14-hour on-duty window)
        if trip_duration_hours > self.max_on_duty_hours:
            days_required = int(trip_duration_hours / self.max_on_duty_hours)

            for day in range(1, days_required + 1):
                required_breaks.append({
                    'type': 'daily_reset',
                    'duration_minutes': self.required_off_duty_hours * 60,
                    'after_hours': float(day * self.max_on_duty_hours),
                    'day_number': day,
                    'description': f'10-hour reset required after day {day} (14-hour on-duty limit)'
                })
        
        return required_breaks
    
    def _generate_feasibility_cache_key(self, trip: Trip, estimated_driving_hours: Decimal) -> str:
        """
        Generate cache key for trip feasibility calculations
        """
        cache_data = {
            'trip_id': str(trip.trip_id),
            'estimated_driving_hours': float(estimated_driving_hours),
            'pickup_duration': trip.pickup_duration_minutes,
            'delivery_duration': trip.delivery_duration_minutes,
            'departure_time': trip.departure_datetime.isoformat(),
            'max_fuel_distance': trip.max_fuel_distance_miles
        }

        cache_string = json.dumps(cache_data, sort_keys=True)
        cache_hash = hashlib.md5(cache_string.encode()).hexdigest()

        return f"trip_feasibility_{cache_hash}"
    
    def validate_trip_feasibility(self, trip: Trip, estimated_driving_hours: Decimal) -> Dict[str, any]:
        """
        Validate if the trip can be completed within HOS limits
        """
        cache_key = self._generate_feasibility_cache_key(trip, estimated_driving_hours)

        try:
            hos_cache = self._get_cache('hos_calculations')
            cached_result = hos_cache.get(cache_key)
        except Exception:
            cached_result = cache.get(cache_key)
            
        if cached_result:
            return cached_result

        feasibility_report = {
            'is_feasible': True,
            'required_breaks': [],
            'violations': [],
            'estimated_completion_time': None,
            'modifications_needed': [],
            'total_trip_hours': 0,
            'total_break_hours': 0
        }

        # Check if estimated driving hours exceed daily limits
        daily_validation = self.validate_daily_driving_limits(estimated_driving_hours)
        if not daily_validation['is_compliant']:
            feasibility_report['violations'].append({
                'type': 'daily_driving_limit_exceeded',
                'details': daily_validation
            })
            feasibility_report['modifications_needed'].append(
                'Trip must be split across multiple days due to 11-hour driving limit'
            )
            feasibility_report['is_feasible'] = False
        
        # Calculate total trip time including non-driving activities
        total_trip_minutes = (estimated_driving_hours * 60) + trip.pickup_duration_minutes + trip.delivery_duration_minutes
        
        # Calculate required breaks
        required_breaks = self.calculate_required_breaks(
            Decimal(total_trip_minutes) / 60, 
            estimated_driving_hours
        )
        feasibility_report['required_breaks'] = required_breaks

        # Add break time to total trip time
        total_break_time = sum(
            break_info['duration_minutes'] for break_info in required_breaks
        )
        total_trip_minutes += total_break_time

        feasibility_report['total_break_hours'] = total_break_time / 60
        feasibility_report['total_trip_hours'] = total_trip_minutes / 60

        # Calculate estimated completion time
        feasibility_report['estimated_completion_time'] = (
            trip.departure_datetime + timedelta(minutes=int(total_trip_minutes))
        ).isoformat()

        # Check if trip exceeds 14-hour on-duty window
        total_on_duty_hours = Decimal(total_trip_minutes) / 60
        on_duty_validation = self.validate_daily_on_duty_limits(total_on_duty_hours)

        if not on_duty_validation['is_compliant']:
            feasibility_report['violations'].append({
                'type': 'daily_on_duty_limit_exceeded',
                'details': on_duty_validation
            })
            feasibility_report['modifications_needed'].append(
                'Trip requires daily reset (10-hour off-duty period) due to 14-hour limit'
            )
            feasibility_report['is_feasible'] = False
        
        # Cache the result
        try:
            hos_cache = self._get_cache('hos_calculations')
            hos_cache.set(cache_key, feasibility_report, timeout=1800)
        except Exception:
            cache.set(cache_key, feasibility_report, timeout=1800)

        return feasibility_report
    
    def validate_trip_feasibility_with_current_status(self, trip: Trip, estimated_driving_hours: Decimal, driver_status: 'DriverCycleStatus') -> Dict[str, any]:
        base_feasibility = self.validate_trip_feasibility(trip, estimated_driving_hours)
        enhanced_feasibility = base_feasibility.copy()

        # Convert to Decimal for consistent calculations
        remaining_driving_today = Decimal(str(self.max_driving_hours)) - Decimal(str(driver_status.today_driving_hours))
        remaining_cycle_hours = Decimal('70') - Decimal(str(driver_status.total_cycle_hours))

        if estimated_driving_hours > remaining_driving_today:
            enhanced_feasibility['violations'].append({
                'type': 'insufficient_daily_driving_hours',
                'required': float(estimated_driving_hours),
                'available': float(remaining_driving_today),
                'shortfall': float(estimated_driving_hours - remaining_driving_today)
            })
            enhanced_feasibility['is_feasible'] = False
        
        if estimated_driving_hours > remaining_cycle_hours:
            enhanced_feasibility['violations'].append({
                'type': 'insufficient_cycle_hours',
                'required': float(estimated_driving_hours),
                'available': float(remaining_cycle_hours),
                'shortfall': float(estimated_driving_hours - remaining_cycle_hours)
            })
            enhanced_feasibility['is_feasible'] = False
        
        if driver_status.needs_immediate_break:
            enhanced_feasibility['required_breaks'].insert(0, {
                'type': 'immediate_mandatory_break',
                'duration_minutes': 30,
                'before_trip_start': True,
                'reason': f'Driver has been driving for {driver_status.hours_since_last_break:.1f} hours'
            })

        enhanced_feasibility['current_status_impact'] = {
            'today_driving_hours_used': driver_status.today_driving_hours,
            'remaining_driving_hours_today': float(remaining_driving_today),
            'cycle_hours_used': driver_status.total_cycle_hours,
            'remaining_cycle_hours': float(remaining_cycle_hours),
            'needs_immediate_break': driver_status.needs_immediate_break,
            'current_duty_status': driver_status.current_duty_status
        }

        return enhanced_feasibility
    
    def generate_compliance_report(self, trip: Trip) -> ComplianceReport:
        """
        Generate comprehensive compliance report for completed trips with ELD Validations
        """
        periods = trip.hos_periods.all().order_by('start_datetime')
        
        # Calculate totals
        total_driving_hours = sum(
            Decimal(p.duration_minutes) / 60 
            for p in periods if p.duty_status == 'driving'
        )
        
        total_on_duty_hours = sum(
            Decimal(p.duration_minutes) / 60 
            for p in periods if p.duty_status in ['driving', 'on_duty_not_driving']
        )
        
        total_off_duty_hours = sum(
            Decimal(p.duration_minutes) / 60 
            for p in periods if p.duty_status in ['off_duty', 'sleeper_berth']
        )
        
        # Run all validations
        violations = []
        warnings = []
        
        # Daily driving validation
        daily_driving = self.validate_daily_driving_limits(total_driving_hours)
        if not daily_driving['is_compliant']:
            violations.append({
                'type': 'daily_driving_limit',
                'details': daily_driving
            })
        elif daily_driving['remaining_hours'] <= 1:
            warnings.append({
                'type': 'approaching_driving_limit',
                'message': f"Only {daily_driving['remaining_hours']:.2f} hours remaining for driving"
            })
        
        # Daily on-duty validation
        daily_on_duty = self.validate_daily_on_duty_limits(total_on_duty_hours)
        if not daily_on_duty['is_compliant']:
            violations.append({
                'type': 'daily_on_duty_limit',
                'details': daily_on_duty
            })
        elif daily_on_duty['remaining_hours'] <= 2:
            warnings.append({
                'type': 'approaching_on_duty_limit',
                'message': f"Only {daily_on_duty['remaining_hours']:.2f} hours remaining for on-duty time"
            })
        
        # Off-duty validation
        off_duty_validation = self.validate_off_duty_requirements(total_off_duty_hours)
        if not off_duty_validation['is_compliant']:
            violations.append({
                'type': 'insufficient_off_duty',
                'details': off_duty_validation
            })
        
        # Break validation
        driving_periods = [p for p in periods if p.duty_status in ['driving', 'off_duty', 'sleeper_berth']]
        break_validation = self.validate_30_minute_break_requirement(driving_periods)
        if not break_validation['is_compliant']:
            for violation in break_validation['violations']:
                violations.append({
                    'type': 'missing_30min_break',
                    'details': violation
                })
        
        # Weekly hours validation (if we have historical data)
        if periods:
            reference_date = periods[0].start_datetime
            weekly_validation = self.calculate_weekly_hours(periods, reference_date)
            if not weekly_validation['is_compliant']:
                violations.append({
                    'type': 'weekly_driving_limit',
                    'details': weekly_validation
                })
        
        # Calculate compliance score
        total_checks = 4  # daily driving, daily on-duty, off-duty, breaks
        passed_checks = sum([
            daily_driving['is_compliant'],
            daily_on_duty['is_compliant'],
            off_duty_validation['is_compliant'],
            break_validation['is_compliant']
        ])
        
        compliance_score = Decimal((passed_checks / total_checks) * 100)
        is_compliant = len(violations) == 0
        
        # Create or update compliance report
        compliance_report, created = ComplianceReport.objects.update_or_create(
            trip=trip,
            defaults={
                'is_compliant': is_compliant,
                'compliance_score': compliance_score,
                'total_driving_hours': total_driving_hours,
                'total_on_duty_hours': total_on_duty_hours,
                'total_off_duty_hours': total_off_duty_hours,
                'violations': violations,
                'warnings': warnings,
                'required_30min_breaks': break_validation['breaks_required'],
                'scheduled_30min_breaks': break_validation['breaks_taken'],
                'required_daily_resets': 1 if total_on_duty_hours > self.max_on_duty_hours else 0,
                'scheduled_daily_resets': 1 if total_off_duty_hours >= self.required_off_duty_hours else 0
            }
        )
        
        return compliance_report
    
    def calculate_optimal_departure_time(self, trip: Trip, estimated_driving_hours: Decimal, desired_arrival_time: Optional[datetime] = None) -> Dict[str, any]:
        """
        Calculate optimal departure time based on HOS constraints
        """
        feasibility = self.validate_trip_feasibility(trip, estimated_driving_hours)
        
        if not feasibility['is_feasible']:
            return {
                'success': False,
                'error': 'Trip is not feasible under current HOS regulations',
                'violations': feasibility['violations'],
                'modifications_needed': feasibility['modifications_needed']
            }
        
        # Calculate minimum trip time including all breaks
        minimum_trip_hours = feasibility['total_trip_hours']
        
        if desired_arrival_time:
            # Work backwards from desired arrival
            optimal_departure = desired_arrival_time - timedelta(hours=minimum_trip_hours)
        else:
            # Use trip's current departure time
            optimal_departure = trip.departure_datetime
        
        return {
            'success': True,
            'optimal_departure_time': optimal_departure.isoformat(),
            'minimum_trip_hours': minimum_trip_hours,
            'estimated_arrival_time': feasibility['estimated_completion_time'],
            'required_breaks': feasibility['required_breaks'],
            'is_feasible': True
        }
    

    def generate_trip_planning_compliance_report(self, trip: Trip) -> ComplianceReport:
        """
        Generate compliance report specifically for trip planning WITH proper calculation
        """
        # Get HOS periods - check both saved and calculated periods
        periods = trip.hos_periods.all().order_by('start_datetime')
        
        # If no saved periods, use the calculated values from route planning
        if not periods.exists():
            logger.info("No saved HOS periods found, using trip calculated values")
            
            # Use the calculated driving time from route planning
            planned_driving_hours = Decimal(str(trip.total_driving_time or 0))
            planned_on_duty_hours = Decimal(str(trip.total_on_duty_time or 0))
            planned_off_duty_hours = Decimal('0.5')  # Assume 30 min break if break was inserted
            
            # Count actual breaks from stops
            break_stops = trip.stops.filter(stop_type='mandatory_break')
            scheduled_breaks = break_stops.count()
            
        else:
            # Calculate from actual periods
            planned_driving_hours = sum(
                Decimal(p.duration_minutes) / 60 
                for p in periods if p.duty_status == 'driving'
            )
            planned_on_duty_hours = sum(
                Decimal(p.duration_minutes) / 60 
                for p in periods if p.duty_status in ['driving', 'on_duty_not_driving']
            )
            planned_off_duty_hours = sum(
                Decimal(p.duration_minutes) / 60 
                for p in periods if p.duty_status in ['off_duty', 'sleeper_berth']
            )
            
            # Count breaks from periods
            break_periods = [p for p in periods if p.duty_status == 'off_duty' and p.duration_minutes >= 30]
            scheduled_breaks = len(break_periods)

        # Get driver's starting conditions
        starting_cycle_hours = Decimal(trip.starting_cycle_hours or 0)
        starting_driving_hours = Decimal(trip.starting_driving_hours or 0)
        starting_on_duty_hours = Decimal(trip.starting_on_duty_hours or 0)

        # Calculate cumulative hours after trip
        total_driving_after_trip = starting_driving_hours + planned_driving_hours
        total_on_duty_after_trip = starting_on_duty_hours + planned_on_duty_hours

        violations = []
        warnings = []

        # Validate daily driving limits (11 hours max)
        daily_driving = self.validate_daily_driving_limits(total_driving_after_trip)
        if not daily_driving['is_compliant']:
            violations.append({
                'type': 'daily_driving_limit',
                'details': {
                    **daily_driving,
                    'starting_hours': float(starting_driving_hours),
                    'trip_hours': float(planned_driving_hours),
                    'total_after_trip': float(total_driving_after_trip)
                }
            })
        elif daily_driving['remaining_hours'] <= 1:
            warnings.append({
                'type': 'approaching_driving_limit',
                'message': f'Only {daily_driving["remaining_hours"]:.1f} hours remaining for driving after this trip'
            })

        # Validate daily on-duty limits (14 hours max)
        daily_on_duty = self.validate_daily_on_duty_limits(total_on_duty_after_trip)
        if not daily_on_duty['is_compliant']:
            violations.append({
                'type': 'daily_on_duty_limit',
                'details': {
                    **daily_on_duty,
                    'starting_hours': float(starting_on_duty_hours),
                    'trip_hours': float(planned_on_duty_hours),
                    'total_after_trip': float(total_on_duty_after_trip)
                }
            })
        elif daily_on_duty['remaining_hours'] <= 1:
            warnings.append({
                'type': 'approaching_on_duty_limit',
                'message': f'Only {daily_on_duty["remaining_hours"]:.1f} hours remaining for on-duty time after this trip'
            })

        # Validate 30-minute break requirement
        required_breaks = 1 if planned_driving_hours > 8 else 0
        
        if required_breaks > scheduled_breaks:
            violations.append({
                'type': 'missing_30min_break',
                'details': {
                    'breaks_required': required_breaks,
                    'breaks_scheduled': scheduled_breaks,
                    'continuous_hours': float(planned_driving_hours),
                    'description': f'Trip plan shows {planned_driving_hours:.2f} hours of continuous driving without required 30-minute break'
                }
            })

        # Calculate compliance score correctly (max 100%)
        total_checks = 3  # driving, on-duty, breaks
        passed_checks = sum([
            daily_driving['is_compliant'],
            daily_on_duty['is_compliant'],
            scheduled_breaks >= required_breaks  # Break compliance
        ])
        
        # Compliance score should be 0-100%, not 0-200%
        compliance_score = Decimal((passed_checks / total_checks) * 100)
        is_compliant = len(violations) == 0

        # Create or update compliance report
        compliance_report, created = ComplianceReport.objects.update_or_create(
            trip=trip,
            defaults={
                'is_compliant': is_compliant,
                'compliance_score': compliance_score,
                'total_driving_hours': planned_driving_hours,
                'total_on_duty_hours': planned_on_duty_hours,
                'total_off_duty_hours': planned_off_duty_hours,
                'violations': violations,
                'warnings': warnings,
                'required_30min_breaks': required_breaks,
                'scheduled_30min_breaks': scheduled_breaks,
                'required_daily_resets': 1 if total_on_duty_after_trip > self.max_on_duty_hours else 0,
                'scheduled_daily_resets': 1 if planned_off_duty_hours >= self.required_off_duty_hours else 0
            }
        )

        logger.info(f"Compliance report generated:")
        logger.info(f"  - Driving hours: {planned_driving_hours}")
        logger.info(f"  - On-duty hours: {planned_on_duty_hours}")
        logger.info(f"  - Required breaks: {required_breaks}")
        logger.info(f"  - Scheduled breaks: {scheduled_breaks}")
        logger.info(f"  - Compliance score: {compliance_score}%")
        logger.info(f"  - Is compliant: {is_compliant}")

        return compliance_report
    
    def validate_30_minute_break_requirement_for_planning(self, periods: List[HOSPeriod], total_driving_hours: Decimal) -> Dict[str, any]:
        """
        Validate 30-minute break requirement specifically for trip planning.
        This checks if breaks are properly scheduled within the planned trip.
        """
        if total_driving_hours <= self.max_hours_before_break:
            return {
                'is_compliant': True,
                'breaks_required': 0,
                'breaks_taken': 0,
                'violations': [],
                'continuous_driving_hours': float(total_driving_hours),
            }
        
        continuous_driving_hours = Decimal('0')
        breaks_taken = 0
        violations = []

        # Look for 30+ minute breaks in the planned periods
        for period in periods:
            if period.duty_status == 'driving':
                continuous_driving_hours += Decimal(period.duration_minutes) / 60
            elif period.duty_status in ['off_duty', 'sleeper_berth']:
                if period.duration_minutes >= self.required_break_minutes:
                    breaks_taken += 1
                    continuous_driving_hours = Decimal('0')
        
        # Check if we ended with too much continuous driving
        if continuous_driving_hours > self.max_hours_before_break:
            violations.append({
                'type': 'missing_30minute_break',
                'description': f'Trip plan shows {float(continuous_driving_hours):.2f} hours of continuous driving without required 30-minute break',
                'continuous_hours': float(continuous_driving_hours),
                'breaks_scheduled': breaks_taken
            })

        break_required = max(1, int(total_driving_hours / self.max_hours_before_break))
        is_compliant = len(violations) == 0 and breaks_taken >= break_required

        return {
            'is_compliant': is_compliant,
            'breaks_required': break_required,
            'breaks_taken': breaks_taken,
            'violations': violations,
            'continuous_driving_hours': float(continuous_driving_hours)
        }