# Interview guide (short)

## 60-second pitch
"I built two automation projects for a Bahrain service business. First: a WhatsApp AI lead assistant — a customer writes in English or Arabic, AI understands the request, scores the lead, saves it to Zoho CRM, alerts sales on WhatsApp if it's hot, and replies in the customer's language. Second: a bilingual email drip for new leads that stops automatically when they reply or unsubscribe. It works with Claude, OpenAI or Gemini, and falls back to rules if the AI is down, so the automation never stops."

## Demo order (5 minutes)
1. Dashboard → P1 → "Hot English" → Send. Show: score, reasons (Activity log), alert in Outbox, CRM record.
2. Send the Arabic sample → reply comes in Arabic, asks the next missing detail.
3. Send Spam → no reply. Send Complaint → goes to the manager, not sales.
4. P2 → submit a "both" lead → open Outbox (EN + AR block, RTL) → fast-forward 3 days → mark "replied" → run scheduler: drip stops.

## Questions you will get
- **Why a fallback?** AI/CRM can be down; losing a customer reply is worse than a simpler reply. CRM errors are logged and never block the reply.
- **How do you stop duplicates?** WhatsApp retries webhooks; messages are deduped by `wa_id`; CRM upsert dedupes by phone/email.
- **Security?** Meta HMAC signature check, unsubscribe links are HMAC-signed, AI output is validated (intent/interest whitelists), customer text is treated as data not instructions, HTML escaped in emails.
- **WhatsApp 24-hour rule?** Free-form replies only within 24h of the customer's message; outside that window (e.g. alerts to staff) you need approved templates.
- **Make vs n8n vs Zapier?** n8n: self-host free, code nodes. Make: visual, good free tier. Zapier: biggest app catalogue, costs more at volume. Same logic in all three — see the rebuild guide.
- **What would you improve?** Real templates for WhatsApp, media (voice notes/photos), human hand-over, A/B subject lines, analytics.

## Be honest
Say which parts you tested live (the demo) and which you only unit-tested (Zoho/Meta/Twilio with your own account) — interviewers respect that.
