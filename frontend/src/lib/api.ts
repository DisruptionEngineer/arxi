import type {
  AuthUser,
  ClinicalCheck,
  ClinicalReviewResult,
  FollowupAction,
  Patient,
  PatientListResponse,
  PipelineCallbacks,
  PrescribeAssistResult,
  Prescription,
  QueueResponse,
  RejectionReason,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const apiFetch = (path: string, init?: RequestInit) =>
  fetch(`${API_BASE}${path}`, { credentials: "include", ...init });

// --- Auth ---

export async function login(username: string, password: string): Promise<AuthUser> {
  const res = await apiFetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Login failed" }));
    throw new Error(err.detail || "Login failed");
  }
  return res.json();
}

export async function logout(): Promise<void> {
  await apiFetch("/api/auth/logout", { method: "POST" });
}

export async function fetchMe(): Promise<AuthUser | null> {
  const res = await apiFetch("/api/auth/me");
  if (!res.ok) return null;
  return res.json();
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  const res = await apiFetch("/api/auth/change-password", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed" }));
    throw new Error(err.detail || "Password change failed");
  }
}

export async function fetchToken(): Promise<string> {
  const res = await apiFetch("/api/auth/token");
  if (!res.ok) throw new Error("Failed to get auth token");
  const body = await res.json();
  return body.token;
}

// --- Intake ---

export async function fetchQueue(status?: string): Promise<QueueResponse> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const res = await apiFetch(`/api/intake/queue?${params}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to fetch queue" }));
    throw new Error(err.detail || "Failed to fetch queue");
  }
  return res.json();
}

export async function fetchPrescription(id: string): Promise<Prescription> {
  const res = await apiFetch(`/api/intake/${id}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Prescription not found" }));
    throw new Error(err.detail || "Prescription not found");
  }
  return res.json();
}

export async function approveRx(
  id: string,
  pharmacistId: string,
  notes?: string,
  clinicalChecks?: ClinicalCheck[],
): Promise<Prescription> {
  const res = await apiFetch(`/api/intake/${id}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pharmacist_id: pharmacistId,
      notes,
      clinical_checks: clinicalChecks ?? [],
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to approve" }));
    throw new Error(err.detail || "Failed to approve");
  }
  return res.json();
}

export async function rejectRx(
  id: string,
  pharmacistId: string,
  data: {
    notes: string;
    rejection_reason: RejectionReason;
    followup_action: FollowupAction;
    clinical_checks: ClinicalCheck[];
  },
): Promise<Prescription> {
  const res = await apiFetch(`/api/intake/${id}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pharmacist_id: pharmacistId,
      ...data,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to reject" }));
    throw new Error(err.detail || "Failed to reject");
  }
  return res.json();
}

// --- Clinical Decision Support ---

export async function runClinicalReview(rxId: string): Promise<ClinicalReviewResult> {
  const res = await apiFetch(`/api/intake/${rxId}/clinical-review`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Clinical review failed" }));
    throw new Error(err.detail || "Clinical review failed");
  }
  return res.json();
}

export async function prescribeAssist(
  patientId: string,
  drugId: string,
  prescriberNpi: string,
): Promise<PrescribeAssistResult> {
  const res = await apiFetch("/api/intake/prescribe-assist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      patient_id: patientId,
      drug_id: drugId,
      prescriber_npi: prescriberNpi,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Prescribe assist failed" }));
    throw new Error(err.detail || "Prescribe assist failed");
  }
  return res.json();
}

// --- Manual Entry ---

export async function createManualRx(data: import("./types").ManualRxInput): Promise<Prescription> {
  const res = await apiFetch("/api/intake/manual", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to create prescription" }));
    throw new Error(err.detail || "Failed to create prescription");
  }
  return res.json();
}

// --- E-prescribe Ingest ---

export async function ingestNewRx(xmlContent: string): Promise<Prescription> {
  const res = await apiFetch("/api/intake/newrx", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(xmlContent),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to ingest e-prescription" }));
    throw new Error(err.detail || "Failed to ingest e-prescription");
  }
  return res.json();
}

// --- Prescriber NPI ---

export async function validateNPI(npi: string): Promise<import("./types").NPIValidationResult> {
  const res = await apiFetch(`/api/prescribers/validate-npi/${encodeURIComponent(npi)}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "NPI validation failed" }));
    throw new Error(err.detail || "NPI validation failed");
  }
  return res.json();
}

// --- Drugs ---

export async function searchDrugs(query: string, limit = 15): Promise<import("./types").DrugSearchResponse> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  const res = await apiFetch(`/api/drugs/search?${params}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Drug search failed" }));
    throw new Error(err.detail || "Drug search failed");
  }
  return res.json();
}

