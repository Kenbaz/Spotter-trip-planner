/* eslint-disable @typescript-eslint/no-explicit-any */

import { useEffect, useRef, useMemo } from "react";
import { MapContainer, TileLayer, Polyline, useMap } from "react-leaflet";
import type { LatLngExpression, Map as LeafletMap } from "leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { MapMarkers } from "./MapMarkers";
import type { Trip, RoutePlanStop } from "../../types";
import { MapControls } from "./MapControls";

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
});

interface RouteMapProps {
  trip: Trip;
  routeStops?: RoutePlanStop[];
  routeCoordinates?: LatLngExpression[];
  currentLocation?: LatLngExpression;
  showTraffic?: boolean;
  onStopClick?: (stop: RoutePlanStop) => void;
  onMapClick?: (coordinates: LatLngExpression) => void;
  className?: string;
}

function MapEventHandler({
  onMapClick,
}: {
  onMapClick?: (coordinates: LatLngExpression) => void;
}) {
  const map = useMap();

  useEffect(() => {
    if (!onMapClick) return;

    const handleClick = (e: L.LeafletMouseEvent) => {
      const { lat, lng } = e.latlng;
      onMapClick([lat, lng]);
    };

    map.on("click", handleClick);
    return () => {
      map.off("click", handleClick);
    };
  }, [map, onMapClick]);

  return null;
}

function FitBoundsHandler({
  coordinates,
}: {
  coordinates: LatLngExpression[];
}) {
  const map = useMap();

  useEffect(() => {
    if (coordinates.length > 0) {
      const bounds = L.latLngBounds(coordinates);
      map.fitBounds(bounds, { padding: [20, 20] });
    }
  }, [map, coordinates]);

  return null;
}

export function RouteMap({
  trip,
  routeStops = [],
  routeCoordinates = [],
  currentLocation,
  showTraffic = false,
  onStopClick,
  onMapClick,
  className = "",
}: RouteMapProps) {
  const mapRef = useRef<LeafletMap | null>(null);

  // Calculate map center from available data
  const mapCenter: LatLngExpression = useMemo(() => {
    if (currentLocation) return currentLocation;
    if (routeCoordinates.length > 0) return routeCoordinates[0];

    const pickupLat = trip.pickup_latitude;
    const pickupLng = trip.pickup_longitude;

    if (pickupLat && pickupLng) {
      return [pickupLat, pickupLng];
    }

    return [39.8283, -98.5795]; // Default center of US
  }, [currentLocation, routeCoordinates, trip]);

  // Combine all coordinates for bounds calculation
  const allCoordinates = useMemo(() => {
    const coords: LatLngExpression[] = [...routeCoordinates];
    if (currentLocation) coords.push(currentLocation);
    return coords;
  }, [routeCoordinates, currentLocation]);

  // Map control handlers
  const handleCenterOnRoute = () => {
    if (mapRef.current && allCoordinates.length > 0) {
      const bounds = L.latLngBounds(allCoordinates);
      mapRef.current.fitBounds(bounds, { padding: [20, 20] });
    }
  };

  const handleToggleTraffic = () => {
    console.log("Traffic toggle:", !showTraffic);
  };

  const handleLocateUser = async () => {
    try {
      if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(
          (position) => {
            const { latitude, longitude } = position.coords;
            if (mapRef.current) {
              mapRef.current.setView([latitude, longitude], 15);
            }
          },
          (error) => {
            console.error("Location error:", error);
          }
        );
      }
    } catch (error) {
      console.error("Geolocation not supported or error:", error);
    }
  };

  return (
    <div className={`relative w-full h-full ${className}`}>
      <MapContainer
        center={mapCenter}
        zoom={10}
        className="w-full h-full rounded-lg"
        ref={mapRef}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />

        {/* Route polyline */}
        {routeCoordinates.length > 0 && (
          <Polyline
            positions={routeCoordinates}
            color="#2563eb"
            weight={4}
            opacity={0.8}
          />
        )}

        {/* Map markers */}
        <MapMarkers
          trip={trip}
          routeStops={routeStops}
          currentLocation={currentLocation}
          onStopClick={onStopClick}
        />

        {/* Event handlers */}
        <MapEventHandler onMapClick={onMapClick} />
        <FitBoundsHandler coordinates={allCoordinates} />
      </MapContainer>

      {/* Map controls */}
      <MapControls
        onCenterOnRoute={handleCenterOnRoute}
        onToggleTraffic={handleToggleTraffic}
        onLocateUser={handleLocateUser}
        showTraffic={showTraffic}
        isLocating={false}
      />

      {/* Map legend */}
      <div className="absolute bottom-4 left-4 z-[40]">
        <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-3">
          <h4 className="text-sm font-medium text-gray-900 mb-2">Map Legend</h4>
          <div className="space-y-1 text-xs">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-gray-700 rounded-full"></div>
              <span className="text-gray-900">Trip start</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
              <span className="text-gray-900">Pickup</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-red-500 rounded-full"></div>
              <span className="text-gray-900">Delivery</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
              <span className="text-gray-900">Break</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
              <span className="text-gray-900">Fuel Stop</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
