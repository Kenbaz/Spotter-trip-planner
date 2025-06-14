import type { GridPoint } from "../../types";


interface ELDGridProps { 
    gridData: GridPoint[];
    compact?: boolean;
}


export function ELDGrid({ gridData, compact = false }: ELDGridProps) { 
    // Create grid matrix
    const grid = Array(11).fill(null).map(() => Array(8).fill(0));

    // Fill grid will duty status data
    gridData.forEach(point => {
        if (point.grid_row >= 0 && point.grid_row < 11 && point.grid_column >= 0 && point.grid_column < 8) {
            grid[point.grid_row][point.grid_column] = point.duty_status_symbol
        }
    });


    const getDutyStatusStyle = (symbol: number): string => {
      switch (symbol) {
        case 1: // Off Duty
          return "bg-white border-gray-400";
        case 2: // Sleeper Berth
          return "bg-gray-200 border-gray-500";
        case 3: // Driving
          return "bg-red-300 border-red-500";
        case 4: // On Duty (Not Driving)
          return "bg-blue-300 border-blue-500";
        default:
          return "bg-gray-50 border-gray-300";
      }
    };

    const getDutyStatusSymbol = (symbol: number): string => {
      switch (symbol) {
        case 1:
          return "○";
        case 2:
          return "◐";
        case 3:
          return "●";
        case 4:
          return "◆";
        default:
          return "";
      }
    };

    const cellSize = compact ? 'w-8 h-6' : 'w-12 h-8';
    const textSize = compact ? 'text-xs' : 'text-sm';
    const headerTextSize = compact ? 'text-xs' : 'text-sm';

    
    return (
      <div className="space-y-4">
        {/* Legend */}
        <div className="bg-gray-50 p-3 rounded-lg">
          <h5 className="text-sm font-medium text-gray-900 mb-2">Legend</h5>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div className="flex items-center space-x-2">
              <div className="w-5 h-5 bg-white border-2 border-gray-400 rounded flex items-center justify-center font-bold">
                ○
              </div>
              <span className="text-gray-700">1 - Off Duty</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-5 h-5 bg-gray-200 border-2 border-gray-500 rounded flex items-center justify-center font-bold">
                ◐
              </div>
              <span className="text-gray-700">2 - Sleeper Berth</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-5 h-5 bg-red-300 border-2 border-red-500 rounded flex items-center justify-center font-bold text-red-800">
                ●
              </div>
              <span className="text-gray-700">3 - Driving</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-5 h-5 bg-blue-300 border-2 border-blue-500 rounded flex items-center justify-center font-bold text-blue-800">
                ◆
              </div>
              <span className="text-gray-700">4 - On Duty (Not Driving)</span>
            </div>
          </div>
        </div>

        {/* ELD Grid */}
        <div className="bg-white border-2 border-gray-800 rounded-lg overflow-hidden">
          {/* Title */}
          <div className="bg-gray-100 px-4 py-2 border-b-2 border-gray-800">
            <h4 className="font-bold text-center text-gray-900">
              HOURS OF SERVICE - DAILY LOG
            </h4>
          </div>

          {/* Grid Container */}
          <div className="p-2">
            <div className="flex">
              <div className="w-20 flex-shrink-0"></div>
              <div className="flex-1 grid grid-cols-8 border-b border-gray-400">
                {Array.from({ length: 8 }, (_, i) => (
                  <div
                    key={i}
                    className={`${headerTextSize} text-center py-1 border-r border-gray-300 last:border-r-0 font-medium text-gray-700`}
                  >
                    :{(i * 15).toString().padStart(2, "0")}
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-0">
              {grid.map((row, rowIndex) => (
                <div key={rowIndex} className="flex">
                  {/* Hour Label */}
                  <div className="w-20 flex-shrink-0 pr-2 py-1 border-r border-gray-400">
                    <div
                      className={`${headerTextSize} text-right font-medium text-gray-700 leading-tight`}
                    >
                      <div>{`${(rowIndex * 2)
                        .toString()
                        .padStart(2, "0")}:00`}</div>
                      <div className="text-xs text-gray-500">to</div>
                      <div>{`${(rowIndex * 2 + 2)
                        .toString()
                        .padStart(2, "0")}:00`}</div>
                    </div>
                  </div>

                  {/* Grid Cells */}
                  <div className="flex-1 grid grid-cols-8">
                    {row.map((cell, cellIndex) => (
                      <div
                        key={cellIndex}
                        className={`${cellSize} ${getDutyStatusStyle(
                          cell
                        )} border-r border-b border-gray-400 last:border-r-0 flex items-center justify-center ${textSize} font-bold transition-colors`}
                        title={`${(rowIndex * 2)
                          .toString()
                          .padStart(2, "0")}:${(cellIndex * 15)
                          .toString()
                          .padStart(2, "0")} - Status: ${
                          cell === 1
                            ? "Off Duty"
                            : cell === 2
                            ? "Sleeper Berth"
                            : cell === 3
                            ? "Driving"
                            : cell === 4
                            ? "On Duty (Not Driving)"
                            : "No Status"
                        }`}
                      >
                        <span
                          className={
                            cell === 3
                              ? "text-red-800"
                              : cell === 4
                              ? "text-blue-800"
                              : cell === 2
                              ? "text-gray-700"
                              : "text-gray-600"
                          }
                        >
                          {getDutyStatusSymbol(cell)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="border-t-2 border-gray-800 mt-1"></div>
          </div>

          {/* Footer */}
          <div className="bg-gray-50 px-4 py-2 border-t border-gray-300">
            <div className="flex justify-between items-center text-xs text-gray-600">
              <span>24-Hour Period: 00:00 to 24:00</span>
              <span>Each cell = 15 minutes</span>
            </div>
          </div>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <h5 className="text-sm font-medium text-blue-900 mb-1">
            How to Read This Log
          </h5>
          <ul className="text-xs text-blue-800 space-y-1">
            <li>
              • Each row represents 2 hours (e.g., 00:00-02:00, 02:00-04:00)
            </li>
            <li>
              • Each column represents 15-minute intervals within that 2-hour
              period
            </li>
            <li>
              • Symbols show your duty status during each 15-minute period
            </li>
            <li>• Red (●) = Driving time - limited to 11 hours per day</li>
            <li>
              • Blue (◆) = On-duty time - combined with driving, limited to 14
              hours per day
            </li>
          </ul>
        </div>
      </div>
    );
}