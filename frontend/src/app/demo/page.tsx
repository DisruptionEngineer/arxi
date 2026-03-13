"use client";

import { useCallback, useState } from "react";
import { fetchPatients, fetchQueue, searchDrugs } from "@/lib/api";
import type {
  ClinicalReviewResult,
  Drug,
  Patient,
  PipelineStageEvent,
  PrescribeAssistResult,
  Prescription,
} from "@/lib/types";
import { InferencePipeline } from "@/components/inference-pipeline";

type DemoMode = "clinical-review" | "prescribe-assist";

interface RawData {
  stages: PipelineStageEvent[];
  tokens: string;
  result: ClinicalReviewResult | PrescribeAssistResult | null;
}

export default function DemoPage() {
  // Selection state
  const [mode, setMode] = useState<DemoMode>("clinical-review");
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [drugs, setDrugs] = useState<Drug[]>([]);
  const [selectedRxId, setSelectedRxId] = useState("");
  const [selectedPatientId, setSelectedPatientId] = useState("");
  const [selectedDrugId, setSelectedDrugId] = useState("");
  const [drugSearch, setDrugSearch] = useState("");
  const [prescriberNpi, setPrescriberNpi] = useState("1234567890");
  const [loaded, setLoaded] = useState(false);

  // Pipeline state
  const [running, setRunning] = useState(false);
  const [pipelineKey, setPipelineKey] = useState(0);

  // Raw data tabs
  const [activeTab, setActiveTab] = useState<"stages" | "tokens" | "result">("stages");
  const [rawData, setRawData] = useState<RawData>({
    stages: [],
    tokens: "",
    result: null,
  });

  // Load data on first interaction
  const loadData = useCallback(async () => {
    if (loaded) return;
    try {
      const [queueRes, patientRes] = await Promise.all([
        fetchQueue("pending_review"),
        fetchPatients(50, 0),
      ]);
      setPrescriptions(queueRes.prescriptions);
      setPatients(patientRes.patients);
      if (queueRes.prescriptions.length > 0) {
        setSelectedRxId(queueRes.prescriptions[0].id);
      }
      if (patientRes.patients.length > 0) {
        setSelectedPatientId(patientRes.patients[0].id);
      }
      setLoaded(true);
    } catch {
      // ignore
    }
  }, [loaded]);

  const handleDrugSearch = async (q: string) => {
    setDrugSearch(q);
    if (q.length < 2) {
      setDrugs([]);
      return;
    }
    try {
      const res = await searchDrugs(q, 10);
      setDrugs(res.drugs);
      if (res.drugs.length > 0 && !selectedDrugId) {
        setSelectedDrugId(res.drugs[0].id);
      }
    } catch {
      // ignore
    }
  };

  const handleStart = () => {
    setRunning(true);
    setRawData({ stages: [], tokens: "", result: null });
    setPipelineKey((k) => k + 1);
  };

  const handleStage = useCallback((event: PipelineStageEvent) => {
    setRawData((prev) => ({ ...prev, stages: [...prev.stages, event] }));
  }, []);

  const handleToken = useCallback((text: string) => {
    setRawData((prev) => ({ ...prev, tokens: prev.tokens + text }));
  }, []);

  const canStart =
    mode === "clinical-review"
      ? !!selectedRxId
      : !!selectedPatientId && !!selectedDrugId && !!prescriberNpi;

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-100">
            AI Pipeline Demo
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Real-time visualization of the ARXI inference pipeline
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setMode("clinical-review");
              loadData();
            }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              mode === "clinical-review"
                ? "bg-purple-600 text-white"
                : "bg-gray-800 text-gray-400 hover:text-gray-200"
            }`}
          >
            Clinical Review
          </button>
          <button
            type="button"
            onClick={() => {
              setMode("prescribe-assist");
              loadData();
            }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              mode === "prescribe-assist"
                ? "bg-purple-600 text-white"
                : "bg-gray-800 text-gray-400 hover:text-gray-200"
            }`}
          >
            Prescribe Assist
          </button>
        </div>
      </div>

      {/* Selection Bar */}
      <div className="bg-gray-900/70 border border-gray-800 rounded-lg p-4 mb-6">
        <div className="flex items-end gap-4">
          {mode === "clinical-review" ? (
            <div className="flex-1">
              <label className="block text-xs text-gray-400 mb-1">
                Prescription
              </label>
              <select
                className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-purple-500"
                value={selectedRxId}
                onChange={(e) => setSelectedRxId(e.target.value)}
                onFocus={loadData}
              >
                {prescriptions.length === 0 && (
                  <option value="">Click to load...</option>
                )}
                {prescriptions.map((rx) => (
                  <option key={rx.id} value={rx.id}>
                    {rx.patient_last_name}, {rx.patient_first_name} — {rx.drug_description} ({rx.id.slice(0, 8)})
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <>
              <div className="flex-1">
                <label className="block text-xs text-gray-400 mb-1">
                  Patient
                </label>
                <select
                  className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-purple-500"
                  value={selectedPatientId}
                  onChange={(e) => setSelectedPatientId(e.target.value)}
                  onFocus={loadData}
                >
                  {patients.length === 0 && (
                    <option value="">Click to load...</option>
                  )}
                  {patients.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.last_name}, {p.first_name} — DOB: {p.date_of_birth}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex-1">
                <label className="block text-xs text-gray-400 mb-1">
                  Drug
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={drugSearch}
                    onChange={(e) => handleDrugSearch(e.target.value)}
                    placeholder="Search drugs..."
                    className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-purple-500"
                  />
                  {drugs.length > 0 && drugSearch.length >= 2 && (
                    <ul className="absolute z-50 mt-1 w-full max-h-48 overflow-y-auto bg-gray-900 border border-gray-700 rounded-lg shadow-xl">
                      {drugs.map((d) => (
                        <li
                          key={d.id}
                          onClick={() => {
                            setSelectedDrugId(d.id);
                            setDrugSearch(d.drug_name);
                            setDrugs([]);
                          }}
                          className={`px-3 py-2 cursor-pointer text-sm hover:bg-gray-800 ${
                            selectedDrugId === d.id ? "bg-purple-900/30" : ""
                          }`}
                        >
                          <span className="text-gray-100">{d.drug_name}</span>
                          <span className="text-gray-500 text-xs ml-2">
                            {d.generic_name} — {d.ndc}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
              <div className="w-40">
                <label className="block text-xs text-gray-400 mb-1">
                  Prescriber NPI
                </label>
                <input
                  type="text"
                  value={prescriberNpi}
                  onChange={(e) => setPrescriberNpi(e.target.value)}
                  placeholder="NPI..."
                  className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-purple-500"
                />
              </div>
            </>
          )}
          <button
            type="button"
            onClick={handleStart}
            disabled={!canStart || running}
            className="px-6 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-40 text-white rounded-md text-sm font-medium transition-colors whitespace-nowrap"
          >
            {running ? "Running..." : "Run Pipeline"}
          </button>
        </div>
      </div>

      {/* Side-by-side: Pipeline | Raw Data */}
      <div className="grid grid-cols-5 gap-6">
        {/* Left: Pipeline Visualization (40%) */}
        <div className="col-span-2">
          <div className="bg-gray-900/70 border border-gray-800 rounded-lg p-5">
            <h2 className="text-xs font-medium text-purple-400 uppercase tracking-wider mb-4">
              Pipeline Visualization
            </h2>
            {running ? (
              <InferencePipeline
                key={pipelineKey}
                mode={mode}
                rxId={mode === "clinical-review" ? selectedRxId : undefined}
                patientId={mode === "prescribe-assist" ? selectedPatientId : undefined}
                drugId={mode === "prescribe-assist" ? selectedDrugId : undefined}
                prescriberNpi={mode === "prescribe-assist" ? prescriberNpi : undefined}
                compact={false}
                onStage={handleStage}
                onToken={handleToken}
                onComplete={(result) => {
                  setRunning(false);
                  setRawData((prev) => ({ ...prev, result }));
                }}
                onError={(msg) => {
                  setRunning(false);
                  setRawData((prev) => ({ ...prev, result: null }));
                }}
              />
            ) : (
              <div className="text-center py-12">
                <p className="text-gray-600 text-sm">
                  Select parameters above and click &quot;Run Pipeline&quot; to begin
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Right: Tabbed Raw Data (60%) */}
        <div className="col-span-3">
          <div className="bg-gray-900/70 border border-gray-800 rounded-lg overflow-hidden">
            {/* Tab bar */}
            <div className="flex border-b border-gray-800">
              {(["stages", "tokens", "result"] as const).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setActiveTab(tab)}
                  className={`px-5 py-3 text-xs font-medium uppercase tracking-wider transition-colors ${
                    activeTab === tab
                      ? "text-purple-400 border-b-2 border-purple-500 bg-gray-900/50"
                      : "text-gray-500 hover:text-gray-300"
                  }`}
                >
                  {tab === "stages" ? "Context" : tab === "tokens" ? "Tokens" : "Result"}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div className="p-4 max-h-[600px] overflow-y-auto">
              {activeTab === "stages" && (
                <div className="space-y-2">
                  {rawData.stages.length === 0 ? (
                    <p className="text-gray-600 text-sm text-center py-8">
                      Stage events will appear here during pipeline execution
                    </p>
                  ) : (
                    rawData.stages.map((s, i) => (
                      <div key={i} className="bg-gray-950/50 rounded-md p-3">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-mono text-purple-400">
                            {s.stage}
                          </span>
                          <span
                            className={`text-[10px] font-bold ${
                              s.status === "complete"
                                ? "text-emerald-400"
                                : "text-yellow-400"
                            }`}
                          >
                            {s.status.toUpperCase()}
                          </span>
                        </div>
                        <pre className="text-[11px] text-gray-400 font-mono whitespace-pre-wrap">
                          {JSON.stringify(s, null, 2)}
                        </pre>
                      </div>
                    ))
                  )}
                </div>
              )}

              {activeTab === "tokens" && (
                <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap leading-relaxed">
                  {rawData.tokens || (
                    <span className="text-gray-600">
                      Token stream will appear here during LLM inference
                    </span>
                  )}
                </pre>
              )}

              {activeTab === "result" && (
                <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">
                  {rawData.result
                    ? JSON.stringify(rawData.result, null, 2)
                    : (
                      <span className="text-gray-600">
                        Parsed result will appear here after pipeline completes
                      </span>
                    )}
                </pre>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
