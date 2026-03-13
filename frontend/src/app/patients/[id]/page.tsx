"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import type { Patient, Prescription } from "@/lib/types";
import { fetchPatient, fetchPatientPrescriptions } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

export default function PatientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([fetchPatient(id), fetchPatientPrescriptions(id)])
      .then(([p, rxData]) => {
        setPatient(p);
        setPrescriptions(rxData.prescriptions);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <p className="text-gray-500">Loading...</p>;
  if (error)
    return (
      <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 text-red-300 text-sm">
        {error}
      </div>
    );
  if (!patient) return <p className="text-gray-500">Patient not found.</p>;

  return (
    <div className="max-w-4xl">
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => router.push("/patients")}
          className="text-gray-400 hover:text-white text-sm"
        >
          &larr; Patients
        </button>
        <h1 className="text-xl font-semibold">
          {patient.last_name}, {patient.first_name}
        </h1>
        <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded-full font-mono">
          {patient.id.slice(0, 8)}
        </span>
      </div>

      {/* Patient Info Card */}
      <section className="bg-gray-900/70 border border-gray-800 rounded-lg p-4 mb-6">
        <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">
          Demographics
        </h3>
        <div className="grid grid-cols-4 gap-4">
          <div>
            <span className="text-[11px] uppercase tracking-wider text-gray-500">
              Name
            </span>
            <p className="text-sm text-gray-100 mt-0.5">
              {patient.last_name}, {patient.first_name}
            </p>
          </div>
          <div>
            <span className="text-[11px] uppercase tracking-wider text-gray-500">
              Date of Birth
            </span>
            <p className="text-sm text-gray-300 font-mono mt-0.5">
              {patient.date_of_birth}
            </p>
          </div>
          <div>
            <span className="text-[11px] uppercase tracking-wider text-gray-500">
              Gender
            </span>
            <p className="text-sm text-gray-300 mt-0.5">
              {patient.gender || "Not specified"}
            </p>
          </div>
          <div>
            <span className="text-[11px] uppercase tracking-wider text-gray-500">
              Location
            </span>
            <p className="text-sm text-gray-300 mt-0.5">
              {patient.city && patient.state
                ? `${patient.city}, ${patient.state} ${patient.postal_code}`
                : "Not on file"}
            </p>
          </div>
        </div>
      </section>

      {/* Prescription History */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <h3 className="text-sm font-medium text-gray-300 uppercase tracking-wider">
            Prescription History
          </h3>
          <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded-full">
            {prescriptions.length}
          </span>
        </div>

        {prescriptions.length === 0 ? (
          <p className="text-gray-500 text-sm py-4">
            No prescriptions on file.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-left text-gray-400">
                <th className="pb-2 pr-4">Drug</th>
                <th className="pb-2 pr-4">Status</th>
                <th className="pb-2 pr-4">Prescriber</th>
                <th className="pb-2 pr-4">Date</th>
                <th className="pb-2"></th>
              </tr>
            </thead>
            <tbody>
              {prescriptions.map((rx) => (
                <tr
                  key={rx.id}
                  className="border-b border-gray-800/50 hover:bg-gray-900/50"
                >
                  <td className="py-3 pr-4">
                    <div className="font-medium text-gray-100">
                      {rx.drug_description}
                    </div>
                    {rx.ndc && (
                      <div className="text-[11px] text-gray-600 font-mono">
                        NDC: {rx.ndc}
                      </div>
                    )}
                  </td>
                  <td className="py-3 pr-4">
                    <StatusBadge status={rx.status} />
                  </td>
                  <td className="py-3 pr-4 text-gray-400">
                    {rx.prescriber_name}
                  </td>
                  <td className="py-3 pr-4 text-gray-400">
                    {new Date(rx.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-3">
                    <Link
                      href={`/review/${rx.id}`}
                      className="text-blue-400 hover:text-blue-300 text-xs"
                    >
                      Review
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
