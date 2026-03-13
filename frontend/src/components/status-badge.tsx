import type { RxStatus } from "@/lib/types";

const STATUS_CONFIG: Record<RxStatus, { label: string; color: string }> = {
  received: { label: "Received", color: "bg-gray-500" },
  parsed: { label: "Parsed", color: "bg-blue-500" },
  validated: { label: "Validated", color: "bg-cyan-500" },
  pending_review: { label: "Pending Review", color: "bg-yellow-500" },
  approved: { label: "Approved", color: "bg-green-500" },
  rejected: { label: "Rejected", color: "bg-red-500" },
  corrected: { label: "Corrected", color: "bg-orange-500" },
};

export function StatusBadge({ status }: { status: RxStatus }) {
  const cfg = STATUS_CONFIG[status];
  return (
    <span className={`${cfg.color} text-white text-xs px-2 py-1 rounded-full`}>
      {cfg.label}
    </span>
  );
}
