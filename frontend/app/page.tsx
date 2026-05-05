"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import {
  ApiError,
  ReportOut,
  api,
  getToken,
  setToken,
} from "@/lib/api";

type UploadSlot = {
  file: File | null;
  documentId: string | null;
  uploading: boolean;
  error: string | null;
};

const emptySlot: UploadSlot = {
  file: null,
  documentId: null,
  uploading: false,
  error: null,
};

export default function HomePage() {
  const router = useRouter();
  const [authChecked, setAuthChecked] = useState(false);
  const [email, setEmail] = useState<string | null>(null);
  const [regulatory, setRegulatory] = useState<UploadSlot>(emptySlot);
  const [company, setCompany] = useState<UploadSlot>(emptySlot);
  const [reports, setReports] = useState<ReportOut[]>([]);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    api
      .me()
      .then((user) => {
        setEmail(user.email);
        setAuthChecked(true);
      })
      .catch(() => {
        setToken(null);
        router.replace("/login");
      });
  }, [router]);

  const refreshReports = useCallback(async () => {
    try {
      const data = await api.listReports();
      setReports(data);
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
    }
  }, []);

  useEffect(() => {
    if (authChecked) void refreshReports();
  }, [authChecked, refreshReports]);

  const canRunReport = useMemo(
    () => Boolean(regulatory.documentId && company.documentId && !creating),
    [regulatory.documentId, company.documentId, creating],
  );

  async function handleUpload(
    kind: "regulatory" | "company",
    file: File,
  ): Promise<void> {
    const setSlot = kind === "regulatory" ? setRegulatory : setCompany;
    setSlot({ file, documentId: null, uploading: true, error: null });
    try {
      const doc = await api.uploadDocument(file, kind);
      setSlot({ file, documentId: doc.id, uploading: false, error: null });
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Upload failed";
      setSlot({ file, documentId: null, uploading: false, error: detail });
    }
  }

  async function handleCreateReport() {
    if (!regulatory.documentId || !company.documentId) return;
    setCreating(true);
    setError(null);
    try {
      const report = await api.createReport(
        regulatory.documentId,
        company.documentId,
      );
      router.push(`/reports/${report.id}`);
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Report failed";
      setError(detail);
    } finally {
      setCreating(false);
    }
  }

  function logout() {
    setToken(null);
    router.replace("/login");
  }

  if (!authChecked) {
    return <div className="p-6 text-sm text-slate-500">Loading…</div>;
  }

  return (
    <main className="mx-auto max-w-4xl space-y-6 p-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Compliance Reviewer</h1>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-slate-600">{email}</span>
          <button
            onClick={logout}
            className="rounded border border-slate-300 px-3 py-1 hover:bg-slate-100"
          >
            Sign out
          </button>
        </div>
      </header>

      <DisclaimerBanner />

      <section className="grid gap-4 md:grid-cols-2">
        <UploadCard
          title="1. Regulatory document"
          description="The rules and requirements the submission must satisfy."
          slot={regulatory}
          onSelect={(file) => handleUpload("regulatory", file)}
        />
        <UploadCard
          title="2. Company submission"
          description="The document you want to check for compliance."
          slot={company}
          onSelect={(file) => handleUpload("company", file)}
        />
      </section>

      <section className="rounded border border-slate-200 bg-white p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-medium">Generate compliance report</h2>
          <button
            onClick={handleCreateReport}
            disabled={!canRunReport}
            className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {creating ? "Running…" : "Run review"}
          </button>
        </div>
        <p className="mt-2 text-sm text-slate-600">
          The pipeline runs synchronously for the MVP. Source files are deleted
          after processing when the privacy mode is enabled on the server.
        </p>
        {error && (
          <p className="mt-2 rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>
        )}
      </section>

      <section className="rounded border border-slate-200 bg-white p-4">
        <h2 className="font-medium">Recent reports</h2>
        {reports.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No reports yet.</p>
        ) : (
          <ul className="mt-2 divide-y">
            {reports.map((r) => (
              <li key={r.id} className="flex items-center justify-between py-2 text-sm">
                <div>
                  <Link
                    href={`/reports/${r.id}`}
                    className="font-medium text-slate-800 hover:underline"
                  >
                    Report {r.id.slice(0, 8)}
                  </Link>
                  <span className="ml-2 text-slate-500">{r.status}</span>
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
  onSelect: (file: File) => void | Promise<void>;
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
          if (file) void onSelect(file);
        }}
        className="mt-3 block w-full text-sm"
      />
      {slot.uploading && (
        <p className="mt-2 text-sm text-slate-500">Uploading…</p>
      )}
      {slot.documentId && !slot.uploading && (
        <p className="mt-2 text-sm text-emerald-700">
          Uploaded ({slot.file?.name})
        </p>
      )}
      {slot.error && (
        <p className="mt-2 text-sm text-red-700">{slot.error}</p>
      )}
    </div>
  );
}
