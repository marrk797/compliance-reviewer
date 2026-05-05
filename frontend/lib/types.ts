/**
 * Shared types for the in-browser compliance pipeline.
 *
 * Mirrors the original FastAPI schema so the existing /reports/[id] UI
 * doesn't need a structural rewrite.
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

export interface DocumentMeta {
  kind: DocumentKind;
  filename: string;
  size_bytes: number;
}

export interface ReportOut {
  id: string;
  status: ReportStatus;
  regulatory_document: DocumentMeta | null;
  company_document: DocumentMeta | null;
  summary: ReportSummary | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  findings: FindingOut[];
}
