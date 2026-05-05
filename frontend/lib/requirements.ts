/**
 * Heuristic requirement extractor.
 *
 * Splits a regulatory document into atomic requirements. Tries hardest-to-easiest:
 *   1. Numbered clauses ("1.", "2.3.", "3) ", "Article 5 -")
 *   2. Bulleted lines ("- foo", "* bar", "• baz")
 *   3. Sentences containing "shall", "must", or "is required to"
 *   4. As a last resort, every non-trivial paragraph.
 *
 * This deliberately does not call the LLM; the regulator's structure usually
 * lines up with one of these patterns and skipping a network call makes the
 * pipeline reliable offline.
 */

export interface RequirementItem {
  requirement_id: string;
  text: string;
  section: string | null;
}

const NUMBERED_RE =
  /^\s*(?<num>(?:\d+(?:\.\d+)*|[A-Z]\.\d+|[A-Z]\d+))(?:\.(?!\d)|[)\]:]|\s+[-–—]+|\s+)\s*(?<rest>.+)$/;
const ARTICLE_RE =
  /^\s*(?:Article|Section|Clause|Rule|§)\s+(?<num>\d+(?:\.\d+)*)[.):\s-]+\s*(?<rest>.+)$/i;
const BULLET_RE = /^\s*(?:[-*•·–—]|\u2022)\s+(?<rest>.+)$/;
const SENTENCE_SHALL_RE = /\b(?:shall|must|is required to|are required to)\b/i;

const MIN_CHARS = 20;
const MAX_CHARS = 1500;

export function extractRequirements(text: string): RequirementItem[] {
  const lines = text.split(/\r?\n/);
  const items: RequirementItem[] = [];
  let counter = 0;

  // 1+2: numbered/article/bullet lines.
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;

    const numbered = NUMBERED_RE.exec(line) ?? ARTICLE_RE.exec(line);
    if (numbered?.groups?.rest && numbered.groups.rest.length >= MIN_CHARS) {
      counter += 1;
      items.push({
        requirement_id: `R-${numbered.groups.num}`,
        text: numbered.groups.rest.trim().slice(0, MAX_CHARS),
        section: numbered.groups.num,
      });
      continue;
    }

    const bullet = BULLET_RE.exec(line);
    if (bullet?.groups?.rest && bullet.groups.rest.length >= MIN_CHARS) {
      counter += 1;
      items.push({
        requirement_id: `R-B${counter.toString().padStart(3, "0")}`,
        text: bullet.groups.rest.trim().slice(0, MAX_CHARS),
        section: null,
      });
    }
  }

  if (items.length >= 3) return dedupe(items);

  // 3: shall/must sentences.
  const sentences = text
    .replace(/\s+/g, " ")
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter((s) => s.length >= MIN_CHARS);

  const shallItems: RequirementItem[] = [];
  for (const sentence of sentences) {
    if (SENTENCE_SHALL_RE.test(sentence)) {
      shallItems.push({
        requirement_id: `R-S${(shallItems.length + 1).toString().padStart(3, "0")}`,
        text: sentence.slice(0, MAX_CHARS),
        section: null,
      });
    }
  }
  if (shallItems.length >= 3) return dedupe(shallItems);

  // 4: every non-trivial paragraph.
  const paragraphs = text
    .split(/\n{2,}/)
    .map((p) => p.replace(/\s+/g, " ").trim())
    .filter((p) => p.length >= MIN_CHARS);
  return dedupe(
    paragraphs.map((p, i) => ({
      requirement_id: `R-P${(i + 1).toString().padStart(3, "0")}`,
      text: p.slice(0, MAX_CHARS),
      section: null,
    })),
  );
}

function dedupe(items: RequirementItem[]): RequirementItem[] {
  const seen = new Set<string>();
  const out: RequirementItem[] = [];
  for (const item of items) {
    const key = item.text.toLowerCase().slice(0, 200);
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(item);
  }
  return out;
}
