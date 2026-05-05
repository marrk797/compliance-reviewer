"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import {
  ApiError,
  ComplianceStatus,
  FindingOut,
  ReportOut,
  RiskLevel,
  api,
  getToken,
} from "@/lib/api";

const STATUS_STYLES: Record<ComplianceStatus, string> = {
  compliant: "bg-emerald-100 text-emerald-800 border-emerald-200",
  non_compliant: "bg-red-100 text-red-800 border-red-200",
  partially_compliant: "bg-amber-100 text-amber-800 border-amber-200",
  not_found: "bg-slate-100 text-slate-700 border-slate-200",
  needs_human_review: "bg-indigo-100 text-indigo-800 border-indigo-200",
};

const RISK_STYLES: Record<RiskLevel, string> = {
  low: "bg-emerald-50 text-emerald-700 border-emerald-200",
  medium: "bg-amber-50 text-amber-700 border-amber-200",
  high: "bg-red-50 text-red-700 border-red-200",
};

export default function ReportPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [report, setReport] = useState<ReportOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api
      .getReport(params.id)
      .then(setReport)
      .catch((err) => {
        const detail = err instanceof ApiError ? err.detail : "Failed to load report";
        setError(detail);
      });
  }, [params.id, router]);

  if (error) {
    return (
      <main className="mx-auto max-w-4xl p-6">
        <p className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>
        <Link href="/" className="text-sm text-slate-600 underline">
          Back
        </Link>
      </main>
    );
  }

  if (!report) {
    return <div className="p-6 text-sm text-slate-500">Loading…</div>;
  }

  return (
    <main className="mx-auto max-w-4xl space-y-6 p-6">
      <header className="flex items-center justify-between">
        <div>
          <Link href="/" className="text-sm text-slate-500 hover:underline">
            ← Back
          </Link>
          <h1 className="text-2xl font-semibold">Compliance report</h1>
          <p className="text-sm text-slate-500">
            ID {report.id} · {report.status}
            {report.completed_at &&
              ` · finished ${new Date(report.completed_at).toLocaleString()}`}
          </p>
        </div>
      </header>

      <DisclaimerBanner />

      {report.status === "failed" && report.error_message && (
        <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          <strong>Pipeline failed:</strong> {report.error_message}
        </div>
      )}

      {report.summary && (
        <section className="grid grid-cols-2 gap-3 rounded border border-slate-200 bg-white p-4 sm:grid-cols-3">
          <SummaryCell label="Total" value={report.summary.total_requirements} />
          <SummaryCell label="Compliant" value={report.summary.compliant} />
          <SummaryCell label="Partial" value={report.summary.partially_compliant} />
          <SummaryCell label="Non-compliant" value={report.summary.non_compliant} />
          <SummaryCell label="Not found" value={report.summary.not_found} />
          <SummaryCell label="Needs review" value={report.summary.needs_human_review} />
        </section>
      )}

      <section className="space-y-4">
        {report.findings.map((finding) => (
          <FindingCard key={finding.ordinal} finding={finding} />
        ))}
      </section>
    </main>
  );
}

function SummaryCell({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded border border-slate-200 p-3 text-sm">
      <div className="text-slate-500">{label}</div>
      <div className="text-xl font-semibold">{value}</div>
    </div>
  );
}

function FindingCard({ finding }: { finding: FindingOut }) {
  return (
    <article className="rounded border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-xs text-slate-500">
          {finding.requirement_id}
        </span>
        <span
          className={`rounded border px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[finding.status]}`}
        >
          {finding.status.replace("_", " ")}
        </span>
        <span
          className={`rounded border px-2 py-0.5 text-xs font-medium ${RISK_STYLES[finding.risk_level]}`}
        >
          risk: {finding.risk_level}
        </span>
        <span className="text-xs text-slate-500">
          confidence {(finding.confidence * 100).toFixed(0)}%
        </span>
      </div>
      <p className="mt-2 text-sm text-slate-800">{finding.requirement_text}</p>
      {finding.explanation && (
        <p className="mt-2 text-sm text-slate-600">{finding.explanation}</p>
      )}
      {finding.suggested_fix && (
        <p className="mt-2 rounded bg-slate-50 p-2 text-sm text-slate-700">
          <strong>Suggested fix: </strong>
          {finding.suggested_fix}
        </p>
      )}
      {finding.evidence.length > 0 && (
        <details className="mt-3">
          <summary className="cursor-pointer text-sm text-slate-600">
            Evidence ({finding.evidence.length})
          </summary>
          <ul className="mt-2 space-y-2">
            {finding.evidence.map((ev, i) => (
              <li
                key={i}
                className="rounded border border-slate-200 bg-slate-50 p-2 text-sm"
              >
                <span className="text-xs text-slate-500">
                  {ev.chunk_ordinal !== null
                    ? `chunk #${ev.chunk_ordinal}`
                    : "unsourced"}
                </span>
                <blockquote className="mt-1 italic text-slate-700">
                  “{ev.quote}”
                </blockquote>
              </li>
            ))}
          </ul>
        </details>
      )}
    </article>
  );
}
