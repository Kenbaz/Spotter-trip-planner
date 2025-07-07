import { apiClient } from "./apiClient";
import type {
    ELDDailyLog,
    ELDLogGenerationRequest,
    ELDLogGenerationResponse,
    ELDLogCertificationRequest,
    ELDLogEditRequest,
    ELDExportRequest,
    ELDExportResponse,
    ELDComplianceSummary,
    TripELDLogsResponse,
    ELDLogsPaginatedResponse
} from "../types";


interface APIErrorResponse {
    error?: string;
    detail?: string;
    message?: string;
    [key: string]: unknown;
}

interface AxiosErrorResponse {
    response?: {
        status: number;
        data?: APIErrorResponse;
    };
    message: string;
}

export class ELDServiceError extends Error {
    public statusCode?: number;
    public code?: string;
    public details?: Record<string, unknown>;

    constructor(
        message: string,
        statusCode?: number,
        code?: string,
        details?: Record<string, unknown>
    ) {
        super(message);
        this.name = "ELDServiceError";
        this.statusCode = statusCode;
        this.code = code;
        this.details = details;
    }
};


class ELDService {
  async generateELDLogs(
    tripId: string,
    options: ELDLogGenerationRequest
  ): Promise<ELDLogGenerationResponse> {
    try {
      const response = await apiClient.post(
        `/api/trips/${tripId}/generate_eld_logs/`,
        options
      );
      return response.data;
    } catch (error) {
      console.error("Failed to generate ELD logs:", error);

      const axiosError = error as AxiosErrorResponse;

      if (axiosError.response?.status === 403) {
        throw new ELDServiceError(
          "You do not have permission to generate ELD logs for this trip",
          403,
          "PERMISSION_DENIED"
        );
      }

      if (axiosError.response?.status === 404) {
        throw new ELDServiceError("Trip not found", 404, "TRIP_NOT_FOUND");
      }

      if (axiosError.response?.data?.error) {
        throw new ELDServiceError(
          axiosError.response.data.error,
          axiosError.response.status,
          "API_ERROR",
          axiosError.response.data
        );
      }

      throw new ELDServiceError(
        "Failed to generate ELD logs. Please try again.",
        axiosError.response?.status || 500,
        "GENERATION_FAILED"
      );
    }
  }

  async getTripELDLogs(tripId: string): Promise<TripELDLogsResponse> {
    try {
      const response = await apiClient.get(`/api/trips/${tripId}/eld_logs/`);
      return response.data;
    } catch (error) {
      console.error("Failed to fetch trip ELD logs:", error);

      const axiosError = error as AxiosErrorResponse;

      if (axiosError.response?.status === 403) {
        throw new ELDServiceError(
          "You do not have permission to view ELD logs for this trip",
          403,
          "PERMISSION_DENIED"
        );
      }

      if (axiosError.response?.status === 404) {
        throw new ELDServiceError(
          "No ELD logs found for this trip",
          404,
          "NO_LOGS_FOUND"
        );
      }

      throw new ELDServiceError(
        "Failed to fetch trip ELD logs. Please try again.",
        axiosError.response?.status || 500,
        "FETCH_FAILED"
      );
    }
  }

  async getELDLog(logId: string): Promise<ELDDailyLog> {
    try {
      const response = await apiClient.get(`/eld-logs/${logId}/`);
      return response.data;
    } catch (error) {
      console.error("Failed to get ELD log:", error);

      const axiosError = error as AxiosErrorResponse;

      if (axiosError.response?.status === 403) {
        throw new ELDServiceError(
          "You do not have permission to view this ELD log",
          403,
          "PERMISSION_DENIED"
        );
      }

      if (axiosError.response?.status === 404) {
        throw new ELDServiceError("ELD log not found", 404, "LOG_NOT_FOUND");
      }

      throw new ELDServiceError(
        "Failed to retrieve ELD log. Please try again.",
        axiosError.response?.status || 500,
        "RETRIEVAL_FAILED"
      );
    }
  };
  
