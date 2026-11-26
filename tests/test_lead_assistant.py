import hashlib
import hmac
import json

import httpx
import pytest

from core import config, crm, db
from lead_assistant import analyzer, meta, pipeline, scoring
from core import profile

PROF = profile.load()


# ---------- analyzer (rule-based fallback) ----------
def test_english_pricing_extraction():
    r = analyzer.mock_analyze("Hi my name is Ali Hassan, how much for AC maintenance in Riffa? urgent, budget 80 BHD", PROF)
    assert r["intent"] == "pricing" and r["interest"] == "ac_maintenance" and r["area"] == "Riffa"
    assert r["name"] == "Ali Hassan" and r["budget_bhd"] == 80 and r["urgency"] == "high" and r["language"] == "en"


def test_arabic_extraction():
    r = analyzer.mock_analyze("مرحبا اسمي خالد أحتاج تنظيف في المنامة كم السعر؟", PROF)
    assert r["language"] == "ar" and r["name"] == "خالد" and r["interest"] == "cleaning"
    assert r["area"] == "Manama" and r["intent"] == "pricing"


def test_no_false_keyword_matches():
    r = analyzer.mock_analyze("I love your rating, my plants look great", PROF)
    assert r["interest"] != "pest_control"            # 'ants' in plants / 'rat' in rating must not match pest control


def test_spam_and_complaint():
    assert analyzer.mock_analyze("win crypto lottery click here", PROF)["intent"] == "spam"
    assert analyzer.mock_analyze("worst service, I want a refund", PROF)["intent"] == "complaint"


def test_email_and_low_urgency():
    r = analyzer.mock_analyze("just checking prices, no rush. email me at a.b@mail.com", PROF)
    assert r["email"] == "a.b@mail.com" and r["urgency"] == "low"


def test_ai_output_is_sanitised(monkeypatch):
    monkeypatch.setattr(analyzer.ai, "ask_json", lambda *a, **k: {
        "intent": "HACKED", "language": "fr", "interest": "nonsense", "urgency": "extreme",
        "budget_bhd": "abc", "name": "X" * 500, "_source": "openai"})
    r = analyzer.analyze("anything", PROF)
    assert r["intent"] == "other" and r["language"] == "en" and r["interest"] is None
    assert r["urgency"] == "medium" and r["budget_bhd"] is None and len(r["name"]) == 200


# ---------- scoring ----------
def test_scoring_thresholds():
    hot = {"intent": "pricing", "interest": "cleaning", "budget_bhd": 50, "urgency": "high", "timeline": "today"}
    s, status, why = scoring.score_lead(hot)
    assert status == "hot" and s >= 65 and any("urgent" in w for w in why)
    assert scoring.score_lead({"intent": "greeting", "urgency": "low"})[1] == "cold"
    assert scoring.score_lead({"intent": "inquiry", "interest": "cleaning", "urgency": "medium"})[1] == "warm"
    assert scoring.score_lead({"intent": "spam"}) == (0, "spam", ["looks like spam"])
    assert scoring.score_lead({"intent": "complaint", "urgency": "high"})[1] == "support"


# ---------- pipeline ----------
def test_pipeline_creates_scores_alerts_once():
    pipeline.handle_incoming("97333111222", "Hi my name is Ali, how much for AC maintenance in Riffa? urgent today, 80 BHD")
    lead = db.one("SELECT * FROM leads")
    assert lead["status"] == "hot" and lead["crm_id"].startswith("LOCAL-") and lead["alerted"] == 1
    alerts = db.rows("SELECT * FROM outbox WHERE to_addr=?", (config.SALES_REP_PHONE,))
    assert len(alerts) == 1
    pipeline.handle_incoming("97333111222", "please call me")
    assert len(db.rows("SELECT * FROM outbox WHERE to_addr=?", (config.SALES_REP_PHONE,))) == 1   # no second alert


def test_pipeline_progressive_merge_and_reply_language():
    r1 = pipeline.handle_incoming("97333444555", "مرحبا أحتاج تنظيف")
    assert "منطقة" in r1                                  # Arabic reply asking for the area
    pipeline.handle_incoming("97333444555", "في المنامة")
    lead = db.one("SELECT * FROM leads")
    assert lead["interest"] == "cleaning" and lead["area"] == "Manama"   # earlier fact kept, new one added


