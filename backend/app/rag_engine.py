"""
Retrieval engine for SwasthyaSetu AI.

Why TF-IDF instead of a heavy embedding model for the hackathon MVP?
- Zero external API calls -> works fully offline, deterministic, free.
- The knowledge base is small and curated (not open-web), so exact/near
  keyword matching already performs very well and is easy to explain to
  judges: "here is exactly why this topic was retrieved."
- The retrieval interface (`retrieve`) is isolated in this one file, so
  swapping in `sentence-transformers` + FAISS/Chroma later (see
  ARCHITECTURE.md "Upgrade path") does not touch any other module.

Every result carries its `sources` list straight from the knowledge base,
so no answer is ever generated without a citation attached.
"""
import json
import re
from dataclasses import dataclass
from typing import List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import DATA_DIR, RETRIEVAL_THRESHOLD, TOP_K_RESULTS

with open(DATA_DIR / "knowledge_base.json", encoding="utf-8") as f:
    _KB = json.load(f)

ENTRIES = _KB["entries"]
DISCLAIMER = _KB["disclaimer"]
LAST_REVIEWED = _KB["last_reviewed"]


def _entry_corpus_text(entry: dict) -> str:
    parts = [
        " ".join(entry.get("keywords", [])),
        entry["title"]["en"], entry["title"]["hi"],
        entry["overview"]["en"], entry["overview"]["hi"],
    ]
    return " ".join(parts).lower()


_CORPUS = [_entry_corpus_text(e) for e in ENTRIES]
_VECTORIZER = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
_MATRIX = _VECTORIZER.fit_transform(_CORPUS)


@dataclass
class RetrievalHit:
    entry: dict
    score: float


def _keyword_boost(query: str, entry: dict) -> float:
    """Direct substring keyword hits are a very strong, explainable signal
    (e.g. user literally typed 'bukhar' or 'fever') so we boost them above
    whatever the TF-IDF cosine score would give."""
    q = query.lower()
    for kw in entry.get("keywords", []):
        if kw.lower() in q:
            return 1.0
    return 0.0


def retrieve(query: str, top_k: int = TOP_K_RESULTS, threshold: float = RETRIEVAL_THRESHOLD) -> List[RetrievalHit]:
    """Return the best-matching knowledge-base entries for a free-text query."""
    query_vec = _VECTORIZER.transform([query.lower()])
    sims = cosine_similarity(query_vec, _MATRIX)[0]

    hits = []
    for entry, sim in zip(ENTRIES, sims):
        score = max(sim, _keyword_boost(query, entry))
        if score >= threshold:
            hits.append(RetrievalHit(entry=entry, score=float(score)))

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top_k]


def get_entry_by_id(topic_id: str) -> Optional[dict]:
    for e in ENTRIES:
        if e["id"] == topic_id:
            return e
    return None


def list_all_sources() -> List[dict]:
    """Deduplicated list of every verified source cited anywhere in the
    knowledge base — powers the transparent '/api/sources' endpoint and the
    'Verified Sources' page in the frontend."""
    seen = {}
    for entry in ENTRIES:
        for src in entry.get("sources", []):
            seen[src["url"]] = src
    return list(seen.values())
