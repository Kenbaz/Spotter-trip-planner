from django.utils import timezone
from datetime import timedelta
from users.models import DriverCycleStatus, DailyDrivingRecord


class DriverCycleStatusService:
    """
    Service for properly managing driver cycle status throughout trip lifecycle.
    Ensures HOS data accumulates correctly and maintains compliance tracking.
    """
    @staticmethod
    def get_or_create_current_status(driver):
        """Get driver's current cycle status, creating if it doesn't exist"""
        try:
            return driver.cycle_status
        except DriverCycleStatus.DoesNotExist:
            return DriverCycleStatus.objects.create(
                driver=driver,
                cycle_start_date=timezone.now() - timedelta(days=7),
                total_cycle_hours=0.0,
                current_duty_status='off_duty',
                current_status_start=timezone.now(),
                today_driving_hours=0.0,
                today_on_duty_hours=0.0,
                today_date=timezone.now().date(),
            )
        
    @staticmethod
    def update_status_for_trip_completion(trip):
        """
        Update driver cycle status when a trip is completed.
        This is where hours actually accumulate.
        """
        driver = trip.driver
        cycle_status = DriverCycleStatusService.get_or_create_current_status(driver)

        # Caculate trip duration for HOS periods
        total_driving_hours = 0.0
        total_on_duty_hours = 0.0

        for period in trip.hos_periods.all():
            # Convert period duration to hours
            period_hours = period.duration_minutes / 60.0
            if period.duty_status == 'driving':
                total_driving_hours += period_hours
                total_on_duty_hours += period_hours
            elif period.duty_status == 'on_duty_not_driving':
                total_on_duty_hours += period_hours
        
        # Check if rolling over to a new day is needed
        trip_date = trip.departure_datetime.date()
        current_date = timezone.now().date()

        if trip_date != cycle_status.today_date:
            # Trip spans multiple days, or is for a different day
            # Create daily record for the trip date
            DriverCycleStatusService._create_daily_record(
                driver, trip_date, total_driving_hours, total_on_duty_hours
            )

            if trip_date == current_date:
                # Update current day's totals
                cycle_status.today_driving_hours = total_driving_hours
                cycle_status.today_on_duty_hours = total_on_duty_hours
                cycle_status.today_date = current_date
            else:
                # accumulate totals for the current day
                cycle_status.today_driving_hours += total_driving_hours
                cycle_status.today_on_duty_hours += total_on_duty_hours
            
            # Always accumulate cycle hours
            cycle_status.total_cycle_hours += total_on_duty_hours

            # Update current status based on trip ending
            if trip.status == 'completed':
                cycle_status.current_duty_status = 'off_duty'
                cycle_status.current_status_start = timezone.now()
            
            cycle_status.save()

            print(f"Updated cycle status for {driver.full_name} after trip completion")
            print(f"  Trip hours - Driving: {total_driving_hours}h, On-duty: {total_on_duty_hours}h")
            print(f"  New totals - Today driving: {cycle_status.today_driving_hours}h")
            print(f"  Today on-duty: {cycle_status.today_on_duty_hours}h") 
            print(f"  Cycle total: {cycle_status.total_cycle_hours}h")

            return cycle_status
        
    @staticmethod
    def _create_daily_record(driver, date, driving_hours, on_duty_hours):
        """Create or update daily driving record"""
        daily_record, created = DailyDrivingRecord.objects.update_or_create(
            driver=driver,
            date=date,
            defaults={
                'total_driving_hours': driving_hours,
                'total_on_duty_hours': on_duty_hours,
                'is_compliant': driving_hours <= 11 and on_duty_hours <= 14
            }
        )

        action = "Created" if created else "Updated"
        print(f"{action} daily record for {driver.full_name} on {date}")

        return daily_record
    
    @staticmethod
    def reset_daily_hours_if_needed(driver):
        """Reset daily hours if it's a new day"""
        cycle_status = DriverCycleStatusService.get_or_create_current_status(driver)
        current_date = timezone.now().date()

        if cycle_status.today_date != current_date:
            # Archive previous day's data
            if cycle_status.today_driving_hours > 0 or cycle_status.today_on_duty_hours > 0:
                DriverCycleStatusService._create_daily_record(
                    driver, 
                    cycle_status.today_date, 
                    cycle_status.today_driving_hours, 
                    cycle_status.today_on_duty_hours
                )
            
            # Reset for new day
            cycle_status.today_driving_hours = 0.0
            cycle_status.today_on_duty_hours = 0.0
            cycle_status.today_date = current_date
            cycle_status.save()

            print(f"Reset daily hours for {driver.full_name} - new day: {current_date}")
        
        return cycle_status
    
    @staticmethod
    def get_driver_status_for_trip_planning(driver):
        """
        Get driver's current status formatted for trip planning.
        Resets daily hours if needed and returns current totals.
        """
        # Ensure daily hours are current
        cycle_status = DriverCycleStatusService.reset_daily_hours_if_needed(driver)

        return {
            'total_cycle_hours': cycle_status.total_cycle_hours,
            'today_driving_hours': cycle_status.today_driving_hours,
            'today_on_duty_hours': cycle_status.today_on_duty_hours,
            'current_duty_status': cycle_status.current_duty_status,
            'current_status_start': cycle_status.current_status_start,
            'last_30min_break_end': cycle_status.last_30min_break_end,
            'today_date': cycle_status.today_date,
            
            'remaining_cycle_hours': cycle_status.remaining_cycle_hours,
            'remaining_driving_hours_today': cycle_status.remaining_driving_hours_today,
            'remaining_on_duty_hours_today': cycle_status.remaining_on_duty_hours_today,
            'needs_immediate_break': cycle_status.needs_immediate_break,
            'compliance_warnings': cycle_status.compliance_warnings
        }
    
    @staticmethod
    def manual_status_update(driver, new_status, status_start_time=None):
        """
        Manually update driver's current duty status.
        Use this for status changes outside of trip completion.
        """
        cycle_status = DriverCycleStatusService.get_or_create_current_status(driver)
        
        old_status = cycle_status.current_duty_status
        cycle_status.current_duty_status = new_status
        cycle_status.current_status_start = status_start_time or timezone.now()
        cycle_status.save()
        
        print(f"Manual status update for {driver.full_name}: {old_status} → {new_status}")
        
        return cycle_status
        
        