import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from core import config, db
import server

client = TestClient(server.app)


def test_health():
    assert client.get("/").json()["ai"] == "mock"


def test_meta_verification_handshake():
    ok = client.get("/lead-assistant/webhook", params={
        "hub.mode": "subscribe", "hub.verify_token": config.META_VERIFY_TOKEN, "hub.challenge": "12345"})
    assert ok.status_code == 200 and ok.text == "12345"
    bad = client.get("/lead-assistant/webhook", params={
        "hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "1"})
    assert bad.status_code == 403


PAYLOAD = {"entry": [{"changes": [{"value": {
    "contacts": [{"wa_id": "97333111222", "profile": {"name": "Ali"}}],
    "messages": [{"from": "97333111222", "id": "wamid.A", "type": "text",
                  "text": {"body": "how much for AC maintenance in Riffa? urgent today"}}]}}]}]}


def test_meta_post_creates_lead_and_enforces_signature(monkeypatch):
    monkeypatch.setattr(config, "META_APP_SECRET", "sek")
    raw = json.dumps(PAYLOAD).encode()
    assert client.post("/lead-assistant/webhook", content=raw).status_code == 403          # unsigned
    sig = "sha256=" + hmac.new(b"sek", raw, hashlib.sha256).hexdigest()
    r = client.post("/lead-assistant/webhook", content=raw, headers={"X-Hub-Signature-256": sig})
    assert r.status_code == 200 and r.json() == {"received": 1}
    assert db.one("SELECT * FROM leads WHERE phone='+97333111222'")["interest"] == "ac_maintenance"


def test_twilio_returns_twiml():
    r = client.post("/lead-assistant/twilio", data={"From": "whatsapp:+97333111222", "Body": "hello", "MessageSid": "SM1"})
    assert r.status_code == 200 and r.text.startswith("<Response><Message>")
    assert "xml" in r.headers["content-type"]


def test_simulate_and_leads_endpoints():
    r = client.post("/lead-assistant/simulate", json={"text": "I need pest control in Muharraq tomorrow, budget 40 BD"}).json()
    assert r["lead"]["interest"] == "pest_control" and r["reply"]
    assert len(client.get("/lead-assistant/leads").json()) == 1
    assert "Lead summary" in client.get("/lead-assistant/summary").text


def test_marketing_lead_form_to_unsubscribe():
    r = client.post("/marketing/leads", json={"email": "sara@test.com", "name": "Sara", "language": "both"})
    assert r.status_code == 200 and r.json()["duplicate"] is False
    assert db.one("SELECT COUNT(*) AS n FROM drip WHERE status='sent'")["n"] == 1          # welcome sent at once
    assert client.post("/marketing/leads", json={"email": "sara@test.com"}).json()["duplicate"] is True
    assert client.post("/marketing/leads", json={"email": "bad"}).status_code == 422
    sub = client.get("/marketing/subscribers").json()[0]
    assert client.post(f"/marketing/subscribers/{sub['id']}/event", json={"kind": "replied"}).json()["status"] == "replied"
    assert client.post(f"/marketing/subscribers/{sub['id']}/event", json={"kind": "bogus"}).status_code == 422
    assert client.post("/marketing/subscribers/999/event", json={"kind": "replied"}).status_code == 404
    from marketing_automation import campaign
    token = campaign.make_token(sub["id"], sub["email"])
    assert client.get(f"/marketing/unsubscribe/{token}").status_code == 200
    assert client.get("/marketing/unsubscribe/1.fake").status_code == 404
    assert client.get("/marketing/report").json()["subscribers"] == 1