def test_duplicate_webhook_is_ignored():
    assert pipeline.handle_incoming("97333111222", "hello", wa_id="wamid.1") is not None
    assert pipeline.handle_incoming("97333111222", "hello", wa_id="wamid.1") is None
    assert db.one("SELECT COUNT(*) AS n FROM messages WHERE direction='in'")["n"] == 1


def test_spam_gets_no_reply_and_complaint_alerts_manager():
    assert pipeline.handle_incoming("97333666777", "win crypto lottery click here") is None
    pipeline.handle_incoming("97333888999", "my AC is not working, worst service, refund")
    assert db.rows("SELECT * FROM outbox WHERE to_addr=?", (config.MANAGER_PHONE,))


def test_crm_failure_does_not_lose_the_reply(monkeypatch):
    class Boom:
        def upsert_lead(self, lead):
            raise RuntimeError("CRM down")
    monkeypatch.setattr(crm, "get_crm", lambda: Boom())
    assert pipeline.handle_incoming("97333111222", "hello, I need cleaning") is not None
    assert db.one("SELECT 1 FROM events WHERE kind='crm_error'")


def test_daily_summary():
    pipeline.handle_incoming("97333111222", "Hi how much for AC maintenance in Riffa? urgent today 80 BHD")
    assert "Hot 1" in pipeline.daily_summary()


# ---------- Meta webhook ----------
META_PAYLOAD = {"entry": [{"changes": [{"value": {
    "contacts": [{"wa_id": "97333111222", "profile": {"name": "Ali"}}],
    "messages": [{"from": "97333111222", "id": "wamid.X", "type": "text", "text": {"body": "hi, need cleaning"}}]}}]}]}


def test_meta_parse_and_status_updates_ignored():
    msgs = meta.parse_messages(META_PAYLOAD)
    assert msgs == [{"phone": "+97333111222", "text": "hi, need cleaning", "wa_id": "wamid.X", "name": "Ali"}]
    assert meta.parse_messages({"entry": [{"changes": [{"value": {"statuses": [{"id": "1"}]}}]}]}) == []


def test_signature_check():
    body = b'{"a":1}'
    good = "sha256=" + hmac.new(b"sek", body, hashlib.sha256).hexdigest()
    assert meta.valid_signature(body, good, "sek")
    assert not meta.valid_signature(body, "sha256=bad", "sek")
    assert not meta.valid_signature(body, None, "sek")


# ---------- Zoho (request shape verified with a mock transport) ----------
def test_zoho_upsert_request_shape_and_token_cache(monkeypatch):
    for k, v in {"ZOHO_REFRESH_TOKEN": "rt", "ZOHO_CLIENT_ID": "cid", "ZOHO_CLIENT_SECRET": "cs"}.items():
        monkeypatch.setattr(config, k, v)
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if "oauth/v2/token" in request.url.path:
            return httpx.Response(200, json={"access_token": "AT", "expires_in": 3600})
        return httpx.Response(200, json={"data": [{"status": "success", "details": {"id": "Z123"}}]})

    z = crm.ZohoCRM(httpx.Client(transport=httpx.MockTransport(handler)))
    lead = {"id": 1, "phone": "+97333111222", "name": "Ali", "email": "a@b.com", "score": 90, "status": "hot",
            "summary": "wants AC"}
    assert z.upsert_lead(lead) == "Z123"
    assert z.upsert_lead(lead) == "Z123"
    upserts = [r for r in seen if "upsert" in r.url.path]
    body = json.loads(upserts[0].content)
    assert upserts[0].url.path == "/crm/v2/Leads/upsert"
    assert upserts[0].headers["Authorization"] == "Zoho-oauthtoken AT"
    assert body["duplicate_check_fields"] == ["Phone"] and body["data"][0]["Last_Name"] == "Ali"
    assert sum("oauth" in r.url.path for r in seen) == 1          # token fetched once, then cached


def test_zoho_rejection_raises():
    def handler(request):
        if "oauth" in request.url.path:
            return httpx.Response(200, json={"access_token": "AT", "expires_in": 3600})
        return httpx.Response(200, json={"data": [{"status": "error", "code": "INVALID_DATA"}]})
    z = crm.ZohoCRM(httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(RuntimeError):
        z.upsert_lead({"id": 1, "phone": "+1"})
