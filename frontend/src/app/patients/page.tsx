"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import type { Patient } from "@/lib/types";
import { fetchPatients } from "@/lib/api";

export default function PatientsPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    setLoading(true);
    fetchPatients(200)
      .then((data) => {
        setPatients(data.patients);
        setTotal(data.total);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const filtered = search.trim()
    ? patients.filter((p) => {
        const q = search.toLowerCase();
        return (
          p.last_name.toLowerCase().includes(q) ||
          p.first_name.toLowerCase().includes(q) ||
          p.date_of_birth.includes(q)
        );
      })
    : patients;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold">Patients</h1>
          <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded-full">
            {total}
          </span>
        </div>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name or DOB..."
          className="w-64 bg-gray-900 border border-gray-700 rounded-md px-3 py-1.5 text-sm text-gray-100 placeholder:text-gray-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : error ? (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 text-red-300 text-sm">
          {error}
        </div>
      ) : filtered.length === 0 ? (
        <p className="text-gray-500 text-center py-8">
          {search ? "No patients match your search." : "No patients found."}
        </p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-left text-gray-400">
              <th className="pb-2 pr-4">Name</th>
              <th className="pb-2 pr-4">Date of Birth</th>
              <th className="pb-2 pr-4">Gender</th>
              <th className="pb-2 pr-4">Location</th>
              <th className="pb-2"></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((p) => (
              <tr key={p.id} className="border-b border-gray-800/50 hover:bg-gray-900/50">
                <td className="py-3 pr-4 font-medium text-gray-100">
                  {p.last_name}, {p.first_name}
                </td>
                <td className="py-3 pr-4 font-mono text-gray-300">{p.date_of_birth}</td>
                <td className="py-3 pr-4 text-gray-400">{p.gender || "—"}</td>
                <td className="py-3 pr-4 text-gray-400">
                  {p.city && p.state ? `${p.city}, ${p.state}` : "—"}
                </td>
                <td className="py-3">
                  <Link
                    href={`/patients/${p.id}`}
                    className="text-blue-400 hover:text-blue-300 text-xs"
                  >
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
