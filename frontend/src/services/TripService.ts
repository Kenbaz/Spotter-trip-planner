import { apiClient } from "./apiClient";
import type {
    Trip,
    TripListItem,
    CreateTripRequest,
    TripCalculationRequest,
    TripCalculationResponse,
    ELDLogRequest,
    ELDLogResponse,
    ComplianceReport,
    RouteOptimizationResponse,
    GeocodingResponse,
    ReverseGeocodingResponse,
    TestRouteResponse,
    APIStatusCheckResponse,
    PaginatedResponse,
    CurrentDriverStatusResponse,
    TripCompletionResponse,
    DriverStatusUpdateRequest,
    DriverStatusUpdateResponse,
    MyTripsResponse
} from "../types";


interface ServiceError {
    message: string;
    code?: number;
    statusCode?: number;
    details?: unknown;
}


class TripService {
  private readonly BASE_URL = "/api/trips/";

  private handleError(error: unknown, context: string): never {
    // console.error(`TripService Error in ${context}:`, error);

    if (error && typeof error === "object" && "response" in error) {
      const axiosError = error as {
        response?: {
          data?: { error?: string; detail?: string; message?: string };
          status?: number;
        };
        message?: string;
      };

      const errorData = axiosError.response?.data;
      const statusCode = axiosError.response?.status;

      const serviceError: ServiceError = {
        message:
          errorData?.error ||
          errorData?.detail ||
          errorData?.message ||
          axiosError.message ||
          `${context} failed`,
        statusCode,
        details: errorData,
      };

      switch (statusCode) {
        case 401:
          serviceError.details = "UNAUTHORIZED";
          serviceError.message = "Unauthorized access. Please log in.";
          break;
        case 403:
          serviceError.details = "FORBIDDEN";
          serviceError.message =
            "Forbidden access. You do not have permission to perform this action.";
          break;
        case 404:
          serviceError.details = "NOT_FOUND";
          serviceError.message = "The requested resource was not found.";
          break;
        default:
          if (statusCode && statusCode >= 500) {
            serviceError.details = "INTERNAL_SERVER_ERROR";
            serviceError.message =
              "An internal server error occurred. Please try again later.";
          }
          break;
      }

      throw serviceError;
    }

    // Fallback for truly unknown errors
    const fallbackError: ServiceError = {
      message: error instanceof Error ? error.message : `${context} failed`,
      details: "Unknown error occurred",
    };

    throw fallbackError;
  }

  // Get all trips
  async getTrips(params?: {
    status?: string;
    page?: number;
    pageSize?: number;
    search?: string;
  }): Promise<PaginatedResponse<TripListItem>> {
    try {
      const response = await apiClient.get(this.BASE_URL, { params });

      if (!response.data) {
        throw new Error("Invalid response data");
      }

      return response.data;
    } catch (error) {
      this.handleError(error, "Get trips");
    }
  }

  // Get user's trips
  async getMyTrips(status?: string): Promise<MyTripsResponse> {
    try {
      const params = status ? { status } : undefined;
      const response = await apiClient.get(`${this.BASE_URL}my_trips/`, {
        params,
      });

      if (!response.data) {
        throw new Error("No response data received");
      }

      if (typeof response.data.success === "boolean") {
        return response.data;
      }

      if (response.data.results && Array.isArray(response.data.results)) {
        return {
          success: true,
          trips: response.data.results,
          count: response.data.count || response.data.results.length,
        };
      }

      // console.error("Unexpected response format:", response.data);
      throw new Error("Invalid response data format");
    } catch (error) {
      this.handleError(error, "Get my trips");
    }
  }

  // Get trip details
  async getTripDetails(tripId: string): Promise<{
    success: boolean;
    trip: Trip;
  }> {
    try {
      if (!tripId?.trim()) {
        throw new Error("Trip ID is required");
      }

      const response = await apiClient.get(`${this.BASE_URL}${tripId}/`);

      if (!response.data || typeof response.data.success !== "boolean") {
        throw new Error("Invalid response data");
      }

      return response.data;
    } catch (error) {
      this.handleError(error, "Get trip details");
    }
  }

