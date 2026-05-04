import type { AuditLog } from "../types";

const MISMATCH_LABELS: Record<string, string> = {
  missed_event: "Missed Event",
  duplicate_event: "Duplicate",
  state_mismatch: "State Mismatch",
};

interface AuditLogTableProps {
  logs: AuditLog[];
  loading: boolean;
}

export default function AuditLogTable({ logs, loading }: AuditLogTableProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <h2 className="font-semibold text-gray-700 text-sm">Audit Log</h2>
        <span className="text-xs text-gray-400">Latest 50 entries</span>
      </div>

      {loading ? (
        <div className="p-8 text-center text-gray-400 text-sm">Loading...</div>
      ) : logs.length === 0 ? (
        <div className="p-8 text-center text-gray-400 text-sm">
          No audit entries yet.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
              <tr>
                <th className="px-5 py-3 text-left font-medium">Time</th>
                <th className="px-5 py-3 text-left font-medium">Mismatch Type</th>
                <th className="px-5 py-3 text-left font-medium">Action Taken</th>
                <th className="px-5 py-3 text-left font-medium">Details</th>
                <th className="px-5 py-3 text-left font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-5 py-3 text-gray-500 whitespace-nowrap">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                  <td className="px-5 py-3 text-gray-700">
                    {log.mismatch_type
                      ? MISMATCH_LABELS[log.mismatch_type] ?? log.mismatch_type
                      : "—"}
                  </td>
                  <td className="px-5 py-3 font-mono text-xs text-gray-600">
                    {log.action_taken}
                  </td>
                  <td className="px-5 py-3 text-gray-500 max-w-xs truncate">
                    {log.details ?? "—"}
                  </td>
                  <td className="px-5 py-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        log.resolved
                          ? "bg-green-50 text-green-700"
                          : "bg-red-50 text-red-700"
                      }`}
                    >
                      {log.resolved ? "Resolved" : "Open"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
