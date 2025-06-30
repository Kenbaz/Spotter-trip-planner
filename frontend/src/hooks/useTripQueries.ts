import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { tripService } from "../services/TripService";
import type {
  CreateTripRequest,
  TripCalculationRequest,
  ELDLogRequest,
  PaginatedResponse,
  TripListItem,
  Trip,
  ComplianceReport,
  GeocodingResponse,
  APIStatusCheckResponse,
  CurrentDriverStatusResponse,
  TripCompletionResponse,
  DriverStatusUpdateRequest,
  DriverStatusUpdateResponse,
  MyTripsResponse,
  TripCalculationResponse,
} from "../types";


export const tripQueryKeys = {
    all: ["trips"] as const,

    list: (params?: Record<string, unknown>) => ['trips', 'list', params] as const,
    detail: (Id: string) => ['trips', 'details', Id] as const,
    myTrips: (status?: string) => ['trips', 'my-trips', status] as const,
    compliance: (id: string) => ['trips', 'compliance', id] as const,
};


export const driverQueryKeys = {
  all: ["driver"] as const,
  currentStatus: ["driver", "current-status"] as const,
};


export const utilityQueryKeys = {
    apiStatus: ['utilities', 'api-status'] as const,
    geocoding: (address: string) => ['utilities', 'geocoding', address] as const,
};


// Get user's trips
export function useMyTrips(status?: string) {
    return useQuery({
        queryKey: tripQueryKeys.myTrips(status),
        queryFn: (): Promise<MyTripsResponse> => tripService.getMyTrips(status),
        staleTime: 2 * 60 * 1000,
        gcTime: 5 * 60 * 1000,
    });
};

// Get current driver HOS status
export function useCurrentDriverStatus() { 
    return useQuery({
        queryKey: driverQueryKeys.currentStatus,
        queryFn: (): Promise<CurrentDriverStatusResponse> => tripService.getCurrentDriverStatus(),
        staleTime: 5 * 60 * 1000,
        refetchInterval: 10 * 60 * 1000,
        refetchOnWindowFocus: true,
    });
};

// Complete a trip
export function useCompleteTrip() {
    const queryClient = useQueryClient();
    
    return useMutation({
      mutationFn: (tripId: string): Promise<TripCompletionResponse> => 
        tripService.completeTrip(tripId),
      onSuccess: (data, tripId) => {
        queryClient.invalidateQueries({
          queryKey: tripQueryKeys.detail(tripId),
        });

        // Invalidate trip lists to update status/counts
        queryClient.invalidateQueries({
          queryKey: tripQueryKeys.myTrips(),
        });

        queryClient.invalidateQueries({
          queryKey: driverQueryKeys.currentStatus,
        });

        // If we have trip data in the response, update the specific trip cache
        if (data.hours_summary) {
          queryClient.invalidateQueries({ queryKey: tripQueryKeys.myTrips() });
        }
      },
    });
};

// Update driver status
export function useUpdateDriverStatus() {
    const queryClient = useQueryClient();
    
    return useMutation({
      mutationFn: (updateData: DriverStatusUpdateRequest): Promise<DriverStatusUpdateResponse> => 
        tripService.updateDriverStatus(updateData),
      onSuccess: () => {
        // Invalidate driver status queries
        queryClient.invalidateQueries({ queryKey: driverQueryKeys.currentStatus });
      },
    });
};

// Get trip list
export function useGetTrips(params?: {
    status?: string;
    page?: number;
    pageSize?: number;
    search?: string;
}) {
    return useQuery({
        queryKey: tripQueryKeys.list(params),
        queryFn: (): Promise<PaginatedResponse<TripListItem>> => tripService.getTrips(params),
        staleTime: 2 * 60 * 1000,
        placeholderData: keepPreviousData,
    });
};

// Get trip details
export function useGetTripDetails(tripId: string | undefined) {
    return useQuery({
        queryKey: tripQueryKeys.detail(tripId || ""),
        queryFn: (): Promise<{ success: boolean; trip: Trip }> => tripService.getTripDetails(tripId!),
        enabled: !!tripId,
        staleTime: 30 * 1000,
    });
};

// Get compliance report
export function useGetTripComplianceReport(tripId: string | undefined) {
    return useQuery({
        queryKey: tripQueryKeys.compliance(tripId || ""),
        queryFn: (): Promise<{ success: boolean; compliance_report: ComplianceReport }> => tripService.getComplianceReport(tripId!),
        enabled: !!tripId,
        staleTime: 5 * 60 * 1000,
    });
}

// Geocode an address
export function useGeocodeAddress(address: string, enabled: true) { 
    return useQuery({
        queryKey: utilityQueryKeys.geocoding(address),
        queryFn: (): Promise<GeocodingResponse> => tripService.geocodeAddress(address),
        enabled: enabled && !!address.trim(),
        staleTime: 24 * 60 * 60 * 1000,
        gcTime: 7 * 24 * 60 * 60 * 1000,
    });
};

