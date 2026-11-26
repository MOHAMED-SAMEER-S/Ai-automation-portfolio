from datetime import datetime, timedelta

import pytest

from core import db
from marketing_automation import campaign


def test_subscribe_schedules_4_steps_and_dedupes():
    a = campaign.subscribe("Sara@Test.com", "Sara", "en", "cleaning")
    assert a["duplicate"] is False and a["crm_id"].startswith("LOCAL-SUB-")
    assert [d["step_name"] for d in db.rows("SELECT * FROM drip ORDER BY step")] == ["welcome", "tip", "offer", "last_call"]
    assert campaign.subscribe("sara@test.com")["duplicate"] is True
    assert db.one("SELECT COUNT(*) AS n FROM subscribers")["n"] == 1


def test_invalid_email_rejected():
    with pytest.raises(ValueError):
        campaign.subscribe("not-an-email")


def test_run_due_time_travel_sends_in_order_and_never_twice():
    campaign.subscribe("a@test.com")
    assert campaign.run_due()["sent"] == 1                                    # day 0 welcome
    assert campaign.run_due()["sent"] == 0                                    # nothing else due yet
    assert campaign.run_due(datetime.now() + timedelta(days=2, minutes=1))["sent"] == 1
    assert campaign.run_due(datetime.now() + timedelta(days=30))["sent"] == 2  # offer + last call
    assert campaign.run_due(datetime.now() + timedelta(days=60))["sent"] == 0
    assert db.one("SELECT COUNT(*) AS n FROM outbox WHERE channel='email'")["n"] == 4


@pytest.mark.parametrize("kind", ["replied", "converted", "unsubscribed"])
def test_engagement_stops_the_drip(kind):
    s = campaign.subscribe("a@test.com")
    campaign.run_due()
    campaign.mark(s["id"], kind)
    assert campaign.run_due(datetime.now() + timedelta(days=30))["sent"] == 0
    assert db.one("SELECT COUNT(*) AS n FROM drip WHERE status='skipped'")["n"] == 3


def test_unsubscribed_stays_unsubscribed():
    s = campaign.subscribe("a@test.com")
    campaign.mark(s["id"], "unsubscribed")
    assert campaign.mark(s["id"], "converted")["status"] == "unsubscribed"


def test_unsubscribe_token_is_signed():
    s = campaign.subscribe("a@test.com")
    token = campaign.make_token(s["id"], "a@test.com")
    assert campaign.read_token(token)["id"] == s["id"]
    assert campaign.read_token(f"{s['id']}.forgedsignature") is None
    assert campaign.read_token("garbage") is None
    assert campaign.unsubscribe(token)["status"] == "unsubscribed"


def test_arabic_email_is_rtl_and_bilingual_has_both():
    ar = campaign.compose_email("welcome", {"id": 1, "email": "a@b.com", "name": "سارة", "language": "ar"})
    assert 'dir="rtl"' in ar["html"] and "أهلاً" in ar["subject"]
    both = campaign.compose_email("offer", {"id": 1, "email": "a@b.com", "name": "Sara", "language": "both"})
    assert 'dir="rtl"' in both["html"] and 'dir="ltr"' in both["html"] and "unsubscribe" in both["html"].lower()


def test_email_html_is_escaped():
    m = campaign.compose_email("welcome", {"id": 1, "email": "a@b.com", "name": "<script>alert(1)</script>", "language": "en"})
    assert "<script>" not in m["html"]


def test_ai_garbage_falls_back_to_template(monkeypatch):
    monkeypatch.setattr(campaign.ai, "ask_json", lambda *a, **k: {"subject": "", "_source": "openai"})
    m = campaign.compose_email("welcome", {"id": 1, "email": "a@b.com", "name": "Sara", "language": "en"})
    assert m["subject"].startswith("Welcome") and "bad AI output" in m["source"]


def test_funnel_report():
    a = campaign.subscribe("a@test.com")
    campaign.subscribe("b@test.com")
    campaign.mark(a["id"], "converted")
    f = campaign.funnel()
    assert f["subscribers"] == 2 and f["conversion_rate_pct"] == 50.0