  // Create a new trip
  async createTrip(tripData: CreateTripRequest): Promise<{
    success: boolean;
    message: string;
    trip: Trip;
  }> {
    try {
      if (!tripData) {
        throw new Error("Trip data is required");
      }

      if (!tripData.current_address?.trim()) {
        throw new Error("Current address is required");
      }
      if (!tripData.pickup_address?.trim()) {
        throw new Error("Pickup address is required");
      }
      if (!tripData.delivery_address?.trim()) {
        throw new Error("Delivery address is required");
      }
      if (!tripData.departure_datetime) {
        throw new Error("Departure datetime is required");
      }

      const response = await apiClient.post(this.BASE_URL, tripData);

      if (!response.data || typeof response.data.success !== "boolean") {
        throw new Error("Invalid response data");
      }

      return response.data;
    } catch (error) {
      this.handleError(error, "Create trip");
    }
  }

  // Update existing trip
  async updateTrip(
    tripId: string,
    tripData: Partial<CreateTripRequest>
  ): Promise<{
    success: boolean;
    message: string;
    trip: Trip;
  }> {
    try {
      if (!tripId?.trim()) {
        throw new Error("Trip ID is required");
      }
      if (!tripData) {
        throw new Error("Trip data is required");
      }

      const response = await apiClient.patch(
        `${this.BASE_URL}${tripId}/`,
        tripData
      );

      if (!response.data || typeof response.data.success !== "boolean") {
        throw new Error("Invalid response data");
      }

      return response.data;
    } catch (error) {
      this.handleError(error, "Update trip");
    }
  }

  // Delete a trip
  async deleteTrip(tripId: string): Promise<{
    success: boolean;
    message: string;
  }> {
    try {
      if (!tripId?.trim()) {
        throw new Error("Trip ID is required");
      }

      const response = await apiClient.delete(`${this.BASE_URL}${tripId}/`);

      if (response.status === 204) {
        return {
          success: true,
          message: "Trip deleted successfully",
        };
      }

      if (!response.data || typeof response.data.success !== "boolean") {
        throw new Error("Invalid response data");
      }

      return response.data;
    } catch (error) {
      this.handleError(error, "Delete trip");
    }
  }

  // Calculate route and HOS Compliance for trip
  async calculateRoute(
    tripId: string,
    options: TripCalculationRequest = {}
  ): Promise<TripCalculationResponse> {
    try {
      if (!tripId?.trim()) {
        throw new Error("Trip ID is required");
      }

      const response = await apiClient.post(
        `${this.BASE_URL}${tripId}/calculate_route/`,
        options
      );

      if (!response.data) {
        throw new Error("Invalid response data");
      }

      return response.data;
    } catch (error) {
      this.handleError(error, "Calculate route");
    }
  }

  // Optimize existing route
  async optimizeRoute(
    tripId: string,
    options: {
      optimize_breaks?: boolean;
      optimize_fuel_stops?: boolean;
      optimize_daily_resets?: boolean;
      max_optimization_distance?: number;
    } = {}
  ): Promise<RouteOptimizationResponse> {
    try {
      if (!tripId?.trim()) {
        throw new Error("Trip ID is required");
      }

      const response = await apiClient.post(
        `${this.BASE_URL}${tripId}/optimize_route/`,
        options
      );

      if (!response.data || typeof response.data.success !== "boolean") {
        throw new Error("Invalid response data");
      }

      return response.data;
    } catch (error) {
      this.handleError(error, "Optimize route");
    }
  }

  // Generate ELD logs for trip
  async generateELDLogs(
    tripId: string,
    options: ELDLogRequest = {}
  ): Promise<ELDLogResponse> {
    try {
      if (!tripId?.trim()) {
        throw new Error("Trip ID is required");
      }

      const response = await apiClient.post(
        `${this.BASE_URL}${tripId}/generate_eld_logs/`,
        options
      );

      if (!response.data || typeof response.data.success !== "boolean") {
        throw new Error("Invalid response data");
      }

      return response.data;
    } catch (error) {
      this.handleError(error, "Generate ELD logs");
    }
  }

  // Get compliance report for trip
  async getComplianceReport(tripId: string): Promise<{
    success: boolean;
    compliance_report: ComplianceReport;
  }> {
    try {
      if (!tripId?.trim()) {
        throw new Error("Trip ID is required");
      }

      const response = await apiClient.get(
        `${this.BASE_URL}${tripId}/compliance_report/`
      );

      if (!response.data || typeof response.data.success !== "boolean") {
        throw new Error("Invalid response data");
      }

      return response.data;
    } catch (error) {
      this.handleError(error, "Get compliance report");
    }
  }

