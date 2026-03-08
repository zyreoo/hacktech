import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchOverview,
  fetchAodbOverview,
  fetchFlights,
  fetchFlight,
  fetchFlightUpdates,
  fetchFlightIssues,
  fetchAlerts,
  fetchAlertIssues,
  fetchRunways,
  fetchRunwayIssues,
  fetchResources,
  fetchResourceIssues,
  fetchPassengerFlow,
  fetchPassengerFlowIssues,
  fetchInfrastructure,
  fetchInfrastructureIssues,
  fetchServices,
  fetchServiceIssues,
  fetchIdentity,
  fetchRetail,
  fetchPredictions,
  fetchPredictionIssues,
  fetchPredictionsForFlight,
  runPrediction,
  resolveAlert,
  updateResourceStatus,
  updateInfrastructureStatus,
  updateRunwayStatus,
  updateRunwayHazard,
  reassignFlight,
} from "@/lib/api/endpoints";
import type { PredictRequest } from "@/types/api";

const STALE = 1_000; // 1 s for very responsive feel

export const useOverview = () =>
  useQuery({
    queryKey: ["overview"],
    queryFn: fetchOverview,
    staleTime: STALE,
    refetchInterval: 1_000, // Very fast refresh for maximum visibility
  });

export const useAodbOverview = () =>
  useQuery({ queryKey: ["aodb-overview"], queryFn: fetchAodbOverview, staleTime: STALE });

export const useFlights = (params?: { skip?: number; limit?: number }) =>
  useQuery({
    queryKey: ["flights", params],
    queryFn: () => fetchFlights(params),
    staleTime: STALE,
    refetchInterval: 2_000,
  });

export const useFlightIssues = (params?: { limit?: number }) =>
  useQuery({
    queryKey: ["flights", "issues", params],
    queryFn: () => fetchFlightIssues(params),
    staleTime: STALE,
    refetchInterval: 2_000,
  });

export const useFlight = (id: number) =>
  useQuery({ queryKey: ["flight", id], queryFn: () => fetchFlight(id), staleTime: STALE });

export const useFlightUpdates = (flightId: number) =>
  useQuery({ queryKey: ["flight-updates", flightId], queryFn: () => fetchFlightUpdates(flightId), staleTime: STALE });

export const useAlerts = (params?: { resolved?: boolean; limit?: number }) =>
  useQuery({
    queryKey: ["alerts", params],
    queryFn: () => fetchAlerts(params),
    staleTime: STALE,
    refetchInterval: 2_000,
  });

export const useAlertIssues = (params?: { limit?: number }) =>
  useQuery({
    queryKey: ["alerts", "issues", params],
    queryFn: () => fetchAlertIssues(params),
    staleTime: STALE,
    refetchInterval: 2_000,
  });

export const useRunways = () =>
  useQuery({
    queryKey: ["runways"],
    queryFn: fetchRunways,
    staleTime: STALE,
    refetchInterval: 2_000,
  });

export const useRunwayIssues = () =>
  useQuery({
    queryKey: ["runways", "issues"],
    queryFn: fetchRunwayIssues,
    staleTime: STALE,
    refetchInterval: 2_000,
  });

export const useResources = (params?: { limit?: number }) =>
  useQuery({
    queryKey: ["resources", params],
    queryFn: () => fetchResources(params),
    staleTime: STALE,
    refetchInterval: 2_000,
  });

export const useResourceIssues = () =>
  useQuery({
    queryKey: ["resources", "issues"],
    queryFn: fetchResourceIssues,
    staleTime: STALE,
    refetchInterval: 2_000,
  });

export const usePassengerFlow = (params?: { limit?: number }) =>
  useQuery({ 
    queryKey: ["passenger-flow", params], 
    queryFn: () => fetchPassengerFlow(params), 
    staleTime: STALE,
    refetchInterval: 2_000,
  });

export const usePassengerFlowIssues = (params?: { limit?: number }) =>
  useQuery({
    queryKey: ["passenger-flow", "issues", params],
    queryFn: () => fetchPassengerFlowIssues(params),
    staleTime: STALE,
    refetchInterval: 2_000,
  });

export const useInfrastructure = () =>
  useQuery({ queryKey: ["infrastructure"], queryFn: fetchInfrastructure, staleTime: STALE, refetchInterval: 2_000 });

