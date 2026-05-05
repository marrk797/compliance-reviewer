"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { ApiError, api, setToken } from "@/lib/api";

type Mode = "login" | "register";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "register") {
        if (!acknowledged) {
          setError(
            "Please acknowledge the data-handling notice before continuing.",
          );
          return;
        }
        await api.register(email, password);
      }
      const token = await api.login(email, password);
      setToken(token.access_token);
      router.replace("/");
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Authentication failed";
      setError(detail);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 p-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">Compliance Reviewer</h1>
        <p className="text-sm text-slate-600">
          {mode === "login" ? "Sign in to continue." : "Create an account."}
        </p>
      </div>

      <DisclaimerBanner />

      <form onSubmit={onSubmit} className="space-y-3 rounded border border-slate-200 bg-white p-4">
        <label className="block text-sm">
          <span className="font-medium">Email</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium">Password</span>
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
          />
        </label>
        {mode === "register" && (
          <label className="flex items-start gap-2 text-xs text-slate-700">
            <input
              type="checkbox"
              className="mt-1"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
            />
            <span>
              I will not upload personal or confidential data unless I am
              authorized to do so. I understand this tool assists human
              reviewers and does not provide legal advice.
            </span>
          </label>
        )}
        {error && (
          <p className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>
        )}
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded bg-slate-900 py-2 text-sm font-medium text-white disabled:bg-slate-400"
        >
          {submitting ? "…" : mode === "login" ? "Sign in" : "Create account"}
        </button>
      </form>

      <button
        type="button"
        onClick={() => {
          setMode(mode === "login" ? "register" : "login");
          setError(null);
        }}
        className="text-sm text-slate-600 underline"
      >
        {mode === "login"
          ? "Need an account? Register"
          : "Already have an account? Sign in"}
      </button>
    </main>
  );
}
