/**
 * localStorage wrappers.
 *
 * - Groq API key (so the user only has to paste it once per browser).
 * - Acknowledgement flag (so we don't re-ask after the first review).
 * - Generated reports (the structured output, not the source documents).
 *
 * Nothing here ever crosses the network.
 */

import type { ReportOut } from "./types";

const KEY_GROQ = "compliance_reviewer:groq_api_key";
const KEY_MODEL = "compliance_reviewer:groq_model";
const KEY_ACK = "compliance_reviewer:acknowledged";
const KEY_REPORTS = "compliance_reviewer:reports";

function safeWindow(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function getGroqKey(): string | null {
  return safeWindow()?.getItem(KEY_GROQ) ?? null;
}

export function setGroqKey(key: string | null): void {
  const ls = safeWindow();
  if (!ls) return;
  if (key && key.trim()) ls.setItem(KEY_GROQ, key.trim());
  else ls.removeItem(KEY_GROQ);
}

export function getGroqModel(): string | null {
  return safeWindow()?.getItem(KEY_MODEL) ?? null;
}

export function setGroqModel(model: string | null): void {
  const ls = safeWindow();
  if (!ls) return;
  if (model && model.trim()) ls.setItem(KEY_MODEL, model.trim());
  else ls.removeItem(KEY_MODEL);
}

export function getAcknowledged(): boolean {
  return safeWindow()?.getItem(KEY_ACK) === "true";
}

export function setAcknowledged(ack: boolean): void {
  const ls = safeWindow();
  if (!ls) return;
  if (ack) ls.setItem(KEY_ACK, "true");
  else ls.removeItem(KEY_ACK);
}

export function listReports(): ReportOut[] {
  const ls = safeWindow();
  if (!ls) return [];
  const raw = ls.getItem(KEY_REPORTS);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed as ReportOut[];
  } catch {
    return [];
  }
}

export function saveReport(report: ReportOut): void {
  const ls = safeWindow();
  if (!ls) return;
  const all = listReports().filter((r) => r.id !== report.id);
  all.unshift(report);
  ls.setItem(KEY_REPORTS, JSON.stringify(all.slice(0, 50)));
}

export function getReport(id: string): ReportOut | null {
  return listReports().find((r) => r.id === id) ?? null;
}

export function deleteReport(id: string): void {
  const ls = safeWindow();
  if (!ls) return;
  const all = listReports().filter((r) => r.id !== id);
  ls.setItem(KEY_REPORTS, JSON.stringify(all));
}
