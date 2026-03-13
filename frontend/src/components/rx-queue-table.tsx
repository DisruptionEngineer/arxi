import Link from "next/link";
import type { Prescription } from "@/lib/types";
import { StatusBadge } from "./status-badge";

interface Props {
  prescriptions: Prescription[];
  searchQuery?: string;
}

export function RxQueueTable({ prescriptions, searchQuery = "" }: Props) {
  // Client-side filter by patient name, drug, prescriber, or NDC
  const q = searchQuery.toLowerCase().trim();
  const filtered = q
    ? prescriptions.filter(
        (rx) =>
          `${rx.patient_last_name} ${rx.patient_first_name}`.toLowerCase().includes(q) ||
          rx.drug_description.toLowerCase().includes(q) ||
          rx.prescriber_name.toLowerCase().includes(q) ||
          (rx.ndc && rx.ndc.includes(q))
      )
    : prescriptions;

  if (filtered.length === 0) {
    return (
      <p className="text-gray-500 text-center py-8">
        {q ? "No prescriptions match your search." : "No prescriptions in queue."}
      </p>
    );
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-gray-800 text-left text-gray-400">
          <th className="pb-2 pr-4">Patient</th>
          <th className="pb-2 pr-4">Drug</th>
          <th className="pb-2 pr-4">Prescriber</th>
          <th className="pb-2 pr-4">Source</th>
          <th className="pb-2 pr-4">Status</th>
          <th className="pb-2 pr-4">Date</th>
          <th className="pb-2"></th>
        </tr>
      </thead>
      <tbody>
        {filtered.map((rx) => (
          <tr key={rx.id} className="border-b border-gray-800/50 hover:bg-gray-900/50">
            <td className="py-3 pr-4">
              <div className="flex items-center gap-2">
                {rx.patient_id ? (
                  <Link
                    href={`/patients/${rx.patient_id}`}
                    className="text-blue-400 hover:text-blue-300 font-medium"
                  >
                    {rx.patient_last_name}, {rx.patient_first_name}
                  </Link>
                ) : (
                  <span className="text-gray-100">
                    {rx.patient_last_name}, {rx.patient_first_name}
                  </span>
                )}
                {rx.patient_id && (
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500 flex-shrink-0" title="Patient linked" />
                )}
              </div>
            </td>
            <td className="py-3 pr-4 max-w-[200px]">
              <div className="truncate text-gray-100">{rx.drug_description}</div>
              {rx.ndc && (
                <div className="text-[10px] text-gray-600 font-mono">
                  {rx.ndc}
                </div>
              )}
            </td>
            <td className="py-3 pr-4 text-gray-400">{rx.prescriber_name || "\u2014"}</td>
            <td className="py-3 pr-4">
              <span
                className={`text-xs px-1.5 py-0.5 rounded ${
                  rx.source === "e-prescribe"
                    ? "bg-purple-900/40 text-purple-300"
                    : rx.source === "manual"
                    ? "bg-gray-800 text-gray-400"
                    : "bg-gray-800 text-gray-400"
                }`}
              >
                {rx.source}
              </span>
            </td>
            <td className="py-3 pr-4">
              <StatusBadge status={rx.status} />
            </td>
            <td className="py-3 pr-4 text-gray-400">
              {new Date(rx.created_at).toLocaleDateString()}
            </td>
            <td className="py-3">
              <Link href={`/review/${rx.id}`} className="text-blue-400 hover:text-blue-300 text-xs">
                Review
              </Link>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
