/**
 * Local embedding via Transformers.js (@xenova/transformers v2).
 *
 * Uses ``Xenova/bge-small-en-v1.5`` (the ONNX-compiled mirror of
 * BAAI/bge-small-en-v1.5). The model weights are downloaded once into the
 * browser's IndexedDB cache (~70 MB) and reused on subsequent visits.
 *
 * The whole module is dynamic-imported and gated on ``typeof window``, so
 * Next.js' build/typecheck never tries to instantiate the model server-side.
 *
 * We deliberately stayed on the v2 package (@xenova/transformers) rather
 * than the v3 rename (@huggingface/transformers) because v3's prebuilt
 * webpack bundle does not currently re-bundle cleanly in Next.js 14 — see
 * https://github.com/huggingface/transformers.js/issues/.
 */

export const EMBEDDING_MODEL = "Xenova/bge-small-en-v1.5";
export const EMBEDDING_DIM = 384;

type FeatureExtractor = (
  texts: string | string[],
  options?: { pooling?: "none" | "mean" | "cls"; normalize?: boolean },
) => Promise<{ data: Float32Array; dims: number[]; tolist: () => number[][] }>;

let _extractorPromise: Promise<FeatureExtractor> | null = null;

async function getExtractor(
  onProgress?: (info: { progress?: number; status?: string }) => void,
): Promise<FeatureExtractor> {
  if (typeof window === "undefined") {
    throw new Error("embed.ts can only run in the browser");
  }
  if (!_extractorPromise) {
    _extractorPromise = (async () => {
      const transformers = await import("@xenova/transformers");
      const pipeline = transformers.pipeline as unknown as (
        task: string,
        model: string,
        options?: { progress_callback?: (info: unknown) => void },
      ) => Promise<FeatureExtractor>;
      return pipeline("feature-extraction", EMBEDDING_MODEL, {
        progress_callback: (info: unknown) => {
          if (onProgress && typeof info === "object" && info !== null) {
            const i = info as { progress?: number; status?: string };
            onProgress({ progress: i.progress, status: i.status });
          }
        },
      });
    })();
  }
  return _extractorPromise;
}

export async function preloadEmbedder(
  onProgress?: (info: { progress?: number; status?: string }) => void,
): Promise<void> {
  await getExtractor(onProgress);
}

export async function embed(
  texts: string[],
  onProgress?: (info: { progress?: number; status?: string }) => void,
): Promise<number[][]> {
  if (texts.length === 0) return [];
  const extractor = await getExtractor(onProgress);
  const output = await extractor(texts, { pooling: "mean", normalize: true });
  // Flat Float32Array of length (texts.length * EMBEDDING_DIM).
  const flat = output.data;
  const dim = output.dims[output.dims.length - 1] ?? EMBEDDING_DIM;
  const result: number[][] = [];
  for (let i = 0; i < texts.length; i++) {
    result.push(Array.from(flat.slice(i * dim, (i + 1) * dim)));
  }
  return result;
}
