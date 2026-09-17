# Task Division — Two-Person Team

This project is scoped so each person owns a full vertical slice with a
clean interface between them: **the JSON shape of `ChatResponse`**
(`backend/app/schemas.py`). As long as that contract holds, both of you
can work almost entirely in parallel.

## Person A — Backend & Intelligence

**Owns:** `backend/` end to end.

| Area | Files |
|---|---|
| API routes | `app/main.py` |
| Follow-up conversation flow, topic confirmation, recap | `app/conversation.py` |
| Safety layer & triage escalation | `app/safety_layer.py` |
| Retrieval (RAG) engine | `app/rag_engine.py` |
| Knowledge base content + citations (WHO/NHS/MoHFW) | `app/data/knowledge_base.json` |
| Home remedies content + AYUSH citations | same file, `home_remedies` / `remedy_sources` fields |
| Cross-topic emergency phrase list | `app/data/red_flags.json` |
| Language detection + Bhashini voice wrapper | `app/translation.py` |
| Tests | `backend/tests/` |

**Hackathon focus, in priority order:**
1. Get the 5 must-have topics rock-solid (fever, cough/cold, headache,
   stomach/diarrhea, one always-urgent topic like chest pain) with real
   citations — this is what judges will poke at hardest.
2. Add 3-5 more topics if time allows (skin rash, fatigue, injury, stress).
3. Tighten the red-flag keyword lists (in both languages) — this is the
   single highest-leverage thing for "safety-first" scoring.
4. Add automated tests for any new topic you add (`pytest`, see
   `test_safety_layer.py` for the pattern) — a green test suite is a
   strong signal to judges that this isn't held together by luck.

## Person B — Frontend, Voice & Offline Experience

**Owns:** `frontend/` end to end.

| Area | Files |
|---|---|
| Conversation UI, state management | `src/App.jsx` |
| Bilingual chrome text | `src/i18n.js` |
| Chat bubbles, safety banner, citation badges | `src/components/` |
| Voice input (Web Speech API + Bhashini hook) | `src/components/VoiceButton.jsx` |
| Offline fallback engine (mirrors backend logic) | `src/offline/` |
| PWA app-shell caching | `public/manifest.webmanifest`, `public/sw.js` |
| Visual design / Tailwind tokens | `tailwind.config.js`, `src/index.css` |

**Hackathon focus, in priority order:**
1. Get the online chat flow polished: smooth quick-reply chips, clear
   triage banner colors, readable Hindi typography (test with real
   Devanagari text early — font fallbacks matter).
2. Test the offline fallback for real: turn off wifi mid-conversation and
   confirm the chat keeps working and clearly tells the user it switched
   modes (see `App.jsx`'s `sendMessage` catch block).
3. Polish the mobile layout — assume judges will look at this on a phone.
4. Voice input: confirm the mic button works in Chrome for both `en-IN`
   and `hi-IN`; Bhashini integration is a stretch goal, not required for
   a strong demo.

## Shared / either person

- `ARCHITECTURE.md`, `README.md`, this file — keep updated as you build,
  not at the end. Judges read these.
- `docker-compose.yml`, GitHub Actions workflows — set these up **on day
  1**, even before there's much to build. A green CI badge and a working
  `docker compose up` from minute one removes a ton of last-day stress.
- Run `npm run sync-kb` (or just `npm run dev` / `npm run build`, which
  do it automatically) any time Person A changes
  `backend/app/data/knowledge_base.json`, so Person B's offline engine
  stays in sync. This is scripted precisely so neither of you has to
  remember to do it by hand.

## Suggested day-by-day plan (typical 24-36h hackathon)

| Time | Person A | Person B |
|---|---|---|
| Hour 0-2 | Set up backend skeleton, `/api/health`, first 2 KB topics | Set up frontend skeleton, Tailwind tokens, static chat mockup |
| Hour 2-6 | Full conversation state machine (duration/severity/age/red-flags) | Wire chat UI to a mocked API response; build TriageBanner + SourceBadges |
| Hour 6-10 | Safety layer + global emergency detection; 5+ more KB topics | Connect to real backend; polish quick-reply chips, Hindi text rendering |
| Hour 10-14 | Home remedies + AYUSH citations; topic-confirmation step | Offline engine (`src/offline/`) + PWA service worker |
| Hour 14-18 | Write tests; tighten red-flag phrase lists; deploy backend to Render | Voice input; deploy frontend to Vercel; connect the two |
| Hour 18-22 | Bug bash together: try to break the safety layer on purpose | Bug bash together: try every device size, try offline mid-flow |
| Hour 22-24 | Finalize docs, prep demo script, rehearse pitch | Same — rehearse the live demo end to end at least 3 times |

## Demo script (aim for ~3 minutes)

1. **Open with the problem** (10s): "People Google symptoms and get
   either scary WebMD spirals or nothing trustworthy at all — especially
   in Hindi."
2. **Show the happy path** (60s): Type "मुझे बुखार है" (or "I have a
   fever"). Walk through: topic confirmation with visible confidence →
   duration/severity/age chips → final answer with the recap, WHO/MoHFW
   citations, AND the separately-cited AYUSH home remedies block.
3. **Show the safety layer** (30s): Type "chest pain and can't breathe"
   at any point — show it interrupts immediately with the red EMERGENCY
   banner and one-tap 108/112 numbers, not waiting for follow-ups.
4. **Show offline mode** (30s): Turn off wifi (or airplane mode on your
   demo phone), send a message, show the amber "offline" banner and that
   the answer still comes back fully cited from the on-device engine.
5. **Close on why it's trustworthy** (20s): Point at `/api/sources` or
   the Verified Sources sidebar — "every claim traces back to WHO, NHS,
   India's National Health Portal, or the Ministry of AYUSH — never open
   web search, never an unsourced model guess."

## What to say if a judge asks "why not just use ChatGPT?"

- ChatGPT (or a raw LLM call) can't guarantee a citation, can silently
  hallucinate a dosage, and has no structural reason to separate "this is
  dangerous" from "here's some general info" — it's all one blended
  stream of text.
- Here, the safety verdict and the citations are **typed fields in the
  API response**, not vibes extracted from prose. A reviewer can inspect
  `ChatResponse.sources` and `ChatResponse.triage_level` directly.
- And it keeps working with no internet at all, which matters a lot for
  the audience this is actually built for.
