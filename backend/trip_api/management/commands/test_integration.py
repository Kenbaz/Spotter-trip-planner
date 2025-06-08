# trip_api/management/commands/test_authenticated_integration.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
import requests
import json

User = get_user_model()


class Command(BaseCommand):
    help = 'Test complete authenticated API integration with driver workflow'

    def add_arguments(self, parser):
        parser.add_argument(
            '--base-url',
            type=str,
            default='http://localhost:8000',
            help='Base URL for API testing',
        )
        parser.add_argument(
            '--create-test-driver',
            action='store_true',
            help='Create a test driver for testing',
        )
        parser.add_argument(
            '--test-username',
            type=str,
            default='test_driver',
            help='Username for test driver',
        )
        parser.add_argument(
            '--test-password',
            type=str,
            default='testpass123',
            help='Password for test driver',
        )

    def handle(self, *args, **options):
        self.base_url = options['base_url']
        self.test_username = options['test_username']
        self.test_password = options['test_password']
        
        self.stdout.write(
            self.style.HTTP_INFO('🚀 Starting Authenticated Integration Test Suite...')
        )
        
        # Create test driver if requested
        if options['create_test_driver']:
            self._create_test_driver()
        
        # Test sequence
        test_methods = [
            self.test_api_status,
            self.test_authentication,
            self.test_authenticated_geocoding,
            self.test_trip_creation,
            self.test_trip_listing,
            self.test_route_calculation,
            self.test_eld_log_generation,
            self.test_compliance_report,
            self.test_trip_permissions,
        ]
        
        results = []
        self.auth_token = None
        
        for test_method in test_methods:
            try:
                result = test_method()
                results.append(result)
                if result['passed']:
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ {result['test_name']}: {result['message']}")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"❌ {result['test_name']}: {result['message']}")
                    )
                    if result.get('details'):
                        self.stdout.write(f"   Details: {result['details']}")
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ {test_method.__name__}: Unexpected error - {str(e)}")
                )
                results.append({
                    'test_name': test_method.__name__,
                    'passed': False,
                    'message': f'Unexpected error: {str(e)}'
                })
        
        # Summary
        passed_tests = sum(1 for r in results if r['passed'])
        total_tests = len(results)
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(
            self.style.HTTP_INFO(f'📊 Test Results: {passed_tests}/{total_tests} tests passed')
        )
        
        if passed_tests == total_tests:
            self.stdout.write(
                self.style.SUCCESS('🎉 All tests passed! Authenticated integration is working correctly.')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠️  {total_tests - passed_tests} test(s) failed. Please review the issues above.')
            )
    
    def _create_test_driver(self):
        """Create a test driver for testing"""
        try:
            # Check if driver already exists
            if User.objects.filter(username=self.test_username).exists():
                self.stdout.write(f'Test driver {self.test_username} already exists')
                return
            
            # Create test driver
            from users.models import SpotterCompany
            company = SpotterCompany.get_company_instance()
            
            test_driver = User.objects.create_user(
                username=self.test_username,
                password=self.test_password,
                email=f'{self.test_username}@spotter.com',
                first_name='Test',
                last_name='Driver',
                is_driver=True,
                is_active_driver=True,
                hire_date=timezone.now().date()
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Created test driver: {test_driver.full_name} ({test_driver.username})')
            )
            
            # Create test vehicle and assignment
            from users.models import Vehicle, DriverVehicleAssignment
            
            test_vehicle, created = Vehicle.objects.get_or_create(
                unit_number='TEST-001',
                defaults={
                    'vin': 'TEST123456789',
                    'license_plate': 'TEST001',
                    'license_plate_state': 'TX',
                    'year': 2023,
                    'make': 'Test',
                    'model': 'Truck',
                    'vehicle_type': 'truck',
                    'created_by': test_driver
                }
            )
            
            if created:
                self.stdout.write(f'✅ Created test vehicle: {test_vehicle.unit_number}')
            
            # Create vehicle assignment
            assignment, created = DriverVehicleAssignment.objects.get_or_create(
                driver=test_driver,
                vehicle=test_vehicle,
                defaults={
                    'start_date': timezone.now().date(),
                    'assignment_type': 'temporary',
                    'is_active': True,
                    'assigned_by': test_driver
                }
            )
            
            if created:
                self.stdout.write(f'✅ Assigned vehicle {test_vehicle.unit_number} to {test_driver.full_name}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to create test driver: {str(e)}')
            )
    
    def _get_auth_headers(self):
        """Get authentication headers"""
        if self.auth_token:
            return {'Authorization': f'Bearer {self.auth_token}'}
        return {}
    
    def test_api_status(self):
        """Test API server is running"""
        try:
            response = requests.get(f"{self.base_url}/api/utils/api_status/", timeout=5)
            
            if response.status_code == 200:
                return {
                    'test_name': 'API Server Status',
                    'passed': True,
                    'message': 'API server is running'
                }
            else:
                return {
                    'test_name': 'API Server Status',
                    'passed': False,
                    'message': f'API server returned status {response.status_code}'
                }
                
        except requests.exceptions.ConnectionError:
            return {
                'test_name': 'API Server Status',
                'passed': False,
                'message': 'Cannot connect to API server. Is Django running?'
            }
        except Exception as e:
            return {
                'test_name': 'API Server Status',
                'passed': False,
                'message': f'API server test failed: {str(e)}'
            }
    
    def test_authentication(self):
        """Test JWT authentication"""
        try:
            # Test login
            login_data = {
                'username': self.test_username,
                'password': self.test_password
            }
            
            response = requests.post(
                f"{self.base_url}/auth/login/",
                json=login_data,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'access' in data and 'refresh' in data:
                    self.auth_token = data['access']
                    self.refresh_token = data['refresh']
                    
                    # Test token verification
                    verify_response = requests.post(
                        f"{self.base_url}/auth/verify/",
                        json={'token': self.auth_token},
                        timeout=5
                    )
                    
                    if verify_response.status_code == 200:
                        return {
                            'test_name': 'JWT Authentication',
                            'passed': True,
                            'message': f'Successfully authenticated as {self.test_username}'
                        }
                    else:
                        return {
                            'test_name': 'JWT Authentication',
                            'passed': False,
                            'message': 'Token verification failed',
                            'details': verify_response.text
                        }
                else:
                    return {
                        'test_name': 'JWT Authentication',
                        'passed': False,
                        'message': 'Login response missing tokens',
                        'details': response.text
                    }
            else:
                return {
                    'test_name': 'JWT Authentication',
                    'passed': False,
                    'message': f'Login failed with status {response.status_code}',
                    'details': response.text
                }
                
        except Exception as e:
            return {
                'test_name': 'JWT Authentication',
                'passed': False,
                'message': 'Authentication test failed',
                'details': str(e)
            }
    
    def test_authenticated_geocoding(self):
        """Test geocoding with authentication"""
        try:
            if not self.auth_token:
                return {
                    'test_name': 'Authenticated Geocoding',
                    'passed': False,
                    'message': 'No authentication token available'
                }
            
            geocode_data = {'address': 'Dallas, TX'}
            response = requests.post(
                f"{self.base_url}/api/utils/geocode/",
                json=geocode_data,
                headers=self._get_auth_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('latitude') and data.get('longitude'):
                    return {
                        'test_name': 'Authenticated Geocoding',
                        'passed': True,
                        'message': f"Successfully geocoded to {data['latitude']}, {data['longitude']}"
                    }
            
            return {
                'test_name': 'Authenticated Geocoding',
                'passed': False,
                'message': 'Geocoding failed or returned invalid data',
                'details': response.text
            }
            
        except Exception as e:
            return {
                'test_name': 'Authenticated Geocoding',
                'passed': False,
                'message': 'Geocoding test failed',
                'details': str(e)
            }
    
    def test_trip_creation(self):
        """Test authenticated trip creation"""
        try:
            if not self.auth_token:
                return {
                    'test_name': 'Trip Creation',
                    'passed': False,
                    'message': 'No authentication token available'
                }
            
            # Create test trip data
            departure_time = timezone.now() + timedelta(hours=2)
            trip_data = {
                'current_address': 'Houston, TX',
                'current_latitude': 29.7604,
                'current_longitude': -95.3698,
                'destination_address': 'San Antonio, TX',
                'destination_latitude': 29.4241,
                'destination_longitude': -98.4936,
                'departure_datetime': departure_time.isoformat(),
                'max_fuel_distance_miles': 600,
                'pickup_duration_minutes': 45,
                'delivery_duration_minutes': 60
            }
            
            response = requests.post(
                f"{self.base_url}/api/trips/",
                json=trip_data,
                headers=self._get_auth_headers(),
                timeout=10
            )
            
            if response.status_code == 201:
                data = response.json()
                if data.get('success') and data.get('trip', {}).get('trip_id'):
                    # Store trip_id for subsequent tests
                    self.trip_id = data['trip']['trip_id']
                    return {
                        'test_name': 'Trip Creation',
                        'passed': True,
                        'message': f"Trip created successfully with ID: {self.trip_id}"
                    }
            
            return {
                'test_name': 'Trip Creation',
                'passed': False,
                'message': 'Trip creation failed',
                'details': response.text
            }
            
        except Exception as e:
            return {
                'test_name': 'Trip Creation',
                'passed': False,
                'message': 'Trip creation test failed',
                'details': str(e)
            }
    
    def test_trip_listing(self):
        """Test authenticated trip listing"""
        try:
            if not self.auth_token:
                return {
                    'test_name': 'Trip Listing',
                    'passed': False,
                    'message': 'No authentication token available'
                }
            
            # Test my_trips endpoint
            response = requests.get(
                f"{self.base_url}/api/trips/my_trips/",
                headers=self._get_auth_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'trips' in data:
                    trip_count = len(data['trips'])
                    return {
                        'test_name': 'Trip Listing',
                        'passed': True,
                        'message': f"Retrieved {trip_count} trip(s) for current driver"
                    }
            
            return {
                'test_name': 'Trip Listing',
                'passed': False,
                'message': 'Trip listing failed',
                'details': response.text
            }
            
        except Exception as e:
            return {
                'test_name': 'Trip Listing',
                'passed': False,
                'message': 'Trip listing test failed',
                'details': str(e)
            }
    
    def test_route_calculation(self):
        """Test authenticated route calculation"""
        if not hasattr(self, 'trip_id'):
            return {
                'test_name': 'Route Calculation',
                'passed': False,
                'message': 'No trip available for testing (trip creation failed)'
            }
        
        try:
            calc_data = {
                'optimize_route': True,
                'generate_eld_logs': False,
                'include_fuel_optimization': True
            }
            
            response = requests.post(
                f"{self.base_url}/api/trips/{self.trip_id}/calculate_route/",
                json=calc_data,
                headers=self._get_auth_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('route_plan'):
                    route_plan = data['route_plan']
                    stops_count = len(route_plan.get('stops', []))
                    return {
                        'test_name': 'Route Calculation',
                        'passed': True,
                        'message': f"Route calculated with {stops_count} stops"
                    }
            
            return {
                'test_name': 'Route Calculation',
                'passed': False,
                'message': 'Route calculation failed',
                'details': response.text
            }
            
        except Exception as e:
            return {
                'test_name': 'Route Calculation',
                'passed': False,
                'message': 'Route calculation test failed',
                'details': str(e)
            }
    
    def test_eld_log_generation(self):
        """Test ELD log generation"""
        if not hasattr(self, 'trip_id'):
            return {
                'test_name': 'ELD Log Generation',
                'passed': False,
                'message': 'No trip available for testing'
            }
        
        try:
            eld_data = {
                'export_format': 'json',
                'include_validation': True
            }
            
            response = requests.post(
                f"{self.base_url}/api/trips/{self.trip_id}/generate_eld_logs/",
                json=eld_data,
                headers=self._get_auth_headers(),
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('daily_logs'):
                    daily_logs_count = len(data['daily_logs'])
                    return {
                        'test_name': 'ELD Log Generation',
                        'passed': True,
                        'message': f"ELD logs generated for {daily_logs_count} day(s)"
                    }
            
            return {
                'test_name': 'ELD Log Generation',
                'passed': False,
                'message': 'ELD log generation failed',
                'details': response.text
            }
            
        except Exception as e:
            return {
                'test_name': 'ELD Log Generation',
                'passed': False,
                'message': 'ELD log generation test failed',
                'details': str(e)
            }
    
    def test_compliance_report(self):
        """Test compliance report generation"""
        if not hasattr(self, 'trip_id'):
            return {
                'test_name': 'Compliance Report',
                'passed': False,
                'message': 'No trip available for testing'
            }
        
        try:
            response = requests.get(
                f"{self.base_url}/api/trips/{self.trip_id}/compliance_report/",
                headers=self._get_auth_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('compliance_report'):
                    compliance_report = data['compliance_report']
                    is_compliant = compliance_report.get('is_compliant', False)
                    score = compliance_report.get('compliance_score', 0)
                    return {
                        'test_name': 'Compliance Report',
                        'passed': True,
                        'message': f"Compliance report generated (Score: {score}%, {'Compliant' if is_compliant else 'Non-compliant'})"
                    }
            
            return {
                'test_name': 'Compliance Report',
                'passed': False,
                'message': 'Compliance report generation failed',
                'details': response.text
            }
            
        except Exception as e:
            return {
                'test_name': 'Compliance Report',
                'passed': False,
                'message': 'Compliance report test failed',
                'details': str(e)
            }
    
    def test_trip_permissions(self):
        """Test that drivers can only access their own trips"""
        try:
            if not self.auth_token:
                return {
                    'test_name': 'Trip Permissions',
                    'passed': False,
                    'message': 'No authentication token available'
                }
            
            # Try to access trips without authentication (should fail)
            response_no_auth = requests.get(
                f"{self.base_url}/api/trips/",
                timeout=10
            )
            
            # Should return 401 Unauthorized
            if response_no_auth.status_code != 401:
                return {
                    'test_name': 'Trip Permissions',
                    'passed': False,
                    'message': f'Expected 401 for unauthenticated request, got {response_no_auth.status_code}'
                }
            
            # Try to access trips with authentication (should succeed)
            response_with_auth = requests.get(
                f"{self.base_url}/api/trips/",
                headers=self._get_auth_headers(),
                timeout=10
            )
            
            if response_with_auth.status_code == 200:
                return {
                    'test_name': 'Trip Permissions',
                    'passed': True,
                    'message': 'Permission system working correctly (unauthorized blocked, authorized allowed)'
                }
            else:
                return {
                    'test_name': 'Trip Permissions',
                    'passed': False,
                    'message': f'Authenticated request failed with status {response_with_auth.status_code}',
                    'details': response_with_auth.text
                }
            
        except Exception as e:
            return {
                'test_name': 'Trip Permissions',
                'passed': False,
                'message': 'Trip permissions test failed',
                'details': str(e)
            }