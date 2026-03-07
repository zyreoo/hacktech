import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchOverview,
  fetchAodbOverview,
  fetchFlights,
  fetchFlight,
  fetchFlightUpdates,
  fetchAlerts,
  fetchRunways,
  fetchResources,
  fetchPassengerFlow,
  fetchInfrastructure,
  fetchServices,
  fetchIdentity,
  fetchRetail,
  fetchPredictions,
  fetchPredictionsForFlight,
  runPrediction,
} from "@/lib/api/endpoints";
import type { PredictRequest } from "@/types/api";

const STALE = 30_000; // 30 s

export const useOverview = () =>
  useQuery({ queryKey: ["overview"], queryFn: fetchOverview, staleTime: STALE, refetchInterval: 60_000 });

export const useAodbOverview = () =>
  useQuery({ queryKey: ["aodb-overview"], queryFn: fetchAodbOverview, staleTime: STALE });

export const useFlights = (params?: { skip?: number; limit?: number }) =>
  useQuery({ queryKey: ["flights", params], queryFn: () => fetchFlights(params), staleTime: STALE });

export const useFlight = (id: number) =>
  useQuery({ queryKey: ["flight", id], queryFn: () => fetchFlight(id), staleTime: STALE });

export const useFlightUpdates = (flightId: number) =>
  useQuery({ queryKey: ["flight-updates", flightId], queryFn: () => fetchFlightUpdates(flightId), staleTime: STALE });

export const useAlerts = (params?: { resolved?: boolean; limit?: number }) =>
  useQuery({ queryKey: ["alerts", params], queryFn: () => fetchAlerts(params), staleTime: STALE, refetchInterval: 30_000 });

export const useRunways = () =>
  useQuery({ queryKey: ["runways"], queryFn: fetchRunways, staleTime: STALE });

export const useResources = (params?: { limit?: number }) =>
  useQuery({ queryKey: ["resources", params], queryFn: () => fetchResources(params), staleTime: STALE });

export const usePassengerFlow = (params?: { limit?: number }) =>
  useQuery({ queryKey: ["passenger-flow", params], queryFn: () => fetchPassengerFlow(params), staleTime: STALE });

export const useInfrastructure = () =>
  useQuery({ queryKey: ["infrastructure"], queryFn: fetchInfrastructure, staleTime: STALE });

export const useServices = (params?: { limit?: number }) =>
  useQuery({ queryKey: ["services", params], queryFn: () => fetchServices(params), staleTime: STALE });

export const useIdentity = (params?: { limit?: number }) =>
  useQuery({ queryKey: ["identity", params], queryFn: () => fetchIdentity(params), staleTime: STALE });

export const useRetail = (params?: { limit?: number }) =>
  useQuery({ queryKey: ["retail", params], queryFn: () => fetchRetail(params), staleTime: STALE });

export const usePredictions = (params?: { skip?: number; limit?: number }) =>
  useQuery({ queryKey: ["predictions", params], queryFn: () => fetchPredictions(params), staleTime: STALE });

export const usePredictionsForFlight = (flightId: number) =>
  useQuery({ queryKey: ["predictions-flight", flightId], queryFn: () => fetchPredictionsForFlight(flightId), staleTime: STALE });

export const useRunPrediction = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: PredictRequest) => runPrediction(body),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["flight", variables.flight_id] });
      queryClient.invalidateQueries({ queryKey: ["predictions-flight", variables.flight_id] });
      queryClient.invalidateQueries({ queryKey: ["predictions"] });
    },
  });
};
