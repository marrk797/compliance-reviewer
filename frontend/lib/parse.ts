/**
 * Browser-side document parsing for PDF, DOCX, and TXT.
 *
 * Files never leave the browser; we read them as ArrayBuffers and extract
 * plain text in-memory. PDF parsing uses pdf.js (with a CDN-hosted worker so
 * Vercel's static deploy doesn't need extra bundler config); DOCX uses
 * mammoth's browser build; TXT is a TextDecoder pass.
 */

const PDF_WORKER_URL =
  "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.7.76/build/pdf.worker.min.mjs";

export class ParsingError extends Error {}

export async function extractText(file: File): Promise<string> {
  const ext = file.name.toLowerCase().split(".").pop() ?? "";
  const buffer = await file.arrayBuffer();
  if (ext === "pdf") return extractPdf(buffer);
  if (ext === "docx") return extractDocx(buffer);
  if (ext === "txt") return new TextDecoder("utf-8").decode(buffer);
  throw new ParsingError(
    `Unsupported file type: .${ext}. Use PDF, DOCX, or TXT.`,
  );
}

async function extractPdf(buffer: ArrayBuffer): Promise<string> {
  const pdfjs = await import("pdfjs-dist");
  pdfjs.GlobalWorkerOptions.workerSrc = PDF_WORKER_URL;
  const doc = await pdfjs.getDocument({ data: buffer }).promise;
  const parts: string[] = [];
  for (let i = 1; i <= doc.numPages; i++) {
    const page = await doc.getPage(i);
    const content = await page.getTextContent();
    const text = content.items
      .map((item) => ("str" in item ? item.str : ""))
      .join(" ");
    parts.push(text);
  }
  return parts.join("\n\n");
}

async function extractDocx(buffer: ArrayBuffer): Promise<string> {
  const mammoth = await import("mammoth/mammoth.browser");
  const result = await mammoth.extractRawText({ arrayBuffer: buffer });
  return result.value ?? "";
}
