/**
 * Browser-side Groq client.
 *
 * Uses the official ``groq-sdk`` with ``dangerouslyAllowBrowser: true`` —
 * which is acceptable here because the user enters their *own* key into the
 * UI; we do not embed any shared secret. The key is held only in localStorage
 * and is never sent anywhere except api.groq.com.
 */

import Groq from "groq-sdk";

export const DEFAULT_MODEL = "llama-3.3-70b-versatile";

export interface GroqJsonOptions {
  apiKey: string;
  model?: string;
  system: string;
  user: string;
  schemaHint?: string;
  temperature?: number;
  maxTokens?: number;
}

export async function completeJson<T = unknown>(
  options: GroqJsonOptions,
): Promise<T> {
  const client = new Groq({
    apiKey: options.apiKey,
    dangerouslyAllowBrowser: true,
  });
  const instruction =
    "Respond with a single valid JSON object that matches the requested schema. " +
    "Do not include markdown fences, prose, or any text outside the JSON object." +
    (options.schemaHint ? `\n\nSchema:\n${options.schemaHint}` : "");
  const response = await client.chat.completions.create({
    model: options.model ?? DEFAULT_MODEL,
    messages: [
      { role: "system", content: `${options.system}\n\n${instruction}` },
      { role: "user", content: options.user },
    ],
    temperature: options.temperature ?? 0,
    max_tokens: options.maxTokens ?? 1024,
    response_format: { type: "json_object" },
  });
  const raw = response.choices[0]?.message?.content ?? "{}";
  let text = raw.trim();
  if (text.startsWith("```")) {
    text = text.replace(/^```[a-zA-Z]*\n?/, "").replace(/```$/, "").trim();
  }
  const parsed = JSON.parse(text);
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error("Groq did not return a JSON object");
  }
  return parsed as T;
}

export async function pingGroq(apiKey: string): Promise<boolean> {
  const client = new Groq({ apiKey, dangerouslyAllowBrowser: true });
  try {
    await client.models.list();
    return true;
  } catch {
    return false;
  }
}