// Check API status
export function useCheckAPIStatus() {
    return useQuery({
        queryKey: utilityQueryKeys.apiStatus,
        queryFn: (): Promise<APIStatusCheckResponse> => tripService.getAPIStatus(),
        staleTime: 5 * 60 * 1000,
        refetchInterval: 10 * 60 * 1000,
    });
};

// Create a new trip
export function useCreateTrip() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (tripData: CreateTripRequest) => tripService.createTrip(tripData),
        onSuccess: (data) => {
          // Set the new trip in cache immediately
          queryClient.setQueryData(tripQueryKeys.detail(data.trip.trip_id), {
            success: true,
            trip: data.trip,
          });

          // Invalidate the trips list to ensure it reflects the new trip
          queryClient.invalidateQueries({ queryKey: tripQueryKeys.myTrips() });
        },
    });
};

// Update an existing trip
export function useUpdateTrip() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ tripId, tripData }: {
            tripId: string;
            tripData: Partial<CreateTripRequest>;
        }) => tripService.updateTrip(tripId, tripData),
        onSuccess: (data, variables) => {
            // Update cached trip details
            queryClient.setQueryData(
                tripQueryKeys.detail(variables.tripId),
                { success: true, trip: data.trip }
            );

            queryClient.invalidateQueries({ queryKey: tripQueryKeys.myTrips() });
        },
    });
};

// Delete trip
export function useDeleteTrip() {
    const queryClient = useQueryClient();
  
    return useMutation({
      mutationFn: (tripId: string) => tripService.deleteTrip(tripId),
      onSuccess: (_, tripId) => {
        // Remove from cache
        queryClient.removeQueries({ queryKey: tripQueryKeys.detail(tripId) });

        // Remove compliance data for deleted trip
        queryClient.removeQueries({
          queryKey: tripQueryKeys.compliance(tripId),
        });

        // Update trip lists
        queryClient.invalidateQueries({
          queryKey: tripQueryKeys.myTrips(),
        });
      },
    });
};

// Calculate route for trip
export function useCalculateRoute() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({
            tripId,
            options = {},
        }: {
            tripId: string;
            options?: TripCalculationRequest;
        }): Promise<TripCalculationResponse> => tripService.calculateRoute(tripId, options),
        onSuccess: (data, variables) => {
            if (data.success) {
              // Invalidate specific trip details to refetch updated trip data
              queryClient.invalidateQueries({
                queryKey: tripQueryKeys.detail(variables.tripId),
              });

              // Only invalidate compliance for this trip
              queryClient.invalidateQueries({
                queryKey: tripQueryKeys.compliance(variables.tripId),
              });

              // Only invalidate trip lists (for status updates)
              queryClient.invalidateQueries({
                queryKey: tripQueryKeys.myTrips(),
              });

              if (data.driver_status_impact) {
                queryClient.invalidateQueries({
                  queryKey: driverQueryKeys.currentStatus,
                });
              }
            }
        },
    });
};

// Optimize route
export function useOptimizeRoute() {
    const queryClient = useQueryClient();
  
    return useMutation({
      mutationFn: ({ 
        tripId, 
        options = {} 
      }: { 
        tripId: string; 
        options?: {
          optimize_breaks?: boolean;
          optimize_fuel_stops?: boolean;
          optimize_daily_resets?: boolean;
          max_optimization_distance?: number;
        }
      }) => tripService.optimizeRoute(tripId, options),
      onSuccess: (data, variables) => {
        if (data.success && data.optimized) {
          // Invalidate trip data to refetch optimized route
          queryClient.invalidateQueries({ 
            queryKey: tripQueryKeys.detail(variables.tripId) 
          });
            
          queryClient.invalidateQueries({
            queryKey: tripQueryKeys.compliance(variables.tripId),
          });

          // Only invalidate trip lists (for status updates)
          queryClient.invalidateQueries({
            queryKey: tripQueryKeys.myTrips(),
          });
        }
      },
    });
};

// Generate ELD Logs
export function useGenerateELDLogs() {
    return useMutation({
        mutationFn: ({
            tripId,
            options = {},
        }: {
            tripId: string;
            options?: ELDLogRequest;
        }) => tripService.generateELDLogs(tripId, options),
    });
}

// Geocode address mutation (for immediate geocoding)
export function useGeocodeMutation() {
    return useMutation({
      mutationFn: (address: string): Promise<GeocodingResponse> => tripService.geocodeAddress(address),
    });
}
  
// Reverse geocode mutation
export function useReverseGeocodeMutation() {
    return useMutation({
      mutationFn: ({ latitude, longitude }: { latitude: number; longitude: number }) =>
        tripService.reverseGeocode(latitude, longitude),
    });
}