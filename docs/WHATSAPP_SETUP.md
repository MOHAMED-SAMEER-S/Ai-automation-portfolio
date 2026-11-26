# WhatsApp setup

## Option A — Twilio sandbox (fastest for a demo)
1. Twilio account → Messaging → Try it out → WhatsApp sandbox. Join it from your phone with the code shown.
2. Run `uvicorn server:app --port 8000` and expose it: `ngrok http 8000` (or cloudflared).
3. Sandbox settings → "When a message comes in" = `https://YOUR-URL/lead-assistant/twilio` (POST).
4. `.env`: `WA_MODE=twilio`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `SALES_REP_PHONE=+973...` (must also have joined the sandbox).
5. Message the sandbox number from your phone.

## Option B — Meta WhatsApp Cloud API (what a real company uses)
1. developers.facebook.com → create app → add WhatsApp → use the free test number (up to 5 recipient numbers).
2. Webhook callback URL: `https://YOUR-URL/lead-assistant/webhook`, verify token = `META_VERIFY_TOKEN` (default `verify-me`). Subscribe to **messages**.
3. `.env`: `WA_MODE=meta`, `META_TOKEN` (temporary tokens expire in ~24h — use a System User token for anything longer), `META_PHONE_ID` (the phone number ID, not the number), `META_APP_SECRET` (enables signature checking).
4. 24-hour rule: free-form replies work only within 24h of the customer's last message. Staff alerts outside that window need approved templates.

Troubleshooting: check the dashboard Outbox (`delivery` column) and Activity log (`whatsapp_error`).
