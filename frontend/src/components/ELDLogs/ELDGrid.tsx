import type { ELDLogEntry } from "../../types";

interface ELDGridProps {
  logEntries: ELDLogEntry[];
  onEditEntry?: (entryId: number, field: string, currentValue: string) => void;
  className?: string;
}

export function ELDGrid({
  logEntries,
  onEditEntry,
  className = "",
}: ELDGridProps) {
  // Create 24-hour grid (midnight to midnight)
  const hours = Array.from({ length: 24 }, (_, i) => i);
  const quarterHours = Array.from({ length: 4 }, (_, i) => i * 15); // 0, 15, 30, 45 minutes

  // Convert log entries to grid data
  const gridData = createGridData(logEntries);

  const getDutyStatusColor = (status: string) => {
    switch (status) {
      case "off_duty":
        return "#000000";
      case "sleeper_berth":
        return "#808080";
      case "driving":
        return "#FF0000";
      case "on_duty_not_driving":
        return "#0000FF";
      default:
        return "#000000";
    }
  };

  const getDutyStatusSymbol = (status: string) => {
    switch (status) {
      case "off_duty":
        return "○";
      case "sleeper_berth":
        return "◐";
      case "driving":
        return "●";
      case "on_duty_not_driving":
        return "◆";
      default:
        return "○";
    }
  };

  return (
    <div className={`eld-grid ${className}`}>
      {/* Legend */}
      <div className="mb-4 p-3 bg-gray-50 rounded border">
        <h4 className="font-semibold text-gray-900 text-sm mb-2">
          Duty Status Legend:
        </h4>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 text-sm">
          <div className="flex items-center space-x-2">
            <span style={{ color: "#000000" }} className="text-lg">
              ○
            </span>
            <span className="text-gray-900">1 - Off Duty</span>
          </div>
          <div className="flex items-center space-x-2">
            <span style={{ color: "#808080" }} className="text-lg">
              ◐
            </span>
            <span>2 - Sleeper Berth</span>
          </div>
          <div className="flex items-center space-x-2">
            <span style={{ color: "#FF0000" }} className="text-lg">
              ●
            </span>
            <span>3 - Driving</span>
          </div>
          <div className="flex items-center space-x-2">
            <span style={{ color: "#0000FF" }} className="text-lg">
              ◆
            </span>
            <span>4 - On Duty (Not Driving)</span>
          </div>
        </div>
      </div>

      {/* Grid Header */}
      <div className="grid grid-cols-25 gap-0 border-2 border-gray-900">
        {/* Time labels column */}
        <div className="bg-gray-100 border-r border-gray-900 p-1 text-xs font-semibold text-center text-gray-900">
          HOUR
        </div>

        {/* Quarter hour columns */}
        {hours.map((hour) =>
          quarterHours.map((quarter) => (
            <div
              key={`header-${hour}-${quarter}`}
              className="bg-gray-100 border-r border-gray-300 p-1 text-xs text-center font-medium"
            >
              {hour.toString().padStart(2, "0")}:
              {quarter.toString().padStart(2, "0")}
            </div>
          ))
        )}
      </div>

      {/* Grid Rows - One for each duty status */}
      {["off_duty", "sleeper_berth", "driving", "on_duty_not_driving"].map(
        (dutyStatus) => (
          <div
            key={dutyStatus}
            className="grid grid-cols-25 gap-0 border-l-2 border-r-2 border-gray-900"
          >
            {/* Row label */}
            <div
              className={`border-r border-gray-900 p-2 text-xs font-semibold text-center ${
                dutyStatus === "driving"
                  ? "bg-red-50"
                  : dutyStatus === "on_duty_not_driving"
                  ? "bg-blue-50"
                  : dutyStatus === "sleeper_berth"
                  ? "bg-gray-50"
                  : "bg-white"
              }`}
            >
              <div className="transform -rotate-90 whitespace-nowrap">
                {dutyStatus.replace("_", " ").toUpperCase()}
              </div>
            </div>

            {/* Time cells */}
            {hours.map((hour) =>
              quarterHours.map((quarter) => {
                const timeKey = `${hour.toString().padStart(2, "0")}:${quarter
                  .toString()
                  .padStart(2, "0")}`;
                const cellData = gridData[timeKey];
                const isActive = cellData?.duty_status === dutyStatus;

                return (
                  <div
                    key={`${dutyStatus}-${hour}-${quarter}`}
                    className={`border-r border-gray-300 h-8 flex items-center justify-center cursor-pointer hover:bg-gray-100 ${
                      isActive ? "bg-yellow-100" : ""
                    }`}
                    title={
                      isActive
                        ? `${cellData?.duty_status_label} - ${
                            cellData?.location || "Unknown location"
                          }`
                        : ""
                    }
                    onClick={() => {
                      if (isActive && cellData?.entry_id && onEditEntry) {
                        onEditEntry(cellData.entry_id, "start_time", timeKey);
                      }
                    }}
                  >
                    {isActive && (
                      <span
                        style={{ color: getDutyStatusColor(dutyStatus) }}
                        className="text-lg font-bold"
                      >
                        {getDutyStatusSymbol(dutyStatus)}
                      </span>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )
      )}

      {/* Bottom border */}
      <div className="border-b-2 border-gray-900"></div>

      {/* Grid footer with midnight markers */}
      <div className="mt-2 text-xs text-gray-600 text-center">
        <div className="flex justify-between">
          <span>MIDNIGHT</span>
          <span>NOON</span>
          <span>MIDNIGHT</span>
        </div>
      </div>
    </div>
  );
}

// Helper function to convert log entries to grid data
function createGridData(logEntries: ELDLogEntry[]) {
  const gridData: Record<
    string,
    {
      duty_status: string;
      duty_status_label: string;
      location: string;
      entry_id: number;
    }
  > = {};

  logEntries.forEach((entry) => {
    // Convert start and end times to minutes
    const startMinutes = timeToMinutes(entry.start_time);
    const endMinutes = timeToMinutes(entry.end_time);

    // Handle entries that cross midnight
    let currentMinutes = startMinutes;
    const endOfDay = endMinutes < startMinutes ? 24 * 60 : endMinutes;

    while (currentMinutes < endOfDay) {
      const hour = Math.floor(currentMinutes / 60) % 24;
      const minute = currentMinutes % 60;
      const quarterMinute = Math.floor(minute / 15) * 15;

      const timeKey = `${hour.toString().padStart(2, "0")}:${quarterMinute
        .toString()
        .padStart(2, "0")}`;

      gridData[timeKey] = {
        duty_status: entry.duty_status,
        duty_status_label: entry.duty_status_label,
        location: entry.start_location || "",
        entry_id: entry.id,
      };

      currentMinutes += 15; // Move to next quarter hour
    }
  });

  return gridData;
}

function timeToMinutes(timeString: string): number {
  const [hours, minutes] = timeString.split(":").map(Number);
  return hours * 60 + minutes;
}
