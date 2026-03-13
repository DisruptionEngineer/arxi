"use client";
import { useState } from "react";
import type {
  ClinicalCheck,
  ClinicalCategoryResult,
  ClinicalReviewResult,
  FollowupAction,
  Prescription,
  RejectionReason,
} from "@/lib/types";
import { approveRx, rejectRx, runClinicalReview } from "@/lib/api";
import { useAuth } from "@/context/auth-context";

const DAW_LABELS: Record<number, string> = {
  0: "Substitution Permitted",
  1: "Substitution Not Allowed (brand medically necessary)",
  2: "Patient Requested Brand",
};

const REJECTION_REASON_LABELS: Record<RejectionReason, string> = {
  clinical_concern: "Clinical Concern \u2014 Drug interaction, allergy, contraindication",
  incomplete_rx: "Incomplete Rx \u2014 Missing/invalid info (NPI, DEA, quantity)",
  dur_issue: "DUR Issue \u2014 Duplicate therapy, early refill, excessive qty/days",
  prescriber_contact: "Prescriber Contact \u2014 Need clarification, dose question",
  insurance_issue: "Insurance Issue \u2014 Prior auth needed, not covered",
  patient_safety: "Patient Safety \u2014 Abuse concern, high-risk combination",
  other: "Other",
};

const FOLLOWUP_ACTION_LABELS: Record<FollowupAction, string> = {
  contact_prescriber: "Contact Prescriber",
  contact_patient: "Contact Patient",
  request_prior_auth: "Request Prior Authorization",
  return_to_prescriber: "Return Rx to Prescriber",
  no_action: "No Action (documentation only)",
};

const CLINICAL_CHECK_LABELS: Record<ClinicalCheck, string> = {
  dur_review: "DUR review completed",
  drug_interactions: "Drug interactions checked",
  allergy_screening: "Allergy screening done",
  dose_range: "Dose range verified",
  patient_profile: "Patient profile reviewed",
  prescriber_credentials: "Prescriber credentials verified",
};

const ALL_CHECKS: ClinicalCheck[] = [
  "dur_review",
  "drug_interactions",
  "allergy_screening",
  "dose_range",
  "patient_profile",
  "prescriber_credentials",
];

const CATEGORY_LABELS: Record<string, string> = {
  dur_review: "DUR Review",
  drug_interactions: "Drug Interactions",
  allergy_screening: "Allergy Screening",
  dose_range: "Dose Range",
  patient_profile: "Patient Profile",
  prescriber_credentials: "Prescriber Credentials",
};

const SEVERITY_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  high: { bg: "bg-red-900/30", text: "text-red-400", border: "border-red-800/50" },
  moderate: { bg: "bg-yellow-900/30", text: "text-yellow-400", border: "border-yellow-800/50" },
  low: { bg: "bg-blue-900/30", text: "text-blue-400", border: "border-blue-800/50" },
};

const RISK_STYLES: Record<string, { bg: string; text: string; border: string; label: string }> = {
  high: { bg: "bg-red-900/40", text: "text-red-400", border: "border-red-700", label: "HIGH RISK" },
  moderate: { bg: "bg-yellow-900/40", text: "text-yellow-400", border: "border-yellow-700", label: "MODERATE" },
  low: { bg: "bg-emerald-900/40", text: "text-emerald-400", border: "border-emerald-700", label: "LOW RISK" },
};

function Detail({
  label,
  value,
  mono,
}: {
  label: string;
  value: string | number | null | undefined;
  mono?: boolean;
}) {
  if (!value && value !== 0) return null;
  return (
    <div>
      <span className="text-[11px] uppercase tracking-wider text-gray-500">
        {label}
      </span>
      <p
        className={`text-sm mt-0.5 ${mono ? "font-mono text-gray-300" : "text-gray-100"}`}
      >
        {value}
      </p>
    </div>
  );
}

