/**
 * Tiny typed fetch helper for the FastAPI backend.
 *
 * Stores the JWT in localStorage. We avoid a third-party state library to
 * keep the MVP dependency surface minimal.
 */

export type ComplianceStatus =
  | "compliant"
  | "non_compliant"
  | "partially_compliant"
  | "not_found"
  | "needs_human_review";

export type RiskLevel = "low" | "medium" | "high";

export type ReportStatus = "pending" | "running" | "completed" | "failed";

export type DocumentKind = "regulatory" | "company";

export interface DocumentOut {
  id: string;
  kind: DocumentKind;
  status: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  created_at: string;
  deleted_at: string | null;
}

export interface EvidenceItem {
  chunk_ordinal: number | null;
  quote: string;
  score?: number | null;
}

export interface FindingOut {
  ordinal: number;
  requirement_id: string;
  requirement_text: string;
  status: ComplianceStatus;
  confidence: number;
  risk_level: RiskLevel;
  explanation: string;
  suggested_fix: string;
  evidence: EvidenceItem[];
}

export interface ReportSummary {
  total_requirements: number;
  compliant: number;
  non_compliant: number;
  partially_compliant: number;
  not_found: number;
  needs_human_review: number;
}

export interface ReportOut {
  id: string;
  status: ReportStatus;
  regulatory_document_id: string | null;
  company_document_id: string | null;
  summary: ReportSummary | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  findings: FindingOut[];
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
}

export interface UserOut {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

const TOKEN_KEY = "compliance_reviewer_token";

export function getApiBase(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) {
    window.localStorage.setItem(TOKEN_KEY, token);
  } else {
    window.localStorage.removeItem(TOKEN_KEY);
  }
}

class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`API error ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

export { ApiError };

async function request<T>(
  path: string,
  init: RequestInit & { auth?: boolean } = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (init.auth !== false && token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (
    !(init.body instanceof FormData) &&
    init.body !== undefined &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`${getApiBase()}${path}`, {
    ...init,
    headers,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = typeof data?.detail === "string" ? data.detail : JSON.stringify(data);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  register(email: string, password: string): Promise<UserOut> {
    return request<UserOut>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
      auth: false,
    });
  },
  login(email: string, password: string): Promise<TokenResponse> {
    return request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
      auth: false,
    });
  },
  me(): Promise<UserOut> {
    return request<UserOut>("/auth/me");
  },
  uploadDocument(file: File, kind: DocumentKind): Promise<DocumentOut> {
    const form = new FormData();
    form.append("file", file);
    form.append("kind", kind);
    return request<DocumentOut>("/uploads", {
      method: "POST",
      body: form,
    });
  },
  createReport(
    regulatoryDocumentId: string,
    companyDocumentId: string,
  ): Promise<ReportOut> {
    return request<ReportOut>("/reports", {
      method: "POST",
      body: JSON.stringify({
        regulatory_document_id: regulatoryDocumentId,
        company_document_id: companyDocumentId,
      }),
    });
  },
  listReports(): Promise<ReportOut[]> {
    return request<ReportOut[]>("/reports");
  },
  getReport(id: string): Promise<ReportOut> {
    return request<ReportOut>(`/reports/${id}`);
  },
  disclaimer(): Promise<{ notice: string; delete_source_files_after_processing: string }> {
    return request("/disclaimer", { auth: false });
  },
};
