"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import type { Prescription } from "@/lib/types";
import { fetchPrescription } from "@/lib/api";
import { RxReviewForm } from "@/components/rx-review-form";
import { StatusBadge } from "@/components/status-badge";

export default function ReviewPage() {
  const params = useParams();
  const router = useRouter();
  const [rx, setRx] = useState<Prescription | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (params.id) {
      fetchPrescription(params.id as string)
        .then(setRx)
        .catch((e) => setError(e.message));
    }
  }, [params.id]);

  if (error) {
    return (
      <div className="max-w-2xl">
        <button onClick={() => router.push("/queue")} className="text-gray-400 hover:text-white text-sm mb-4">
          &larr; Back to Queue
        </button>
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 text-red-300 text-sm">
          {error}
        </div>
      </div>
    );
  }

  if (!rx) return <p className="text-gray-500">Loading...</p>;

  return (
    <div className="max-w-3xl">
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => router.push("/queue")} className="text-gray-400 hover:text-white text-sm">
          &larr; Back to Queue
        </button>
        <h1 className="text-xl font-semibold">Rx Review</h1>
        <StatusBadge status={rx.status} />
        <span className="text-xs text-gray-500 font-mono ml-auto">{rx.id.slice(0, 8)}</span>
      </div>
      <RxReviewForm prescription={rx} onAction={() => router.push("/queue")} />
    </div>
  );
}
