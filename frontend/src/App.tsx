import { useEffect, useState } from "react";
import { createStatusStream, fetchAuditLogs } from "./api";
import AuditLogTable from "./components/AuditLogTable";
import ReconcileButton from "./components/ReconcileButton";
import StatCard from "./components/StatCard";
import type { AuditLog, EventState, StatusData } from "./types";

const STATE_CONFIG: { key: EventState; label: string; color: string }[] = [
  { key: "received", label: "Received", color: "text-blue-500" },
  { key: "processing", label: "Processing", color: "text-yellow-500" },
  { key: "reconciled", label: "Reconciled", color: "text-green-500" },
  { key: "failed", label: "Failed", color: "text-red-500" },
  { key: "skipped", label: "Skipped", color: "text-gray-400" },
];

const DEFAULT_STATUS: StatusData = {
  event_states: {
    received: 0,
    processing: 0,
    reconciled: 0,
    failed: 0,
    skipped: 0,
  },
  unresolved_mismatches: 0,
};

export default function App() {
  const [status, setStatus] = useState<StatusData>(DEFAULT_STATUS);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [logsLoading, setLogsLoading] = useState(true);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const es = createStatusStream(
      (data) => {
        setStatus(data);
        setConnected(true);
      },
      () => setConnected(false)
    );
    return () => es.close();
  }, []);

  useEffect(() => {
    fetchAuditLogs()
      .then(setLogs)
      .finally(() => setLogsLoading(false));

    const interval = setInterval(() => {
      fetchAuditLogs().then(setLogs);
    }, 15_000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold text-gray-900 tracking-tight">
            WebhookRecon
          </span>
          <span
            className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              connected
                ? "bg-green-50 text-green-700"
                : "bg-gray-100 text-gray-500"
            }`}
          >
            {connected ? "Live" : "Connecting..."}
          </span>
        </div>
        <ReconcileButton />
      </header>

      {/* Main content */}
      <main className="max-w-6xl mx-auto px-6 py-8 flex flex-col gap-8">
        {/* Stats */}
        <section>
          <h1 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
            Event States
          </h1>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            {STATE_CONFIG.map(({ key, label, color }) => (
              <StatCard
                key={key}
                label={label}
                value={status.event_states[key]}
                color={color}
              />
            ))}
            <StatCard
              label="Unresolved"
              value={status.unresolved_mismatches}
              color={
                status.unresolved_mismatches > 0
                  ? "text-red-500"
                  : "text-gray-400"
              }
            />
          </div>
        </section>

        {/* Audit log */}
        <section>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
            Reconciliation History
          </h2>
          <AuditLogTable logs={logs} loading={logsLoading} />
        </section>
      </main>
    </div>
  );
}
