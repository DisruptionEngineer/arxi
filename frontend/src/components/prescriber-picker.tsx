"use client";

import { useState } from "react";
import type { PrescriberSummary } from "@/lib/types";
import { NPIField } from "@/components/npi-field";

interface Props {
  prescribers: PrescriberSummary[];
  selectedNpi: string;
  onSelect: (npi: string, name: string, dea: string) => void;
  loading?: boolean;
  /** Fallback fields for manual entry */
  prescriberName: string;
  prescriberDea: string;
  npiValue: string;
  onNpiChange: (npi: string) => void;
  onNameChange: (name: string) => void;
  onDeaChange: (dea: string) => void;
  onPrescriberFound?: (name: string) => void;
  inputClass: string;
}

export function PrescriberPicker({
  prescribers,
  selectedNpi,
  onSelect,
  loading,
  prescriberName,
  prescriberDea,
  npiValue,
  onNpiChange,
  onNameChange,
  onDeaChange,
  onPrescriberFound,
  inputClass,
}: Props) {
  const [showManual, setShowManual] = useState(false);

  const hasKnown = prescribers.length > 0;

  if (loading) {
    return (
      <div className="space-y-2">
        <label className="block text-xs text-gray-400 mb-1">Prescriber</label>
        <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-4 flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-gray-600 border-t-blue-400 rounded-full animate-spin" />
          <span className="text-xs text-gray-500">Loading prescriber history...</span>
        </div>
      </div>
    );
  }

  // No known prescribers or user clicked "New Prescriber" → manual entry
  if (!hasKnown || showManual) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="block text-xs text-gray-400">Prescriber</label>
          {hasKnown && (
            <button
              type="button"
              onClick={() => setShowManual(false)}
              className="text-[11px] text-blue-400 hover:text-blue-300"
            >
              &larr; Back to known prescribers
            </button>
          )}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">
              NPI <span className="text-red-400">*</span>
            </label>
            <NPIField
              value={npiValue}
              onChange={onNpiChange}
              onPrescriberFound={onPrescriberFound}
              className={inputClass}
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Name</label>
            <input
              className={inputClass}
              value={prescriberName}
              onChange={(e) => onNameChange(e.target.value)}
              placeholder="Dr. Jane Smith"
            />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">DEA Number</label>
            <input
              className={inputClass}
              value={prescriberDea}
              onChange={(e) => onDeaChange(e.target.value)}
              placeholder="AB1234567"
              maxLength={20}
            />
          </div>
        </div>
      </div>
    );
  }

  // Known prescribers — selectable cards
  return (
    <div className="space-y-2">
      <label className="block text-xs text-gray-400 uppercase tracking-wider">
        Prescriber
      </label>
      <div className="space-y-2">
        {prescribers.map((p) => {
          const isSelected = selectedNpi === p.npi;
          return (
            <button
              key={p.npi}
              type="button"
              onClick={() => onSelect(p.npi, p.name, p.dea)}
              className={`w-full text-left rounded-lg border px-3 py-2.5 transition-all ${
                isSelected
                  ? "border-emerald-600 bg-emerald-900/20"
                  : "border-gray-700 bg-gray-900/50 hover:border-gray-600 hover:bg-gray-900/80"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {isSelected && (
                    <span className="text-emerald-400 text-sm">&#10003;</span>
                  )}
                  <span className={`text-sm font-medium ${isSelected ? "text-emerald-300" : "text-gray-200"}`}>
                    {p.name}
                  </span>
                </div>
                <span className="text-xs text-gray-500 font-mono">
                  NPI: {p.npi}
                </span>
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[11px] text-gray-500">
                  {p.rx_count} prescription{p.rx_count !== 1 ? "s" : ""}
                </span>
                <span className="text-[11px] text-gray-600">&middot;</span>
                <span className="text-[11px] text-gray-500">
                  Last: {p.last_rx_date}
                </span>
                {p.dea && (
                  <>
                    <span className="text-[11px] text-gray-600">&middot;</span>
                    <span className="text-[11px] text-gray-600 font-mono">
                      DEA: {p.dea}
                    </span>
                  </>
                )}
              </div>
            </button>
          );
        })}
      </div>

      <button
        type="button"
        onClick={() => {
          setShowManual(true);
          // Clear selection so parent knows we're in manual mode
          onNpiChange("");
          onNameChange("");
          onDeaChange("");
        }}
        className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 mt-1"
      >
        <span className="text-base leading-none">+</span>
        New Prescriber
      </button>
    </div>
  );
}
