# Same logic in Make, Zapier, Power Automate

Interviewers often ask for the tool they use. The logic is identical — only the boxes change.

## P1 — WhatsApp lead assistant
| Step | n8n | Make | Zapier | Power Automate |
|---|---|---|---|---|
| Trigger | Webhook | Custom webhook (or WhatsApp Business Cloud module) | Webhooks by Zapier – Catch Hook | "When an HTTP request is received" |
| AI understanding | HTTP Request → LLM | HTTP / OpenAI module | OpenAI / Anthropic step | HTTP action → LLM |
| Score | Code node | Set variable + math | Code by Zapier / Formatter | Compose + expressions |
| CRM | Zoho node | Zoho CRM "Create/Update record" | Zoho CRM "Find or Create Lead" | Zoho connector (premium) or Dataverse |
| Hot? | IF | Router + filter | Filter / Paths | Condition |
| Alert + reply | WhatsApp / HTTP | WhatsApp Business module | WhatsApp Business app | HTTP to Meta API |

## P2 — marketing drip
Trigger = form/webhook → upsert contact in CRM → AI writes email → send (Gmail / Outlook) → **Delay 2 days** → check "replied/unsubscribed" field in CRM → send next or stop.
- Make: Sleep / scheduled scenario + filter. Zapier: Delay For + Filter. Power Automate: Delay + Condition.

## Free-tier note
Check each vendor's current limits before relying on them (they change). Verified earlier: n8n Community self-host is free; Make Free = 1,000 credits/month, 2 active scenarios; Zoho CRM Free = 3 users. Zapier and Power Automate free access were not verified.
