# Verified Sources

SwasthyaSetu AI never answers from open-web search or from an LLM's unaided
memory. Every symptom entry in `backend/app/data/knowledge_base.json` is a
short, original paraphrase written by the team and tagged with the
public-health authority it was grounded against. This file is the master
ledger judges/reviewers can check against the code.

| Organisation | Role in this project | URL |
|---|---|---|
| World Health Organization (WHO) | Global fact sheets on common conditions, fever, diarrhoeal disease, cardiovascular disease, mental health, injuries | https://www.who.int/news-room/fact-sheets |
| National Health Portal of India (NHP), Ministry of Health & Family Welfare | India-specific "Health A–Z" guidance, run by the Centre for Health Informatics under MoHFW | https://www.nhp.gov.in/ |
| NHS (UK) — Health A to Z | Plain-language condition and symptom pages, widely used as a public triage reference | https://www.nhs.uk/conditions/ |
| Ministry of AYUSH, Government of India | Source for the **traditional home remedies** block — kept in its own separately-cited section, distinct from clinical self-care, and never shown for urgent/emergency topics | https://www.ayush.gov.in/ |
| Tele-MANAS, Government of India | 24x7 toll-free mental health support helpline, surfaced directly in the app for crisis situations | 14416 |

## Two distinct citation tracks, on purpose

The knowledge base deliberately keeps two separate `sources` lists per
topic:

- `sources` — clinical/public-health guidance (WHO, NHS, MoHFW), backing
  the "What you can do" section.
- `remedy_sources` — Ministry of AYUSH, backing the separate "Traditional
  home remedies" section.

They are rendered as visually distinct badges in the UI (a plain check
mark for clinical sources, a 🌿 leaf for AYUSH-sourced remedies) so a user
can tell at a glance which kind of guidance they're looking at, and never
have the two blended into one undifferentiated claim. `conversation.py`'s
`_format_final_answer()` also hard-gates `remedy_sources` to only ever
appear alongside a SELF_CARE or ROUTINE triage level — they are never
attached to a URGENT/EMERGENCY response, even for a topic that normally
has remedies, once a red flag has been raised.

## How citations flow through the code

1. Each entry in `knowledge_base.json` has a `sources: [{name, url, type}]` list.
2. `rag_engine.retrieve()` never returns an entry without its `sources` attached.
3. `conversation.py` copies those sources onto the final `ChatResponse.sources`
   field — the API response schema (`schemas.py`) makes `sources` a required,
   typed field, not an optional afterthought.
4. The frontend (`SourceBadges.jsx`) renders every source as a clickable,
   linked badge directly under the answer it supports, and `/api/sources`
   exposes the full deduplicated list for a "Verified Sources" page.

## Extending the knowledge base responsibly

If you add a new symptom topic:
- Write the `overview`, `self_care`, and `red_flags` text **in your own
  words** — do not copy-paste from the source website (both for copyright
  reasons and because verbatim medical text can be miscontextualized).
- Always attach at least one `sources` entry with a real, working URL.
- Prefer WHO, national ministries of health, and major public health
  services (NHS, CDC, ICMR) over blogs, forums, or unverified sites.
- Update `last_reviewed` in `knowledge_base.json` whenever content changes.

## Stretch goal: automated freshness checks

`backend/app/scripts/` is a good place to add a scheduled job (GitHub Actions
cron) that pings each source URL and flags in a PR comment if any link goes
dead or a "last reviewed" date passes 6 months — a nice extra "verified
sources" talking point for judges if Person A has spare time.
