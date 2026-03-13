"use client";

import { useEffect, useState, useMemo } from "react";
import type { Patient } from "@/lib/types";
import { fetchPatients } from "@/lib/api";

interface Props {
  selected: Patient | null;
  onSelect: (patient: Patient | null) => void;
}

export function PatientPicker({ selected, onSelect }: Props) {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPatients(200).then((res) => {
      setPatients(res.patients);
      setLoading(false);
    });
  }, []);

  const filtered = useMemo(() => {
    if (!search.trim()) return patients;
    const q = search.toLowerCase();
    return patients.filter(
      (p) =>
        p.last_name.toLowerCase().includes(q) ||
        p.first_name.toLowerCase().includes(q) ||
        p.date_of_birth.includes(q),
    );
  }, [patients, search]);

  if (selected) {
    const allergies = selected.allergies || [];
    const conditions = selected.conditions || [];

    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-medium text-emerald-400 uppercase tracking-wider">
            Selected Patient
          </h3>
          <button
            type="button"
            onClick={() => onSelect(null)}
            className="text-xs text-gray-500 hover:text-gray-300"
          >
            Change
          </button>
        </div>

        <div className="bg-gray-900/70 border border-emerald-900/40 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-base font-semibold text-gray-100">
              {selected.last_name}, {selected.first_name}
            </span>
            <span className="text-xs text-gray-400 font-mono">
              DOB: {selected.date_of_birth}
            </span>
          </div>
          <div className="text-xs text-gray-500 mb-3">
            {selected.gender === "M" ? "Male" : "Female"} &middot;{" "}
            {selected.city}, {selected.state} {selected.postal_code}
          </div>

          {/* Allergies */}
          <div className="mb-2">
            <span className="text-[10px] uppercase tracking-wider text-gray-500">
              Allergies
            </span>
            {allergies.length > 0 ? (
              <div className="flex flex-wrap gap-1.5 mt-1">
                {allergies.map((a, i) => (
                  <span
                    key={i}
                    className={`text-[11px] px-2 py-0.5 rounded border ${
                      a.severity === "severe"
                        ? "bg-red-900/30 text-red-400 border-red-800/50"
                        : a.severity === "moderate"
                          ? "bg-yellow-900/30 text-yellow-400 border-yellow-800/50"
                          : "bg-blue-900/30 text-blue-400 border-blue-800/50"
                    }`}
                  >
                    {a.substance} ({a.reaction})
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-emerald-600 mt-0.5">NKDA</p>
            )}
          </div>

          {/* Conditions */}
          <div>
            <span className="text-[10px] uppercase tracking-wider text-gray-500">
              Conditions
            </span>
            {conditions.length > 0 ? (
              <div className="flex flex-wrap gap-1.5 mt-1">
                {conditions.map((c, i) => (
                  <span
                    key={i}
                    className="text-[11px] bg-gray-800 text-gray-300 px-2 py-0.5 rounded border border-gray-700"
                  >
                    {c}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-600 mt-0.5">None documented</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider">
        Select Patient
      </h3>

      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search by name or DOB..."
        autoFocus
        className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-sm text-gray-100 placeholder:text-gray-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
      />

      {loading ? (
        <p className="text-xs text-gray-500">Loading patients...</p>
      ) : (
        <div className="max-h-64 overflow-y-auto space-y-1 border border-gray-800 rounded-lg p-1">
          {filtered.length === 0 && (
            <p className="text-xs text-gray-600 p-2">No patients found</p>
          )}
          {filtered.map((p) => {
            const allergies = p.allergies || [];
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => onSelect(p)}
                className="w-full text-left px-3 py-2 rounded-md hover:bg-gray-800/60 transition-colors group"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-200 group-hover:text-white">
                    {p.last_name}, {p.first_name}
                  </span>
                  <span className="text-xs text-gray-500 font-mono">
                    {p.date_of_birth}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[10px] text-gray-600">
                    {p.gender === "M" ? "Male" : "Female"}
                  </span>
                  {allergies.length > 0 && (
                    <span className="text-[10px] text-red-500">
                      {allergies.length} allerg{allergies.length === 1 ? "y" : "ies"}
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
