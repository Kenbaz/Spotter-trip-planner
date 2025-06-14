import { Card, CardContent, CardHeader, CardTitle } from "../UI/Card";
import { Button } from "../UI/Button";
import { LoadingSpinner } from "../UI/LoadingSpinner";
import { Download, FileText, AlertCircle, CheckCircle } from "lucide-react";
import { ELDGrid } from "./ELDGrid";
import type { DailyELDLog, ELDLogResponse } from "../../types";


interface ELDLogViewerProps { 
    eldData: ELDLogResponse | null;
    isLoading: boolean;
    error: string | null;
    onDownload: () => void;
    onRefresh: () => void;
}


export function ELDLogViewer({
    eldData,
    isLoading = false,
    error = null,
    onDownload,
    onRefresh
}: ELDLogViewerProps) { 
    if (isLoading) {
      return (
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner size="large" text="Generating ELD logs..." />
            </div>
          </CardContent>
        </Card>
      );
    }

    if (error) {
      return (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-6">
            <div className="flex items-center space-x-3">
              <AlertCircle className="w-8 h-8 text-red-600" />
              <div>
                <h3 className="text-lg font-medium text-red-800">
                  Failed to Generate ELD Logs
                </h3>
                <p className="text-red-700 mt-1">{error}</p>
                {onRefresh && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={onRefresh}
                    className="mt-3"
                  >
                    Try Again
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      );
    }

    if (!eldData || !eldData.success) {
      return (
        <Card>
          <CardContent className="p-6">
            <div className="text-center py-8">
              <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">No ELD logs available</p>
              <p className="text-sm text-gray-500">
                Calculate a route first to generate ELD logs
              </p>
            </div>
          </CardContent>
        </Card>
      );
    }


    return (
      <div className="space-y-6">
        {/* Header */}
        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <div>
                <CardTitle className="flex items-center">
                  <FileText className="w-5 h-5 mr-2" />
                  ELD Logs - Trip {eldData.trip_id}
                </CardTitle>
                <p className="text-sm text-gray-600 mt-1">
                  {eldData.total_days} day(s) • Generated:{" "}
                  {new Date(eldData.generated_at).toLocaleDateString()}
                </p>
              </div>
              {onDownload && (
                <Button
                  leftIcon={<Download className="w-4 h-4" />}
                  onClick={onDownload}
                >
                  Download PDF
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between text-sm">
              <div>
                <span className="text-gray-600">Date Range: </span>
                <span className="font-medium">
                  {new Date(eldData.log_date_range.start).toLocaleDateString()}{" "}
                  - {new Date(eldData.log_date_range.end).toLocaleDateString()}
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle className="w-4 h-4 text-green-500" />
                <span className="text-green-600">HOS Compliant</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Daily Logs */}
        {eldData.daily_logs.map((dailyLog, index) => (
          <DailyLogSheet
            key={dailyLog.log_date}
            dailyLog={dailyLog}
            dayNumber={index + 1}
          />
        ))}

        {/* Summary */}
        <Card>
          <CardHeader>
            <CardTitle>Trip Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-gray-600">Total Distance</p>
                <p className="font-medium">
                  {eldData.summary.total_distance_miles} miles
                </p>
              </div>
              <div>
                <p className="text-gray-600">Total Driving Time</p>
                <p className="font-medium">
                  {eldData.summary.total_driving_hours} hours
                </p>
              </div>
              <div>
                <p className="text-gray-600">Total Trip Time</p>
                <p className="font-medium">
                  {eldData.summary.trip_duration_hours.toFixed(1)} hours
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
};


interface DailyLogSheetProps {
  dailyLog: DailyELDLog;
  dayNumber: number;
}

function DailyLogSheet({ dailyLog, dayNumber }: DailyLogSheetProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">
          Day {dayNumber} -{" "}
          {new Date(dailyLog.log_date).toLocaleDateString("en-US", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
          })}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Driver Info */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm border-b border-gray-200 pb-4">
            <div>
              <p className="text-gray-600">Driver</p>
              <p className="font-medium">{dailyLog.driver_name}</p>
            </div>
            <div>
              <p className="text-gray-600">Carrier</p>
              <p className="font-medium">{dailyLog.carrier_name}</p>
            </div>
            <div>
              <p className="text-gray-600">Vehicle</p>
              <p className="font-medium">{dailyLog.vehicle_id}</p>
            </div>
          </div>

          {/* ELD Grid */}
          <ELDGrid gridData={dailyLog.grid_data} />

          {/* Daily Totals */}
          <DailyTotals totals={dailyLog.daily_totals} />

          {/* Log Entries */}
          <LogEntries entries={dailyLog.log_entries} />
        </div>
      </CardContent>
    </Card>
  );
};


interface DailyTotalsProps {
  totals: {
    off_duty: number;
    sleeper_berth: number;
    driving: number;
    on_duty_not_driving: number;
    total_on_duty: number;
    total_driving: number;
  };
}

function DailyTotals({ totals }: DailyTotalsProps) {
  return (
    <div className="space-y-3">
      <h4 className="font-medium text-gray-900">Daily Totals</h4>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">Driving:</span>
          <span className="font-medium">{totals.driving.toFixed(1)}h</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">On Duty:</span>
          <span className="font-medium">
            {totals.total_on_duty.toFixed(1)}h
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Off Duty:</span>
          <span className="font-medium">{totals.off_duty.toFixed(1)}h</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Sleeper Berth:</span>
          <span className="font-medium">
            {totals.sleeper_berth.toFixed(1)}h
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">On Duty (Not Driving):</span>
          <span className="font-medium">
            {totals.on_duty_not_driving.toFixed(1)}h
          </span>
        </div>
      </div>
    </div>
  );
}


interface LogEntriesProps {
  entries: Array<{
    start_time: string;
    end_time: string;
    duty_status: string;
    duration_minutes: number;
    location: string;
    remarks: string;
  }>;
}

function LogEntries({ entries }: LogEntriesProps) {
  return (
    <div className="space-y-3">
      <h4 className="font-medium text-gray-900">Log Entries</h4>
      <div className="overflow-x-auto">
        <table className="min-w-full text-xs">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left text-gray-600">Time</th>
              <th className="px-3 py-2 text-left text-gray-600">Status</th>
              <th className="px-3 py-2 text-left text-gray-600">Duration</th>
              <th className="px-3 py-2 text-left text-gray-600">Location</th>
              <th className="px-3 py-2 text-left text-gray-600">Remarks</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {entries.map((entry, index) => (
              <tr key={index} className="hover:bg-gray-50">
                <td className="px-3 py-2 whitespace-nowrap">
                  {entry.start_time} - {entry.end_time}
                </td>
                <td className="px-3 py-2">
                  <span
                    className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                      entry.duty_status === "driving"
                        ? "bg-red-100 text-red-800"
                        : entry.duty_status === "on_duty_not_driving"
                        ? "bg-blue-100 text-blue-800"
                        : entry.duty_status === "off_duty"
                        ? "bg-gray-100 text-gray-800"
                        : "bg-gray-100 text-gray-800"
                    }`}
                  >
                    {entry.duty_status
                      .replace(/_/g, " ")
                      .replace(/\b\w/g, (l) => l.toUpperCase())}
                  </span>
                </td>
                <td className="px-3 py-2 whitespace-nowrap">
                  {Math.round((entry.duration_minutes / 60) * 10) / 10}h
                </td>
                <td className="px-3 py-2">{entry.location}</td>
                <td className="px-3 py-2">{entry.remarks}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}