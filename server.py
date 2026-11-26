"""One FastAPI app exposing both projects as webhooks / REST endpoints.

Run:  uvicorn server:app --reload --port 8000        Docs: http://localhost:8000/docs"""
from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from pydantic import BaseModel

from core import config, db
from lead_assistant import meta, pipeline
from marketing_automation import campaign

app = FastAPI(title="AI Automation Portfolio", version="1.0")
db.init()


@app.get("/")
def health():
    return {"status": "ok", "ai": config.LLM_PROVIDER, "whatsapp": config.WA_MODE, "crm": config.CRM_MODE,
            "email": config.EMAIL_MODE}


# ======================= Project 1: WhatsApp AI Lead Assistant =======================
@app.get("/lead-assistant/webhook")
def meta_verify(mode: str = Query(None, alias="hub.mode"), token: str = Query(None, alias="hub.verify_token"),
                challenge: str = Query(None, alias="hub.challenge")):
    """Meta calls this once when you save the webhook URL in the developer dashboard."""
    if mode == "subscribe" and token == config.META_VERIFY_TOKEN and challenge is not None:
        return PlainTextResponse(challenge)
    raise HTTPException(403, "verification failed")


@app.post("/lead-assistant/webhook")
async def meta_incoming(request: Request, background: BackgroundTasks):
    raw = await request.body()
    if config.META_APP_SECRET and not meta.valid_signature(
            raw, request.headers.get("X-Hub-Signature-256"), config.META_APP_SECRET):
        raise HTTPException(403, "bad signature")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(400, "invalid JSON")
    msgs = meta.parse_messages(payload)
    for m in msgs:                                            # answer 200 fast; Meta retries slow webhooks
        background.add_task(pipeline.handle_incoming, m["phone"], m["text"], m["name"], m["wa_id"])
    return {"received": len(msgs)}


@app.post("/lead-assistant/twilio")
def twilio_incoming(From: str = Form(...), Body: str = Form(""), MessageSid: str = Form(None),
                    ProfileName: str = Form(None)):
    """Twilio WhatsApp sandbox webhook: replies by returning TwiML."""
    reply = pipeline.handle_incoming(From.replace("whatsapp:", ""), Body, ProfileName, MessageSid)
    xml = "<Response></Response>"
    if reply and config.WA_MODE == "twilio":
        # pipeline already sent via REST; avoid a double reply
        pass
    elif reply:
        from xml.sax.saxutils import escape
        xml = f"<Response><Message>{escape(reply)}</Message></Response>"
    return Response(xml, media_type="application/xml")


class Simulate(BaseModel):
    phone: str = "+97333000111"
    text: str
    name: str | None = None


@app.post("/lead-assistant/simulate")
def simulate(body: Simulate):
    """Test without WhatsApp: pretend a customer sent this message."""
    reply = pipeline.handle_incoming(body.phone, body.text, body.name)
    lead = db.one("SELECT * FROM leads WHERE phone=?", ("+" + "".join(c for c in body.phone if c.isdigit()),))
    return {"reply": reply, "lead": lead}


@app.get("/lead-assistant/leads")
def leads(status: str | None = None):
    if status:
        return db.rows("SELECT * FROM leads WHERE status=? ORDER BY score DESC", (status,))
    return db.rows("SELECT * FROM leads ORDER BY score DESC, updated_at DESC")


@app.get("/lead-assistant/summary", response_class=PlainTextResponse)
def summary():
    return pipeline.daily_summary()


# ======================= Project 2: Bilingual Marketing Automation =======================
class LeadForm(BaseModel):
    email: str
    name: str | None = None
    language: str = "en"
    interest: str | None = None
    source: str = "website form"


@app.post("/marketing/leads")
def new_lead(form: LeadForm):
    """Webhook for a website / Facebook-lead / Zapier form."""
    try:
        sub = campaign.subscribe(form.email, form.name, form.language, form.interest, form.source)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    if not sub["duplicate"]:
        campaign.run_due()                                    # welcome email goes out immediately
    return sub


@app.get("/marketing/subscribers")
def subscribers():
    return db.rows("SELECT * FROM subscribers ORDER BY id DESC")


@app.post("/marketing/run-due")
def run_due():
    """Call this from a scheduler (cron / n8n / Make) every hour."""
    return campaign.run_due()


class EventBody(BaseModel):
    kind: str


@app.post("/marketing/subscribers/{sub_id}/event")
def event(sub_id: int, body: EventBody):
    try:
        sub = campaign.mark(sub_id, body.kind)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    if not sub:
        raise HTTPException(404, "subscriber not found")
    return sub


@app.get("/marketing/unsubscribe/{token}", response_class=HTMLResponse)
def unsubscribe(token: str):
    sub = campaign.unsubscribe(token)
    if not sub:
        raise HTTPException(404, "invalid link")
    return ("<div style='font-family:Arial;text-align:center;margin-top:60px'><h2>You are unsubscribed ✔</h2>"
            "<p>لقد تم إلغاء اشتراكك بنجاح</p></div>")


@app.get("/marketing/report")
def report():
    return campaign.funnel()
