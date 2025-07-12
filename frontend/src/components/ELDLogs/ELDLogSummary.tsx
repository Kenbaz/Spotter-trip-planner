import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../UI/Card";
import { Button } from "../UI/Button";
import {
  AlertTriangle,
  CheckCircle,
  FileText,
  Download,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { ELDComplianceIndicator } from "./ELDComplianceIndicator";
import type { ELDDailyLog } from "../../types";

interface ELDLogSummaryProps {
  dailyLogs: ELDDailyLog[];
  tripId: string;
  currentLogIndex?: number;
  onLogSelect?: (index: number) => void;
  onExportAll?: () => void;
}

// Helper function to safely convert to number with fallback
const safeNumberValue = (value: unknown, fallback: number = 0): number => {
  if (typeof value === "number" && !isNaN(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = parseFloat(value);
    return isNaN(parsed) ? fallback : parsed;
  }
  return fallback;
};

export function ELDLogSummary({
  dailyLogs,
  tripId,
  currentLogIndex = 0,
  onLogSelect,
  onExportAll,
}: ELDLogSummaryProps) {
  const [showAllLogs, setShowAllLogs] = useState(false);

  // Calculate summary statistics with safe numeric conversions
  const totalDays = dailyLogs.length;
  const compliantDays = dailyLogs.filter((log) => log.is_compliant).length;
  const certifiedDays = dailyLogs.filter((log) => log.is_certified).length;
  const totalViolations = dailyLogs.reduce((sum, log) => {
    return sum + safeNumberValue(log.violation_count, 0);
  }, 0);

  const totalDrivingHours = dailyLogs.reduce((sum, log) => {
    return sum + safeNumberValue(log.total_driving_hours, 0);
  }, 0);

  const totalOnDutyHours = dailyLogs.reduce((sum, log) => {
    return sum + safeNumberValue(log.total_on_duty_hours, 0);
  }, 0);

  const totalDistance = dailyLogs.reduce((sum, log) => {
    return sum + safeNumberValue(log.total_distance_miles, 0);
  }, 0);

  const avgComplianceScore =
    totalDays > 0
      ? dailyLogs.reduce((sum, log) => {
          return sum + safeNumberValue(log.compliance_score, 0);
        }, 0) / totalDays
      : 0;

  const handlePrevious = () => {
    if (currentLogIndex > 0 && onLogSelect) {
      onLogSelect(currentLogIndex - 1);
    }
  };

  const handleNext = () => {
    if (currentLogIndex < dailyLogs.length - 1 && onLogSelect) {
      onLogSelect(currentLogIndex + 1);
    }
  };

  return (
    <div className="space-y-6">
      {/* Trip Summary Header */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle className="flex items-center">
                <FileText className="w-5 h-5 mr-2" />
                ELD Logs Summary
              </CardTitle>
              <p className="text-sm text-gray-600 mt-1">
                Trip {tripId} • {totalDays} day(s)
              </p>
            </div>

            <div className="flex items-center space-x-3">
              <ELDComplianceIndicator
                isCompliant={compliantDays === totalDays}
                complianceScore={avgComplianceScore}
                violationCount={totalViolations}
                size="md"
              />

              {onExportAll && (
                <Button
                  variant="secondary"
                  leftIcon={<Download className="w-4 h-4" />}
                  onClick={onExportAll}
                >
                  Export All
                </Button>
              )}
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {/* Summary Statistics */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="text-center p-3 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">
                {totalDrivingHours.toFixed(1)}
              </div>
              <div className="text-sm text-gray-600">Total Driving Hours</div>
            </div>

            <div className="text-center p-3 bg-purple-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">
                {totalOnDutyHours.toFixed(1)}
              </div>
              <div className="text-sm text-gray-600">Total On-Duty Hours</div>
            </div>

            <div className="text-center p-3 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">
                {totalDistance.toFixed(0)}
              </div>
              <div className="text-sm text-gray-600">Total Miles</div>
            </div>

            <div className="text-center p-3 bg-orange-50 rounded-lg">
              <div className="text-2xl font-bold text-orange-600">
                {avgComplianceScore.toFixed(1)}%
              </div>
              <div className="text-sm text-gray-600">Avg Compliance</div>
            </div>
          </div>

          {/* Compliance Overview */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center space-x-2">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <span className="font-medium">Compliant Days</span>
              </div>
              <span className="text-lg font-bold">
                {compliantDays}/{totalDays}
              </span>
            </div>

            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center space-x-2">
                <FileText className="w-5 h-5 text-blue-600" />
                <span className="font-medium">Certified Days</span>
              </div>
              <span className="text-lg font-bold">
                {certifiedDays}/{totalDays}
              </span>
            </div>

            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-5 h-5 text-red-600" />
                <span className="font-medium">Total Violations</span>
              </div>
              <span className="text-lg font-bold text-red-600">
                {totalViolations}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Daily Logs Navigation */}
      {dailyLogs.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle>Daily Logs</CardTitle>
              <div className="flex items-center space-x-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setShowAllLogs(!showAllLogs)}
                >
                  {showAllLogs ? "Show Less" : "Show All"}
                </Button>
                {onLogSelect && (
                  <>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handlePrevious}
                      disabled={currentLogIndex === 0}
                      leftIcon={<ChevronLeft className="w-4 h-4" />}
                    >
                      Previous
                    </Button>
                    <span className="text-sm text-gray-600">
                      {currentLogIndex + 1} of {dailyLogs.length}
                    </span>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handleNext}
                      disabled={currentLogIndex === dailyLogs.length - 1}
                      rightIcon={<ChevronRight className="w-4 h-4" />}
                    >
                      Next
                    </Button>
                  </>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {showAllLogs ? (
              <div className="space-y-3">
                {dailyLogs.map((log, index) => (
                  <div
                    key={log.log_id}
                    className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                      index === currentLogIndex
                        ? "border-blue-500 bg-blue-50"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                    onClick={() => onLogSelect?.(index)}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-medium">
                          {new Date(log.log_date).toLocaleDateString()}
                        </div>
                        <div className="text-sm text-gray-600">
                          {log.driver_name_display}
                        </div>
                      </div>

                      <div className="flex items-center space-x-1">
                        {log.is_compliant ? (
                          <CheckCircle className="w-4 h-4 text-green-600" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-red-600" />
                        )}
                        {log.is_certified && (
                          <FileText className="w-4 h-4 text-blue-600" />
                        )}
                      </div>
                    </div>

                    <div className="text-xs text-gray-600 space-y-1">
                      <div>
                        Driving:{" "}
                        {safeNumberValue(log.total_driving_hours).toFixed(1)}h
                      </div>
                      <div>
                        On-Duty:{" "}
                        {safeNumberValue(log.total_on_duty_hours).toFixed(1)}h
                      </div>
                      <div>
                        Miles:{" "}
                        {safeNumberValue(log.total_distance_miles).toFixed(0)}
                      </div>
                      {safeNumberValue(log.violation_count) > 0 && (
                        <div className="text-red-600 font-medium">
                          {safeNumberValue(log.violation_count)} violations
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center text-gray-600">
                <p>
                  Viewing log {currentLogIndex + 1} of {dailyLogs.length}
                </p>
                <p className="text-sm mt-1">
                  Click "Show All" to see all daily logs
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
