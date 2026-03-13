"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  createManualRx,
  fetchDrugByNdc,
  fetchPatientRxContext,
  prescribeAssist,
} from "@/lib/api";
import type {
  Drug,
  ManualRxInput,
  Patient,
  PrescribeAssistResult,
  RefillCandidate,
  RxContextResponse,
} from "@/lib/types";
import { DrugSearch } from "@/components/drug-search";
import { PatientPicker } from "@/components/patient-picker";
import { PrescriberPicker } from "@/components/prescriber-picker";

const inputClass =
  "w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-sm text-gray-100 placeholder:text-gray-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500";

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-xs text-gray-400 mb-1">
        {label}
        {required && <span className="text-red-400 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}

const CLASSIFICATION_LABELS: Record<string, { label: string; color: string; desc: string }> = {
  routine: { label: "ROUTINE", color: "text-blue-400 bg-blue-900/30 border-blue-800/50", desc: "Maintenance medication, regular ongoing schedule" },
  stat_supply: { label: "STAT SUPPLY", color: "text-yellow-400 bg-yellow-900/30 border-yellow-800/50", desc: "Short bridge fill to catch up to routine cycle" },
  acute: { label: "ACUTE", color: "text-orange-400 bg-orange-900/30 border-orange-800/50", desc: "Time-limited therapy, defined course" },
  prn: { label: "PRN", color: "text-purple-400 bg-purple-900/30 border-purple-800/50", desc: "As-needed, variable usage" },
};

export default function NewRxPage() {
  const router = useRouter();

  // Step 1: Patient
  const [patient, setPatient] = useState<Patient | null>(null);

  // Rx Context (loaded when patient selected)
  const [rxContext, setRxContext] = useState<RxContextResponse | null>(null);
  const [rxContextLoading, setRxContextLoading] = useState(false);

  // Step 2: Drug + Prescriber
  const [selectedDrug, setSelectedDrug] = useState<Drug | null>(null);
  const [drugSearch, setDrugSearch] = useState("");
  const [prescriberNpi, setPrescriberNpi] = useState("");
  const [prescriberName, setPrescriberName] = useState("");
  const [prescriberDea, setPrescriberDea] = useState("");

  // Step 3: AI Recommendation
  const [aiResult, setAiResult] = useState<PrescribeAssistResult | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  // Edit mode
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState<Partial<ManualRxInput>>({});

  // Submit
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [showThinking, setShowThinking] = useState(false);

  // Trigger AI when drug is selected
  const handleDrugSelect = async (drug: Drug) => {
    setSelectedDrug(drug);
    setDrugSearch(drug.drug_name);
    setAiResult(null);
    setEditing(false);

    if (patient) {
      setAiLoading(true);
      setAiError(null);
      try {
        const result = await prescribeAssist(
          patient.id,
          drug.id,
          prescriberNpi || "",
        );
        setAiResult(result);
      } catch (e: unknown) {
        setAiError(e instanceof Error ? e.message : "AI prescribing failed");
      } finally {
        setAiLoading(false);
      }
    }
  };

  // Patient selected → fetch rx-context
  const handlePatientSelect = async (p: Patient | null) => {
    setPatient(p);
    setRxContext(null);
    setPrescriberNpi("");
    setPrescriberName("");
    setPrescriberDea("");

    if (p) {
      // Fetch rx context for patient-centric suggestions
      setRxContextLoading(true);
      try {
        const ctx = await fetchPatientRxContext(p.id);
        setRxContext(ctx);

        // Auto-select sole prescriber
        if (ctx.prescribers.length === 1) {
          const sole = ctx.prescribers[0];
          setPrescriberNpi(sole.npi);
          setPrescriberName(sole.name);
          setPrescriberDea(sole.dea);
        }
      } catch {
        // Non-fatal — just means no suggestions
        setRxContext(null);
      } finally {
        setRxContextLoading(false);
      }

      // Re-trigger AI if drug already selected
      if (selectedDrug) {
        setAiLoading(true);
        setAiError(null);
        setAiResult(null);
        try {
          const result = await prescribeAssist(
            p.id,
            selectedDrug.id,
            prescriberNpi || "",
          );
          setAiResult(result);
        } catch (e: unknown) {
          setAiError(e instanceof Error ? e.message : "AI prescribing failed");
        } finally {
          setAiLoading(false);
        }
      }
    }
  };

  // Prescriber card selected from PrescriberPicker
  const handlePrescriberSelect = (npi: string, name: string, dea: string) => {
    setPrescriberNpi(npi);
    setPrescriberName(name);
    setPrescriberDea(dea);
  };

  // Refill candidate selected from DrugSearch
  const handleRefillSelect = async (candidate: RefillCandidate) => {
    // Auto-fill prescriber from this candidate if not already set
    if (!prescriberNpi && candidate.prescriber_npi) {
      setPrescriberNpi(candidate.prescriber_npi);
      setPrescriberName(candidate.prescriber_name);
      // Try to find DEA from rx-context prescribers
      const matchedPrescriber = rxContext?.prescribers.find(
        (p) => p.npi === candidate.prescriber_npi,
      );
      if (matchedPrescriber?.dea) {
        setPrescriberDea(matchedPrescriber.dea);
      }
    }

    // Resolve drug by NDC
    if (candidate.drug_id) {
      try {
        const drug = await fetchDrugByNdc(candidate.ndc);
        handleDrugSelect(drug);
      } catch {
        // If NDC lookup fails, set what we have from the candidate
        setDrugSearch(candidate.drug_description);
      }
    } else {
      setDrugSearch(candidate.drug_description);
    }
  };

  // Switch to edit mode
  const handleEdit = () => {
    if (aiResult) {
      setEditForm({
        quantity: aiResult.quantity,
        days_supply: aiResult.days_supply,
        refills: aiResult.refills,
        sig_text: aiResult.sig_text,
        substitutions: aiResult.substitutions,
      });
    }
    setEditing(true);
  };

  // Submit prescription
  const handleSubmit = async () => {
    if (!patient || !selectedDrug) return;

    const data: ManualRxInput = {
      patient_first_name: patient.first_name,
      patient_last_name: patient.last_name,
      patient_dob: patient.date_of_birth,
      prescriber_name: prescriberName,
      prescriber_npi: prescriberNpi,
      prescriber_dea: prescriberDea,
      drug_description: selectedDrug.drug_name,
      ndc: selectedDrug.ndc,
      quantity: editing ? (editForm.quantity ?? 0) : (aiResult?.quantity ?? 0),
      days_supply: editing ? (editForm.days_supply ?? 0) : (aiResult?.days_supply ?? 0),
      refills: editing ? (editForm.refills ?? 0) : (aiResult?.refills ?? 0),
      sig_text: editing ? (editForm.sig_text ?? "") : (aiResult?.sig_text ?? ""),
      written_date: new Date().toISOString().slice(0, 10),
      substitutions: editing ? (editForm.substitutions ?? 0) : (aiResult?.substitutions ?? 0),
    };

    setSubmitting(true);
    setError(null);
    try {
      const rx = await createManualRx(data);
      router.push(`/review/${rx.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create prescription");
    } finally {
      setSubmitting(false);
    }
  };

  // Determine current step
  const step = !patient ? 1 : !selectedDrug ? 2 : 3;

  return (
    <div className="max-w-3xl">
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => router.push("/queue")}
          className="text-gray-400 hover:text-white text-sm"
        >
          &larr; Back
        </button>
        <h1 className="text-xl font-semibold">New Prescription</h1>
        <span className="text-xs text-purple-400 bg-purple-900/30 border border-purple-800/50 px-2 py-0.5 rounded-full">
          AI-Assisted
        </span>
      </div>

      {/* Step indicators */}
      <div className="flex items-center gap-2 mb-6">
        {[
          { n: 1, label: "Patient" },
          { n: 2, label: "Drug & Prescriber" },
          { n: 3, label: "AI Recommendation" },
        ].map(({ n, label }) => (
          <div key={n} className="flex items-center gap-2">
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                step > n
                  ? "bg-emerald-600 text-white"
                  : step === n
                    ? "bg-blue-600 text-white"
                    : "bg-gray-800 text-gray-500"
              }`}
            >
              {step > n ? "\u2713" : n}
            </div>
            <span
              className={`text-xs ${
                step >= n ? "text-gray-300" : "text-gray-600"
              }`}
            >
              {label}
            </span>
            {n < 3 && (
              <div
                className={`w-8 h-px ${
                  step > n ? "bg-emerald-600" : "bg-gray-800"
                }`}
              />
            )}
          </div>
        ))}
      </div>

      <div className="space-y-6">
        {/* Step 1: Patient Selection */}
        <PatientPicker selected={patient} onSelect={handlePatientSelect} />

        {/* Step 2: Drug + Prescriber (visible once patient is selected) */}
        {patient && (
          <section className="space-y-4">
            <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider">
              Drug & Prescriber
            </h3>

            {/* Drug search with patient medications */}
            <Field label="Drug" required>
              <DrugSearch
                value={drugSearch}
                onChange={setDrugSearch}
                onSelect={handleDrugSelect}
                placeholder="Search all drugs by name or NDC..."
                className={inputClass}
                refillCandidates={rxContext?.refill_candidates}
                onRefillSelect={handleRefillSelect}
              />
            </Field>

            {/* Prescriber picker — intelligent selection */}
            <PrescriberPicker
              prescribers={rxContext?.prescribers ?? []}
              selectedNpi={prescriberNpi}
              onSelect={handlePrescriberSelect}
              loading={rxContextLoading}
              prescriberName={prescriberName}
              prescriberDea={prescriberDea}
              npiValue={prescriberNpi}
              onNpiChange={setPrescriberNpi}
              onNameChange={setPrescriberName}
              onDeaChange={setPrescriberDea}
              onPrescriberFound={(name) => {
                if (!prescriberName.trim()) setPrescriberName(name);
              }}
              inputClass={inputClass}
            />
          </section>
        )}

        {/* Step 3: AI Recommendation */}
        {patient && selectedDrug && (
          <section>
            {/* Loading */}
            {aiLoading && (
              <div className="bg-purple-900/20 border border-purple-800/40 rounded-lg p-6">
                <div className="flex items-center gap-3 mb-2">
                  <div className="animate-pulse flex items-center gap-1.5">
                    <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" />
                    <div
                      className="w-2 h-2 bg-purple-400 rounded-full animate-bounce"
                      style={{ animationDelay: "0.15s" }}
                    />
                    <div
                      className="w-2 h-2 bg-purple-400 rounded-full animate-bounce"
                      style={{ animationDelay: "0.3s" }}
                    />
                  </div>
                  <span className="text-sm text-purple-300 font-medium">
                    Generating prescribing details...
                  </span>
                </div>
                <p className="text-xs text-gray-500">
                  Analyzing patient profile, drug characteristics, and active
                  medications to determine appropriate prescribing parameters.
                </p>
              </div>
            )}

            {/* Error */}
            {aiError && !aiLoading && (
              <div className="bg-red-900/20 border border-red-800/50 rounded-lg p-4">
                <p className="text-sm text-red-400 mb-2">{aiError}</p>
                <button
                  type="button"
                  onClick={() => handleDrugSelect(selectedDrug)}
                  className="text-xs text-red-300 hover:text-red-200 underline"
                >
                  Retry
                </button>
              </div>
            )}

            {/* AI Result */}
            {aiResult && !aiLoading && !editing && (
              <div className="bg-gray-900/70 border border-purple-900/40 rounded-lg p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-medium text-purple-400 uppercase tracking-wider">
                    Agent Recommendation
                  </h3>
                  {aiResult.rx_classification && (
                    <span
                      className={`text-xs font-bold px-2.5 py-1 rounded border ${
                        CLASSIFICATION_LABELS[aiResult.rx_classification]?.color ||
                        "text-gray-400"
                      }`}
                    >
                      {CLASSIFICATION_LABELS[aiResult.rx_classification]?.label ||
                        aiResult.rx_classification.toUpperCase()}
                    </span>
                  )}
                </div>

                {aiResult.classification_reasoning && (
                  <p className="text-xs text-gray-500">
                    {aiResult.classification_reasoning}
                  </p>
                )}

                <div className="bg-gray-950/50 rounded-lg p-4">
                  <p className="text-sm font-semibold text-gray-100 mb-3">
                    {aiResult.drug_description}
                  </p>
                  <div className="grid grid-cols-4 gap-4 mb-3">
                    <div>
                      <span className="text-[10px] uppercase tracking-wider text-gray-500">
                        NDC
                      </span>
                      <p className="text-sm text-gray-300 font-mono mt-0.5">
                        {aiResult.ndc}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase tracking-wider text-gray-500">
                        Quantity
                      </span>
                      <p className="text-sm text-gray-100 mt-0.5 font-semibold">
                        {aiResult.quantity}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase tracking-wider text-gray-500">
                        Days Supply
                      </span>
                      <p className="text-sm text-gray-100 mt-0.5 font-semibold">
                        {aiResult.days_supply}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase tracking-wider text-gray-500">
                        Refills
                      </span>
                      <p className="text-sm text-gray-100 mt-0.5 font-semibold">
                        {aiResult.refills}
                      </p>
                    </div>
                  </div>
                  <div className="bg-gray-900/50 rounded-md p-3">
                    <span className="text-[10px] uppercase tracking-wider text-gray-500">
                      Sig
                    </span>
                    <p className="text-sm text-gray-100 mt-1">
                      {aiResult.sig_text}
                    </p>
                  </div>
                </div>

                {/* Reasoning */}
                {aiResult.reasoning && (
                  <div className="bg-blue-900/10 border border-blue-900/30 rounded-md p-3">
                    <span className="text-[10px] uppercase tracking-wider text-blue-400">
                      Reasoning
                    </span>
                    <p className="text-sm text-gray-300 mt-1 leading-relaxed">
                      {aiResult.reasoning}
                    </p>
                  </div>
                )}

                {/* Thinking (collapsible) */}
                {aiResult._thinking && (
                  <div>
                    <button
                      type="button"
                      onClick={() => setShowThinking(!showThinking)}
                      className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1"
                    >
                      <span>{showThinking ? "\u25BC" : "\u25B6"}</span>
                      Model Thinking
                    </button>
                    {showThinking && (
                      <div className="mt-2 bg-gray-950/50 rounded-md p-3">
                        <p className="text-[11px] text-gray-600 whitespace-pre-wrap font-mono leading-relaxed">
                          {aiResult._thinking}
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Metadata */}
                <div className="flex items-center justify-between pt-2 border-t border-gray-800/50">
                  <span className="text-[10px] text-gray-600 font-mono">
                    {aiResult._model}
                    {aiResult._eval_duration_ms &&
                      ` \u00B7 ${(aiResult._eval_duration_ms / 1000).toFixed(1)}s`}
                  </span>
                  <span className="text-[10px] text-gray-600">
                    {"\u2695"} AI-assisted &mdash; pharmacist review required
                  </span>
                </div>

                {/* Actions */}
                <div className="flex gap-3 pt-2">
                  <button
                    type="button"
                    onClick={handleSubmit}
                    disabled={submitting}
                    className="px-5 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm font-medium disabled:opacity-50 transition-colors"
                  >
                    {submitting ? "Submitting..." : "Accept & Submit"}
                  </button>
                  <button
                    type="button"
                    onClick={handleEdit}
                    className="px-4 py-2.5 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-md text-sm font-medium transition-colors"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDrugSelect(selectedDrug)}
                    className="px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-400 rounded-md text-sm transition-colors"
                  >
                    Re-generate
                  </button>
                </div>
              </div>
            )}

            {/* Edit mode */}
            {editing && (
              <div className="bg-gray-900/70 border border-gray-800 rounded-lg p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Edit Prescription Details
                  </h3>
                  <button
                    type="button"
                    onClick={() => setEditing(false)}
                    className="text-xs text-gray-500 hover:text-gray-300"
                  >
                    Back to AI Recommendation
                  </button>
                </div>

                <div className="grid grid-cols-4 gap-3">
                  <Field label="Quantity" required>
                    <input
                      type="number"
                      min={0}
                      className={inputClass}
                      value={editForm.quantity || ""}
                      onChange={(e) =>
                        setEditForm((p) => ({
                          ...p,
                          quantity: parseInt(e.target.value) || 0,
                        }))
                      }
                    />
                  </Field>
                  <Field label="Days Supply" required>
                    <input
                      type="number"
                      min={0}
                      className={inputClass}
                      value={editForm.days_supply || ""}
                      onChange={(e) =>
                        setEditForm((p) => ({
                          ...p,
                          days_supply: parseInt(e.target.value) || 0,
                        }))
                      }
                    />
                  </Field>
                  <Field label="Refills">
                    <input
                      type="number"
                      min={0}
                      max={99}
                      className={inputClass}
                      value={editForm.refills ?? ""}
                      onChange={(e) =>
                        setEditForm((p) => ({
                          ...p,
                          refills: parseInt(e.target.value) || 0,
                        }))
                      }
                    />
                  </Field>
                  <Field label="DAW">
                    <select
                      className={inputClass}
                      value={editForm.substitutions ?? 0}
                      onChange={(e) =>
                        setEditForm((p) => ({
                          ...p,
                          substitutions: parseInt(e.target.value),
                        }))
                      }
                    >
                      <option value={0}>0 - Sub Permitted</option>
                      <option value={1}>1 - Sub Not Allowed</option>
                      <option value={2}>2 - Patient Brand</option>
                    </select>
                  </Field>
                </div>
                <Field label="Sig (Directions)" required>
                  <textarea
                    className={inputClass}
                    rows={2}
                    value={editForm.sig_text || ""}
                    onChange={(e) =>
                      setEditForm((p) => ({ ...p, sig_text: e.target.value }))
                    }
                  />
                </Field>

                <div className="flex gap-3 pt-2">
                  <button
                    type="button"
                    onClick={handleSubmit}
                    disabled={submitting || !editForm.quantity || !editForm.days_supply || !editForm.sig_text?.trim()}
                    className="px-5 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm font-medium disabled:opacity-50 transition-colors"
                  >
                    {submitting ? "Submitting..." : "Submit to Queue"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditing(false)}
                    className="px-4 py-2.5 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-md text-sm transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </section>
        )}

        {/* Global error */}
        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-300 text-sm">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