export const useInfrastructureIssues = () =>
  useQuery({
    queryKey: ["infrastructure", "issues"],
    queryFn: fetchInfrastructureIssues,
    staleTime: STALE,
    refetchInterval: 2_000,
  });

export const useUpdateInfrastructureStatus = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status, tamper_detected, network_health }: { id: number; status?: string; tamper_detected?: boolean; network_health?: number }) =>
      updateInfrastructureStatus(id, { status, tamper_detected, network_health }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["infrastructure"] });
      queryClient.invalidateQueries({ queryKey: ["infrastructure", "issues"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
    },
  });
};

export const useServices = (params?: { limit?: number }) =>
  useQuery({ queryKey: ["services", params], queryFn: () => fetchServices(params), staleTime: STALE });

export const useServiceIssues = (params?: { limit?: number }) =>
  useQuery({
    queryKey: ["services", "issues", params],
    queryFn: () => fetchServiceIssues(params),
    staleTime: STALE,
    refetchInterval: 2_000,
  });

export const useIdentity = (params?: { limit?: number }) =>
  useQuery({ queryKey: ["identity", params], queryFn: () => fetchIdentity(params), staleTime: STALE });

export const useRetail = (params?: { limit?: number }) =>
  useQuery({ queryKey: ["retail", params], queryFn: () => fetchRetail(params), staleTime: STALE });

export const usePredictions = (params?: { skip?: number; limit?: number }) =>
  useQuery({
    queryKey: ["predictions", params],
    queryFn: () => fetchPredictions(params),
    staleTime: STALE,
    refetchInterval: 2_000,
  });

export const usePredictionIssues = (params?: { limit?: number }) =>
  useQuery({
    queryKey: ["predictions", "issues", params],
    queryFn: () => fetchPredictionIssues(params),
    staleTime: STALE,
    refetchInterval: 2_000,
  });

export const usePredictionsForFlight = (flightId: number) =>
  useQuery({ queryKey: ["predictions-flight", flightId], queryFn: () => fetchPredictionsForFlight(flightId), staleTime: STALE });

export const useResolveAlert = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, resolved = true }: { id: number; resolved?: boolean }) => resolveAlert(id, resolved),
    onSuccess: async () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["alerts", "issues"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      queryClient.invalidateQueries({ queryKey: ["aodb-overview"] });
      await queryClient.refetchQueries({ queryKey: ["overview"] });
    },
  });
};

export const useUpdateResourceStatus = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status, assigned_to }: { id: number; status: string; assigned_to?: string | null }) =>
      updateResourceStatus(id, status, assigned_to),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resources"] });
      queryClient.invalidateQueries({ queryKey: ["resources", "issues"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      queryClient.invalidateQueries({ queryKey: ["aodb-overview"] });
    },
  });
};

export const useUpdateRunwayStatus = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) => updateRunwayStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["runways"] });
      queryClient.invalidateQueries({ queryKey: ["runways", "issues"] });
    },
  });
};

export const useUpdateRunwayHazard = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, hazard_detected, hazard_type }: { id: number; hazard_detected: boolean; hazard_type?: string | null }) =>
      updateRunwayHazard(id, hazard_detected, hazard_type),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["runways"] });
      queryClient.invalidateQueries({ queryKey: ["runways", "issues"] });
    },
  });
};

export const useReassignFlight = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, runway_id, gate, reconciled_gate }: { id: number; runway_id?: number; gate?: string; reconciled_gate?: string }) =>
      reassignFlight(id, { runway_id, gate, reconciled_gate }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["flights"] });
      queryClient.invalidateQueries({ queryKey: ["flights", "issues"] });
      queryClient.invalidateQueries({ queryKey: ["aodb-overview"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      queryClient.invalidateQueries({ queryKey: ["resources"] });
      queryClient.invalidateQueries({ queryKey: ["resources", "issues"] });
    },
  });
};

export const useRunPrediction = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: PredictRequest) => runPrediction(body),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["flight", variables.flight_id] });
      queryClient.invalidateQueries({ queryKey: ["predictions-flight", variables.flight_id] });
      queryClient.invalidateQueries({ queryKey: ["predictions"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      queryClient.invalidateQueries({ queryKey: ["aodb-overview"] });
    },
  });
};
