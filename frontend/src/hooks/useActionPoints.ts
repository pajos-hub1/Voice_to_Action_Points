import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  approveActionPoint,
  createActionPoint,
  executeActionPoint,
  getActionPoint,
  listActionPoints,
  rejectActionPoint,
} from "../api/actionPoints";
import type { ActionPointStatus } from "../api/types";

const actionPointsKey = (statusFilter?: ActionPointStatus) => ["action-points", statusFilter ?? "all"];
const actionPointKey = (id: string) => ["action-points", id];

export function useActionPoints(statusFilter?: ActionPointStatus) {
  return useQuery({
    queryKey: actionPointsKey(statusFilter),
    queryFn: () => listActionPoints(statusFilter),
  });
}

export function useActionPoint(id: string) {
  return useQuery({
    queryKey: actionPointKey(id),
    queryFn: () => getActionPoint(id),
    enabled: Boolean(id),
  });
}

export function useCreateActionPoint() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ transcript, confidence }: { transcript: string; confidence: number }) =>
      createActionPoint(transcript, confidence),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["action-points"] }),
  });
}

export function useApproveActionPoint() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, approver }: { id: string; approver: string }) => approveActionPoint(id, approver),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["action-points"] });
      queryClient.invalidateQueries({ queryKey: actionPointKey(id) });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}

export function useRejectActionPoint() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, approver, reason }: { id: string; approver: string; reason?: string }) =>
      rejectActionPoint(id, approver, reason),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["action-points"] });
      queryClient.invalidateQueries({ queryKey: actionPointKey(id) });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}

export function useExecuteActionPoint() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => executeActionPoint(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ["action-points"] });
      queryClient.invalidateQueries({ queryKey: actionPointKey(id) });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}
