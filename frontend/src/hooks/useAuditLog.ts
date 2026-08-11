import { useQuery } from "@tanstack/react-query";

import { listAuditLog } from "../api/audit";

export function useAuditLog(actionPointId?: string) {
  return useQuery({
    queryKey: ["audit-log", actionPointId ?? "all"],
    queryFn: () => listAuditLog(actionPointId),
  });
}
