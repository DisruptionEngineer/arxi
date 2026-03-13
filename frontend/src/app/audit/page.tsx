"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/auth-context";
import type { AuditLogEntry, AuditLogParams } from "@/lib/types";
import { fetchAuditLogs } from "@/lib/api";

const ACTION_OPTIONS = [
  { label: "All Actions", value: "" },
  { label: "Create", value: "prescription.create" },
  { label: "Validate", value: "prescription.validate" },
  { label: "Submit for Review", value: "prescription.submit_for_review" },
  { label: "Approve", value: "prescription.approve" },
  { label: "Reject", value: "prescription.reject" },
];

const ACTION_COLORS: Record<string, string> = {
  "prescription.create": "bg-blue-900/40 text-blue-300",
  "prescription.validate": "bg-gray-700/40 text-gray-300",
  "prescription.submit_for_review": "bg-yellow-900/40 text-yellow-300",
  "prescription.approve": "bg-green-900/40 text-green-300",
  "prescription.reject": "bg-red-900/40 text-red-300",
};

const PAGE_SIZE = 20;

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

function formatAction(action: string): string {
  const parts = action.split(".");
  return parts[parts.length - 1].replace(/_/g, " ");
}

function ChangeSummary({ changes }: { changes: AuditLogEntry["changes"] }) {
  if (changes.length === 0) return <span className="text-gray-600">&mdash;</span>;
  return (
    <span className="text-xs">
      {changes.map((c, i) => (
        <span key={c.field}>
          {i > 0 && ", "}
          <span className="text-gray-400">{c.field}:</span>{" "}
          <span className="text-red-400">{c.from_value ?? "null"}</span>
          {" \u2192 "}
          <span className="text-green-400">{c.to_value ?? "null"}</span>
        </span>
      ))}
    </span>
  );
}

export default function AuditPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [action, setAction] = useState("");
  const [actorId, setActorId] = useState("");
  const [resourceId, setResourceId] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [search, setSearch] = useState("");

  // Redirect non-admins
  useEffect(() => {
    if (!authLoading && (!user || user.role !== "admin")) {
      router.push("/");
    }
  }, [user, authLoading, router]);

  const doFetch = (newOffset: number) => {
    setLoading(true);
    setError(null);
    const params: AuditLogParams = { limit: PAGE_SIZE, offset: newOffset };
    if (action) params.action = action;
    if (actorId) params.actor_id = actorId;
    if (resourceId) params.resource_id = resourceId;
    if (fromDate) params.from_date = new Date(fromDate).toISOString();
    if (toDate) params.to_date = new Date(toDate).toISOString();
    if (search) params.search = search;

    fetchAuditLogs(params)
      .then((data) => {
        setLogs(data.logs);
        setTotal(data.total);
        setOffset(newOffset);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (user?.role === "admin") doFetch(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const handleApply = () => doFetch(0);

  if (authLoading || !user || user.role !== "admin") return null;

  return (
    <div>
      <h1 className="text-xl font-semibold mb-4">Audit Trail</h1>

      {/* Filter Bar */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2 mb-4">
        <select
          value={action}
          onChange={(e) => setAction(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-300"
        >
          {ACTION_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <input
          placeholder="Actor ID"
          value={actorId}
          onChange={(e) => setActorId(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-300 placeholder-gray-600"
        />
        <input
          placeholder="Resource ID"
          value={resourceId}
          onChange={(e) => setResourceId(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-300 placeholder-gray-600"
        />
        <input
          type="date"
          value={fromDate}
          onChange={(e) => setFromDate(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-300"
        />
        <input
          type="date"
          value={toDate}
          onChange={(e) => setToDate(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-300"
        />
        <div className="flex gap-2">
          <input
            placeholder="Search..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-300 placeholder-gray-600"
          />
          <button
            onClick={handleApply}
            className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
          >
            Apply
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-300 text-sm mb-4">
          {error}
        </div>
      )}

      {/* Table */}
      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : logs.length === 0 ? (
        <p className="text-gray-500">No audit entries found.</p>
      ) : (
        <>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 text-left border-b border-gray-800">
                <th className="pb-2 font-medium">Timestamp</th>
                <th className="pb-2 font-medium">Action</th>
                <th className="pb-2 font-medium">Actor</th>
                <th className="pb-2 font-medium">Resource</th>
                <th className="pb-2 font-medium">Changes</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} className="border-b border-gray-800/50 hover:bg-gray-900/30">
                  <td className="py-2 text-gray-400 text-xs whitespace-nowrap">
                    {formatTimestamp(log.timestamp)}
                  </td>
                  <td className="py-2">
                    <span className={`px-2 py-0.5 rounded text-xs ${ACTION_COLORS[log.action] || "bg-gray-700 text-gray-300"}`}>
                      {formatAction(log.action)}
                    </span>
                  </td>
                  <td className="py-2 text-gray-300 text-xs">
                    {log.actor_id.substring(0, 12)}
                    <span className="text-gray-600 ml-1">({log.actor_role})</span>
                  </td>
                  <td className="py-2 text-gray-400 text-xs">
                    {log.resource_type}/{log.resource_id.substring(0, 8)}
                  </td>
                  <td className="py-2">
                    <ChangeSummary changes={log.changes} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-4 text-sm text-gray-400">
            <span>
              Showing {offset + 1}&ndash;{Math.min(offset + PAGE_SIZE, total)} of {total}
            </span>
            <div className="flex gap-2">
              <button
                disabled={offset === 0}
                onClick={() => doFetch(Math.max(0, offset - PAGE_SIZE))}
                className="px-3 py-1 rounded bg-gray-800 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <button
                disabled={offset + PAGE_SIZE >= total}
                onClick={() => doFetch(offset + PAGE_SIZE)}
                className="px-3 py-1 rounded bg-gray-800 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
