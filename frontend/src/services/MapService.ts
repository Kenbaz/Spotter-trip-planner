/* eslint-disable @typescript-eslint/no-explicit-any */

import type { LatLngExpression } from "leaflet";
import type {
  GeolocationOptions,
  GeolocationResult,
  RouteCoordinate,
} from "../types";

// Get current user location using browser geolocation API
export async function getCurrentLocation(
  options: GeolocationOptions = {}
): Promise<GeolocationResult> {
  const defaultOptions: GeolocationOptions = {
    enableHighAccuracy: true,
    timeout: 10000,
    maximumAge: 60000,
    ...options,
  };

  if (!navigator.geolocation) {
    throw new Error("Geolocation is not supported by this browser.");
  }

  return new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude, accuracy } = position.coords;
        resolve({
          coordinates: [latitude, longitude],
          accuracy,
          timestamp: position.timestamp,
        });
      },
      (error) => {
        let errorMessage = "Unknown geolocation error";

        switch (error.code) {
          case error.PERMISSION_DENIED:
            errorMessage = "Location access denied by user";
            break;
          case error.POSITION_UNAVAILABLE:
            errorMessage = "Location information unavailable";
            break;
          case error.TIMEOUT:
            errorMessage = "Location request timed out";
            break;
        }

        reject(new Error(errorMessage));
      },
      defaultOptions
    );
  });
}

// Watch user location for real-time tracking
export function watchUserLocation(
  onLocationUpdate: (result: GeolocationResult) => void,
  onError: (error: Error) => void,
  options: GeolocationOptions = {}
): number {
  const defaultOptions: GeolocationOptions = {
    enableHighAccuracy: true,
    timeout: 30000,
    maximumAge: 5000,
    ...options,
  };

  if (!navigator.geolocation) {
    onError(new Error("Geolocation is not supported by this browser"));
    return -1;
  }

  return navigator.geolocation.watchPosition(
    (position) => {
      const { latitude, longitude, accuracy } = position.coords;
      onLocationUpdate({
        coordinates: [latitude, longitude],
        accuracy,
        timestamp: position.timestamp,
      });
    },
    (error) => {
      let errorMessage = "Unknown geolocation error";

      switch (error.code) {
        case error.PERMISSION_DENIED:
          errorMessage = "Location access denied by user";
          break;
        case error.POSITION_UNAVAILABLE:
          errorMessage = "Location information unavailable";
          break;
        case error.TIMEOUT:
          errorMessage = "Location request timed out";
          break;
      }

      onError(new Error(errorMessage));
    },
    defaultOptions
  );
}

// Stop watching user location
export function stopWatchingLocation(watchId: number): void {
  if (navigator.geolocation && watchId !== -1) {
    navigator.geolocation.clearWatch(watchId);
  }
}

// Calculate distance between two coordinates using Haversine formula
export function calculateDistance(
  coord1: LatLngExpression,
  coord2: LatLngExpression
): number {
  const lat1 = Array.isArray(coord1) ? coord1[0] : coord1.lat;
  const lng1 = Array.isArray(coord1) ? coord1[1] : coord1.lng;
  const lat2 = Array.isArray(coord2) ? coord2[0] : coord2.lat;
  const lng2 = Array.isArray(coord2) ? coord2[1] : coord2.lng;

  const R = 3959; // Earth radius in meters
  const dLat = toRadians(lat2 - lat1);
  const dLng = toRadians(lng2 - lng1);

  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRadians(lat1)) *
      Math.cos(toRadians(lat2)) *
      Math.sin(dLng / 2) *
      Math.sin(dLng / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c; // Distance in miles
}

// Convert degree to radians
function toRadians(degrees: number): number {
  return degrees * (Math.PI / 180);
}

// Get map bounds that include all coordinates
export function getMapBounds(coordinates: LatLngExpression[]): {
  north: number;
  south: number;
  east: number;
  west: number;
} | null {
  if (coordinates.length === 0) return null;

  let north = -90;
  let south = 90;
  let east = -180;
  let west = 180;

  coordinates.forEach((coord) => {
    const lat = Array.isArray(coord) ? coord[0] : coord.lat;
    const lng = Array.isArray(coord) ? coord[1] : coord.lng;

    north = Math.max(north, lat);
    south = Math.min(south, lat);
    east = Math.max(east, lng);
    west = Math.min(west, lng);
  });

  return { north, south, east, west };
}

