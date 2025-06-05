# trip_api/management/commands/test_openroute_api.py

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from trip_api.services.external_apis import ExternalAPIService


class Command(BaseCommand):
    help = 'Test OpenRouteService API integration with comprehensive checks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--full-test',
            action='store_true',
            help='Run comprehensive API tests including route calculation',
        )
        parser.add_argument(
            '--origin',
            type=str,
            default='New York, NY',
            help='Origin address for route testing',
        )
        parser.add_argument(
            '--destination',
            type=str,
            default='Los Angeles, CA',
            help='Destination address for route testing',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.HTTP_INFO('Testing OpenRouteService API integration...')
        )
        
        # Check if API key is configured
        if not settings.OPENROUTESERVICE_API_KEY:
            self.stdout.write(
                self.style.ERROR('❌ OPENROUTESERVICE_API_KEY not found in environment variables')
            )
            self.stdout.write('Please add your API key to backend/.env file:')
            self.stdout.write('OPENROUTESERVICE_API_KEY=your_api_key_here')
            raise CommandError('API key not configured')
        
        self.stdout.write(
            self.style.SUCCESS('✅ API key found in configuration')
        )
        
        # Initialize API service
        try:
            api_service = ExternalAPIService()
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to initialize API service: {str(e)}')
            )
            return
        
        # Test API status
        self.stdout.write('\n🔍 Testing API connectivity...')
        status_result = api_service.get_api_status()
        
        if 'openrouteservice' in status_result:
            ors_status = status_result['openrouteservice']
            if ors_status['status'] == 'available':
                self.stdout.write(
                    self.style.SUCCESS(f'✅ API is available (Response time: {ors_status["response_time"]:.2f}ms)')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  API status: {ors_status["status"]}')
                )
                if 'error' in ors_status:
                    self.stdout.write(f'   Error: {ors_status["error"]}')
        
        # Test geocoding
        self.stdout.write('\n🗺️  Testing geocoding...')
        origin_address = options['origin']
        geocode_result = api_service.geocode_address(origin_address)
        
        if geocode_result['success']:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Geocoding successful: {geocode_result["formatted_address"]}')
            )
            self.stdout.write(f'   Coordinates: {geocode_result["latitude"]}, {geocode_result["longitude"]}')
            self.stdout.write(f'   Confidence: {geocode_result["confidence"]}')
            origin_coords = (geocode_result["latitude"], geocode_result["longitude"])
        else:
            self.stdout.write(
                self.style.ERROR(f'❌ Geocoding failed: {geocode_result["error"]}')
            )
            if not options['full_test']:
                return
            # Use fallback coordinates for testing
            origin_coords = (40.7128, -74.0060)  # New York fallback
        
        # Test destination geocoding if doing full test
        if options['full_test']:
            destination_address = options['destination']
            dest_geocode_result = api_service.geocode_address(destination_address)
            
            if dest_geocode_result['success']:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Destination geocoding successful: {dest_geocode_result["formatted_address"]}')
                )
                destination_coords = (dest_geocode_result["latitude"], dest_geocode_result["longitude"])
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Destination geocoding failed: {dest_geocode_result["error"]}')
                )
                destination_coords = (34.0522, -118.2437)  # Los Angeles fallback
            
            # Test route calculation
            self.stdout.write('\n🛣️  Testing route calculation...')
            route_result = api_service.get_route_data(
                origin=origin_coords,
                destination=destination_coords
            )
            
            if route_result['success']:
                self.stdout.write(
                    self.style.SUCCESS('✅ Route calculation successful')
                )
                self.stdout.write(f'   Distance: {route_result["distance_miles"]} miles')
                self.stdout.write(f'   Duration: {route_result["duration_hours"]:.2f} hours')
                self.stdout.write(f'   Provider: {route_result["provider"]}')
                
                # Show additional route details
                if route_result.get('instructions'):
                    instruction_count = len(route_result['instructions'])
                    self.stdout.write(f'   Turn-by-turn instructions: {instruction_count} steps')
                
                if route_result.get('waypoints'):
                    waypoint_count = len(route_result['waypoints'])
                    self.stdout.write(f'   Route waypoints: {waypoint_count} points')
                
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Route calculation failed: {route_result["error"]}')
                )
                if 'details' in route_result:
                    self.stdout.write(f'   Details: {route_result["details"]}')
        
        # Test reverse geocoding
        if options['full_test'] and geocode_result['success']:
            self.stdout.write('\n🔄 Testing reverse geocoding...')
            reverse_result = api_service.reverse_geocode(
                latitude=geocode_result["latitude"],
                longitude=geocode_result["longitude"]
            )
            
            if reverse_result['success']:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Reverse geocoding successful: {reverse_result["formatted_address"]}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Reverse geocoding failed: {reverse_result["error"]}')
                )
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.HTTP_INFO('🎉 API integration test complete!')
        )
        
        if options['full_test']:
            self.stdout.write('Run with --full-test flag for comprehensive testing.')
        else:
            self.stdout.write('Use: python manage.py test_openroute_api --full-test')
            self.stdout.write('     python manage.py test_openroute_api --origin "Chicago, IL" --destination "Miami, FL"')