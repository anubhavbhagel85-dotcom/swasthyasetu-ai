# SwasthyaSetu AI 🩺🇮🇳

**A multilingual symptom guidance assistant that answers with cited, verified medical information — not guesses.**

> स्वास्थ्य + सेतु — "a bridge to health." Built for a college hackathon by a two-person team.

SwasthyaSetu AI helps people describe a symptom in plain English or Hindi,
asks a few careful follow-up questions (duration, severity, age group,
warning signs), and returns two clearly separated things:

1. **General guidance**, grounded in a curated knowledge base and shown
   with the exact health authority it came from (WHO / NHS / National
   Health Portal India), and
2. **A safety verdict** — self-care, routine check-up, urgent, or
   emergency — rendered as its own visually distinct banner, never mixed
   into the general text.

It never claims to diagnose anything. That's a deliberate design choice,
not a limitation we're hiding — see [`SOURCES.md`](./SOURCES.md) and
[`ARCHITECTURE.md`](./ARCHITECTURE.md) for how that's enforced in code.

---

## Why this is different from "just wrapping an LLM"

| | Generic AI chatbot | SwasthyaSetu AI |
|---|---|---|
| Where answers come from | Model's memory / open web | A small, curated, cited knowledge base |
| Citations | Rare, often fabricated | Attached to every answer, required by the API schema |
| Safety handling | Mixed into free-text prose | A separate, independent safety layer that cannot be skipped |
| Emergency detection | Not guaranteed | Runs on **every** message, at every conversation stage |
| Language | Usually English-first | Hindi & English from the ground up, voice-ready |
| Diagnosis | Often implied | Explicitly never given — only triage + information |

## Must-have features (hackathon brief)

- [x] **Symptom input** — free text, Hindi or English, auto-detects script
- [x] **Follow-up questions** — topic confirmation (with a visible confidence score) → duration → severity → age group → red-flag checklist, then a plain-language **recap** of exactly what was said before the final answer
- [x] **Verified sources** — every answer carries citations from WHO / NHS / National Health Portal India (MoHFW); see `/api/sources`
- [x] **Safety response** — urgent warning signs rendered as a separate banner from general guidance, with one-tap emergency numbers (108 / 112 / Tele-MANAS 14416)
- [x] **Bonus: Voice + Hindi** — mic input via the Web Speech API out of the box, with an optional upgrade path to the Government of India's Bhashini API for higher-accuracy Hindi ASR/TTS

## What makes this a *complete* project, not just an MVP checkbox list

- **🌿 Home remedies, separately cited** — every self-care answer also
  surfaces traditional home remedies sourced from the **Ministry of AYUSH,
  Government of India** (`ayush.gov.in`), shown in their own cited block
  with its own caution text. These are *never* shown for urgent/emergency
  topics (chest pain, breathing difficulty) or once a red flag has been
  raised — that gate lives in the safety layer, not the UI, so it can't be
  bypassed. See `SOURCES.md`.
- **✅ Topic confirmation + confidence** — instead of silently trusting one
  keyword match, the assistant asks "Did you mean *X*?" (with a
  low-confidence hedge shown when relevant) before spending the user's
  time on follow-up questions. Say "no" and it lets you rephrase or pick
  from a topic list directly.
- **📋 Transparent recap** — before giving guidance, the assistant echoes
  back exactly what you told it (topic, duration, severity, age group,
  any red flags) so the answer visibly traces back to your own words, not
  a generic template.
- **📴 Works with poor or no internet** — a Progressive Web App shell
  (`public/sw.js`) caches the app itself, and a client-side offline engine
  (`src/offline/`) mirrors the backend's retrieval + safety logic against
  the same cited knowledge base. If the network drops mid-conversation,
  the chat keeps working transparently — no lost turns, no dead-end error
  screen — and syncs the transcript back once connectivity returns
  (`POST /api/sync`).

## Project structure