    async getUserELDLogs(params?: {
        date_from?: string;
        date_to?: string;
        compliance?: 'compliant' | 'non_compliant';
        certified?: 'certified' | 'uncertified';
        page?: number;
        page_size?: number;
    }): Promise<ELDLogsPaginatedResponse> { 
        try {
          const response = await apiClient.get("/eld-logs/", { params });
          return response.data;
        } catch (error) {
          console.error("Failed to get my ELD logs:", error);

          const axiosError = error as AxiosErrorResponse;

          if (axiosError.response?.status === 403) {
            throw new ELDServiceError(
              "You do not have permission to view ELD logs",
              403,
              "PERMISSION_DENIED"
            );
          }

          throw new ELDServiceError(
            "Failed to retrieve your ELD logs. Please try again.",
            axiosError.response?.status || 500,
            "RETRIEVAL_FAILED"
          );
        }
    };

    async certifyELDLog(
        logId: string,
        request: ELDLogCertificationRequest
    ): Promise<{
        success: boolean;
        message: string;
        certified_at: string;
        log_id: string;
    }> {
        try {
          const response = await apiClient.post(
            `/eld-logs/${logId}/certify_log/`,
            request
          );
          return response.data;
        } catch (error) {
          console.error("Failed to certify ELD log:", error);

          const axiosError = error as AxiosErrorResponse;

          if (axiosError.response?.status === 403) {
            throw new ELDServiceError(
              "You can only certify your own ELD logs",
              403,
              "PERMISSION_DENIED"
            );
          }

          if (axiosError.response?.status === 400) {
            const errorMsg =
              axiosError.response.data?.error || "This log cannot be certified";
            throw new ELDServiceError(errorMsg, 400, "CERTIFICATION_INVALID");
          }

          if (axiosError.response?.status === 404) {
            throw new ELDServiceError(
              "ELD log not found",
              404,
              "LOG_NOT_FOUND"
            );
          }

          throw new ELDServiceError(
            "Failed to certify ELD log. Please try again.",
            axiosError.response?.status || 500,
            "CERTIFICATION_FAILED"
          );
        }
    };

    async editELDLogEntry(
        logId: string,
        request: ELDLogEditRequest
    ): Promise<{
        success: boolean;
        message: string;
        log_entry_id: number;
        field_updated: string;
        new_value: string;
    }> {
        try {
          const response = await apiClient.post(
            `/eld-logs/${logId}/edit_log_entry/`,
            request
          );
          return response.data;
        } catch (error) {
          console.error("Failed to edit ELD log entry:", error);

          const axiosError = error as AxiosErrorResponse;

          if (axiosError.response?.status === 403) {
            const errorMsg =
              axiosError.response.data?.error ||
              "You can only edit your own uncertified ELD logs";
            throw new ELDServiceError(errorMsg, 403, "PERMISSION_DENIED");
          }

          if (axiosError.response?.status === 400) {
            const errorMsg =
              axiosError.response.data?.error || "Invalid edit request";
            throw new ELDServiceError(errorMsg, 400, "EDIT_INVALID");
          }

          if (axiosError.response?.status === 404) {
            throw new ELDServiceError(
              "ELD log or log entry not found",
              404,
              "NOT_FOUND"
            );
          }

          throw new ELDServiceError(
            "Failed to edit ELD log entry. Please try again.",
            axiosError.response?.status || 500,
            "EDIT_FAILED"
          );
        }
    };

    async exportELDLog(
        logId: string,
        request: ELDExportRequest
    ): Promise<ELDExportResponse> { 
        try {
          const response = await apiClient.post(
            `/eld-logs/${logId}/export_log/`,
            request
          );
          return response.data;
        } catch (error) {
          console.error("Failed to export ELD log:", error);

          const axiosError = error as AxiosErrorResponse;

          if (axiosError.response?.status === 403) {
            throw new ELDServiceError(
              "You can only export your own ELD logs",
              403,
              "PERMISSION_DENIED"
            );
          }

          if (axiosError.response?.status === 404) {
            throw new ELDServiceError(
              "ELD log not found",
              404,
              "LOG_NOT_FOUND"
            );
          }

          throw new ELDServiceError(
            "Failed to export ELD log. Please try again.",
            axiosError.response?.status || 500,
            "EXPORT_FAILED"
          );
        }
    };

