"use client";
import { useEffect, useState } from "react";
import { fetchQueue } from "@/lib/api";
import { useEventSocket } from "@/hooks/useEventSocket";

export default function Home() {
  const [total, setTotal] = useState(0);
  const [pending, setPending] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const { lastEvent, connected } = useEventSocket();

  const loadStats = () => {
    Promise.all([fetchQueue(), fetchQueue("pending_review")])
      .then(([all, pend]) => {
        setTotal(all.total);
        setPending(pend.total);
      })
      .catch((e) => setError(e.message));
  };

  useEffect(() => {
    loadStats();
  }, []);

  useEffect(() => {
    if (lastEvent?.type === "prescription.status_changed") {
      loadStats();
    }
  }, [lastEvent]);

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-2xl font-semibold">ARXI Dashboard</h1>
        <span
          className={`w-2 h-2 rounded-full ${connected ? "bg-green-500" : "bg-gray-600"}`}
          title={connected ? "Live updates active" : "Reconnecting..."}
        />
      </div>
      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 text-red-300 text-sm mb-6">
          {error}
        </div>
      )}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-gray-900 rounded-lg p-6">
          <div className="text-3xl font-bold text-blue-400">{total}</div>
          <div className="text-sm text-gray-400 mt-1">Total Prescriptions</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-6">
          <div className="text-3xl font-bold text-yellow-400">{pending}</div>
          <div className="text-sm text-gray-400 mt-1">Pending Review</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-6">
          <div className="text-3xl font-bold text-green-400">{total - pending}</div>
          <div className="text-sm text-gray-400 mt-1">Processed</div>
        </div>
      </div>
    </div>
  );
}
