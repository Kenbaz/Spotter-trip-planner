import { useState, useCallback } from 'react';
import { useGenerateELDLogs } from './useTripQueries';
import type { ELDLogRequest, ELDLogResponse } from '../types';


interface ELDLogState {
    eldData: ELDLogResponse | null;
    isLoading: boolean;
    error: string | null;
}

interface UseELDLogsOptions {
    onSuccess?: (data: ELDLogResponse) => void;
    onError?: (error: string) => void;
}

export function useELDLogs(tripId: string, options: UseELDLogsOptions = {}) {
    const [state, setState] = useState<ELDLogState>({
        eldData: null,
        isLoading: false,
        error: null,
    });

    const generateELDMutation = useGenerateELDLogs();

    const generateLogs = useCallback(
        async (requestOptions: ELDLogRequest = {}) => {
            if (!tripId) { 
                setState(prev => ({
                    ...prev,
                    error: 'Trip ID is required to generate ELD logs',
                }));
                return;
            }

            setState(prev => ({
                ...prev,
                isLoading: true,
                error: null,
            }));

            try {
                const result = await generateELDMutation.mutateAsync({
                    tripId,
                    options: requestOptions,
                });

                if (result.success) {
                    setState({
                        eldData: result,
                        isLoading: false,
                        error: null,
                    });
                    options.onSuccess?.(result);
                } else {
                    const errorMessage = result.error || 'Failed to generate ELD logs';
                    setState({
                        eldData: null,
                        isLoading: false,
                        error: errorMessage,
                    });
                    options.onError?.(errorMessage);
                }

                return result;
            } catch (error) { 
                const errorMessage = error instanceof Error ? error.message : 'ELD log generation failed';
                setState({
                    eldData: null,
                    isLoading: false,
                    error: errorMessage,
                });
                options.onError?.(errorMessage);
                throw error;
            }
        },
        [tripId, generateELDMutation, options]
    );


    const downloadPDF = useCallback(
        async () => {
            return generateLogs({
                export_format: 'pdf_data',
                include_validation: true,
            });
        },
        [generateLogs]
    );

    const clearError = useCallback(() => {
      setState((prev) => ({
        ...prev,
        error: null,
      }));
    }, []);

    const reset = useCallback(() => {
      setState({
        eldData: null,
        isLoading: false,
        error: null,
      });
    }, []);

    return {
        eldData: state.eldData,
        isLoading: state.isLoading,
        error: state.error,

        generateLogs,
        downloadPDF,
        clearError,
        reset,

        mutation: generateELDMutation,
    };
}