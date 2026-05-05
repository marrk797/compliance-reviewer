/**
 * End-to-end browser-only compliance pipeline.
 *
 * Inputs: regulatory File, company File, Groq API key.
 * Output: a structured ReportOut, persisted to localStorage.
 *
 * Stages are reported through ``onProgress`` so the UI can show a live
 * status. Files never leave the browser; the Groq call sees only short
 * excerpts plus the requirement text.
 */

import { chunkText } from "./chunk";
import { evaluateRequirement } from "./compliance";
import { embed, EMBEDDING_DIM } from "./embed";
import { extractText } from "./parse";
import { extractRequirements } from "./requirements";
import { topK } from "./retrieval";
import { saveReport } from "./storage";
import type {
  ComplianceStatus,
  FindingOut,
  ReportOut,
  ReportSummary,
} from "./types";

export interface PipelineInputs {
  regulatoryFile: File;
  companyFile: File;
  apiKey: string;
  model?: string;
  topK?: number;
}

export type PipelineStage =
  | "parse"
  | "extract"
  | "chunk"
  | "model_load"
  | "embed"
  | "evaluate"
  | "done";

export interface PipelineProgress {
  stage: PipelineStage;
  message: string;
  current?: number;
  total?: number;
}

export async function runPipeline(
  inputs: PipelineInputs,
  onProgress: (p: PipelineProgress) => void = () => {},
): Promise<ReportOut> {
  const reportId =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `r-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  const created_at = new Date().toISOString();

  const baseReport: ReportOut = {
    id: reportId,
    status: "running",
    regulatory_document: {
      kind: "regulatory",
      filename: inputs.regulatoryFile.name,
      size_bytes: inputs.regulatoryFile.size,
    },
    company_document: {
      kind: "company",
      filename: inputs.companyFile.name,
      size_bytes: inputs.companyFile.size,
    },
    summary: null,
    error_message: null,
    created_at,
    completed_at: null,
    findings: [],
  };
  saveReport(baseReport);

  try {
    onProgress({ stage: "parse", message: "Parsing regulatory document…" });
    const regulatoryText = await extractText(inputs.regulatoryFile);
    onProgress({ stage: "parse", message: "Parsing company submission…" });
    const companyText = await extractText(inputs.companyFile);

    onProgress({ stage: "extract", message: "Extracting requirements…" });
    const requirements = extractRequirements(regulatoryText);
    if (requirements.length === 0) {
      throw new Error(
        "No requirements could be extracted from the regulatory document.",
      );
    }

    onProgress({ stage: "chunk", message: "Chunking company submission…" });
    const chunks = chunkText(companyText);
    if (chunks.length === 0) {
      throw new Error("Company document produced no usable chunks.");
    }

    onProgress({
      stage: "model_load",
      message: "Loading embedding model (one-time ~70 MB download)…",
    });
    const embedTexts = [
      ...requirements.map((r) => r.text),
      ...chunks.map((c) => c.text),
    ];
    const allVectors = await embed(embedTexts, (info) => {
      if (info.progress !== undefined && info.status) {
        onProgress({
          stage: "model_load",
          message: `${info.status} (${Math.round((info.progress ?? 0) * 100)}%)`,
        });
      }
    });
    onProgress({ stage: "embed", message: "Embedded all texts" });
    if (allVectors.length !== embedTexts.length) {
      throw new Error("Unexpected embedding count");
    }
    if (allVectors[0]?.length && allVectors[0].length !== EMBEDDING_DIM) {
      throw new Error(
        `Embedding dimension ${allVectors[0].length} != ${EMBEDDING_DIM}`,
      );
    }
    const requirementVectors = allVectors.slice(0, requirements.length);
    const chunkVectors = allVectors.slice(requirements.length);

    const k = Math.min(inputs.topK ?? 6, chunks.length);
    const findings: FindingOut[] = [];
    for (let i = 0; i < requirements.length; i++) {
      const req = requirements[i];
      onProgress({
        stage: "evaluate",
        message: `Evaluating requirement ${i + 1}/${requirements.length}`,
        current: i + 1,
        total: requirements.length,
      });
      const top = topK(requirementVectors[i], chunkVectors, chunks, k);
      const finding = await evaluateRequirement({
        apiKey: inputs.apiKey,
        model: inputs.model,
        ordinal: i,
        requirementId: req.requirement_id,
        requirementText: req.text,
        excerpts: top.map((t) => ({
          ordinal: t.ordinal,
          text: t.text,
          similarity: t.similarity,
        })),
      });
      findings.push(finding);
    }

    const report: ReportOut = {
      ...baseReport,
      status: "completed",
      summary: summarize(findings),
      findings,
      completed_at: new Date().toISOString(),
    };
    saveReport(report);
    onProgress({ stage: "done", message: "Done" });
    return report;
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Unknown pipeline error";
    const report: ReportOut = {
      ...baseReport,
      status: "failed",
      error_message: message.slice(0, 500),
      completed_at: new Date().toISOString(),
    };
    saveReport(report);
    return report;
  }
}

function summarize(findings: FindingOut[]): ReportSummary {
  const counts: Record<ComplianceStatus, number> = {
    compliant: 0,
    non_compliant: 0,
    partially_compliant: 0,
    not_found: 0,
    needs_human_review: 0,
  };
  for (const f of findings) counts[f.status] += 1;
  return {
    total_requirements: findings.length,
    ...counts,
  };
}
