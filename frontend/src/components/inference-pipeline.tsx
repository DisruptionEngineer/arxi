"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { streamClinicalReview, streamPrescribeAssist } from "@/lib/api";
import type {
  ClinicalReviewResult,
  PipelineStage,
  PipelineStageEvent,
  PrescribeAssistResult,
} from "@/lib/types";

const STAGES: { key: PipelineStage; label: string; icon: string }[] = [
  { key: "data_gathering", label: "Data Gathering", icon: "📊" },
  { key: "prompt_construction", label: "Prompt Construction", icon: "📝" },
  { key: "llm_inference", label: "LLM Inference", icon: "🧠" },
  { key: "response_parsing", label: "Response Parsing", icon: "⚙️" },
];

interface StageState {
  status: "pending" | "active" | "complete";
  timing_ms?: number;
  context?: Record<string, unknown>;
  prompt_preview?: string;
  prompt_length?: number;
  model?: string;
}

interface Props {
  mode: "clinical-review" | "prescribe-assist";
  rxId?: string;
  patientId?: string;
  drugId?: string;
  prescriberNpi?: string;
  onComplete?: (result: ClinicalReviewResult | PrescribeAssistResult) => void;
  onError?: (error: string) => void;
  /** Fired for each stage event (started/complete) — useful for demo raw data */
  onStage?: (event: PipelineStageEvent) => void;
  /** Fired for each streaming token — useful for demo raw data */
  onToken?: (text: string) => void;
  compact?: boolean;
  /** Auto-start when true */
  autoStart?: boolean;
}

