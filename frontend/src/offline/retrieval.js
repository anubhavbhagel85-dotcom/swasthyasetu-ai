import kb from "./knowledge_base.json";
import redFlagsData from "./red_flags.json";

export const ENTRIES = kb.entries;
export const DISCLAIMER = kb.disclaimer;
export const EMERGENCY_NUMBERS = redFlagsData.emergency_numbers;

/**
 * Simplified port of backend/app/rag_engine.py's retrieval logic for
 * fully offline use. We skip TF-IDF (no sklearn in the browser) and use
 * weighted keyword overlap instead — good enough for the same small,
 * curated 10-topic knowledge base, and just as explainable.
 */
export function retrieve(query, topK = 2, threshold = 0.15) {
  const q = query.toLowerCase();
  const scored = ENTRIES.map((entry) => {
    let score = 0;
    for (const kw of entry.keywords) {
      if (q.includes(kw.toLowerCase())) {
        score = 1.0; // exact keyword hit = full confidence, same as backend's boost
        break;
      }
    }
    if (score === 0) {
      // Loose overlap fallback: fraction of title/overview words present in the query
      const bag = `${entry.title.en} ${entry.title.hi} ${entry.overview.en}`.toLowerCase().split(/\W+/);
      const hits = bag.filter((w) => w.length > 3 && q.includes(w)).length;
      score = Math.min(hits * 0.12, 0.6);
    }
    return { entry, score };
  });

  return scored
    .filter((s) => s.score >= threshold)
    .sort((a, b) => b.score - a.score)
    .slice(0, topK);
}

export function getEntryById(id) {
  return ENTRIES.find((e) => e.id === id) || null;
}

export function normalize(text) {
  return text.trim().toLowerCase().replace(/\s+/g, " ");
}

export function checkGlobalEmergency(text, language) {
  const normalized = normalize(text);
  for (const group of redFlagsData.emergency_patterns) {
    for (const phrase of group.patterns) {
      if (normalized.includes(phrase.toLowerCase())) {
        return {
          matchedFlags: [group.message[language]],
          isCrisis: !!group.is_crisis,
        };
      }
    }
  }
  return null;
}

export function checkTopicRedFlags(entry, text, language) {
  const normalized = normalize(text);
  const matched = [];
  for (const flag of entry.red_flags[language] || []) {
    const terms = flag
      .toLowerCase()
      .split(/[,/]| or | and /)
      .map((t) => t.trim())
      .filter((t) => t.length > 3);
    if (terms.some((t) => normalized.includes(t))) matched.push(flag);
  }
  return matched;
}
