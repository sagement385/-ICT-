import { useMutation, useQuery } from "@tanstack/react-query";
import { ApiError } from "../api/client";
import { getNearbyHospitals } from "../api/hospitals";
import {
  assistPatientText,
  createPatient,
  geocodeAddress,
  type CreatePatientEvent,
} from "../api/patients";
import { getLatestRecommendation, runRecommendation } from "../api/recommendations";
import { getHospitalRoutes, getRoutingStatus } from "../api/routing";
import { getDataSources, getSystemStatus } from "../api/status";

function retryRequest(failureCount: number, error: Error): boolean {
  if (error instanceof ApiError && error.status !== null && error.status < 500) return false;
  return failureCount < 2;
}

export function useCreatePatient() {
  return useMutation({
    mutationFn: (event: CreatePatientEvent) => createPatient(event),
  });
}

export function useAssistPatient() {
  return useMutation({
    mutationFn: (text: string) => assistPatientText(text),
  });
}

export function useGeocodeAddress() {
  return useMutation({
    mutationFn: (address: string) => geocodeAddress(address),
  });
}

export function useNearbyHospitals(incidentId: string | null) {
  return useQuery({
    queryKey: ["nearby-hospitals", incidentId],
    queryFn: ({ signal }) => getNearbyHospitals(incidentId ?? "", 10, signal),
    enabled: Boolean(incidentId),
    staleTime: 10_000,
    refetchInterval: incidentId ? 20_000 : false,
    retry: retryRequest,
  });
}

export function useHospitalRoutes(
  incidentId: string | null,
  hospitalIds: string[],
) {
  return useQuery({
    queryKey: ["hospital-routes", incidentId, hospitalIds],
    queryFn: ({ signal }) => getHospitalRoutes(incidentId ?? "", hospitalIds, signal),
    enabled: Boolean(incidentId) && hospitalIds.length > 0,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    retry: retryRequest,
  });
}

export function useRunRecommendation() {
  return useMutation({
    mutationFn: ({ incidentId, limit = 3 }: { incidentId: string; limit?: number }) => (
      runRecommendation(incidentId, limit)
    ),
  });
}

export function useLatestRecommendation(incidentId: string | null, enabled = false) {
  return useQuery({
    queryKey: ["latest-recommendation", incidentId],
    queryFn: ({ signal }) => getLatestRecommendation(incidentId ?? "", signal),
    enabled: Boolean(incidentId) && enabled,
    staleTime: 10_000,
    retry: retryRequest,
  });
}

export function useRoutingStatus() {
  return useQuery({
    queryKey: ["routing-status"],
    queryFn: ({ signal }) => getRoutingStatus(signal),
    refetchInterval: 30_000,
    staleTime: 10_000,
    retry: retryRequest,
  });
}

export function useSystemStatus() {
  return useQuery({
    queryKey: ["system-status"],
    queryFn: ({ signal }) => getSystemStatus(signal),
    refetchInterval: 10_000,
    staleTime: 5_000,
    retry: retryRequest,
  });
}

export function useDataSources() {
  return useQuery({
    queryKey: ["data-sources"],
    queryFn: ({ signal }) => getDataSources(signal),
    refetchInterval: 30_000,
    staleTime: 10_000,
    retry: retryRequest,
  });
}
