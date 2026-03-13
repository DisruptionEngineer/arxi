"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import type { Prescription, RxStatus } from "@/lib/types";
import { fetchQueue } from "@/lib/api";
import { RxQueueTable } from "@/components/rx-queue-table";
import { useEventSocket } from "@/hooks/useEventSocket";

const STATUSES: { label: string; value: RxStatus | "" }[] = [
  { label: "All", value: "" },
  { label: "Pending Review", value: "pending_review" },
  { label: "Approved", value: "approved" },
  { label: "Rejected", value: "rejected" },
];

export default function QueuePage() {
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [filter, setFilter] = useState<string>("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { lastEvent, connected } = useEventSocket();

  const loadQueue = () => {
    setLoading(true);
    setError(null);
    fetchQueue(filter || undefined)
      .then((data) => setPrescriptions(data.prescriptions))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadQueue();
  }, [filter]);

  useEffect(() => {
    if (lastEvent?.type === "prescription.status_changed") {
      loadQueue();
    }
  }, [lastEvent]);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold">Rx Queue</h1>
          <span
            className={`w-2 h-2 rounded-full ${connected ? "bg-green-500" : "bg-gray-600"}`}
            title={connected ? "Live updates active" : "Reconnecting..."}
          />
          <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded-full">
            {prescriptions.length}
          </span>
        </div>
        <Link
          href="/new-rx"
          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-xs font-medium"
        >
          + New Rx
        </Link>
      </div>

      {/* Filters + Search */}
      <div className="flex items-center justify-between mb-4 gap-4">
        <div className="flex gap-2">
          {STATUSES.map((s) => (
            <button
              key={s.value}
              onClick={() => setFilter(s.value)}
              className={`px-3 py-1 text-xs rounded-full ${
                filter === s.value ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400 hover:text-gray-200"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
        <input
          type="text"
          placeholder="Search patient, drug, prescriber..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-72 bg-gray-900 border border-gray-700 rounded-md px-3 py-1.5 text-sm text-gray-100 placeholder:text-gray-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : error ? (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 text-red-300 text-sm">
          {error}
        </div>
      ) : (
        <RxQueueTable prescriptions={prescriptions} searchQuery={search} />
      )}
    </div>
  );
}
