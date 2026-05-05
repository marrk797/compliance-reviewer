/**
 * Token-aware-ish chunker for company submissions.
 *
 * In the original Python backend we used tiktoken for exact GPT-style token
 * counts. In the browser we approximate: ~0.75 words per token, so a
 * 500-token chunk is roughly 375 words. This is close enough for retrieval
 * (the chunks just become slightly shorter than the LLM's context budget).
 */

export interface Chunk {
  ordinal: number;
  text: string;
  token_count: number;
}

const WORDS_PER_TOKEN = 0.75;

export function chunkText(
  text: string,
  {
    chunkTokens = 500,
    overlapTokens = 50,
  }: { chunkTokens?: number; overlapTokens?: number } = {},
): Chunk[] {
  const cleaned = text.replace(/\s+/g, " ").trim();
  if (!cleaned) return [];

  const words = cleaned.split(" ");
  const chunkWords = Math.max(1, Math.floor(chunkTokens * WORDS_PER_TOKEN));
  const overlapWords = Math.max(0, Math.floor(overlapTokens * WORDS_PER_TOKEN));
  const stride = Math.max(1, chunkWords - overlapWords);

  const chunks: Chunk[] = [];
  let ordinal = 0;
  for (let start = 0; start < words.length; start += stride) {
    const slice = words.slice(start, start + chunkWords);
    if (slice.length === 0) break;
    chunks.push({
      ordinal,
      text: slice.join(" "),
      token_count: Math.round(slice.length / WORDS_PER_TOKEN),
    });
    ordinal += 1;
    if (start + chunkWords >= words.length) break;
  }
  return chunks;
}
