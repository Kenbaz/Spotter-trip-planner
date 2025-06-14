import { useState, useCallback } from "react";
import { useCalculateRoute, useOptimizeRoute, useGenerateELDLogs } from "./useTripQueries";
import type {
    TripCalculationRequest,
    ELDLogRequest,
    TripCalculationResponse,
    RouteOptimizationResponse,
    ELDLogResponse,
} from "../types";


interface TripCalculationState {
    isCalculating: boolean;
    isOptimizing: boolean;
    isGeneratingELD: boolean;
    lastCalculationResult: TripCalculationResponse | null;
    lastOptimizationResult: RouteOptimizationResponse | null;
    lastELDResult: ELDLogResponse | null;
    calculationError: string | null;
    optimizationError: string | null;
    eldError: string | null;
}

interface TripCalculationOptions {
  onCalculationSuccess?: (result: TripCalculationResponse) => void;
  onCalculationError?: (error: string) => void;
  onOptimizationSuccess?: (result: RouteOptimizationResponse) => void;
  onOptimizationError?: (error: string) => void;
  onELDSuccess?: (result: ELDLogResponse) => void;
  onELDError?: (error: string) => void;
}


export function useTripCalculation(
    tripId: string,
    options: TripCalculationOptions = {}
) {
  const [state, setState] = useState<TripCalculationState>({
    isCalculating: false,
    isOptimizing: false,
    isGeneratingELD: false,
    lastCalculationResult: null,
    lastOptimizationResult: null,
    lastELDResult: null,
    calculationError: null,
    optimizationError: null,
    eldError: null,
  });

  // Mutattions
  const calculateRouteMutation = useCalculateRoute();
  const optimizeRouteMutation = useOptimizeRoute();
  const generateELDMutation = useGenerateELDLogs();

  // Calculate route with HOS Compliance
  const calculateRoute = useCallback(
    async (calculationOptions: TripCalculationRequest = {}) => {
      if (!tripId) {
        setState((prev) => ({
          ...prev,
          calculationError: "Trip ID is required for route calculation",
        }));
        return;
      }

      setState((prev) => ({
        ...prev,
        isCalculating: true,
        calculationError: null,
      }));

      try {
        const result = await calculateRouteMutation.mutateAsync({
          tripId,
          options: calculationOptions,
        });

        setState((prev) => ({
          ...prev,
          isCalculating: false,
          lastCalculationResult: result,
          calculationError: null,
        }));

        if (result.success) {
          options.onCalculationSuccess?.(result);
        } else {
          const errorMessage = result.error || "Route calculation failed";
          setState((prev) => ({
            ...prev,
            calculationError: errorMessage,
          }));
          options.onCalculationError?.(errorMessage);
        }

        return result;
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : "Route calculation failed";
        setState((prev) => ({
          ...prev,
          isCalculating: false,
          calculationError: errorMessage,
        }));
        options.onCalculationError?.(errorMessage);
        throw error;
      }
    },
    [tripId, calculateRouteMutation, options]
  );

  // Optimize route
  const optimizeRoute = useCallback(
    async (
      optimizationOptions: {
        optimize_breaks?: boolean;
        optimize_fuel_stops?: boolean;
        optimize_daily_resets?: boolean;
        max_optimization_distance?: number;
      } = {}
    ) => {
      if (!tripId) {
        setState((prev) => ({
          ...prev,
          optimizationError: "Trip ID is required for route optimization",
        }));
        return;
      }

      setState((prev) => ({
        ...prev,
        isOptimizing: true,
        optimizationError: null,
      }));

      try {
        const result = await optimizeRouteMutation.mutateAsync({
          tripId,
          options: optimizationOptions,
        });

        setState((prev) => ({
          ...prev,
          isOptimizing: false,
          lastOptimizationResult: result,
          optimizationError: null,
        }));

        if (result.success) {
          options.onOptimizationSuccess?.(result);
        } else {
          const errorMessage = result.error || "Route optimization failed";
          setState((prev) => ({
            ...prev,
            optimizationError: errorMessage,
          }));
          options.onOptimizationError?.(errorMessage);
        }

        return result;
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : "Route optimization failed";
        setState((prev) => ({
          ...prev,
          isOptimizing: false,
          optimizationError: errorMessage,
        }));
        options.onOptimizationError?.(errorMessage);
        throw error;
      }
    },
    [tripId, optimizeRouteMutation, options]
  );

  // Generate ELD logs
  const generateELDLogs = useCallback(
    async (eldOptions: ELDLogRequest = {}) => {
      if (!tripId) {
        setState((prev) => ({
          ...prev,
          eldError: "Trip ID is required for ELD log generation",
        }));
        return;
      }

      setState((prev) => ({
        ...prev,
        isGeneratingELD: true,
        eldError: null,
      }));

      try {
        const result = await generateELDMutation.mutateAsync({
          tripId,
          options: eldOptions,
        });

        setState((prev) => ({
          ...prev,
          isGeneratingELD: false,
          lastELDResult: result,
          eldError: null,
        }));

        if (result.success) {
          options.onELDSuccess?.(result);
        } else {
          const errorMessage = result.error || "ELD log generation failed";
          setState((prev) => ({
            ...prev,
            eldError: errorMessage,
          }));
          options.onELDError?.(errorMessage);
        }

        return result;
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : "ELD log generation failed";
        setState((prev) => ({
          ...prev,
          isGeneratingELD: false,
          eldError: errorMessage,
        }));
        options.onELDError?.(errorMessage);
        throw error;
      }
    },
    [tripId, generateELDMutation, options]
  );

  // Calculate and optimize route in one go
  const calculateAndOptimizeRoute = useCallback(
    async (
      calculationOptions: TripCalculationRequest = {},
      optimizationOptions: {
        optimize_breaks?: boolean;
        optimize_fuel_stops?: boolean;
        optimize_daily_resets?: boolean;
        max_optimization_distance?: number;
      } = {}
    ) => {
      try {
        // Calculate route first
        const calculationResult = await calculateRoute(calculationOptions);

        if (calculationResult?.success) {
          // If calculation is successful, proceed to optimization
          const optimizationResult = await optimizeRoute(optimizationOptions);
          return { calculationResult, optimizationResult };
        }

        return { calculationResult, optimizationResult: null };
      } catch (error) {
        console.error("Route calculation and optimization failed:", error);
        throw error;
      }
    },
    [calculateRoute, optimizeRoute]
  );

  // Clear errors
  const clearErrors = useCallback(() => {
    setState((prev) => ({
      ...prev,
      calculationError: null,
      optimizationError: null,
      eldError: null,
    }));
  }, []);

  // Reset all state
  const reset = useCallback(() => {
    setState({
      isCalculating: false,
      isOptimizing: false,
      isGeneratingELD: false,
      lastCalculationResult: null,
      lastOptimizationResult: null,
      lastELDResult: null,
      calculationError: null,
      optimizationError: null,
      eldError: null,
    });
  }, []);

  return {
    // State
    ...state,

    // Actions
    calculateRoute,
    optimizeRoute,
    generateELDLogs,
    calculateAndOptimizeRoute,
    clearErrors,
    reset,

    // Computed states
    hasAnyError: !!(
      state.calculationError ||
      state.optimizationError ||
      state.eldError
    ),
    
    calculateMutation: calculateRouteMutation,
    optimizeMutation: optimizeRouteMutation,
    eldMutation: generateELDMutation,
  };
    
}