```
swasthyasetu-ai/
├── backend/              FastAPI service — RAG engine + safety layer + conversation flow
│   ├── app/
│   │   ├── main.py           API routes (chat, sources, health, voice, sync)
│   │   ├── conversation.py   Multi-turn flow: confirm topic → follow-ups → recap → answer
│   │   ├── safety_layer.py   Independent triage / red-flag detector
│   │   ├── rag_engine.py     TF-IDF retrieval over the knowledge base
│   │   ├── translation.py    Language detection + Bhashini voice wrapper
│   │   ├── schemas.py        Pydantic request/response contracts
│   │   └── data/
│   │       ├── knowledge_base.json   10 bilingual, cited topics + AYUSH home remedies
│   │       └── red_flags.json        Cross-topic emergency phrase list
│   └── tests/
├── frontend/             React + Vite + Tailwind chat UI
│   ├── scripts/
│   │   └── sync-knowledge-base.js   Keeps the offline copy in sync with backend/
│   ├── public/
│   │   ├── manifest.webmanifest     PWA manifest
│   │   └── sw.js                    App-shell service worker (offline support)
│   └── src/
│       ├── App.jsx            Online/offline-aware conversation state
│       ├── i18n.js            EN/HI UI copy
│       ├── offline/           Client-side fallback engine (mirrors the backend)
│       └── components/        Header, chat bubbles, triage banner, voice button, sidebar
├── docker-compose.yml
├── ARCHITECTURE.md
├── DEPLOYMENT_GUIDE.md
├── TASK_DIVISION.md
└── SOURCES.md
```

## Quick start (local)

### 1. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for the interactive API docs, or check
`http://localhost:8000/api/health`.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_URL=http://localhost:8000
npm run dev
```

Visit `http://localhost:5173`.

### 3. Or run both with Docker Compose

```bash
docker compose up --build
```

Frontend on `http://localhost:5173`, backend on `http://localhost:8000`.

Full production deployment steps (Render + Vercel, or a single VM) are in
[`DEPLOYMENT_GUIDE.md`](./DEPLOYMENT_GUIDE.md).

## Try it: example conversation

```
You:        मुझे कल से बुखार है
SwasthyaSetu: समझ गया - यह Fever से संबंधित लगता है। क्या यह सही है?
              [हां, यह सही है] [नहीं]
You:        [हां, यह सही है]
SwasthyaSetu: यह कब से हो रहा है?
              [आज ही शुरू हुआ] [2-3 दिन] [4-7 दिन] [एक हफ्ते से ज़्यादा]
...
SwasthyaSetu: आपने बताया: Fever, आज ही शुरू हुआ से, गंभीरता: हल्का, आयु वर्ग: 18-59 साल।
              बुखार शरीर का संक्रमण या सूजन के प्रति एक स्वाभाविक प्रतिक्रिया है...
              आप क्या कर सकते हैं (WHO / NHS / MoHFW मार्गदर्शन): ...
              पारंपरिक घरेलू उपाय (आयुष मंत्रालय): तुलसी और अदरक का काढ़ा...
              ✓ World Health Organization – Fact sheets
              ✓ National Health Portal India (MoHFW)
              🌿 Ministry of AYUSH, Government of India
```

Type "chest pain and can't breathe" at any point and the safety layer
interrupts the flow immediately with an EMERGENCY banner and one-tap
108/112 numbers — it does not wait for the follow-up questions to finish,
and it never shows home remedies once that's triggered.

Turn off your wifi mid-conversation and the chat keeps going — an amber
banner tells you it has switched to the on-device engine, and the answer
still comes back fully cited from the same knowledge base.

## Team & task division

Built by a two-person team. See [`TASK_DIVISION.md`](./TASK_DIVISION.md)
for the full split, day-by-day hackathon plan, and how to demo it live.

## Disclaimer

SwasthyaSetu AI is a hackathon prototype for general health information.
It does not diagnose conditions, prescribe treatment, or replace a
qualified doctor. In a medical emergency, call 108 (ambulance) or 112
(national emergency number) in India, or your local emergency number.

## License

MIT for the code (see `LICENSE`). The cited third-party medical guidance
belongs to its respective publishers — see `SOURCES.md`.