  // Geocoding utilities
  async geocodeAddress(address: string): Promise<GeocodingResponse> {
    try {
      if (!address?.trim()) {
        throw new Error("Address is required for geocoding");
      }

      const response = await apiClient.post("/api/utils/geocode/", {
        address: address.trim(),
      });

      if (!response.data || typeof response.data.success !== "boolean") {
        throw new Error("Invalid response data");
      }

      return response.data;
    } catch (error) {
      this.handleError(error, "Geocode address");
    }
  }

  // Reverse geocoding
  async reverseGeocode(
    latitude: number,
    longitude: number
  ): Promise<ReverseGeocodingResponse> {
    try {
      if (typeof latitude !== "number" || typeof longitude !== "number") {
        throw new Error("Valid latitude and longitude are required");
      }

      if (latitude < -90 || latitude > 90) {
        throw new Error("Latitude must be between -90 and 90 degrees");
      }

      if (longitude < -180 || longitude > 180) {
        throw new Error("Longitude must be between -180 and 180 degrees");
      }

      const response = await apiClient.post("/api/utils/reverse_geocode/", {
        latitude,
        longitude,
      });

      if (!response.data || typeof response.data.success !== "boolean") {
        throw new Error("Invalid response data");
      }

      return response.data;
    } catch (error) {
      this.handleError(error, "Reverse geocode");
    }
  }

  // Test route calculation
  async testRouteCalculation(
    originLat: number,
    originLng: number,
    destLat: number,
    destLng: number
  ): Promise<TestRouteResponse> {
    try {
      // Validate coordinates
      const coords = [
        { name: "Origin latitude", value: originLat },
        { name: "Origin longitude", value: originLng },
        { name: "Destination latitude", value: destLat },
        { name: "Destination longitude", value: destLng },
      ];

      for (const coord of coords) {
        if (typeof coord.value !== "number" || isNaN(coord.value)) {
          throw new Error(`${coord.name} must be a valid number`);
        }
      }

      if (originLat < -90 || originLat > 90 || destLat < -90 || destLat > 90) {
        throw new Error("Latitude must be between -90 and 90 degrees");
      }

      if (
        originLng < -180 ||
        originLng > 180 ||
        destLng < -180 ||
        destLng > 180
      ) {
        throw new Error("Longitude must be between -180 and 180 degrees");
      }

      const response = await apiClient.post(
        "/api/utils/test_route_calculation/",
        {
          origin_latitude: originLat,
          origin_longitude: originLng,
          destination_latitude: destLat,
          destination_longitude: destLng,
        }
      );

      if (!response.data || typeof response.data.success !== "boolean") {
        throw new Error("Invalid response data");
      }

      return response.data;
    } catch (error) {
      this.handleError(error, "Test route calculation");
    }
  }

  async getCurrentDriverStatus(): Promise<CurrentDriverStatusResponse> {
    try {
      const response = await apiClient.get(
        `${this.BASE_URL}current_driver_status/`
      );

      if (!response.data || typeof response.data.success !== "boolean") {
        throw new Error("Invalid response data");
      }

      return response.data;
    } catch (error) {
      this.handleError(error, "Get current driver status");
    }
  }

  async completeTrip(tripId: string): Promise<TripCompletionResponse> {
    try {
      if (!tripId?.trim()) {
        throw new Error("Trip ID is required");
      }

      const response = await apiClient.post(
        `${this.BASE_URL}${tripId}/complete_trip/`
      );

      if (!response.data || typeof response.data.success !== "boolean") {
        throw new Error("Invalid response data");
      }

      return response.data;
    } catch (error) {
      this.handleError(error, "Complete trip");
    }
  }

  async updateDriverStatus(
    updateData: DriverStatusUpdateRequest
  ): Promise<DriverStatusUpdateResponse> {
    try {
      if (!updateData.current_duty_status) {
        throw new Error("Current duty status is required");
      }

      const response = await apiClient.patch(
        `${this.BASE_URL}update_driver_status/`,
        updateData
      );

      if (!response.data || typeof response.data.success !== "boolean") {
        throw new Error("Invalid response data");
      }

      return response.data;
    } catch (error) {
      this.handleError(error, "Update driver status");
    }
  }

  // Check API status
  async getAPIStatus(): Promise<APIStatusCheckResponse> {
    try {
      const response = await apiClient.get("/api/utils/api_status/");

      if (!response.data || typeof response.data.success !== "boolean") {
        throw new Error("Invalid response data");
      }

      return response.data;
    } catch (error) {
      this.handleError(error, "Get API status");
    }
  }
};

export const tripService = new TripService();