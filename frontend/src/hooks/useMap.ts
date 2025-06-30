import { useState, useEffect, useCallback } from "react";
import type { LatLngExpression } from "leaflet";
import {
  getCurrentLocation,
  watchUserLocation,
  stopWatchingLocation,
  decodePolyline,
} from "../services/MapService";
import type { Trip, RoutePlanStop, GeolocationResult } from "../types";

interface MapIntegrationOptions {
  trip?: Trip;
  enableLocationTracking?: boolean;
  onLocationUpdate?: (location: GeolocationResult) => void;
  onLocationError?: (error: Error) => void;
}

interface MapIntegrationState {
  routeCoordinates: LatLngExpression[];
  routeStops: RoutePlanStop[];
  userLocation: LatLngExpression | null;
  isLocationLoading: boolean;
  locationError: string | null;
  isTrackingLocation: boolean;
}

export function useMap({
  trip,
  enableLocationTracking = false,
  onLocationUpdate,
  onLocationError,
}: MapIntegrationOptions = {}) {
  const [state, setState] = useState<MapIntegrationState>({
    routeCoordinates: [],
    routeStops: [],
    userLocation: null,
    isLocationLoading: false,
    locationError: null,
    isTrackingLocation: false,
  });

  const [watchId, setWatchId] = useState<number>(-1);

  // Process trip data into map-friendly format
  useEffect(() => {
    if (!trip) {
      setState((prev) => ({
        ...prev,
        routeCoordinates: [],
        routeStops: [],
      }));
      return;
    }

    // Generate route coordinates from trip plan
    let coordinates: LatLngExpression[] = [];
    if (trip.route?.route_geometry) {
      const geometry = trip.route.route_geometry;

      if (geometry.type === "combined_polylines") {
        // Handle encoded polylines
        if (geometry.deadhead_polyline) {
          coordinates.push(...decodePolyline(geometry.deadhead_polyline));
        }
        if (geometry.loaded_polyline) {
          coordinates.push(...decodePolyline(geometry.loaded_polyline));
        }
      } else if (geometry.coordinates) {
        // Handle coordinate arrays
        coordinates = geometry.coordinates.map(
          (coord) => [coord[1], coord[0]] as LatLngExpression
        );
      }
    }

    // Generate route stops from trip stops
    const routeStops: RoutePlanStop[] =
      trip.stops?.map((stop, index) => ({
        type: mapStopTypeToRoutePlanType(
          stop.stop_type
        ) as RoutePlanStop["type"],
        address: stop.address || "Unknown Location",
        latitude: stop.latitude || 0,
        longitude: stop.longitude || 0,
        arrival_time: stop.arrival_time || trip.departure_datetime,
        departure_time:
          stop.departure_time || stop.arrival_time || trip.departure_datetime,
        duration_minutes: stop.duration_minutes || 30,
        distance_from_origin: stop.distance_from_origin_miles || 0,
        sequence_order: stop.sequence_order || index,
        is_required_for_compliance: stop.is_required_for_compliance || false,
        break_reason: getBreakReason(stop.stop_type, stop.break_reason),
      })) || [];

    setState((prev) => ({
      ...prev,
      routeCoordinates: coordinates,
      routeStops,
    }));
  }, [trip]);

  // Get current user location
  const getCurrentUserLocation =
    useCallback(async (): Promise<GeolocationResult> => {
      setState((prev) => ({
        ...prev,
        isLocationLoading: true,
        locationError: null,
      }));

      try {
        const result = await getCurrentLocation();
        setState((prev) => ({
          ...prev,
          userLocation: result.coordinates,
          isLocationLoading: false,
          locationError: null,
        }));

        onLocationUpdate?.(result);
        return result;
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : "Failed to get location";
        setState((prev) => ({
          ...prev,
          isLocationLoading: false,
          locationError: errorMessage,
        }));

        const locationError = new Error(errorMessage);
        onLocationError?.(locationError);
        throw locationError;
      }
    }, [onLocationUpdate, onLocationError]);

  // Start watching user location
  const startLocationTracking = useCallback(() => {
    if (state.isTrackingLocation) return;

    const id = watchUserLocation(
      (result) => {
        setState((prev) => ({
          ...prev,
          userLocation: result.coordinates,
          locationError: null,
        }));
        onLocationUpdate?.(result);
      },
      (error) => {
        setState((prev) => ({
          ...prev,
          locationError: error.message,
        }));
        onLocationError?.(error);
      }
    );

    setWatchId(id);
    setState((prev) => ({ ...prev, isTrackingLocation: true }));
  }, [state.isTrackingLocation, onLocationUpdate, onLocationError]);

  // Stop watching user location
  const stopLocationTracking = useCallback(() => {
    if (watchId !== -1) {
      stopWatchingLocation(watchId);
      setWatchId(-1);
    }
    setState((prev) => ({ ...prev, isTrackingLocation: false }));
  }, [watchId]);

  // Auto-start location tracking if enabled
  useEffect(() => {
    if (enableLocationTracking && !state.isTrackingLocation) {
      startLocationTracking();
    }

    return () => {
      if (state.isTrackingLocation) {
        stopLocationTracking();
      }
    };
  }, [
    enableLocationTracking,
    state.isTrackingLocation,
    startLocationTracking,
    stopLocationTracking,
  ]);

  // Computed values
  const mapCenter = useCallback((): LatLngExpression => {
    if (state.userLocation) return state.userLocation;
    if (state.routeCoordinates.length > 0) return state.routeCoordinates[0];
    if (trip?.pickup_latitude && trip?.pickup_longitude) {
      return [trip.pickup_latitude, trip.pickup_longitude];
    }
    return [39.8283, -98.5795]; // Default to center of US
  }, [state.userLocation, state.routeCoordinates, trip]);

  const allCoordinates = useCallback((): LatLngExpression[] => {
    const allCoords: LatLngExpression[] = [...state.routeCoordinates];
    if (state.userLocation) allCoords.push(state.userLocation);
    return allCoords;
  }, [state.routeCoordinates, state.userLocation]);

  return {
    // State
    ...state,

    // Actions
    getCurrentUserLocation,
    startLocationTracking,
    stopLocationTracking,

    // Computed values
    mapCenter: mapCenter(),
    allCoordinates: allCoordinates(),

    // Helper flags
    hasRoute: state.routeCoordinates.length > 0,
    hasStops: state.routeStops.length > 0,
    hasUserLocation: state.userLocation !== null,
  };
}

// Helper function to map stop types
function mapStopTypeToRoutePlanType(stopType: string): string {
  const typeMap: Record<string, string> = {
    break: "required_break",
    rest: "rest_break",
    fuel: "fuel_stop",
    sleeper: "sleeper_berth",
    pickup: "pickup",
    delivery: "delivery",
    other: "other",
  };
  return typeMap[stopType] || stopType;
}

// Helper function to get break reason
function getBreakReason(stopType: string, notes?: string): string | undefined {
  if (stopType.includes("break") || stopType.includes("rest")) {
    return notes || "Required compliance break";
  }
  return undefined;
}
