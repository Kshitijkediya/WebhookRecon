export type EventState =
  | "received"
  | "processing"
  | "reconciled"
  | "failed"
  | "skipped";

export type MismatchType =
  | "missed_event"
  | "duplicate_event"
  | "state_mismatch";

export interface StatusData {
  event_states: Record<EventState, number>;
  unresolved_mismatches: number;
}

export interface AuditLog {
  id: string;
  event_id: string | null;
  mismatch_type: MismatchType | null;
  action_taken: string;
  details: string | null;
  resolved: boolean;
  created_at: string;
}
