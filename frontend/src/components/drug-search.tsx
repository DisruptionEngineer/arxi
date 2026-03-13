"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { searchDrugs } from "@/lib/api";
import type { Drug, RefillCandidate } from "@/lib/types";

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSelect: (drug: Drug) => void;
  placeholder?: string;
  className?: string;
  /** Patient's existing medications for refill/renewal */
  refillCandidates?: RefillCandidate[];
  /** Called when user clicks a refill candidate */
  onRefillSelect?: (candidate: RefillCandidate) => void;
}

function RefillBadge({ candidate }: { candidate: RefillCandidate }) {
  const isRefill =
    candidate.remaining_refills > 0 && candidate.last_status === "approved";
  return (
    <span
      className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${
        isRefill
          ? "text-emerald-400 bg-emerald-900/30 border-emerald-800/50"
          : "text-blue-400 bg-blue-900/30 border-blue-800/50"
      }`}
    >
      {isRefill ? "REFILL" : "RENEWAL"}
    </span>
  );
}

export function DrugSearch({
  value,
  onChange,
  onSelect,
  placeholder,
  className,
  refillCandidates,
  onRefillSelect,
}: Props) {
  const [results, setResults] = useState<Drug[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [highlighted, setHighlighted] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const doSearch = useCallback(async (q: string) => {
    if (q.length < 2) {
      setResults([]);
      setOpen(false);
      return;
    }
    setLoading(true);
    try {
      const res = await searchDrugs(q);
      setResults(res.drugs);
      setOpen(res.drugs.length > 0);
      setHighlighted(-1);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    onChange(val);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => doSearch(val), 250);
  };

  const handleSelect = (drug: Drug) => {
    onSelect(drug);
    setOpen(false);
    setResults([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlighted((h) => Math.min(h + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlighted((h) => Math.max(h - 1, 0));
    } else if (e.key === "Enter" && highlighted >= 0) {
      e.preventDefault();
      handleSelect(results[highlighted]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const hasCandidates =
    refillCandidates && refillCandidates.length > 0 && onRefillSelect;

  return (
    <div ref={wrapperRef} className="space-y-3">
      {/* Patient's medications section */}
      {hasCandidates && (
        <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-3 space-y-2">
          <h4 className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">
            Patient&apos;s Medications
          </h4>
          <div className="space-y-1.5">
            {refillCandidates!.map((c) => (
              <button
                key={c.ndc}
                type="button"
                onClick={() => onRefillSelect!(c)}
                className="w-full text-left rounded-md border border-gray-700/60 bg-gray-950/40 px-3 py-2 hover:border-gray-600 hover:bg-gray-900/60 transition-all group"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm text-gray-100 font-medium truncate">
                        {c.drug_description}
                      </p>
                      <RefillBadge candidate={c} />
                    </div>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span className="text-[11px] text-gray-500">
                        {c.prescriber_name}
                      </span>
                      <span className="text-[11px] text-gray-600">
                        &middot;
                      </span>
                      <span className="text-[11px] text-gray-500">
                        Filled: {c.last_fill_date}
                      </span>
                      <span className="text-[11px] text-gray-600">
                        &middot;
                      </span>
                      <span className="text-[11px] text-gray-500">
                        {c.remaining_refills} refill
                        {c.remaining_refills !== 1 ? "s" : ""}
                      </span>
                    </div>
                  </div>
                  <span className="text-xs text-gray-500 font-mono shrink-0">
                    {c.ndc}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Search input */}
      <div className="relative">
        <div className="relative">
          <input
            type="text"
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            onFocus={() => results.length > 0 && setOpen(true)}
            placeholder={placeholder}
            className={className}
            autoComplete="off"
          />
          {loading && (
            <div className="absolute right-2 top-1/2 -translate-y-1/2">
              <div className="w-4 h-4 border-2 border-gray-600 border-t-blue-400 rounded-full animate-spin" />
            </div>
          )}
        </div>

        {open && results.length > 0 && (
          <ul className="absolute z-50 mt-1 w-full max-h-64 overflow-y-auto bg-gray-900 border border-gray-700 rounded-lg shadow-xl">
            {results.map((drug, i) => (
              <li
                key={drug.id}
                onClick={() => handleSelect(drug)}
                onMouseEnter={() => setHighlighted(i)}
                className={`px-3 py-2 cursor-pointer border-b border-gray-800 last:border-0 ${
                  i === highlighted ? "bg-blue-900/40" : "hover:bg-gray-800"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm text-gray-100 font-medium truncate">{drug.drug_name}</p>
                    <p className="text-xs text-gray-500">{drug.generic_name} &middot; {drug.dosage_form} &middot; {drug.route}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-xs text-gray-400 font-mono">{drug.ndc}</p>
                    {drug.dea_schedule && (
                      <span className="text-[10px] bg-red-900/40 text-red-400 border border-red-800/50 px-1 py-0.5 rounded">
                        {drug.dea_schedule}
                      </span>
                    )}
                  </div>
                </div>
                <p className="text-[11px] text-gray-600 mt-0.5">{drug.manufacturer}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
