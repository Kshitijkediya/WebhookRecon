import type { AuditLog, StatusData } from "./types";

const BASE = "/reconcile";

export async function fetchStatus(): Promise<StatusData> {
  const res = await fetch(`${BASE}/status`);
  if (!res.ok) throw new Error("Failed to fetch status");
  return res.json();
}

export async function fetchAuditLogs(resolved?: boolean): Promise<AuditLog[]> {
  const params = resolved !== undefined ? `?resolved=${resolved}` : "";
  const res = await fetch(`${BASE}/audit-logs${params}&limit=50`);
  if (!res.ok) throw new Error("Failed to fetch audit logs");
  return res.json();
}

export async function triggerReconciliation(): Promise<{ task_id: string }> {
  const res = await fetch(`${BASE}/trigger`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to trigger reconciliation");
  return res.json();
}

export function createStatusStream(
  onData: (data: StatusData) => void,
  onError?: (err: Event) => void
): EventSource {
  const es = new EventSource(`${BASE}/stream`);
  es.onmessage = (e) => onData(JSON.parse(e.data) as StatusData);
  if (onError) es.onerror = onError;
  return es;
}
