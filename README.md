# AI Automation Portfolio — 2 projects

Built to match a "AI Agents & Business Automation" job description (Bahrain / GCC).
Everything runs **offline with no keys** (mock AI, console WhatsApp/email, local CRM). Add keys later to go live.

| Project | What it does |
|---|---|
| **P1 · WhatsApp AI Lead Assistant** | Customer WhatsApp message (EN / AR / mixed) → AI extracts intent, service, area, budget, urgency → lead score (hot/warm/cold) → CRM → instant WhatsApp alert to sales → reply in the customer's language |
| **P2 · Bilingual Marketing Automation** | Website/Facebook lead form → CRM → 4-email drip (day 0/2/5/9) in English, Arabic (RTL) or both → reply / sale / unsubscribe stops it → funnel report |

## JD requirement → where it is covered

| JD asks for | Where |
|---|---|
| Practical AI agents + live business integrations | `lead_assistant/pipeline.py`, `marketing_automation/campaign.py`, `core/ai.py` (Claude / OpenAI / Gemini / Groq + safe fallback) |
| n8n / Make / Power Automate / Zapier | `n8n/*.json` skeleton workflows (see honesty note) + `docs/REBUILD_IN_MAKE_ZAPIER_POWERAUTOMATE.md` |
| Python / JavaScript, APIs, webhooks, JSON | FastAPI webhooks in `server.py` (Meta verify + HMAC signature, Twilio TwiML), JS code nodes in n8n JSON |
| CRM, marketing, sales automation | `core/crm.py` (Zoho CRM + local), lead scoring, drip campaign, funnel |
| English + Arabic content | Arabic NLP in the analyzer, Arabic replies, RTL emails, bilingual mode |
| Zoho / Google Workspace / M365 / WhatsApp Business | `ZohoCRM` upsert (OAuth refresh token), SMTP (Gmail/M365 app password), Meta WhatsApp Cloud API + Twilio sandbox |

## Run it (Windows) — 3 steps
1. Install Python 3.11+ (tick "Add to PATH").
2. Double-click **START_HERE.bat** (creates venv, installs, runs tests, opens the dashboard).
3. In the dashboard: **P1 tab** → pick "Hot English" → *Send as customer*. **P2 tab** → *Submit lead form* → *Run scheduler* (fast-forward days).

Command line: `python demo.py` · `python -m pytest` · `streamlit run dashboard.py` · `uvicorn server:app --port 8000` (docs at /docs).

## Go live (all optional, set in `.env`, copy from `.env.example`)
- **AI**: `LLM_PROVIDER=anthropic` + key, or `openai` + `OPENAI_BASE_URL` (Gemini / Groq free tiers).
- **WhatsApp**: `docs/WHATSAPP_SETUP.md` · **Zoho CRM**: `docs/ZOHO_SETUP.md`
- **Email**: `EMAIL_MODE=smtp` with a Gmail/M365 app password.

## Honest status
- **Tested here** (35 automated tests + live server check + dashboard run): extraction, scoring, pipeline, dedupe, Meta verify/POST/signature, Twilio TwiML, drip scheduling, unsubscribe, Arabic RTL email, AI-failure fallback, Zoho request shape (against a mock server).
- **NOT tested live**: a real LLM key, real Meta/Twilio sending, a real Zoho account, SMTP delivery, and importing the n8n JSON into n8n. The code paths exist and fail safe (logged, never crash); verify each one once with your own account before an interview demo.
- The n8n files are **skeletons**: webhook → code → LLM call → score → branch work as written; CRM/WhatsApp/email nodes are `NoOp` placeholders you replace with the real app nodes + credentials.
- Business profile is a made-up demo company (`business_profile.json`) — swap in the target company's services.
