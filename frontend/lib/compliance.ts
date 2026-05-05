/**
 * Per-requirement compliance evaluator.
 *
 * Mirrors the original Python evaluator: build a tightly-scoped prompt
 * containing only the retrieved excerpts (never the full company doc),
 * call Groq in JSON mode, then coerce the response into a strictly-typed
 * ``FindingOut`` shape.
 */

import { completeJson, DEFAULT_MODEL } from "./groq";
import type {
  ComplianceStatus,
  EvidenceItem,
  FindingOut,
  RiskLevel,
} from "./types";

export interface ExcerptForEval {
  ordinal: number;
  text: string;
  similarity: number;
}

const STATUSES: ComplianceStatus[] = [
  "compliant",
  "non_compliant",
  "partially_compliant",
  "not_found",
  "needs_human_review",
];
const RISKS: RiskLevel[] = ["low", "medium", "high"];

const SYSTEM_PROMPT =
  "You are an assistant supporting a human compliance reviewer. " +
  "You compare a single regulatory requirement against excerpts from a company submission. " +
  "You must NOT provide legal advice; your role is to help a human auditor by structuring evidence. " +
  "Base your assessment ONLY on the provided excerpts; do not invent information. " +
  "If the excerpts are insufficient, return status \"not_found\" or \"needs_human_review\".";

const SCHEMA_HINT = `{
  "status": "compliant" | "non_compliant" | "partially_compliant" | "not_found" | "needs_human_review",
  "confidence": number between 0 and 1,
  "risk_level": "low" | "medium" | "high",
  "explanation": string (1-3 sentences, plain English, no legal advice),
  "suggested_fix": string (concrete action; empty string if compliant),
  "evidence": [
    { "chunk_ordinal": integer or null, "quote": string (verbatim from excerpts) }
  ]
}`;

export async function evaluateRequirement(args: {
  apiKey: string;
  model?: string;
  ordinal: number;
  requirementId: string;
  requirementText: string;
  excerpts: ExcerptForEval[];
}): Promise<FindingOut> {
  const numbered = args.excerpts
    .map(
      (ex) =>
        `[chunk ${ex.ordinal} | similarity ${ex.similarity.toFixed(3)}]\n${ex.text}`,
    )
    .join("\n\n");
  const userPrompt =
    `Regulatory requirement ${args.requirementId}:\n${args.requirementText}\n\n` +
    `Company submission excerpts:\n${numbered || "(no excerpts retrieved)"}`;

  let raw: Record<string, unknown>;
  try {
    raw = await completeJson<Record<string, unknown>>({
      apiKey: args.apiKey,
      model: args.model ?? DEFAULT_MODEL,
      system: SYSTEM_PROMPT,
      user: userPrompt,
      schemaHint: SCHEMA_HINT,
    });
  } catch (err) {
    return fallback(args, `LLM call failed: ${(err as Error).message}`);
  }

  return coerce(args, raw);
}

function coerce(
  args: { ordinal: number; requirementId: string; requirementText: string },
  raw: Record<string, unknown>,
): FindingOut {
  const status = (STATUSES as string[]).includes(String(raw.status))
    ? (raw.status as ComplianceStatus)
    : "needs_human_review";
  const risk = (RISKS as string[]).includes(String(raw.risk_level))
    ? (raw.risk_level as RiskLevel)
    : "medium";
  const confidence = clamp(Number(raw.confidence ?? 0), 0, 1);
  const explanation =
    typeof raw.explanation === "string" ? raw.explanation.trim() : "";
  const suggested_fix =
    typeof raw.suggested_fix === "string" ? raw.suggested_fix.trim() : "";
  const evidence: EvidenceItem[] = Array.isArray(raw.evidence)
    ? raw.evidence
        .map((e: unknown): EvidenceItem | null => {
          if (typeof e !== "object" || e === null) return null;
          const obj = e as { chunk_ordinal?: unknown; quote?: unknown };
          const quote = typeof obj.quote === "string" ? obj.quote.trim() : "";
          if (!quote) return null;
          const chunk_ordinal =
            typeof obj.chunk_ordinal === "number" ? obj.chunk_ordinal : null;
          return { chunk_ordinal, quote };
        })
        .filter((e: EvidenceItem | null): e is EvidenceItem => e !== null)
        .slice(0, 8)
    : [];
  return {
    ordinal: args.ordinal,
    requirement_id: args.requirementId,
    requirement_text: args.requirementText,
    status,
    confidence,
    risk_level: risk,
    explanation,
    suggested_fix,
    evidence,
  };
}

function fallback(
  args: { ordinal: number; requirementId: string; requirementText: string },
  reason: string,
): FindingOut {
  return {
    ordinal: args.ordinal,
    requirement_id: args.requirementId,
    requirement_text: args.requirementText,
    status: "needs_human_review",
    confidence: 0,
    risk_level: "medium",
    explanation: reason,
    suggested_fix: "",
    evidence: [],
  };
}

function clamp(n: number, lo: number, hi: number): number {
  if (Number.isNaN(n)) return lo;
  return Math.min(hi, Math.max(lo, n));
}