    async exportTripELDLogs(
        tripId: string,
        request: ELDExportRequest
    ): Promise<ELDExportResponse> { 
        try {
          const response = await apiClient.post(
            `/api/trips/${tripId}/export_trip_eld_logs/`,
            request
          );
          return response.data;
        } catch (error) {
          console.error("Failed to export trip ELD logs:", error);

          const axiosError = error as AxiosErrorResponse;

          if (axiosError.response?.status === 403) {
            throw new ELDServiceError(
              "You can only export ELD logs for your own trips",
              403,
              "PERMISSION_DENIED"
            );
          }

          if (axiosError.response?.status === 404) {
            throw new ELDServiceError(
              "No ELD logs found for this trip",
              404,
              "LOGS_NOT_FOUND"
            );
          }

          throw new ELDServiceError(
            "Failed to export trip ELD logs. Please try again.",
            axiosError.response?.status || 500,
            "EXPORT_FAILED"
          );
        }
    };

    async getComplianceSummary(params?: {
        date_from?: string;
        date_to?: string;
    }): Promise<ELDComplianceSummary> { 
        try {
          const response = await apiClient.get(
            "/eld-logs/compliance_summary/",
            { params }
          );
          return response.data;
        } catch (error) {
          console.error("Failed to get compliance summary:", error);

          const axiosError = error as AxiosErrorResponse;

          if (axiosError.response?.status === 403) {
            throw new ELDServiceError(
              "You do not have permission to view compliance summary",
              403,
              "PERMISSION_DENIED"
            );
          }

          throw new ELDServiceError(
            "Failed to retrieve compliance summary. Please try again.",
            axiosError.response?.status || 500,
            "SUMMARY_FAILED"
          );
        }
    };

    async deleteELDLog(logId: string): Promise<void> {
        try {
          await apiClient.delete(`/eld-logs/${logId}/`);
        } catch (error) {
          console.error("Failed to delete ELD log:", error);

          const axiosError = error as AxiosErrorResponse;

          if (axiosError.response?.status === 403) {
            const errorMsg =
              axiosError.response.data?.error ||
              "You can only delete your own uncertified ELD logs";
            throw new ELDServiceError(errorMsg, 403, "PERMISSION_DENIED");
          }

          if (axiosError.response?.status === 404) {
            throw new ELDServiceError(
              "ELD log not found",
              404,
              "LOG_NOT_FOUND"
            );
          }

          throw new ELDServiceError(
            "Failed to delete ELD log. Please try again.",
            axiosError.response?.status || 500,
            "DELETE_FAILED"
          );
        }
    };

    async updateELDLog(
        logId: string,
        updates: Partial<ELDDailyLog>
    ): Promise<ELDDailyLog> { 
        try {
          const response = await apiClient.put(`/eld-logs/${logId}/`, updates);
          return response.data;
        } catch (error) {
          console.error("Failed to update ELD log:", error);

          const axiosError = error as AxiosErrorResponse;

          if (axiosError.response?.status === 403) {
            throw new ELDServiceError(
              "You can only update your own uncertified ELD logs",
              403,
              "PERMISSION_DENIED"
            );
          }

          if (axiosError.response?.status === 404) {
            throw new ELDServiceError(
              "ELD log not found",
              404,
              "LOG_NOT_FOUND"
            );
          }

          if (axiosError.response?.status === 400) {
            throw new ELDServiceError(
              "Invalid update data provided",
              400,
              "UPDATE_INVALID",
              axiosError.response.data
            );
          }

          throw new ELDServiceError(
            "Failed to update ELD log. Please try again.",
            axiosError.response?.status || 500,
            "UPDATE_FAILED"
          );
        }
    };
};

export const eldService = new ELDService();