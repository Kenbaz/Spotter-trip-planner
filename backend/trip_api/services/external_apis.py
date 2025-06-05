# trip_api/services/external_apis.py

import requests
import json
from typing import Dict, List, Tuple
from django.conf import settings
from django.core.cache import cache, caches
import logging

logger = logging.getLogger(__name__)


class ExternalAPIService:
    """
    Service class for handling external API integrations.
    Manages OpenRouteService API calls, geocoding, and route optimization.
    """
    def __init__(self):
        self.openrouteservice_api_key = getattr(settings, 'OPENROUTESERVICE_API_KEY', None)
        self.openrouteservice_base_url = 'https://api.openrouteservice.org'
        self.geocoding_base_url = 'https://api.openrouteservice.org/geocode'
        self.direction_base_url = 'https://api.openrouteservice.org/v2/directions'

        self.cache_timeout = 60 * 60 
        self.request_timeout = 30

        self.meters_to_miles = 0.000621371
        self.seconds_to_hours = 1 / 3600
    
    def _get_cache(self, cache_name='default'):
        """Get cache instance with fallback"""
        try:
            if hasattr(caches, cache_name):
                return caches[cache_name]
            else:
                return cache
        except:
            return cache
    
    def get_route_data(self, origin: Tuple[float, float], destination: Tuple[float, float]) -> Dict[str, any]:
        """
        Get route data from OpenRouteService API.
        
        Args:
            origin: Tuple of (latitude, longitude) for starting point
            destination: Tuple of (latitude, longitude) for destination
            
        Returns:
            Dict with route data or error information
        """
        try:
            cache_key = f"route_{origin[0]}_{destination[0]}_{destination[1]}"
            try:
                api_cache = self._get_cache('api_responses')
                cached_result = api_cache.get(cache_key)
            except:
                cached_result = cache.get(cache_key)
                
            if cached_result:
                logger.info(f"Using cached route data for {cache_key}")
                return cached_result
            
            # request parameters
            coordinates = [
                [origin[1], origin[0]],  # OpenRouteService expects [lng, lat]
                [destination[1], destination[0]]
            ]

            headers = {
                'Authorization': self.openrouteservice_api_key,
                'Content-Type': 'application/json'
            }

            # Request payload for driving-hgv (heavy goods vehicle)
            payload = {
                'coordinates': coordinates,
                'profile': 'driving-hgv',
                'format': 'json',
                'geometry_format': 'geojson',
                'instructions': True,
                'elevation': False,
                'extra_info': ['surface', 'tollways', 'restrictions'],
                'options': {
                    'avoid_features': ['ferries'],
                    'vehicle_type': 'hgv'
                }
            }

            response = requests.post(
                f"{self.direction_base_url}/driving-hgv",
                headers=headers,
                json=payload,
                timeout=self.request_timeout
            )

            if response.status_code == 200:
                route_data = response.json()
                processed_data = self._process_route_response(route_data, origin, destination)

                try:
                    api_cache = self._get_cache('api_responses')
                    api_cache.set(cache_key, processed_data, timeout=7200)
                except:
                    cache.set(cache_key, processed_data, timeout=7200)

                return processed_data
            
            else:
                logger.error(f"OpenRouteService API error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f"API request failed with status {response.status_code}",
                    'details': response.text
                }
        
        except requests.exceptions.Timeout:
            logger.error("OpenRouteService API request timed out")
            return {
                'success': False,
                'error': 'API request timed out',
                'details': 'The routing service took too long to respond'
            }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouteService API request failed: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to connect to routing service',
                'details': str(e)
            }
        
        except Exception as e:
            logger.error(f"Unexpected error in route calculation: {str(e)}")
            return {
                'success': False,
                'error': 'Unexpected error occurred',
                'details': str(e)
            }
    
    def _process_route_response(self, route_data: Dict, origin: Tuple[float, float], destination: Tuple[float, float]) -> Dict[str, any]:
        """
        Process and normalize OpenRouteService response data.
        
        Args:
            route_data: Raw response from OpenRouteService
            origin: Origin coordinates
            destination: Destination coordinates
            
        Returns:
            Processed and normalized route data
        """
        try:
            # Extracting route information
            routes = route_data.get('routes', [])
            if not routes:
                return {
                    'success': False,
                    'error': 'No routes found',
                    'details': 'The routing service could not find a route between the specified locations'
                }
            
            best_route = routes[0]
            summary = best_route.get('summary', {})

            # extract basic route metrics
            distance_meters = summary.get('distance', 0)
            duration_seconds = summary.get('duration', 0)

            # convert to standard units
            distance_miles = distance_meters * self.meters_to_miles
            duration_hours = duration_seconds * self.seconds_to_hours

            # extract geometry and instructions
            geometry = best_route.get('geometry', {})
            segments = best_route.get('segments', [])

            # process turn by turn instructions
            instructions = []
            for segment in segments:
                for step in segment.get('steps', []):
                    instruction = {
                        'instruction': step.get('instruction', ''),
                        'distance_meters': step.get('distance', 0),
                        'duration_seconds': step.get('duration', 0),
                        'type': step.get('type', 0),
                        'name': step.get('name', ''),
                        'way_points': step.get('way_points', [])
                    }
                    instructions.append(instruction)
            
            extract_info = best_route.get('extras', {})
            surface_info = extract_info.get('surface', {})
            tollway_info = extract_info.get('tollways', {})

            return {
                'success': True,
                'provider': 'openrouteservice',
                'route_id': route_data.get('metadata', {}).get('query', {}).get('id', ''),
                'distance_meters': distance_meters,
                'distance_miles': round(distance_miles, 2),
                'duration_seconds': duration_seconds,
                'duration_hours': round(duration_hours, 2),
                'geometry': geometry,
                'instructions': instructions,
                'origin_lat': origin[0],
                'origin_lng': origin[1],
                'destination_lat': destination[0],
                'destination_lng': destination[1],
                'surface_types': surface_info.get('values', []),
                'tollways': tollway_info.get('values', []),
                'waypoints': self._extract_waypoints(best_route),
                'elevation_profile': self._extract_elevation_profile(best_route)
            }
        
        except Exception as e:
            logger.error(f"Error processing route response: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to process route data',
                'details': str(e)
            }
    
    def _process_geocode_response(self, geocode_data: Dict, original_address: str) -> Dict[str, any]:
        """
        Process geocoding response from OpenRouteService.
        
        Args:
            geocode_data: Raw geocoding response
            original_address: Original address that was geocoded
            
        Returns:
            Processed geocoding data
        """
        try:
            features = geocode_data.get('features', [])
            if not features:
                return {
                    'success': False,
                    'error': 'No geocoding results found',
                    'details': f"Could not find coordinates for address: {original_address}"
                }
            
            best_match = features[0]
            properties = best_match.get('properties', {})
            geometry = best_match.get('geometry', {})
            coordinates = geometry.get('coordinates', [])

            if len(coordinates) < 2:
                return {
                    'success': False,
                    'error': 'Invalid coordinates in geocoding response',
                    'details': 'The geocoding service returned invalid coordinate data'
                }
            
            # Extract latitude and longitude
            longitude = coordinates[0]
            latitude = coordinates[1]

            formatted_address = properties.get('label', original_address)
            confidence = properties.get('confidence', 0)

            return {
                'success': True,
                'latitude': latitude,
                'longitude': longitude,
                'formatted_address': formatted_address,
                'confidence': confidence,
                'source': properties.get('source', 'openrouteservice'),
                'country': properties.get('country', ''),
                'region': properties.get('region', ''),
                'locality': properties.get('locality', ''),
                'postal_code': properties.get('postalcode', '')
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': 'Failed to process geocoding response',
                'details': str(e)
            }

    def geocode_address(self, address: str) -> Dict[str, any]:
        """
        Geocode an address to get coordinates.
        
        Args:
            address: Address string to geocode
            
        Returns:
            Dict with geocoding results
        """
        try:
            cache_key = f"geocode_{address.lower().replace(' ', '_')}"
            try:
                api_cache = self._get_cache('api_responses')
                cached_result = api_cache.get(cache_key)
            except:
                cached_result = cache.get(cache_key)
                
            if cached_result:
                return cached_result
            
            headers = {
                'Authorization': self.openrouteservice_api_key,
            }

            params = {
                'api_key': self.openrouteservice_api_key,
                'text': address,
                'size': 1,  # Only return the best match
                'layers': ['address', 'venue', 'street']
            }

            response = requests.get(
                f"{self.geocoding_base_url}/search",
                headers=headers,
                params=params,
                timeout=self.request_timeout
            )

            if response.status_code == 200:
                geocode_data = response.json()
                processed_data = self._process_geocode_response(geocode_data, address)

                if processed_data['success']:
                    try:
                        api_cache = self._get_cache('api_responses')
                        api_cache.set(cache_key, processed_data, timeout=86400)
                    except:
                        cache.set(cache_key, processed_data, timeout=86400)

                return processed_data
            
            else:
                return {
                    'success': False,
                    'error': f"Geocoding failed with status {response.status_code}",
                    'details': response.text
                }
        
        except Exception as e:
            logger.error(f"Geocoding error for address '{address}': {str(e)}")
            return {
                'success': False,
                'error': 'Geocoding failed',
                'details': str(e)
            }
    
    def reverse_geocode(self, latitude: float, longitude: float) -> Dict[str, any]:
        """
        Reverse geocode coordinates to get address.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Dict with reverse geocoding results
        """
        try:
            cache_key = f"reverse_geocode_{latitude}_{longitude}"
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result

            headers = {
                'Authorization': self.openrouteservice_api_key,
            }

            params = {
                'api_key': self.openrouteservice_api_key,
                'point.lat': latitude,
                'point.lon': longitude,
                'size': 1,
            }

            response = requests.get(
                f"{self.geocoding_base_url}/reverse",
                headers=headers,
                params=params,
                timeout=self.request_timeout
            )

            if response.status == 200:
                reverse_data = response.json()
                processed_data = self._process_reverse_geocode_response(reverse_data, latitude, longitude)

                # Cache successful results
                if processed_data['success']:
                    cache.set(cache_key, processed_data, self.cache_timeout)
                
                return processed_data
            
            else:
                return {
                    'success': False,
                    'error': f"Reverse geocoding failed with status {response.status_code}",
                    'details': response.text
                }
        
        except Exception as e:
            logger.error(f"Reverse geocoding error for coordinates ({latitude}, {longitude}): {str(e)}")
            return {
                'success': False,
                'error': 'Reverse geocoding failed',
                'details': str(e)
            }
        
    def _process_reverse_geocode_response(self, reverse_data: Dict, latitude: float, longitude: float) -> Dict[str, any]:
        """
        Process reverse geocoding response.
        
        Args:
            reverse_data: Raw reverse geocoding response
            latitude: Original latitude
            longitude: Original longitude
            
        Returns:
            Processed reverse geocoding data
        """
        try:
            features = reverse_data.get('features', [])
            if not features:
                return {
                    'success': False,
                    'error': 'No reverse geocoding results found',
                    'details': f"Could not find address for coordinates: ({latitude}, {longitude})"
                }
            
            best_match = features[0]
            properties = best_match.get('properties', {})

            formatted_address = properties.get('label', f'Location ({latitude}, {longitude})')

            return {
                'success': True,
                'formatted_address': formatted_address,
                'country': properties.get('country', ''),
                'region': properties.get('region', ''),
                'locality': properties.get('locality', ''),
                'postal_code': properties.get('postalcode', ''),
                'confidence': properties.get('confidence', 0),
                'source': 'openrouteservice'
            }
        
        except Exception as e:
            logger.error(f"Error processing reverse geocode response: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to process reverse geocode data',
                'details': str(e)
            }
    
    def _extract_waypoints(self, route: Dict) -> List[Dict]:
        """
        Extract waypoints from route geometry.
        
        Args:
            route: Route data from OpenRouteService
            
        Returns:
            List of waypoint dictionaries
        """
        waypoints = []
        geometry = route.get('geometry', {})
        coordinates = geometry.get('coordinates', [])

        # Extract waypoints from coordinates
        for i, coord in enumerate(coordinates[::10]):
            waypoints.append({
                'sequence': i,
                'longitude': coord[0],
                'latitude': coord[1],
                'elevation': coord[2] if len(coord) > 2 else None
            })
        
        return waypoints
    
    def _extract_elevation_profile(self, route: Dict) -> List[Dict]:
        """
        Extract elevation profile if available.
        
        Args:
            route: Route data from OpenRouteService
            
        Returns:
            List of elevation points
        """
        elevation_profile = []

        # Check if elevation data is available in the route extras
        extras = route.get('extras', {})
        if 'elevation' in extras:
            elevation_data = extras['elevation']
            values = elevation_data.get('values', [])

            for point in values:
                if len(point) >= 3:
                    elevation_profile.append({
                        'distance': point[0],
                        'elevation': point[1],
                        'grade': point[2] if len(point) > 2 else None
                    })
        
        return elevation_profile
    
    def get_api_status(self) -> Dict[str, any]:
        """
        Check the status of external APIs.
        
        Returns:
            Dict with API status information
        """
        try:
            # health check request
            response = requests.get(
                f"{self.openrouteservice_base_url}/health",
                timeout=10
            )

            return {
                'openrouteservice': {
                    'status': 'available' if response.status_code == 200 else 'unavailable',
                    'response_time': response.elapsed.total_seconds() * 1000, # convert to milliseconds
                    'api_key_configured': bool(self.openrouteservice_api_key)
                }
            }
        
        except Exception as e:
            return {
                'openrouteservice': {
                    'status': 'error',
                    'error': str(e),
                    'api_key_configured': bool(self.openrouteservice_api_key)
                }
            }
