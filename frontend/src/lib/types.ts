export type RxStatus = "received" | "parsed" | "validated" | "pending_review" | "approved" | "rejected" | "corrected";

export type RejectionReason =
  | "clinical_concern"
  | "incomplete_rx"
  | "dur_issue"
  | "prescriber_contact"
  | "insurance_issue"
  | "patient_safety"
  | "other";

export type FollowupAction =
  | "contact_prescriber"
  | "contact_patient"
  | "request_prior_auth"
  | "return_to_prescriber"
  | "no_action";

export type ClinicalCheck =
  | "dur_review"
  | "drug_interactions"
  | "allergy_screening"
  | "dose_range"
  | "patient_profile"
  | "prescriber_credentials";

export interface PatientAllergy {
  substance: string;
  reaction: string;
  severity: "mild" | "moderate" | "severe";
}

export interface Patient {
  id: string;
  first_name: string;
  last_name: string;
  gender: string;
  date_of_birth: string;
  address_line1: string;
  city: string;
  state: string;
  postal_code: string;
  allergies: PatientAllergy[] | null;
  conditions: string[] | null;
}

export interface PatientListResponse {
  patients: Patient[];
  total: number;
}

export interface Prescription {
  id: string;
  status: RxStatus;
  source: string;
  patient_id: string | null;
  patient_first_name: string;
  patient_last_name: string;
  patient_dob: string;
  prescriber_name: string;
  prescriber_npi: string;
  prescriber_dea: string;
  drug_description: string;
  ndc: string;
  quantity: number;
  days_supply: number;
  refills: number;
  sig_text: string;
  written_date: string;
  substitutions: number;
  created_at: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_notes: string | null;
  rejection_reason: RejectionReason | null;
  followup_action: FollowupAction | null;
  clinical_checks: ClinicalCheck[] | null;
  reviewer_name: string | null;
  clinical_findings: ClinicalReviewResult | null;
}

export interface QueueResponse {
  prescriptions: Prescription[];
  total: number;
}

export interface ManualRxInput {
  patient_first_name: string;
  patient_last_name: string;
  patient_dob: string;
  prescriber_name: string;
  prescriber_npi: string;
  prescriber_dea: string;
  drug_description: string;
  ndc: string;
  quantity: number;
  days_supply: number;
  refills: number;
  sig_text: string;
  written_date: string;
  substitutions: number;
}

// --- Clinical Decision Support ---

export interface ClinicalFinding {
  type: string;
  severity: "high" | "moderate" | "low";
  description: string;
  recommendation: string;
}

export interface ClinicalCategoryResult {
  status: "flagged" | "clear";
  findings: ClinicalFinding[];
}

export interface ClinicalReviewResult {
  dur_review: ClinicalCategoryResult;
  drug_interactions: ClinicalCategoryResult;
  allergy_screening: ClinicalCategoryResult;
  dose_range: ClinicalCategoryResult;
  patient_profile: ClinicalCategoryResult;
  prescriber_credentials: ClinicalCategoryResult;
  overall_risk: "high" | "moderate" | "low";
  reasoning: string;
  _thinking?: string | null;
  _model?: string;
  _generated_at?: string;
  _eval_duration_ms?: number;
  _trigger?: string;
  _error?: string;
}

export interface PrescribeAssistResult {
  drug_description: string;
  ndc: string;
  rx_classification: "routine" | "stat_supply" | "acute" | "prn";
  classification_reasoning: string;
  quantity: number;
  days_supply: number;
  refills: number;
  sig_text: string;
  substitutions: number;
  reasoning: string;
  _thinking?: string | null;
  _model?: string;
  _generated_at?: string;
  _eval_duration_ms?: number;
}

// --- Drug ---

export interface Drug {
  id: string;
  ndc: string;
  drug_name: string;
  generic_name: string;
  dosage_form: string;
  strength: string;
  route: string;
  manufacturer: string;
  dea_schedule: string;
  package_description: string;
}

export interface DrugSearchResponse {
  drugs: Drug[];
  total: number;
}

// --- Patient Rx Context (New Rx workflow) ---

export interface PrescriberSummary {
  npi: string;
  name: string;
  dea: string;
  rx_count: number;
  last_rx_date: string;
}

export interface RefillCandidate {
  drug_description: string;
  ndc: string;
  drug_id: string | null;
  generic_name: string;
  strength: string;
  dosage_form: string;
  last_fill_date: string;
  last_status: string;
  remaining_refills: number;
  prescriber_name: string;
  prescriber_npi: string;
}

export interface RxContextResponse {
  prescribers: PrescriberSummary[];
  refill_candidates: RefillCandidate[];
}

// --- NPI Validation ---

export interface NPIValidationResult {
  valid: boolean;
  message: string;
  npi: string;
  found: boolean;
  name: string;
  credential: string;
  gender: string;
  enumeration_type: string;
  specialty: string;
  address_city: string;
  address_state: string;
  status: string;
}

export interface AuthUser {
  id: string;
  username: string;
  full_name: string;
  role: string;
}

// --- Audit ---

export interface FieldChange {
  field: string;
  from_value: string | null;
  to_value: string | null;
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  action: string;
  actor_id: string;
  actor_role: string;
  resource_type: string;
  resource_id: string;
  detail: Record<string, unknown> | null;
  changes: FieldChange[];
}

export interface AuditLogResponse {
  logs: AuditLogEntry[];
  total: number;
}

export interface AuditLogParams {
  action?: string;
  actor_id?: string;
  resource_id?: string;
  resource_type?: string;
  from_date?: string;
  to_date?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

// --- WebSocket Events ---

export interface PharmaEvent {
  type: "prescription.status_changed" | "patient.linked" | "patient.created";
  resource_id: string;
  data: Record<string, unknown>;
  actor_id: string;
  timestamp: string;
}

// --- AI Pipeline Streaming ---

export type PipelineStage = "data_gathering" | "prompt_construction" | "llm_inference" | "response_parsing";

export interface PipelineStageEvent {
  stage: PipelineStage;
  status: "started" | "complete";
  timing_ms?: number;
  context?: Record<string, unknown>;
  prompt_preview?: string;
  prompt_length?: number;
  model?: string;
}

export interface PipelineCallbacks {
  onStage: (event: PipelineStageEvent) => void;
  onToken: (text: string) => void;
  onComplete: (result: ClinicalReviewResult | PrescribeAssistResult) => void;
  onError: (error: string) => void;
}
