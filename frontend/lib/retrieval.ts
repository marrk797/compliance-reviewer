/**
 * In-memory cosine top-k retrieval.
 *
 * Vectors come from ``embed()`` already L2-normalised, so a dot product
 * equals cosine similarity. We keep this trivially small: a few hundred
 * chunks × 384 floats fits easily in memory and is fast on any device.
 */

import type { Chunk } from "./chunk";

export interface RetrievedChunk {
  ordinal: number;
  text: string;
  similarity: number;
}

export function topK(
  query: number[],
  chunkVectors: number[][],
  chunks: Chunk[],
  k: number,
): RetrievedChunk[] {
  if (chunkVectors.length !== chunks.length) {
    throw new Error("chunkVectors and chunks length mismatch");
  }
  const scored = chunks.map((chunk, i) => ({
    ordinal: chunk.ordinal,
    text: chunk.text,
    similarity: dot(query, chunkVectors[i]),
  }));
  scored.sort((a, b) => b.similarity - a.similarity);
  return scored.slice(0, k);
}

function dot(a: number[], b: number[]): number {
  let s = 0;
  const n = Math.min(a.length, b.length);
  for (let i = 0; i < n; i++) s += a[i] * b[i];
  return s;
}
