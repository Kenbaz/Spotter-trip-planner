# trip_api/management/commands/diagnose_api.py

from django.core.management.base import BaseCommand
from django.conf import settings
import requests
import json


class Command(BaseCommand):
    help = 'Diagnose OpenRouteService API issues'

    def handle(self, *args, **options):
        self.stdout.write('=== OpenRouteService API Diagnostics ===')
        
        # Step 1: Check API key
        api_key = getattr(settings, 'OPENROUTESERVICE_API_KEY', None)
        if not api_key:
            self.stdout.write(self.style.ERROR('❌ No API key configured'))
            self.stdout.write('Set OPENROUTESERVICE_API_KEY in your .env file')
            return
        
        self.stdout.write(f'✅ API key configured: {api_key[:10]}...{api_key[-4:]}')
        
        # Step 2: Test basic connectivity
        self.test_basic_connectivity()
        
        # Step 3: Test API key validity
        self.test_api_key_validity(api_key)
        
        # Step 4: Test specific endpoints
        self.test_geocoding_endpoint(api_key)
        self.test_routing_endpoint(api_key)

    def test_basic_connectivity(self):
        """Test basic internet connectivity"""
        self.stdout.write('\n--- Testing Basic Connectivity ---')
        
        try:
            response = requests.get('https://httpbin.org/get', timeout=10)
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS('✅ Internet connectivity: OK'))
            else:
                self.stdout.write(self.style.ERROR('❌ Internet connectivity: FAILED'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Internet connectivity: {str(e)}'))

    def test_api_key_validity(self, api_key):
        """Test if API key is valid"""
        self.stdout.write('\n--- Testing API Key Validity ---')
        
        try:
            # Test with a simple request
            headers = {'Authorization': api_key}
            response = requests.get(
                'https://api.openrouteservice.org/geocode/search',
                headers=headers,
                params={'text': 'New York', 'size': 1},
                timeout=30
            )
            
            self.stdout.write(f'API Response Status: {response.status_code}')
            
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS('✅ API key is valid'))
                data = response.json()
                features = data.get('features', [])
                if features:
                    self.stdout.write(f'   Found {len(features)} geocoding results')
            elif response.status_code == 401:
                self.stdout.write(self.style.ERROR('❌ API key is invalid or unauthorized'))
                self.stdout.write('   Check your API key at https://openrouteservice.org/dashboard')
            elif response.status_code == 403:
                self.stdout.write(self.style.ERROR('❌ API key forbidden or quota exceeded'))
                self.stdout.write('   Check your usage limits at https://openrouteservice.org/dashboard')
            elif response.status_code == 429:
                self.stdout.write(self.style.ERROR('❌ Rate limit exceeded'))
                self.stdout.write('   Wait a moment and try again')
            else:
                self.stdout.write(self.style.ERROR(f'❌ Unexpected response: {response.status_code}'))
                self.stdout.write(f'   Response: {response.text[:200]}')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ API key test failed: {str(e)}'))

    def test_geocoding_endpoint(self, api_key):
        """Test geocoding endpoint specifically"""
        self.stdout.write('\n--- Testing Geocoding Endpoint ---')
        
        try:
            headers = {'Authorization': api_key}
            params = {
                'text': 'Chicago, IL',
                'size': 1,
                'layers': ['address']
            }
            
            response = requests.get(
                'https://api.openrouteservice.org/geocode/search',
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                features = data.get('features', [])
                if features:
                    feature = features[0]
                    coords = feature['geometry']['coordinates']
                    address = feature['properties']['label']
                    self.stdout.write(self.style.SUCCESS(f'✅ Geocoding: {address}'))
                    self.stdout.write(f'   Coordinates: {coords[1]}, {coords[0]}')
                else:
                    self.stdout.write(self.style.WARNING('⚠️ Geocoding returned no results'))
            else:
                self.stdout.write(self.style.ERROR(f'❌ Geocoding failed: {response.status_code}'))
                self.stdout.write(f'   Response: {response.text[:200]}')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Geocoding test failed: {str(e)}'))

    def test_routing_endpoint(self, api_key):
        """Test routing endpoint specifically"""
        self.stdout.write('\n--- Testing Routing Endpoint ---')
        
        try:
            headers = {
                'Authorization': api_key,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'coordinates': [[-74.0060, 40.7128], [-118.2437, 34.0522]],  # NYC to LA
                'profile': 'driving-hgv',
                'format': 'json'
            }
            
            response = requests.post(
                'https://api.openrouteservice.org/v2/directions/driving-hgv',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                routes = data.get('routes', [])
                if routes:
                    route = routes[0]
                    summary = route.get('summary', {})
                    distance_km = summary.get('distance', 0) / 1000
                    duration_hrs = summary.get('duration', 0) / 3600
                    
                    self.stdout.write(self.style.SUCCESS('✅ Routing successful'))
                    self.stdout.write(f'   Distance: {distance_km:.1f} km')
                    self.stdout.write(f'   Duration: {duration_hrs:.1f} hours')
                else:
                    self.stdout.write(self.style.WARNING('⚠️ Routing returned no routes'))
            else:
                self.stdout.write(self.style.ERROR(f'❌ Routing failed: {response.status_code}'))
                self.stdout.write(f'   Response: {response.text[:200]}')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Routing test failed: {str(e)}'))

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed response information',
        )