function ClinicalChecksGroup({
  checks,
  onChange,
}: {
  checks: ClinicalCheck[];
  onChange: (checks: ClinicalCheck[]) => void;
}) {
  const toggle = (check: ClinicalCheck) => {
    onChange(
      checks.includes(check)
        ? checks.filter((c) => c !== check)
        : [...checks, check],
    );
  };
  return (
    <div className="grid grid-cols-2 gap-2">
      {ALL_CHECKS.map((check) => (
        <label
          key={check}
          className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer hover:text-gray-100"
        >
          <input
            type="checkbox"
            checked={checks.includes(check)}
            onChange={() => toggle(check)}
            className="rounded border-gray-600 bg-gray-800 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
          />
          {CLINICAL_CHECK_LABELS[check]}
        </label>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// CDS Category Row
// ---------------------------------------------------------------------------

function CDSCategoryRow({
  name,
  data,
}: {
  name: string;
  data: ClinicalCategoryResult;
}) {
  const [expanded, setExpanded] = useState(data.status === "flagged");

  return (
    <div className="border-b border-gray-800/50 last:border-0">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between py-2 px-1 text-left hover:bg-gray-800/30 rounded transition-colors"
      >
        <span className="text-sm text-gray-200">
          {CATEGORY_LABELS[name] || name}
        </span>
        <span
          className={`text-xs font-medium px-2 py-0.5 rounded ${
            data.status === "flagged"
              ? "bg-yellow-900/40 text-yellow-400 border border-yellow-800/50"
              : "text-emerald-400"
          }`}
        >
          {data.status === "flagged" ? "\u26A0 FLAGGED" : "\u2713 CLEAR"}
        </span>
      </button>
      {expanded && data.findings.length > 0 && (
        <div className="pl-3 pb-2 space-y-2">
          {data.findings.map((f, i) => {
            const sev = SEVERITY_STYLES[f.severity] || SEVERITY_STYLES.low;
            return (
              <div
                key={i}
                className={`${sev.bg} border ${sev.border} rounded-md p-3`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`text-[10px] font-bold uppercase ${sev.text}`}
                  >
                    {f.severity}
                  </span>
                  <span className="text-xs text-gray-400">
                    {f.type.replace(/_/g, " ")}
                  </span>
                </div>
                <p className="text-sm text-gray-200">{f.description}</p>
                {f.recommendation && (
                  <p className="text-xs text-gray-400 mt-1">
                    <span className="text-gray-500">{"\u2192"}</span>{" "}
                    {f.recommendation}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// CDS Panel
// ---------------------------------------------------------------------------

function ClinicalDecisionSupport({
  rx,
  onFindingsUpdate,
}: {
  rx: Prescription;
  onFindingsUpdate: (findings: ClinicalReviewResult) => void;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showReasoning, setShowReasoning] = useState(false);
  const [showThinking, setShowThinking] = useState(false);

  const findings = rx.clinical_findings;
  const hasFindings = findings && !findings._error;

  const handleRunReview = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await runClinicalReview(rx.id);
      onFindingsUpdate(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Clinical review failed");
    } finally {
      setLoading(false);
    }
  };

  // Loading state
  if (loading) {
    return (
      <section className="bg-gray-900/70 border border-purple-900/40 rounded-lg p-4">
        <div className="flex items-center gap-3">
          <div className="animate-pulse flex items-center gap-2">
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
          <span className="text-sm text-purple-300">
            Analyzing prescription with AI clinical review...
          </span>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Running DUR, drug interactions, allergy screening, dose range, patient
          profile, and prescriber credential checks. This typically takes 15-60
          seconds.
        </p>
      </section>
    );
  }

  const risk = findings?.overall_risk;
  const riskStyle = risk ? RISK_STYLES[risk] || RISK_STYLES.low : null;

  const categories: (keyof ClinicalReviewResult)[] = [
    "dur_review",
    "drug_interactions",
    "allergy_screening",
    "dose_range",
    "patient_profile",
    "prescriber_credentials",
  ];

  return (
    <section
      className={`rounded-lg p-4 ${
        hasFindings
          ? `bg-gray-900/70 border ${riskStyle?.border || "border-gray-800"}`
          : "bg-gray-900/70 border border-gray-800"
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-medium text-purple-400 uppercase tracking-wider">
          Clinical Decision Support
        </h3>
        {riskStyle && (
          <span
            className={`text-xs font-bold px-2.5 py-1 rounded ${riskStyle.bg} ${riskStyle.text} border ${riskStyle.border}`}
          >
            {riskStyle.label}
          </span>
        )}
      </div>

      {/* Error from previous failed attempt */}
      {findings?._error && (
        <div className="bg-red-900/20 border border-red-800/50 rounded-md p-3 mb-3">
          <p className="text-xs text-red-400">{findings._error}</p>
        </div>
      )}

      {error && (
        <div className="bg-red-900/20 border border-red-800/50 rounded-md p-3 mb-3">
          <p className="text-xs text-red-400">{error}</p>
        </div>
      )}

      {/* Run / Re-run button */}
      {rx.status === "pending_review" && (
        <button
          type="button"
          onClick={handleRunReview}
          className="mb-3 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-md text-sm font-medium transition-colors flex items-center gap-2"
        >
          <span>{"\uD83D\uDD2C"}</span>
          {hasFindings ? "Re-run Analysis" : "Run Clinical Review"}
        </button>
      )}

      {/* Findings */}
      {hasFindings && (
        <>
          <div className="divide-y divide-gray-800/50">
            {categories.map((cat) => {
              const catData = findings[cat] as ClinicalCategoryResult | undefined;
              if (!catData) return null;
              return (
                <CDSCategoryRow key={cat} name={cat} data={catData} />
              );
            })}
          </div>

          {/* AI Reasoning (collapsible) */}
          {findings.reasoning && (
            <div className="mt-3">
              <button
                type="button"
                onClick={() => setShowReasoning(!showReasoning)}
                className="text-sm text-gray-400 hover:text-gray-200 flex items-center gap-1"
              >
                <span className="text-xs">
                  {showReasoning ? "\u25BC" : "\u25B6"}
                </span>
                AI Reasoning
              </button>
              {showReasoning && (
                <div className="mt-2 bg-gray-950/50 rounded-md p-3">
                  <p className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">
                    {findings.reasoning}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Model Thinking (collapsible, if available) */}
          {findings._thinking && (
            <div className="mt-2">
              <button
                type="button"
                onClick={() => setShowThinking(!showThinking)}
                className="text-sm text-gray-400 hover:text-gray-200 flex items-center gap-1"
              >
                <span className="text-xs">
                  {showThinking ? "\u25BC" : "\u25B6"}
                </span>
                Model Thinking
              </button>
              {showThinking && (
                <div className="mt-2 bg-gray-950/50 rounded-md p-3">
                  <p className="text-xs text-gray-500 whitespace-pre-wrap font-mono leading-relaxed">
                    {findings._thinking}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Metadata footer */}
          <div className="mt-3 pt-2 border-t border-gray-800/50 flex items-center justify-between">
            <span className="text-[10px] text-gray-600 font-mono">
              {findings._model}
              {findings._eval_duration_ms &&
                ` \u00B7 ${(findings._eval_duration_ms / 1000).toFixed(1)}s`}
              {findings._generated_at &&
                ` \u00B7 ${new Date(findings._generated_at).toLocaleDateString()}`}
            </span>
            <span className="text-[10px] text-gray-600">
              {"\u2695"} AI-assisted analysis \u2014 clinical judgment required
            </span>
          </div>
        </>
      )}

      {/* No findings and not pending */}
      {!hasFindings && rx.status !== "pending_review" && (
        <p className="text-xs text-gray-600">
          No clinical analysis was performed for this prescription.
        </p>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Main Form
// ---------------------------------------------------------------------------

interface Props {
  prescription: Prescription;
  onAction: () => void;
}

export function RxReviewForm({ prescription: initialRx, onAction }: Props) {
  const { user } = useAuth();
  const [rx, setRx] = useState(initialRx);
  const [notes, setNotes] = useState("");
  const [clinicalChecks, setClinicalChecks] = useState<ClinicalCheck[]>([]);
  const [showRejectPanel, setShowRejectPanel] = useState(false);
  const [rejectionReason, setRejectionReason] = useState<RejectionReason | "">("");
  const [followupAction, setFollowupAction] = useState<FollowupAction | "">("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showChecks, setShowChecks] = useState(false);
  const canReview = rx.status === "pending_review" && user?.role !== "agent";

  const handleFindingsUpdate = (findings: ClinicalReviewResult) => {
    setRx({ ...rx, clinical_findings: findings });
  };

  const handleApprove = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await approveRx(
        rx.id,
        user?.id ?? "",
        notes || undefined,
        clinicalChecks.length > 0 ? clinicalChecks : undefined,
      );
      onAction();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Approve failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!rejectionReason) {
      setError("Rejection reason is required");
      return;
    }
    if (!followupAction) {
      setError("Follow-up action is required");
      return;
    }
    if (!notes.trim()) {
      setError("Clinical notes are required for rejection");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await rejectRx(rx.id, user?.id ?? "", {
        notes: notes.trim(),
        rejection_reason: rejectionReason,
        followup_action: followupAction,
        clinical_checks: clinicalChecks,
      });
      onAction();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Reject failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Patient Card */}
      <section className="bg-gray-900/70 border border-gray-800 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider">
            Patient
          </h3>
          {rx.patient_id ? (
            <span className="text-[10px] bg-emerald-900/40 text-emerald-400 border border-emerald-800/50 px-1.5 py-0.5 rounded font-mono">
              Linked
            </span>
          ) : (
            <span className="text-[10px] bg-yellow-900/40 text-yellow-400 border border-yellow-800/50 px-1.5 py-0.5 rounded font-mono">
              Unlinked
            </span>
          )}
        </div>
        <div className="grid grid-cols-3 gap-4">
          <Detail
            label="Name"
            value={`${rx.patient_last_name}, ${rx.patient_first_name}`}
          />
          <Detail label="Date of Birth" value={rx.patient_dob} mono />
          <Detail label="Source" value={rx.source} />
        </div>
        {rx.patient_id && (
          <div className="mt-2 pt-2 border-t border-gray-800">
            <Detail label="Patient ID" value={rx.patient_id.slice(0, 8)} mono />
          </div>
        )}
      </section>

      {/* Prescriber Card */}
      <section className="bg-gray-900/70 border border-gray-800 rounded-lg p-4">
        <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">
          Prescriber
        </h3>
        <div className="grid grid-cols-3 gap-4">
          <Detail label="Name" value={rx.prescriber_name} />
          <Detail label="NPI" value={rx.prescriber_npi} mono />
          <Detail label="DEA" value={rx.prescriber_dea} mono />
        </div>
      </section>

      {/* Medication Card */}
      <section className="bg-gray-900/70 border border-blue-900/40 rounded-lg p-4">
        <h3 className="text-xs font-medium text-blue-400 uppercase tracking-wider mb-3">
          Medication
        </h3>
        <p className="text-base font-semibold text-gray-100 mb-3">
          {rx.drug_description}
        </p>
        <div className="grid grid-cols-4 gap-4 mb-3">
          <Detail label="NDC" value={rx.ndc} mono />
          <Detail label="Quantity" value={rx.quantity} />
          <Detail label="Days Supply" value={rx.days_supply} />
          <Detail label="Refills" value={rx.refills} />
        </div>
        <div className="grid grid-cols-2 gap-4 mb-3">
          <Detail label="Written Date" value={rx.written_date} mono />
          <Detail
            label="DAW"
            value={DAW_LABELS[rx.substitutions] || `Code ${rx.substitutions}`}
          />
        </div>
        <div className="bg-gray-950/50 rounded-md p-3 mt-2">
          <span className="text-[11px] uppercase tracking-wider text-gray-500">
            Sig
          </span>
          <p className="text-sm text-gray-100 mt-1">{rx.sig_text}</p>
        </div>
      </section>

      {/* Clinical Decision Support */}
      <ClinicalDecisionSupport rx={rx} onFindingsUpdate={handleFindingsUpdate} />

      {/* Pharmacist Review Section (pending_review only) */}
      {canReview && (
        <section className="border-t border-gray-800 pt-5">
          <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">
            Pharmacist Review
          </h3>

          {/* Clinical Checks (collapsible for approve, always visible for reject) */}
          {!showRejectPanel && (
            <div className="mb-4">
              <button
                type="button"
                onClick={() => setShowChecks(!showChecks)}
                className="text-sm text-gray-400 hover:text-gray-200 flex items-center gap-1 mb-2"
              >
                <span className="text-xs">{showChecks ? "\u25BC" : "\u25B6"}</span>
                Clinical Checks Performed
              </button>
              {showChecks && (
                <div className="bg-gray-900/50 rounded-lg p-3">
                  <ClinicalChecksGroup
                    checks={clinicalChecks}
                    onChange={setClinicalChecks}
                  />
                </div>
              )}
            </div>
          )}

          {/* Notes (always visible) */}
          {!showRejectPanel && (
            <div className="mb-4">
              <label className="text-sm text-gray-400">Notes</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="w-full mt-1 bg-gray-900 border border-gray-700 rounded-md p-3 text-sm text-gray-100 placeholder:text-gray-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                rows={3}
                placeholder="Clinical notes, DUR findings..."
              />
            </div>
          )}

          {/* Rejection Panel */}
          {showRejectPanel && (
            <div className="bg-red-950/20 border border-red-900/40 rounded-lg p-4 space-y-4 mb-4">
              <h4 className="text-xs font-medium text-red-400 uppercase tracking-wider">
                Rejection Documentation
              </h4>

              {/* Rejection Reason */}
              <div>
                <label className="text-sm text-gray-300 font-medium block mb-2">
                  Rejection Reason <span className="text-red-400">*</span>
                </label>
                <div className="space-y-2">
                  {(
                    Object.keys(REJECTION_REASON_LABELS) as RejectionReason[]
                  ).map((reason) => (
                    <label
                      key={reason}
                      className={`flex items-start gap-2 text-sm cursor-pointer p-2 rounded-md transition-colors ${
                        rejectionReason === reason
                          ? "bg-red-900/30 text-red-200"
                          : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
                      }`}
                    >
                      <input
                        type="radio"
                        name="rejectionReason"
                        value={reason}
                        checked={rejectionReason === reason}
                        onChange={() => setRejectionReason(reason)}
                        className="mt-0.5 border-gray-600 bg-gray-800 text-red-500 focus:ring-red-500 focus:ring-offset-0"
                      />
                      {REJECTION_REASON_LABELS[reason]}
                    </label>
                  ))}
                </div>
              </div>

              {/* Follow-up Action */}
              <div>
                <label className="text-sm text-gray-300 font-medium block mb-2">
                  Follow-up Action <span className="text-red-400">*</span>
                </label>
                <div className="space-y-2">
                  {(
                    Object.keys(FOLLOWUP_ACTION_LABELS) as FollowupAction[]
                  ).map((action) => (
                    <label
                      key={action}
                      className={`flex items-start gap-2 text-sm cursor-pointer p-2 rounded-md transition-colors ${
                        followupAction === action
                          ? "bg-yellow-900/30 text-yellow-200"
                          : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
                      }`}
                    >
                      <input
                        type="radio"
                        name="followupAction"
                        value={action}
                        checked={followupAction === action}
                        onChange={() => setFollowupAction(action)}
                        className="mt-0.5 border-gray-600 bg-gray-800 text-yellow-500 focus:ring-yellow-500 focus:ring-offset-0"
                      />
                      {FOLLOWUP_ACTION_LABELS[action]}
                    </label>
                  ))}
                </div>
              </div>

              {/* Clinical Checks */}
              <div>
                <label className="text-sm text-gray-300 font-medium block mb-2">
                  Clinical Checks Performed
                </label>
                <ClinicalChecksGroup
                  checks={clinicalChecks}
                  onChange={setClinicalChecks}
                />
              </div>

              {/* Clinical Notes (required for reject) */}
              <div>
                <label className="text-sm text-gray-300 font-medium block mb-1">
                  Clinical Notes <span className="text-red-400">*</span>
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full bg-gray-900 border border-gray-700 rounded-md p-3 text-sm text-gray-100 placeholder:text-gray-600 focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500"
                  rows={3}
                  placeholder="Document clinical reasoning for rejection..."
                />
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-300 text-sm mb-3">
              {error}
            </div>
          )}

          {/* Action Buttons */}
          {!showRejectPanel ? (
            <div className="flex gap-3">
              <button
                onClick={handleApprove}
                disabled={submitting}
                className="px-5 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm font-medium disabled:opacity-50 transition-colors"
              >
                {submitting ? "Processing..." : "Approve Rx"}
              </button>
              <button
                onClick={() => {
                  setShowRejectPanel(true);
                  setError(null);
                }}
                disabled={submitting}
                className="px-5 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-md text-sm font-medium disabled:opacity-50 transition-colors"
              >
                Reject Rx
              </button>
            </div>
          ) : (
            <div className="flex gap-3">
              <button
                onClick={handleReject}
                disabled={submitting}
                className="px-5 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-md text-sm font-medium disabled:opacity-50 transition-colors"
              >
                {submitting ? "Processing..." : "Confirm Rejection"}
              </button>
              <button
                onClick={() => {
                  setShowRejectPanel(false);
                  setRejectionReason("");
                  setFollowupAction("");
                  setError(null);
                }}
                disabled={submitting}
                className="px-5 py-2.5 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-md text-sm font-medium disabled:opacity-50 transition-colors"
              >
                Cancel
              </button>
            </div>
          )}
        </section>
      )}

      {/* Decision Summary (post-review) */}
      {(rx.status === "approved" || rx.status === "rejected") && (
        <section className="border-t border-gray-800 pt-5">
          <div
            className={`rounded-lg p-4 ${
              rx.status === "approved"
                ? "bg-green-900/20 border border-green-800/50"
                : "bg-red-900/20 border border-red-800/50"
            }`}
          >
            {/* Header: status + pharmacist + timestamp */}
            <div className="flex items-center justify-between mb-3">
              <h3
                className={`text-xs font-medium uppercase tracking-wider ${
                  rx.status === "approved" ? "text-green-400" : "text-red-400"
                }`}
              >
                {rx.status === "approved" ? "Approved" : "Rejected"}
              </h3>
              <span className="text-xs text-gray-400">
                {rx.reviewer_name || (rx.reviewed_by ? rx.reviewed_by.slice(0, 8) : "")}
                {rx.reviewed_at &&
                  ` \u2014 ${new Date(rx.reviewed_at).toLocaleString()}`}
              </span>
            </div>

            {/* Rejection Reason + Follow-up (rejected only) */}
            {rx.status === "rejected" && rx.rejection_reason && (
              <div className="grid grid-cols-2 gap-4 mb-3">
                <div>
                  <span className="text-[11px] uppercase tracking-wider text-gray-500">
                    Reason
                  </span>
                  <p className="text-sm text-red-300 mt-0.5">
                    {REJECTION_REASON_LABELS[rx.rejection_reason] ||
                      rx.rejection_reason}
                  </p>
                </div>
                {rx.followup_action && (
                  <div>
                    <span className="text-[11px] uppercase tracking-wider text-gray-500">
                      Follow-up
                    </span>
                    <p className="text-sm text-yellow-300 mt-0.5">
                      {FOLLOWUP_ACTION_LABELS[rx.followup_action] ||
                        rx.followup_action}
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Clinical Checks */}
            {rx.clinical_checks && rx.clinical_checks.length > 0 && (
              <div className="mb-3">
                <span className="text-[11px] uppercase tracking-wider text-gray-500">
                  Clinical Checks
                </span>
                <div className="flex flex-wrap gap-1.5 mt-1">
                  {rx.clinical_checks.map((check) => (
                    <span
                      key={check}
                      className="text-[11px] bg-gray-800 text-gray-300 px-2 py-0.5 rounded border border-gray-700"
                    >
                      {CLINICAL_CHECK_LABELS[check] || check}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Clinical Notes */}
            {rx.review_notes && (
              <div>
                <span className="text-[11px] uppercase tracking-wider text-gray-500">
                  Clinical Notes
                </span>
                <p className="text-sm text-gray-300 mt-1 whitespace-pre-wrap">
                  {rx.review_notes}
                </p>
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
