import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { eldService } from "../services/eldService";
import type {
  ELDDailyLog,
  ELDLogGenerationRequest,
  ELDLogCertificationRequest,
  ELDLogEditRequest,
  ELDExportRequest,
} from "../types";


// Query keys
export const ELD_QUERY_KEYS = {
  all: ["eld-logs"] as const,
  lists: () => [...ELD_QUERY_KEYS.all, "list"] as const,
  list: (filters: Record<string, unknown>) =>
    [...ELD_QUERY_KEYS.lists(), filters] as const,
  details: () => [...ELD_QUERY_KEYS.all, "details"] as const,
  detail: (id: string) => [...ELD_QUERY_KEYS.details(), id] as const,
  tripLogs: (tripId: string) =>
    [...ELD_QUERY_KEYS.all, "trip", tripId] as const,
  compliance: () => [...ELD_QUERY_KEYS.all, "compliance"] as const,
  complianceSummary: (filters: Record<string, unknown>) =>
    [...ELD_QUERY_KEYS.compliance(), filters] as const,
};


export function useTripELDLogs(tripId: string) {
    return useQuery({
        queryKey: ELD_QUERY_KEYS.tripLogs(tripId),
        queryFn: () => eldService.getTripELDLogs(tripId),
        enabled: !!tripId,
        staleTime: 5 * 60 * 1000,
    });
};

export function useELDLog(logId: string) {
  return useQuery({
    queryKey: ELD_QUERY_KEYS.detail(logId),
    queryFn: () => eldService.getELDLog(logId),
    enabled: !!logId,
    staleTime: 2 * 60 * 1000,
  });
};

export function useUserELDLogs(params?: {
  date_from?: string;
  date_to?: string;
  compliance?: 'compliant' | 'non_compliant';
  certified?: 'certified' | 'uncertified';
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: ELD_QUERY_KEYS.list(params || {}),
    queryFn: () => eldService.getUserELDLogs(params),
    staleTime: 2 * 60 * 1000,
  });
};

export function useComplianceSummary(params?: {
  date_from?: string;
  date_to?: string;
}) {
  return useQuery({
    queryKey: ELD_QUERY_KEYS.complianceSummary(params || {}),
    queryFn: () => eldService.getComplianceSummary(params),
    staleTime: 5 * 60 * 1000,
  });
};

export function useGenerateELDLogs() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ tripId, options }: { tripId: string; options: ELDLogGenerationRequest }) => eldService.generateELDLogs(tripId, options),

    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ELD_QUERY_KEYS.tripLogs(variables.tripId),
      });

      queryClient.invalidateQueries({
        queryKey: ELD_QUERY_KEYS.lists(),
      });

      queryClient.invalidateQueries({
        queryKey: ELD_QUERY_KEYS.compliance(),
      });
    },
  });
};

export function useCertifyELDLog() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ logId, request }: { logId: string; request: ELDLogCertificationRequest }) => eldService.certifyELDLog(logId, request),
    
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ELD_QUERY_KEYS.detail(variables.logId),
      });

      queryClient.invalidateQueries({
        queryKey: ELD_QUERY_KEYS.lists(),
      });

      queryClient.invalidateQueries({
        queryKey: ELD_QUERY_KEYS.compliance(),
      });
    }
  });
};

export function useEditELDLogEntry() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      logId,
      request,
    }: {
      logId: string;
      request: ELDLogEditRequest;
    }) => eldService.editELDLogEntry(logId, request),
    onSuccess: (_, variables) => {
      // Invalidate the specific log
      queryClient.invalidateQueries({
        queryKey: ELD_QUERY_KEYS.detail(variables.logId),
      });

      // Invalidate lists to update edit counts
      queryClient.invalidateQueries({
        queryKey: ELD_QUERY_KEYS.lists(),
      });
    },
  });
};

export function useExportELDLog() {
  return useMutation({
    mutationFn: ({
      logId,
      request,
    }: {
      logId: string;
      request: ELDExportRequest;
    }) => eldService.exportELDLog(logId, request),
  });
}

export function useExportTripELDLogs() {
  return useMutation({
    mutationFn: ({
      tripId,
      request,
    }: {
      tripId: string;
      request: ELDExportRequest;
    }) => eldService.exportTripELDLogs(tripId, request),
  });
}

export function useDeleteELDLog() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (logId: string) => eldService.deleteELDLog(logId),
    onSuccess: (_, logId) => {
      queryClient.removeQueries({
        queryKey: ELD_QUERY_KEYS.detail(logId),
      });

      queryClient.invalidateQueries({
        queryKey: ELD_QUERY_KEYS.lists(),
      });

      queryClient.invalidateQueries({
        queryKey: ELD_QUERY_KEYS.compliance(),
      });
    },
  });
}

export function useUpdateELDLog() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      logId,
      updates,
    }: {
      logId: string;
      updates: Partial<ELDDailyLog>;
    }) => eldService.updateELDLog(logId, updates),
    onSuccess: (data, variables) => {
      // Update the specific log in cache
      queryClient.setQueryData(ELD_QUERY_KEYS.detail(variables.logId), data);

      queryClient.invalidateQueries({
        queryKey: ELD_QUERY_KEYS.lists(),
      });
    },
  });
}

