# trip_api/services/hos_calculator.py

from datetime import datetime, timedelta
from typing import List, Dict
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache
import hashlib
import json
from ..models import Trip, HOSPeriod, ComplianceReport


class HOSCalculatorService:
    """
    Service class for calculating HOS compliance based on federal regulations.
    """

    def __init__(self):
        self.hos_settings = getattr(settings, 'HOS_SETTINGS', {})
        self.max_driving_hours = self.hos_settings.get('max_driving_hours', 11)
        self.max_on_duty_hours = self.hos_settings.get('MAX_ON_DUTY_HOURS', 14)
        self.required_off_duty_hours = self.hos_settings.get('REQUIRED_OFF_DUTY_HOURS', 10)
        self.max_hours_before_break = self.hos_settings.get('MAX_HOURS_BEFORE_BREAK', 8)
        self.required_break_minutes = self.hos_settings.get('REQUIRED_BREAK_MINUTES', 30)
        self.weekly_driving_limit = self.hos_settings.get('WEEKLY_DRIVING_LIMIT', 70)
        self.cycle_days = self.hos_settings.get('CYCLE_DAYS', 8)
    
    def validate_daily_driving_limits(self, driving_hours: Decimal) -> Dict[str, any]:
        is_compliant = driving_hours <= self.max_driving_hours

        return {
            'is_compliant': is_compliant,
            'driving_hours': driving_hours,
            'limit': self.max_driving_hours,
            'violation_hours': max(0, driving_hours - self.max_driving_hours),
            'remaining_hours': max(0, self.max_driving_hours - driving_hours)
        }
    
    def validate_daily_on_duty_limits(self, on_duty_hours: Decimal) -> Dict[str, any]:
        is_compliant = on_duty_hours <= self.max_on_duty_hours

        return {
            'is_compliant': is_compliant,
            'on_duty_hours': on_duty_hours,
            'limit': self.max_on_duty_hours,
            'violation_hours': max(0, on_duty_hours - self.max_on_duty_hours),
            'remaining_hours': max(0, self.max_on_duty_hours - on_duty_hours)
        }
    
    def validate_off_duty_requirements(self, off_duty_hours: Decimal) -> Dict[str, any]:
        is_compliant = off_duty_hours >= self.required_off_duty_hours

        return {
            'is_compliant': is_compliant,
            'off_duty_hours': off_duty_hours,
            'required_hours': self.required_off_duty_hours,
            'deficit_hours': max(0, self.required_off_duty_hours - off_duty_hours),
        }
    
    def validate_30_minutes_break_requirement(self, driving_periods: List[HOSPeriod]) -> Dict[str, any]:
        """
        Validate 30-minute break requirement after 8 hours of driving.
        """
        continuous_driving_hours = Decimal('0')
        breaks_taken = 0
        breaks_required = 0
        violations = []

        current_driving_start = None

        for period in driving_periods:
            if period.duty_status == 'driving':
                if current_driving_start is None:
                    current_driving_start = period.start_datetime
                
                continuous_driving_hours += Decimal(period.duration_minutes) / 60

                # check if 8 hours driving limit have been exceeded without a break
                if continuous_driving_hours > self.max_hours_before_break:
                    breaks_required += 1
                    violations.append({
                        'type': 'missing_30minute_break',
                        'period_start': current_driving_start,
                        'period_end': period.end_datetime,
                        'continuous_hours': float(continuous_driving_hours)
                    })
            
            elif period.duty_status in ['off_duty', 'sleeper_berth']:
                # check if the break is sufficient
                break_miutes = period.duration_minutes
                if break_miutes >= self.required_break_minutes:
                    breaks_taken += 1
                    continuous_driving_hours = Decimal('0')
                    current_driving_start = None
        
        is_compliant = len(violations) == 0

        return {
            'is_compliant': is_compliant,
            'breaks_required': breaks_required,
            'breaks_taken': breaks_taken,
            'violations': violations,
        }
    
    def calculate_weekly_hours(self, periods: List[HOSPeriod], reference_data: datetime) -> Dict[str, any]:
        cycle_start = reference_data - timedelta(days=self.cycle_days-1)
        cycle_end = reference_data + timedelta(days=1)

        total_driving_hours = Decimal('0')

        for period in periods:
            if (period.duty_status == 'driving' and cycle_start <= period.start_datetime <= cycle_end):
                total_driving_hours += Decimal(period.duration_minutes) / 60
        
        is_compliant = total_driving_hours <= self.weekly_driving_limit

        return {
            'is_compliant': is_compliant,
            'total_driving_hours': total_driving_hours,
            'limit': self.weekly_driving_limit,
            'remaining_hours': max(0, self.weekly_driving_limit - total_driving_hours),
            'cycle_start': cycle_start,
            'cycle_end': cycle_end
        }
    
    def calculate_required_breaks(self, trip_duration_hours: Decimal) -> List[Dict[str, any]]:
        """Calculate required breaks based on trip duration"""
        required_breaks = []
        accumulated_driving = Decimal('0')
        break_count = 0

        # 30 minutes break every 8 hours of driving
        while accumulated_driving + self.max_hours_before_break < trip_duration_hours:
            accumulated_driving += self.max_hours_before_break
            break_count += 1

            required_breaks.append({
                'type': 'mandatory_break',
                'duration_minutes': self.required_break_minutes,
                'after_driving_hours': float(accumulated_driving),
                'break_number': break_count
            })
        
        # daily resets for multi-day trips
        if trip_duration_hours > self.max_on_duty_hours:
            days_required = int(trip_duration_hours / self.max_on_duty_hours)

            for day in range(1, days_required + 1):
                required_breaks.append({
                    'type': 'daily_reset',
                    'duration_minutes': self.required_off_duty_hours * 60,
                    'after_driving_hours': float(day * self.max_on_duty_hours),
                    'day_number': day
                })
        
        return required_breaks
    
    def _generate_feasibility_cache_key(self, trip: Trip, estimated_driving_hours: Decimal) -> str:
        cache_data = {
            'trip_id': str(trip.trip_id),
            'estimated_driving_hours': float(estimated_driving_hours),
            'pickup_duration': trip.pickup_duration_minutes,
            'delivery_duration': trip.delivery_duration_minutes,
            'departure_time': trip.departure_datetime.isoformat()
        }

        cache_string = json.dumps(cache_data, sort_keys=True)
        cache_hash = hashlib.md5(cache_string.encode()).hexdigest()

        return f"trip_feasibility_{cache_hash}"
    
    def validate_trip_feasibility(self, trip: Trip, estimated_driving_hours: Decimal) -> Dict[str, any]:
        """
        Validate if the trip can be completed within HOS limits.
        """
        cache_key = self._generate_feasibility_cache_key(trip, estimated_driving_hours)

        cached_result = cache.get(cache_key, using='hos_calculations')
        if cached_result:
            return cached_result

        feasibility_report = {
            'is_feasible': True,
            'required_breaks': [],
            'violations': [],
            'estimated_completion_time': None,
            'modifications_needed': [],
        }

        # Check if estimated driving hours exceed daily limits
        daily_validation = self.validate_daily_driving_limits(estimated_driving_hours)
        if not daily_validation['is_compliant']:
            feasibility_report['violations'].append({
                'type': 'daily_driving_limit_exceeded',
                'details': daily_validation
            })
            feasibility_report['modifications_needed'].append({
                'Trip must be split across multiple days due to 11-hour drving limit'
            })
        
        required_breaks = self.calculate_required_breaks(estimated_driving_hours)
        feasibility_report['required_breaks'] = required_breaks

        # Calculate total trip time including breaks
        total_break_time = sum(
            break_info['duration_minutes'] for break_info in required_breaks
        )

        total_trip_minutes = (estimated_driving_hours * 60) + total_break_time

        # Add pickup and delivery time
        total_trip_minutes += trip.pickup_duration_minutes + trip.delivery_duration_minutes

        feasibility_report['estimated_completion_time'] = (
            trip.departure_datetime + timedelta(minutes=int(total_trip_minutes))
        )

        # Check if trip exceeds 14-hour on-duty window
        total_on_duty_hours = Decimal(total_trip_minutes) / 60
        on_duty_validation = self.validate_daily_on_duty_limits(total_on_duty_hours)

        if not on_duty_validation['is_compliant']:
            feasibility_report['violations'].append({
                'type': 'daily_on_duty_limit_exceeded',
                'details': on_duty_validation
            })
            feasibility_report['modifications_needed'].append({
                'Trip requires daily reset (10-hour off-duty period) due to 14-hour limit'
            })
            feasibility_report['is_feasible'] = False
        
        cache.set(cache_key, feasibility_report, timeout=1800, using='hos_calculations')

        return feasibility_report
    
    def generate_compliance_report(self, trip: Trip) -> ComplianceReport:
        """
        comprehensive compliance report for a trip
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
        
        daily_driving = self.validate_daily_driving_limits(total_driving_hours)
        if not daily_driving['is_compliant']:
            violations.append({
                'type': 'daily_driving_limit',
                'details': daily_driving
            })
        
        daily_on_duty = self.validate_daily_on_duty_limits(total_on_duty_hours)
        if not daily_on_duty['is_compliant']:
            violations.append({
                'type': 'daily_on_duty_limit',
                'details': daily_on_duty
            })
        
        off_duty_validation = self.validate_off_duty_requirement(total_off_duty_hours)
        if not off_duty_validation['is_compliant']:
            violations.append({
                'type': 'insufficient_off_duty',
                'details': off_duty_validation
            })
        
        driving_periods = [p for p in periods if p.duty_status == 'driving']
        break_validation = self.validate_30_minute_break_requirement(driving_periods)
        if not break_validation['is_compliant']:
            violations.extend(break_validation['violations'])
        
        # Calculate compliance score
        total_checks = 4
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


        