// --- Patients ---

export async function fetchPatients(limit = 50, offset = 0): Promise<PatientListResponse> {
  const res = await apiFetch(`/api/patients?limit=${limit}&offset=${offset}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to fetch patients" }));
    throw new Error(err.detail || "Failed to fetch patients");
  }
  return res.json();
}

export async function fetchPatient(id: string): Promise<Patient> {
  const res = await apiFetch(`/api/patients/${id}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Patient not found" }));
    throw new Error(err.detail || "Patient not found");
  }
  return res.json();
}

export async function fetchPatientPrescriptions(patientId: string): Promise<{ prescriptions: Prescription[] }> {
  const res = await apiFetch(`/api/patients/${patientId}/prescriptions`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to fetch patient prescriptions" }));
    throw new Error(err.detail || "Failed to fetch patient prescriptions");
  }
  return res.json();
}

// --- Patient Rx Context ---

export async function fetchPatientRxContext(patientId: string): Promise<import("./types").RxContextResponse> {
  const res = await apiFetch(`/api/patients/${patientId}/rx-context`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to fetch rx context" }));
    throw new Error(err.detail || "Failed to fetch rx context");
  }
  return res.json();
}

export async function fetchDrugByNdc(ndc: string): Promise<import("./types").Drug> {
  const res = await apiFetch(`/api/drugs/ndc/${encodeURIComponent(ndc)}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Drug not found" }));
    throw new Error(err.detail || "Drug not found");
  }
  return res.json();
}

// --- SSE Streaming ---

async function parseSSEStream(response: Response, callbacks: PipelineCallbacks): Promise<void> {
  const reader = response.body?.getReader();
  if (!reader) {
    callbacks.onError("No response body");
    return;
  }
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let eventType = "";
    let dataBuffer = "";

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        eventType = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        dataBuffer += line.slice(6);
      } else if (line === "" && eventType && dataBuffer) {
        try {
          const data = JSON.parse(dataBuffer);
          switch (eventType) {
            case "stage":
              callbacks.onStage(data);
              break;
            case "token":
              callbacks.onToken(data.text);
              break;
            case "complete":
              callbacks.onComplete(data);
              break;
            case "error":
              callbacks.onError(data.message || "Unknown error");
              break;
          }
        } catch {
          // skip malformed events
        }
        eventType = "";
        dataBuffer = "";
      }
    }
  }
}

export async function streamClinicalReview(rxId: string, callbacks: PipelineCallbacks): Promise<void> {
  const res = await apiFetch(`/api/intake/${rxId}/clinical-review-stream`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Stream failed" }));
    callbacks.onError(err.detail || "Stream failed");
    return;
  }
  await parseSSEStream(res, callbacks);
}

export async function streamPrescribeAssist(
  patientId: string,
  drugId: string,
  prescriberNpi: string,
  callbacks: PipelineCallbacks,
): Promise<void> {
  const res = await apiFetch("/api/intake/prescribe-assist-stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      patient_id: patientId,
      drug_id: drugId,
      prescriber_npi: prescriberNpi,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Stream failed" }));
    callbacks.onError(err.detail || "Stream failed");
    return;
  }
  await parseSSEStream(res, callbacks);
}

// --- Audit ---

export async function fetchAuditLogs(params: import("./types").AuditLogParams = {}): Promise<import("./types").AuditLogResponse> {
  const query = new URLSearchParams();
  if (params.action) query.set("action", params.action);
  if (params.actor_id) query.set("actor_id", params.actor_id);
  if (params.resource_id) query.set("resource_id", params.resource_id);
  if (params.resource_type) query.set("resource_type", params.resource_type);
  if (params.from_date) query.set("from_date", params.from_date);
  if (params.to_date) query.set("to_date", params.to_date);
  if (params.search) query.set("search", params.search);
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.offset !== undefined) query.set("offset", String(params.offset));
  const res = await apiFetch(`/api/audit/logs?${query}`);
  if (!res.ok) {
    if (res.status === 403) throw new Error("Access denied");
    const err = await res.json().catch(() => ({ detail: "Failed to fetch audit logs" }));
    throw new Error(err.detail || "Failed to fetch audit logs");
  }
  return res.json();
}