export function InferencePipeline({
  mode,
  rxId,
  patientId,
  drugId,
  prescriberNpi,
  onComplete,
  onError,
  onStage: onStageExternal,
  onToken: onTokenExternal,
  compact = false,
  autoStart = true,
}: Props) {
  const [stages, setStages] = useState<Record<PipelineStage, StageState>>({
    data_gathering: { status: "pending" },
    prompt_construction: { status: "pending" },
    llm_inference: { status: "pending" },
    response_parsing: { status: "pending" },
  });
  const [tokens, setTokens] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(false);
  const [showPrompt, setShowPrompt] = useState(false);
  const tokenRef = useRef<HTMLDivElement>(null);
  const startedRef = useRef(false);

  const run = useCallback(async () => {
    if (running) return;
    setRunning(true);
    setDone(false);
    setError(null);
    setTokens("");
    setStages({
      data_gathering: { status: "pending" },
      prompt_construction: { status: "pending" },
      llm_inference: { status: "pending" },
      response_parsing: { status: "pending" },
    });

    const callbacks = {
      onStage: (event: PipelineStageEvent) => {
        setStages((prev) => ({
          ...prev,
          [event.stage]: {
            status: event.status === "complete" ? "complete" : "active",
            timing_ms: event.timing_ms,
            context: event.context,
            prompt_preview: event.prompt_preview,
            prompt_length: event.prompt_length,
            model: event.model,
          },
        }));
        onStageExternal?.(event);
      },
      onToken: (text: string) => {
        setTokens((prev) => prev + text);
        onTokenExternal?.(text);
      },
      onComplete: (result: ClinicalReviewResult | PrescribeAssistResult) => {
        setDone(true);
        setRunning(false);
        onComplete?.(result);
      },
      onError: (msg: string) => {
        setError(msg);
        setRunning(false);
        onError?.(msg);
      },
    };

    try {
      if (mode === "clinical-review" && rxId) {
        await streamClinicalReview(rxId, callbacks);
      } else if (mode === "prescribe-assist" && patientId && drugId && prescriberNpi) {
        await streamPrescribeAssist(patientId, drugId, prescriberNpi, callbacks);
      }
    } catch (err) {
      setError(String(err));
      setRunning(false);
    }
  }, [mode, rxId, patientId, drugId, prescriberNpi, onComplete, onError, onStageExternal, onTokenExternal, running]);

  // Auto-scroll tokens
  useEffect(() => {
    if (tokenRef.current) {
      tokenRef.current.scrollTop = tokenRef.current.scrollHeight;
    }
  }, [tokens]);

  // Auto-start
  useEffect(() => {
    if (autoStart && !startedRef.current) {
      startedRef.current = true;
      run();
    }
  }, [autoStart, run]);

  const currentStageIdx = STAGES.findIndex(
    (s) => stages[s.key].status === "active"
  );

  return (
    <div className={`${compact ? "space-y-3" : "space-y-5"}`}>
      {/* Stage indicators */}
      <div className="flex items-center gap-1">
        {STAGES.map((stage, idx) => {
          const state = stages[stage.key];
          const isActive = state.status === "active";
          const isComplete = state.status === "complete";
          const isPending = state.status === "pending";

          return (
            <div key={stage.key} className="flex items-center flex-1">
              {/* Stage node */}
              <div className="flex flex-col items-center flex-1 min-w-0">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm transition-all duration-300 ${
                    isComplete
                      ? "bg-emerald-600/30 border-2 border-emerald-500 text-emerald-300"
                      : isActive
                        ? "bg-purple-600/30 border-2 border-purple-400 text-purple-300 animate-pulse"
                        : "bg-gray-800/50 border-2 border-gray-700 text-gray-600"
                  }`}
                >
                  {isComplete ? "✓" : stage.icon}
                </div>
                <span
                  className={`text-[10px] mt-1 text-center truncate w-full ${
                    isComplete
                      ? "text-emerald-400"
                      : isActive
                        ? "text-purple-300"
                        : "text-gray-600"
                  }`}
                >
                  {stage.label}
                </span>
                {state.timing_ms !== undefined && (
                  <span className="text-[9px] text-gray-500 font-mono">
                    {state.timing_ms < 1000
                      ? `${state.timing_ms}ms`
                      : `${(state.timing_ms / 1000).toFixed(1)}s`}
                  </span>
                )}
              </div>
              {/* Connector line */}
              {idx < STAGES.length - 1 && (
                <div className="w-6 h-0.5 -mt-4 mx-0.5">
                  <div
                    className={`h-full rounded transition-all duration-500 ${
                      isComplete
                        ? "bg-emerald-500"
                        : isActive
                          ? "bg-gradient-to-r from-purple-500 to-gray-700"
                          : "bg-gray-800"
                    }`}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Context display (data gathering results) */}
      {stages.data_gathering.context && !compact && (
        <div className="bg-gray-900/60 border border-gray-800 rounded-lg p-3">
          <h4 className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-2">
            Context Loaded
          </h4>
          <div className="flex flex-wrap gap-2">
            {Object.entries(stages.data_gathering.context).map(([key, val]) => (
              <span
                key={key}
                className="text-[11px] bg-gray-800 text-gray-300 px-2 py-0.5 rounded-full"
              >
                {key.replace(/_/g, " ")}: <span className="text-white font-medium">{String(val)}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Prompt preview (collapsible) */}
      {stages.prompt_construction.prompt_preview && !compact && (
        <div className="bg-gray-900/60 border border-gray-800 rounded-lg overflow-hidden">
          <button
            type="button"
            onClick={() => setShowPrompt(!showPrompt)}
            className="w-full px-3 py-2 flex items-center justify-between text-xs text-gray-400 hover:text-gray-300"
          >
            <span>
              Prompt ({stages.prompt_construction.prompt_length} chars)
            </span>
            <span>{showPrompt ? "▲" : "▼"}</span>
          </button>
          {showPrompt && (
            <pre className="px-3 pb-3 text-[11px] text-gray-400 font-mono whitespace-pre-wrap max-h-48 overflow-y-auto border-t border-gray-800">
              {stages.prompt_construction.prompt_preview}
            </pre>
          )}
        </div>
      )}

      {/* Model badge */}
      {stages.llm_inference.model && (
        <div className="flex items-center gap-2">
          <span className="text-[10px] bg-purple-900/30 text-purple-400 border border-purple-800/50 px-2 py-0.5 rounded-full">
            {stages.llm_inference.model}
          </span>
          {stages.llm_inference.status === "active" && (
            <span className="text-[10px] text-purple-400 animate-pulse">
              Generating...
            </span>
          )}
        </div>
      )}

      {/* Token stream */}
      {(stages.llm_inference.status === "active" ||
        stages.llm_inference.status === "complete") &&
        tokens && (
          <div
            ref={tokenRef}
            className={`bg-gray-950 border border-gray-800 rounded-lg p-3 font-mono text-xs text-gray-300 overflow-y-auto whitespace-pre-wrap ${
              compact ? "max-h-32" : "max-h-64"
            }`}
          >
            {tokens}
            {stages.llm_inference.status === "active" && (
              <span className="inline-block w-1.5 h-3.5 bg-purple-400 ml-0.5 animate-pulse" />
            )}
          </div>
        )}

      {/* Error */}
      {error && (
        <div className="bg-red-900/20 border border-red-800/50 rounded-lg px-3 py-2">
          <p className="text-xs text-red-400">{error}</p>
        </div>
      )}

      {/* Done indicator */}
      {done && !compact && (
        <div className="text-center">
          <span className="text-[11px] text-emerald-400">
            Pipeline complete — results delivered
          </span>
        </div>
      )}
    </div>
  );
}
