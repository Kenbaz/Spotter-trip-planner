import "leaflet/dist/leaflet.css";
import { Button } from "../UI/Button";
import { MapPin, Navigation, Layers } from "lucide-react";
import type React from "react";

interface MapControlsProps {
  onCenterOnRoute: () => void;
  onToggleTraffic: () => void;
  onLocateUser: () => void;
  showTraffic: boolean;
  isLocating: boolean;
}

export const MapControls: React.FC<MapControlsProps> = ({
  onCenterOnRoute,
  onToggleTraffic,
  onLocateUser,
  showTraffic,
  isLocating,
}) => {
  return (
    <div className="absolute top-4 right-4 z-[1000] flex flex-col space-y-2">
      <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-2 flex flex-col space-y-1">
        <Button
          variant="ghost"
          size="sm"
          onClick={onCenterOnRoute}
          className="w-8 h-8 p-0"
          title="Center on Route"
        >
          <MapPin className="w-4 h-4" />
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={onLocateUser}
          className="w-8 h-8 p-0"
          disabled={isLocating}
          title="Find My Location"
        >
          <Navigation
            className={`w-4 h-4 ${isLocating ? "animate-spin" : ""}`}
          />
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={onToggleTraffic}
          className={`w-8 h-8 p-0 ${
            showTraffic ? "bg-blue-100 text-blue-600" : ""
          }`}
          title="Toggle Traffic Layer"
        >
          <Layers className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
};
