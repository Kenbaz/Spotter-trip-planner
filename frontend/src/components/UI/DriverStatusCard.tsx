// components/DriverStatusCard/DriverStatusCard.tsx

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../UI/Card";
import { Button } from "../UI/Button";
import {
  AlertCircle,
  Truck,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";
import {
  useCurrentDriverStatus,
  useUpdateDriverStatus,
} from "../../hooks/useTripQueries";
import { LoadingSpinner } from "../UI/LoadingSpinner";
import type { CurrentDriverStatus } from "../../types";

interface DriverStatusCardProps {
  onStatusLoad?: (status: CurrentDriverStatus) => void;
  showActions?: boolean;
  className?: string;
}

export const DriverStatusCard: React.FC<DriverStatusCardProps> = ({
  onStatusLoad,
  showActions = false,
  className = "",
}) => {
  const {
    data: statusResponse,
    isLoading,
    isError,
    // error,
    refetch,
    isRefetching
  } = useCurrentDriverStatus();

  const updateStatusMutation = useUpdateDriverStatus();

  React.useEffect(() => {
    if (statusResponse?.current_status && onStatusLoad) {
      onStatusLoad(statusResponse.current_status);
    }
  }, [statusResponse, onStatusLoad]);

  const handleStatusUpdate = async (newStatus: string) => {
    try {
      const validStatuses: Array<
        "off_duty" | "sleeper_berth" | "driving" | "on_duty_not_driving"
      > = ["off_duty", "sleeper_berth", "driving", "on_duty_not_driving"];

      if (
        !validStatuses.includes(newStatus as (typeof validStatuses)[number])
      ) {
        console.error("Invalid status:", newStatus);
        return;
      }

      await updateStatusMutation.mutateAsync({
        current_duty_status: newStatus as (typeof validStatuses)[number],
        current_status_start: new Date().toISOString(),
      });
    } catch (error) {
      console.error("Failed to update status:", error);
    }
  };

  const handleRefresh = () => {
    refetch();
  };

  if (isLoading) {
    return (
      <Card className={`border-gray-100 shadow-none ${className}`}>
        <CardContent className="flex items-center justify-center p-6">
          <div className="flex items-center">
            <LoadingSpinner size="medium" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isError || !statusResponse?.success) {
    return (
      <Card className={`border-red-200 bg-red-50 ${className}`}>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <span className="text-red-800">
                Failed to load HOS status
              </span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRefresh}
              className="text-red-600 hover:text-red-700"
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const status = statusResponse.current_status;
  const hasWarnings = status.compliance_warnings.length > 0;
  const hasCriticalWarnings = status.compliance_warnings.some(
    (w) => w.severity === "critical"
  );

  // Determine card styling based on compliance status
  const cardClass = hasCriticalWarnings
    ? "border-red-200 bg-red-50"
    : hasWarnings
    ? "border-amber-200 bg-amber-50"
    : "border-green-200 bg-green-50";

  const statusIcon = status.needs_immediate_break ? (
    <AlertTriangle className="w-5 h-5 text-red-600" />
  ) : hasWarnings ? (
    <AlertTriangle className="w-5 h-5 text-amber-600" />
  ) : (
    <CheckCircle className="w-5 h-5 text-green-600" />
  );

  const formatDateTime = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "Invalid date";
    }
  };

  const getDutyStatusDisplay = (dutyStatus: string) => {
    const statusMap: Record<string, string> = {
      off_duty: "Off Duty",
      sleeper_berth: "Sleeper Berth",
      driving: "Driving",
      on_duty_not_driving: "On Duty (Not Driving)",
    };
    return statusMap[dutyStatus] || dutyStatus;
  };

  const getDutyStatusColor = (dutyStatus: string) => {
    const colorMap: Record<string, string> = {
      off_duty: "text-gray-600",
      sleeper_berth: "text-blue-600",
      driving: "text-red-600",
      on_duty_not_driving: "text-orange-600",
    };
    return colorMap[dutyStatus] || "text-gray-600";
  };

  return (
    <Card className={`${cardClass} ${className} md:border md:border-gray-200 driver-status-card`}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Truck className="w-5 h-5" />
            <span>Current HOS Status</span>
            {statusIcon}
          </div>
          <div className="flex items-center space-x-2">
            {showActions && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRefresh}
                className="text-gray-700 bg-transparent hover:text-gray-900"
              >
                <RefreshCw
                  className={`${
                    isRefetching
                      ? "animate-spin w-4 h-4"
                      : "w-4 h-4"
                  }`}
                />
              </Button>
            )}
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* HOS Hours Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 md:gap-2 gap-4">
          <div className="space-y-1">
            <p className="text-sm font-medium text-gray-700">Cycle Hours</p>
            <p className="text-lg font-semibold text-gray-600">
              {status.total_cycle_hours.toFixed(1)} / 70
            </p>
            <p className="text-sm text-gray-500">
              {status.remaining_cycle_hours.toFixed(1)} remaining
            </p>
            {status.remaining_cycle_hours <= 10 && (
              <p className="text-xs text-amber-600 font-medium">
                Low remaining!
              </p>
            )}
          </div>

          <div className="space-y-1">
            <p className="text-sm font-medium text-gray-700">Driving Today</p>
            <p className="text-lg text-gray-600 font-semibold">
              {status.today_driving_hours.toFixed(1)} / 11
            </p>
            <p className="text-xs text-gray-500">
              {status.remaining_driving_hours_today.toFixed(1)} remaining
            </p>
            {status.remaining_driving_hours_today <= 2 && (
              <p className="text-xs text-amber-600 font-medium">
                Hours low!
              </p>
            )}
          </div>

          <div className="space-y-1">
            <p className="text-sm font-medium text-gray-700">On-Duty Today</p>
            <p className="text-lg text-gray-600 font-semibold">
              {status.today_on_duty_hours.toFixed(1)} / 14
            </p>
            <p className="text-xs text-gray-500">
              {status.remaining_on_duty_hours_today.toFixed(1)} remaining
            </p>
            {status.remaining_on_duty_hours_today <= 2 && (
              <p className="text-xs text-amber-600 font-medium">
                Hours low!
              </p>
            )}
          </div>

          <div className="space-y-1">
            <p className="text-sm font-medium text-gray-700">Current Status</p>
            <p
              className={`text-lg font-semibold ${getDutyStatusColor(
                status.current_duty_status
              )}`}
            >
              {getDutyStatusDisplay(status.current_duty_status)}
            </p>
            <p className="text-xs text-gray-500">
              Since {formatDateTime(status.current_status_start)}
            </p>
          </div>
        </div>

        {/* Quick Status Change Actions */}
        {showActions && (
          <div className="border-t pt-4">
            <p className="text-base font-medium text-gray-700 mb-2">
              Quick Status Change:
            </p>
            <div className="grid grid-cols-2 gap-2">
              {(
                [
                  "off_duty",
                  "sleeper_berth",
                  "driving",
                  "on_duty_not_driving",
                ] as const
              ).map((statusOption) => (
                <Button
                  key={statusOption}
                  variant={
                    status.current_duty_status === statusOption
                      ? "ghost"
                      : "primary"
                  }
                  size="sm"
                  onClick={() => handleStatusUpdate(statusOption)}
                  disabled={updateStatusMutation.isPending}
                  className="text-xs py-[0.5rem] rounded-md"
                >
                  {getDutyStatusDisplay(statusOption)}
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* Compliance Warnings */}
        {hasWarnings && (
          <div className="border-t pt-4">
            <h4 className="text-sm font-medium text-amber-800 mb-2 flex items-center">
              <AlertTriangle className="w-4 h-4 mr-1" />
              Compliance Alerts:
            </h4>
            <ul className="space-y-1">
              {status.compliance_warnings.map((warning, index) => (
                <li key={index} className="flex items-start space-x-2">
                  <AlertTriangle
                    className={`w-4 h-4 mt-0.5 flex-shrink-0 ${
                      warning.severity === "critical"
                        ? "text-red-600"
                        : "text-amber-600"
                    }`}
                  />
                  <span
                    className={`text-sm ${
                      warning.severity === "critical"
                        ? "text-red-800"
                        : "text-amber-800"
                    }`}
                  >
                    {warning.message}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Last Updated */}
        <div className="text-xs text-gray-500 border-t pt-2 flex items-center justify-between">
          <span>
            Last updated: {formatDateTime(statusResponse.last_updated)}
          </span>
          <span>Date: {new Date(status.today_date).toLocaleDateString()}</span>
        </div>
      </CardContent>
    </Card>
  );
};
