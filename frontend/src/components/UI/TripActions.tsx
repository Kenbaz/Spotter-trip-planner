import React, { useState } from "react";
import { Button } from "../UI/Button";
import { Card, CardContent } from "../UI/Card";
import { CheckCircle, Clock, AlertCircle, Truck } from "lucide-react";
import { useCompleteTrip } from "../../hooks/useTripQueries";
import type { Trip, TripCompletionResponse } from "../../types";

interface TripActionsProps {
  trip: Trip;
  canComplete?: boolean;
  onTripCompleted?: (response: TripCompletionResponse) => void;
  className?: string;
}

export const TripActions: React.FC<TripActionsProps> = ({
  trip,
  canComplete = true,
  onTripCompleted,
  className = "",
}) => {
  const completeTripMutation = useCompleteTrip();
  const [completionResult, setCompletionResult] =
    useState<TripCompletionResponse | null>(null);

  const handleCompleteTrip = async () => {
    if (!canComplete) return;

    try {
      const result = await completeTripMutation.mutateAsync(trip.trip_id);

      if (result.success) {
        setCompletionResult(result);
        onTripCompleted?.(result);
      }
    } catch (error) {
      console.error("Error completing trip:", error);
    }
  };

  const getActionButton = () => {
    if (trip.status === "completed") {
      return (
        <div className="flex items-center space-x-2 text-green-600">
          <CheckCircle className="w-5 h-5" />
          <span className="font-medium">Trip Completed</span>
          {trip.completed_at && (
            <span className="text-sm text-gray-500">
              on {new Date(trip.completed_at).toLocaleDateString()}
            </span>
          )}
        </div>
      );
    }

    if (trip.status === "draft") {
      return (
        <div className="flex items-center space-x-2 text-gray-500">
          <Clock className="w-5 h-5" />
          <span>Calculate route before completing</span>
        </div>
      );
    }

    if (trip.status === "planned") {
      return (
        <div className="flex items-center space-x-2 text-blue-600">
          <Truck className="w-5 h-5" />
          <span>Ready to start trip</span>
        </div>
      );
    }

    if (trip.status === "in_progress") {
      return (
        <Button
          onClick={handleCompleteTrip}
          disabled={!canComplete || completeTripMutation.isPending}
          isLoading={completeTripMutation.isPending}
          className="bg-green-600 hover:bg-green-700"
          leftIcon={<CheckCircle className="w-4 h-4" />}
        >
          {completeTripMutation.isPending ? "Completing..." : "Complete Trip"}
        </Button>
      );
    }

    return null;
  };

  const getStatusBadge = () => {
    const statusConfig = {
      draft: { color: "bg-gray-100 text-gray-800", label: "Draft" },
      planned: { color: "bg-blue-100 text-blue-800", label: "Planned" },
      in_progress: {
        color: "bg-yellow-100 text-yellow-800",
        label: "In Progress",
      },
      completed: { color: "bg-green-100 text-green-800", label: "Completed" },
      cancelled: { color: "bg-red-100 text-red-800", label: "Cancelled" },
    };

    const config =
      statusConfig[trip.status as keyof typeof statusConfig] ||
      statusConfig.draft;

    return (
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color}`}
      >
        {config.label}
      </span>
    );
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Trip Status and Actions */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <span className="text-sm font-medium text-gray-700">Status:</span>
              {getStatusBadge()}
            </div>
            <div className="flex items-center space-x-3">
              {getActionButton()}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Completion Result Display */}
      {completionResult && (
        <Card className="border-green-200 bg-green-50">
          <CardContent className="p-4">
            <div className="flex items-start space-x-3">
              <CheckCircle className="w-5 h-5 text-green-600 mt-0.5" />
              <div className="flex-1">
                <h4 className="font-medium text-green-800">
                  Trip Completed Successfully!
                </h4>
                <p className="text-sm text-green-700 mt-1">
                  {completionResult.message}
                </p>

                {/* Hours Summary */}
                <div className="mt-3 grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                  <div>
                    <span className="font-medium text-green-800">
                      Driving Hours:
                    </span>
                    <span className="ml-1 text-green-700">
                      {completionResult.hours_summary.driving_hours.toFixed(1)}h
                    </span>
                  </div>
                  <div>
                    <span className="font-medium text-green-800">
                      On-Duty Hours:
                    </span>
                    <span className="ml-1 text-green-700">
                      {completionResult.hours_summary.on_duty_hours.toFixed(1)}h
                    </span>
                  </div>
                  <div>
                    <span className="font-medium text-green-800">
                      Started With:
                    </span>
                    <span className="ml-1 text-green-700">
                      {completionResult.hours_summary.started_with_cycle_hours.toFixed(
                        1
                      )}
                      h cycle
                    </span>
                  </div>
                </div>

                {/* Updated Driver Status Summary */}
                {completionResult.updated_driver_status && (
                  <div className="mt-3 p-3 bg-white rounded border border-green-200">
                    <h5 className="text-sm font-medium text-green-800 mb-2">
                      Updated HOS Status:
                    </h5>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
                      <div>
                        <span className="text-green-700">Cycle: </span>
                        <span className="font-medium text-green-800">
                          {completionResult.updated_driver_status.total_cycle_hours.toFixed(
                            1
                          )}
                          /70h
                        </span>
                      </div>
                      <div>
                        <span className="text-green-700">Driving Today: </span>
                        <span className="font-medium text-green-800">
                          {completionResult.updated_driver_status.today_driving_hours.toFixed(
                            1
                          )}
                          /11h
                        </span>
                      </div>
                      <div>
                        <span className="text-green-700">On-Duty Today: </span>
                        <span className="font-medium text-green-800">
                          {completionResult.updated_driver_status.today_on_duty_hours.toFixed(
                            1
                          )}
                          /14h
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* HOS Status Display */}
      {trip.starting_cycle_hours !== undefined && (
        <Card>
          <CardContent className="p-4">
            <h4 className="text-sm font-medium text-gray-700 mb-3">
              Trip Starting Conditions:
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div>
                <span className="text-gray-600">Cycle Hours:</span>
                <span className="ml-1 font-medium">
                  {trip.starting_cycle_hours?.toFixed(1) || 0}h
                </span>
              </div>
              <div>
                <span className="text-gray-600">Driving:</span>
                <span className="ml-1 font-medium">
                  {trip.starting_driving_hours?.toFixed(1) || 0}h
                </span>
              </div>
              <div>
                <span className="text-gray-600">On-Duty:</span>
                <span className="ml-1 font-medium">
                  {trip.starting_on_duty_hours?.toFixed(1) || 0}h
                </span>
              </div>
              <div>
                <span className="text-gray-600">Status:</span>
                <span className="ml-1 font-medium capitalize">
                  {trip.starting_duty_status?.replace("_", " ") || "Unknown"}
                </span>
              </div>
            </div>

            {trip.hos_updated && (
              <div className="mt-2 flex items-center text-xs text-green-600">
                <CheckCircle className="w-3 h-3 mr-1" />
                <span>HOS status updated</span>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Error Display */}
      {completeTripMutation.isError && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-4">
            <div className="flex items-start space-x-3">
              <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
              <div>
                <h4 className="font-medium text-red-800">
                  Failed to Complete Trip
                </h4>
                <p className="text-sm text-red-700 mt-1">
                  {completeTripMutation.error?.message ||
                    "An unexpected error occurred"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
