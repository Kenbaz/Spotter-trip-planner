import { Marker, Popup, Tooltip } from "react-leaflet";
import type { LatLngExpression } from "leaflet";
import { DivIcon } from "leaflet";
import type { Trip, RoutePlanStop } from "../../types";


interface MapMarkersProps {
  trip: Trip;
  routeStops?: RoutePlanStop[];
  currentLocation?: LatLngExpression | null;
  onStopClick?: (stop: RoutePlanStop) => void;
}

// Custom marker icons creator
function createCustomIcon(
  iconName: string,
  color: string,
  size: "sm" | "md" | "lg" = "md"
): DivIcon {
  const sizeClasses = {
    sm: "w-6 h-6",
    md: "w-8 h-8",
    lg: "w-10 h-10",
  };

  const iconHtml = `
    <div class="flex items-center justify-center ${
      sizeClasses[size]
    } ${color} rounded-full border-2 border-white shadow-lg">
      <svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
        ${getIconSvgPath(iconName)}
      </svg>
    </div>
  `;

  return new DivIcon({
    html: iconHtml,
    className: "custom-map-marker",
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32],
  });
}

// Helper to get SVG path from Lucide icon
function getIconSvgPath(iconName: string): string {
  const iconPaths: Record<string, string> = {
    MapPin:
      "M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z M15 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0z",
    Truck:
      "M5 18H3c-.6 0-1-.4-1-1V7c0-.6.4-1 1-1h2V5c0-.6.4-1 1-1h10c.6 0 1 .4 1 1v11c0 .6-.4 1-1 1h-2m-8 0a2 2 0 1 0 4 0m-4 0a2 2 0 1 1 4 0m2-2h4a2 2 0 1 0 4 0",
    Coffee:
      "M18 8h1a4 4 0 0 1 0 8h-1M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8zM6 1v3M10 1v3M14 1v3",
    Fuel: "M3 12a9 9 0 1 0 18 0 9 9 0 1 0-18 0 M12 7v10",
    Navigation: "M3 11l19-9-9 19-2-8-8-2z",
    Package:
      "M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z M3.29 7L12 12l8.71-5 M12 22V12",
    Clock:
      "M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z M12 6v6l4 2",
    AlertTriangle:
      "M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z M12 9v4 M12 17h.01",
  };

  return iconPaths[iconName] || iconPaths.MapPin;
}

function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;

  if (hours === 0) {
    return `${mins}m`;
  }
  if (mins === 0) {
    return `${hours}h`;
  }
  return `${hours}h ${mins}m`
}

function formatTime(dateString: string): string {
  return new Date(dateString).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}


export function MapMarkers({
  routeStops = [],
  onStopClick
}: MapMarkersProps) {

  // Route stops markers
  const routeStopMarkers = routeStops
    .map((stop, index) => {
      if (!stop.latitude || !stop.longitude) return null;

      // Determine marker icon and color based on stop type
      let iconName, color;

      switch (stop.type) {
        case "mandatory_break":
          iconName = "Coffee";
          color = "bg-yellow-500";
          break;
        case "fuel":
          iconName = "Fuel";
          color = "bg-purple-600";
          break;
        case "daily_reset":
          iconName = "Clock";
          color = "bg-orange-500";
          break;
        case "pickup":
          iconName = "Package";
          color = "bg-blue-600";
          break;
        case "delivery":
          iconName = "MapPin";
          color = "bg-red-600";
          break;
        default:
          iconName = "MapPin";
          color = "bg-gray-500";
      }

      return (
        <Marker
          key={`stop-${index}`}
          position={[stop.latitude, stop.longitude]}
          icon={createCustomIcon(iconName, color, "md")}
          eventHandlers={{
            click: () => onStopClick?.(stop),
          }}
        >
          <Popup>
            <div className="p-2 min-w-48">
              <h3 className="font-medium text-sm mb-2 capitalize">
                {stop.type.replace("_", " ")}
              </h3>
              <p className="text-xs text-gray-600 mb-2">{stop.address}</p>

              <div className="text-xs space-y-1">
                <div className="flex justify-between">
                  <span className="text-gray-500">Arrival:</span>
                  <span className="text-gray-900">
                    {formatTime(stop.arrival_time)}
                  </span>
                </div>
                {stop.departure_time && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Departure:</span>
                    <span className="text-gray-900">
                      {formatTime(stop.departure_time)}
                    </span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-gray-500">Duration:</span>
                  <span className="text-gray-900">
                    {formatDuration(stop.duration_minutes)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Distance:</span>
                  <span className="text-gray-900">
                    {stop.distance_from_origin} mi
                  </span>
                </div>
              </div>

              {stop.break_reason && (
                <div className="mt-2 pt-2 border-t border-gray-200">
                  <p className="text-xs">
                    <span className="text-gray-500">Reason:</span>{" "}
                    {stop.break_reason}
                  </p>
                </div>
              )}
            </div>
          </Popup>
          <Tooltip direction="top" offset={[0, -20]} opacity={0.9}>
            <span className="text-xs capitalize">
              {stop.type.replace("_", " ")}
            </span>
          </Tooltip>
        </Marker>
      );
    })
    .filter(Boolean);

  return (
    <>
      {routeStopMarkers}
    </>
  );
}
