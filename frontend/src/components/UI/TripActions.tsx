// components/UI/TripActions.tsx
import React, { useState, useEffect, useRef } from "react";
import { Button } from "./Button";
import { CheckCircle, AlertCircle } from "lucide-react";
import { useCompleteTrip } from "../../hooks/useTripQueries";
import type { Trip, TripCompletionResponse } from "../../types";
import { motion, AnimatePresence } from "framer-motion";

// Extended interface for local state with timestamp
interface TripCompletionWithTimestamp extends TripCompletionResponse {
  completedAt?: string;
}

interface TripActionsProps {
  trip: Trip;
  canComplete?: boolean;
  onTripCompleted?: (response: TripCompletionResponse) => void;
  className?: string;
  showFullActions?: boolean;
}

export const TripActions: React.FC<TripActionsProps> = ({
  trip,
  canComplete = true,
  onTripCompleted,
  className = "",
  // showFullActions = true,
}) => {
  const completeTripMutation = useCompleteTrip();
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [completionResult, setCompletionResult] =
    useState<TripCompletionWithTimestamp | null>(null);

  const completionDataRef = useRef<TripCompletionWithTimestamp | null>(null);

  useEffect(() => {
    if (trip.status === "completed" && !completionResult) {
      const recentCompletionKey = `trip_completion_${trip.trip_id}`;
      const storedCompletion = sessionStorage.getItem(recentCompletionKey);

      if (storedCompletion) {
        try {
          const parsedCompletion: TripCompletionWithTimestamp =
            JSON.parse(storedCompletion);
          setCompletionResult(parsedCompletion);
          completionDataRef.current = parsedCompletion;
        } catch (error) {
          console.error("Error parsing stored completion data:", error);
          sessionStorage.removeItem(recentCompletionKey);
        }
      }
    }
  }, [trip.status, trip.trip_id, completionResult]);

  const handleCompleteTrip = async () => {
    if (!canComplete) return;

    try {
      const result = await completeTripMutation.mutateAsync(trip.trip_id);

      if (result.success) {
        const completionWithTimestamp: TripCompletionWithTimestamp = {
          ...result,
          completedAt: new Date().toISOString(),
        };

        const storageKey = `trip_completion_${trip.trip_id}`;
        sessionStorage.setItem(
          storageKey,
          JSON.stringify(completionWithTimestamp)
        );

        setCompletionResult(completionWithTimestamp);
        completionDataRef.current = completionWithTimestamp;

        // Call parent callback
        onTripCompleted?.(result);
        setShowConfirmation(false);
      }
    } catch (error) {
      console.error("Error completing trip:", error);
      setShowConfirmation(false);
    }
  };

  const handleCompleteClick = () => {
    setShowConfirmation(true);
  };

  const handleCancelComplete = () => {
    setShowConfirmation(false);
  };

  // Check if trip can be completed (has route and HOS periods)
  const canTripBeCompleted = () => {
    return (
      trip.status === "Planned" &&
      trip.hos_periods &&
      trip.hos_periods.length > 0
    );
  };

  // Animation variants for smooth transitions
  const confirmationVariants = {
    hidden: {
      opacity: 0,
      y: -20,
      scale: 0.95,
    },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        type: "spring" as const,
        stiffness: 300,
        damping: 25,
        mass: 0.8,
        duration: 0.5,
      },
    },
    exit: {
      opacity: 0,
      y: -10,
      scale: 0.98,
      transition: {
        type: "tween" as const,
        ease: "easeInOut" as const,
        duration: 0.2,
      },
    },
  };

  // Show hours summary for completed trips
  const currentCompletionResult = completionResult || completionDataRef.current;
  if (
    trip.status === "completed" &&
    currentCompletionResult &&
    currentCompletionResult.hours_summary
  ) {
    return (
      <div
        className={`bg-blue-50 border border-blue-200 py-4 px-2 md:px-4 rounded-lg ${className}`}
      >
        <h4 className="font-medium text-blue-900 mb-3 flex items-center">
          <CheckCircle className="w-5 h-5 mr-2" />
          Trip Hours Summary
        </h4>
        <div className="grid grid-cols-2 gap-2 md:gap-4 text-sm">
          <div className="bg-white p-3 rounded border">
            <span className="text-gray-600 block">Driving Hours:</span>
            <span className="font-semibold text-lg text-blue-900">
              {currentCompletionResult.hours_summary.driving_hours.toFixed(1)}h
            </span>
          </div>
          <div className="bg-white p-3 rounded border">
            <span className="text-gray-600 block">On-Duty Hours:</span>
            <span className="font-semibold text-lg text-blue-900">
              {currentCompletionResult.hours_summary.on_duty_hours.toFixed(1)}h
            </span>
          </div>
          <div className="bg-white p-3 rounded border">
            <span className="text-gray-600 block">
              Driving hours at trip start:
            </span>
            <span className="font-semibold text-lg text-blue-900">
              {currentCompletionResult.hours_summary.started_with_driving_hours.toFixed(
                1
              )}
              h
            </span>
          </div>
          <div className="bg-white p-3 rounded border">
            <span className="text-gray-600 block">
              Cycle hours at trip start:
            </span>
            <span className="font-semibold text-lg text-blue-900">
              {currentCompletionResult.hours_summary.started_with_cycle_hours.toFixed(
                1
              )}
              h
            </span>
          </div>
        </div>
      </div>
    );
  }

  // Only show trip actions for planned trips
  if (trip.status !== "Planned") {
    return null;
  }

  // Check if trip cannot be completed
  if (!canTripBeCompleted()) {
    return (
      <div
        className={`flex items-center space-x-2 text-yellow-600 ${className}`}
      >
        <AlertCircle className="w-5 h-5" />
        <span className="text-sm">
          Route must be calculated before completing trip
        </span>
      </div>
    );
  }

  return (
    <div className={`space-y-3 ${className}`}>
      <AnimatePresence mode="wait">
        {showConfirmation ? (
          <motion.div
            key="confirmation"
            variants={confirmationVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="overflow-hidden"
          >
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg shadow-sm">
              <div className="flex items-center space-x-2 text-yellow-800 mb-2">
                <AlertCircle className="w-5 h-5" />
                <span className="font-medium">Confirm Trip Completion</span>
              </div>
              <p className="text-sm text-yellow-700 mb-3">
                Are you sure you want to complete this trip? This action cannot
                be undone and will update your HOS status.
              </p>
              <div className="flex space-x-2">
                <Button
                  onClick={handleCompleteTrip}
                  disabled={completeTripMutation.isPending}
                  isLoading={completeTripMutation.isPending}
                  className="bg-green-600 hover:bg-green-700"
                  leftIcon={<CheckCircle className="w-4 h-4" />}
                  size="sm"
                >
                  {completeTripMutation.isPending
                    ? "Completing..."
                    : "Yes, Complete Trip"}
                </Button>
                <Button
                  onClick={handleCancelComplete}
                  variant="danger"
                  size="sm"
                  disabled={completeTripMutation.isPending}
                >
                  Cancel
                </Button>
              </div>
            </div>
          </motion.div>
        ) : (
          <div>
            <Button
              onClick={handleCompleteClick}
              className="bg-green-600 hover:bg-green-700 text-white"
              leftIcon={<CheckCircle className="w-4 h-4" />}
              size="sm"
              disabled={!canComplete}
            >
              Complete Trip
            </Button>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
