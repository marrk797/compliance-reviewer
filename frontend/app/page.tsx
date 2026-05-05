"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { runPipeline, type PipelineProgress } from "@/lib/pipeline";
import {
  getAcknowledged,
  getGroqKey,
  getGroqModel,
  listReports,
} from "@/lib/storage";
import type { ReportOut } from "@/lib/types";

type UploadSlot = {
  file: File | null;
  error: string | null;
};

const emptySlot: UploadSlot = { file: null, error: null };

export default function HomePage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [keyMasked, setKeyMasked] = useState<string | null>(null);
  const [regulatory, setRegulatory] = useState<UploadSlot>(emptySlot);
  const [company, setCompany] = useState<UploadSlot>(emptySlot);
  const [reports, setReports] = useState<ReportOut[]>([]);
  const [progress, setProgress] = useState<PipelineProgress | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const key = getGroqKey();
    if (!key || !getAcknowledged()) {
      router.replace("/settings");
      return;
    }
    setKeyMasked(`${key.slice(0, 4)}…${key.slice(-4)}`);
    setReports(listReports());
    setReady(true);
  }, [router]);

  const refresh = useCallback(() => {
    setReports(listReports());
  }, []);

  const canRun = useMemo(
    () => Boolean(regulatory.file && company.file && !running),
    [regulatory.file, company.file, running],
  );

  async function handleRun() {
    if (!regulatory.file || !company.file) return;
    const apiKey = getGroqKey();
    if (!apiKey) {
      router.replace("/settings");
      return;
    }
    setRunning(true);
    setError(null);
    setProgress({ stage: "parse", message: "Starting…" });
    try {
      const report = await runPipeline(
        {
          regulatoryFile: regulatory.file,
          companyFile: company.file,
          apiKey,
          model: getGroqModel() ?? undefined,
        },
        (p) => setProgress(p),
      );
      refresh();
      router.push(`/reports/${report.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pipeline failed");
    } finally {
      setRunning(false);
    }
  }

  if (!ready) {
    return <div className="p-6 text-sm text-slate-500">Loading…</div>;
  }

  return (
    <main className="mx-auto max-w-4xl space-y-6 p-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Compliance Reviewer</h1>
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span>
            Groq key: <code className="font-mono">{keyMasked}</code>
          </span>
          <Link
            href="/settings"
            className="rounded border border-slate-300 px-3 py-1 text-sm text-slate-700 hover:bg-slate-100"
          >
            Settings
          </Link>
        </div>
      </header>

      <DisclaimerBanner />

      <section className="grid gap-4 md:grid-cols-2">
        <UploadCard
          title="1. Regulatory document"
          description="The rules and requirements the submission must satisfy."
          slot={regulatory}
          onSelect={(file) => setRegulatory({ file, error: null })}
        />
        <UploadCard
          title="2. Company submission"
          description="The document you want to check for compliance."
          slot={company}
          onSelect={(file) => setCompany({ file, error: null })}
        />
      </section>

      <section className="rounded border border-slate-200 bg-white p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-medium">Generate compliance report</h2>
          <button
            onClick={handleRun}
            disabled={!canRun}
            className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {running ? "Running…" : "Run review"}
          </button>
        </div>
        <p className="mt-2 text-sm text-slate-600">
          Everything runs in this browser tab. Files never leave your machine;
          only short retrieved excerpts are sent to Groq for evaluation.
        </p>
        {progress && (
          <p className="mt-2 rounded bg-slate-50 p-2 text-sm text-slate-700">
            <strong>{progress.stage}:</strong> {progress.message}
            {progress.current !== undefined && progress.total !== undefined && (
              <> ({progress.current}/{progress.total})</>
            )}
          </p>
        )}
        {error && (
          <p className="mt-2 rounded bg-red-50 p-2 text-sm text-red-700">
            {error}
          </p>
        )}
      </section>

      <section className="rounded border border-slate-200 bg-white p-4">
        <h2 className="font-medium">Recent reports</h2>
        {reports.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No reports yet.</p>
        ) : (
          <ul className="mt-2 divide-y">
            {reports.map((r) => (
              <li
                key={r.id}
                className="flex items-center justify-between py-2 text-sm"
              >
                <div>
                  <Link
                    href={`/reports/${r.id}`}
                    className="font-medium text-slate-800 hover:underline"
                  >
                    Report {r.id.slice(0, 8)}
                  </Link>
                  <span className="ml-2 text-slate-500">{r.status}</span>
                  {r.summary && (
                    <span className="ml-2 text-slate-500">
                      · {r.summary.total_requirements} reqs
                    </span>
                  )}
                </div>
                <span className="text-slate-500">
                  {new Date(r.created_at).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}

function UploadCard({
  title,
  description,
  slot,
  onSelect,
}: {
  title: string;
  description: string;
  slot: UploadSlot;
  onSelect: (file: File) => void;
}) {
  return (
    <div className="rounded border border-slate-200 bg-white p-4">
      <h3 className="font-medium">{title}</h3>
      <p className="mt-1 text-sm text-slate-600">{description}</p>
      <input
        type="file"
        accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onSelect(file);
        }}
        className="mt-3 block w-full text-sm"
      />
      {slot.file && (
        <p className="mt-2 text-sm text-emerald-700">
          Selected: {slot.file.name} ({Math.round(slot.file.size / 1024)} KB)
        </p>
      )}
      {slot.error && (
        <p className="mt-2 text-sm text-red-700">{slot.error}</p>
      )}
    </div>
  );
}