export function getCenterOfCoordinates(
  coordinates: LatLngExpression[]
): LatLngExpression | null {
  if (coordinates.length === 0) return null;

  let totalLat = 0;
  let totalLng = 0;

  coordinates.forEach((coord) => {
    const lat = Array.isArray(coord) ? coord[0] : coord.lat;
    const lng = Array.isArray(coord) ? coord[1] : coord.lng;
    totalLat += lat;
    totalLng += lng;
  });

  return [totalLat / coordinates.length, totalLng / coordinates.length];
}

/**
 * Decode polyline string to coordinates array
 * Used for route geometries from routing services
 */
export function decodePolyline(polyline: string): LatLngExpression[] {
  const coordinates: LatLngExpression[] = [];
  let index = 0;
  let lat = 0;
  let lng = 0;

  while (index < polyline.length) {
    let shift = 0;
    let result = 0;
    let byte: number;

    do {
      byte = polyline.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);

    const deltaLat = (result & 1) !== 0 ? ~(result >> 1) : result >> 1;
    lat += deltaLat;

    shift = 0;
    result = 0;

    do {
      byte = polyline.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);

    const deltaLng = (result & 1) !== 0 ? ~(result >> 1) : result >> 1;
    lng += deltaLng;

    coordinates.push([lat / 1e5, lng / 1e5]);
  }

  return coordinates;
}

export function formatCoordinates(
  coordinates: LatLngExpression,
  precision: number = 4
): string {
  const lat = Array.isArray(coordinates) ? coordinates[0] : coordinates.lat;
  const lng = Array.isArray(coordinates) ? coordinates[1] : coordinates.lng;

  return `${lat.toFixed(precision)}, ${lng.toFixed(precision)}`;
}

// Check if coordinates are within US bounds (approximate)
export function isWithinUSBounds(coordinates: LatLngExpression): boolean {
  const lat = Array.isArray(coordinates) ? coordinates[0] : coordinates.lat;
  const lng = Array.isArray(coordinates) ? coordinates[1] : coordinates.lng;

  // Approximate US bounds
  return (
    lat >= 24.396308 && lat <= 49.384358 && lng >= -125.0 && lng <= -66.93457
  );
}

/**
 * Generate route coordinates from route data
 * This would typically parse encoded polyline or coordinate arrays from routing service
 */
export function generateRouteCoordinates(routeData: any): LatLngExpression[] {
  if (!routeData) return [];

  // Handle different route data formats
  if (routeData.geometry && typeof routeData.geometry === "string") {
    // Encoded polyline
    return decodePolyline(routeData.geometry);
  }

  if (routeData.coordinates && Array.isArray(routeData.coordinates)) {
    // Array of coordinate pairs
    return routeData.coordinates.map(
      (coord: number[]) => [coord[1], coord[0]] as LatLngExpression
    );
  }

  if (
    routeData.route_coordinates &&
    Array.isArray(routeData.route_coordinates)
  ) {
    // Our custom route coordinate format
    return routeData.route_coordinates.map(
      (coord: RouteCoordinate) =>
        [coord.latitude, coord.longitude] as LatLngExpression
    );
  }

  return [];
}

// Get optimal zoom level for given bounds
export function getOptimalZoom(
  bounds: { north: number; south: number; east: number; west: number },
//   mapDimensions: { width: number; height: number }
): number {
  const latDiff = bounds.north - bounds.south;
  const lngDiff = bounds.east - bounds.west;

  // Simple zoom calculation based on coordinate differences
  const maxDiff = Math.max(latDiff, lngDiff);

  if (maxDiff > 10) return 4;
  if (maxDiff > 5) return 5;
  if (maxDiff > 2) return 6;
  if (maxDiff > 1) return 7;
  if (maxDiff > 0.5) return 8;
  if (maxDiff > 0.25) return 9;
  if (maxDiff > 0.125) return 10;
  if (maxDiff > 0.05) return 11;
  return 12;
}

// Check if user has granted location permission
export async function checkLocationPermission(): Promise<
  "granted" | "denied" | "prompt" | "unsupported"
> {
  if (!navigator.permissions) {
    return "unsupported";
  }

  try {
    const result = await navigator.permissions.query({ name: "geolocation" });
    return result.state;
  } catch (error) {
    console.error("Error checking geolocation permission:", error);
    return "unsupported";
  }
}
