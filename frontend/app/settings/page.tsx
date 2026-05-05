"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { DEFAULT_MODEL, pingGroq } from "@/lib/groq";
import {
  getAcknowledged,
  getGroqKey,
  getGroqModel,
  setAcknowledged,
  setGroqKey,
  setGroqModel,
} from "@/lib/storage";

export default function SettingsPage() {
  const router = useRouter();
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState(DEFAULT_MODEL);
  const [ack, setAck] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    setApiKey(getGroqKey() ?? "");
    setModel(getGroqModel() ?? DEFAULT_MODEL);
    setAck(getAcknowledged());
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus(null);
    if (!apiKey.trim()) {
      setStatus("Please paste your Groq API key.");
      return;
    }
    if (!ack) {
      setStatus("Please acknowledge the data-handling notice.");
      return;
    }
    setVerifying(true);
    try {
      const ok = await pingGroq(apiKey.trim());
      if (!ok) {
        setStatus(
          "That key was rejected by Groq. Double-check it at https://console.groq.com/keys.",
        );
        return;
      }
      setGroqKey(apiKey.trim());
      setGroqModel(model.trim() || DEFAULT_MODEL);
      setAcknowledged(true);
      router.push("/");
    } finally {
      setVerifying(false);
    }
  }

  function clearAll() {
    setGroqKey(null);
    setGroqModel(null);
    setAcknowledged(false);
    setApiKey("");
    setModel(DEFAULT_MODEL);
    setAck(false);
    setStatus("Cleared local settings.");
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 p-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">Compliance Reviewer</h1>
        <p className="text-sm text-slate-600">
          Set up your free Groq key. Everything runs in your browser; nothing
          is sent to a server we control.
        </p>
      </div>

      <DisclaimerBanner />

      <form
        onSubmit={onSubmit}
        className="space-y-3 rounded border border-slate-200 bg-white p-4"
      >
        <label className="block text-sm">
          <span className="font-medium">Groq API key</span>
          <input
            type="password"
            required
            autoComplete="off"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="gsk_…"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 font-mono text-sm"
          />
          <span className="mt-1 block text-xs text-slate-500">
            Get a free key (no credit card) at{" "}
            <a
              href="https://console.groq.com/keys"
              target="_blank"
              rel="noreferrer noopener"
              className="underline"
            >
              console.groq.com/keys
            </a>
            . The key is stored only in this browser&apos;s localStorage and is
            sent only to api.groq.com.
          </span>
        </label>

        <label className="block text-sm">
          <span className="font-medium">Model</span>
          <input
            type="text"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 font-mono text-sm"
          />
          <span className="mt-1 block text-xs text-slate-500">
            Default <code>{DEFAULT_MODEL}</code> works on the Groq free tier.
          </span>
        </label>

        <label className="flex items-start gap-2 text-xs text-slate-700">
          <input
            type="checkbox"
            className="mt-1"
            checked={ack}
            onChange={(e) => setAck(e.target.checked)}
          />
          <span>
            I will not upload personal or confidential data unless I am
            authorized to do so. I understand this tool assists human
            reviewers and does not provide legal advice.
          </span>
        </label>

        {status && (
          <p className="rounded bg-slate-50 p-2 text-sm text-slate-700">
            {status}
          </p>
        )}

        <button
          type="submit"
          disabled={verifying}
          className="w-full rounded bg-slate-900 py-2 text-sm font-medium text-white disabled:bg-slate-400"
        >
          {verifying ? "Verifying with Groq…" : "Save and continue"}
        </button>

        <button
          type="button"
          onClick={clearAll}
          className="w-full rounded border border-slate-300 py-2 text-xs text-slate-600 hover:bg-slate-50"
        >
          Clear local settings
        </button>
      </form>

      <Link href="/" className="text-center text-sm text-slate-600 underline">
        Back to home
      </Link>
    </main>
  );
}
