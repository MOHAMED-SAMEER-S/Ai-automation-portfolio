"""Project 1 pipeline: WhatsApp message -> AI understanding -> lead record -> score -> CRM -> alert -> reply."""
from core import config, crm, db, notify, profile

from . import analyzer, replies, scoring


def _merge(lead: dict, info: dict) -> dict:
    """New non-empty facts from this message overwrite old ones; nothing already known is erased."""
    merged = dict(lead)
    for k in ("name", "email", "interest", "area", "budget_bhd", "timeline"):
        if info.get(k):
            merged[k] = info[k]
    merged["language"] = info["language"]
    merged["intent"] = info["intent"]
    merged["urgency"] = info["urgency"] if info["urgency"] == "high" or not lead.get("urgency") else \
        (lead["urgency"] if lead.get("urgency") == "high" else info["urgency"])
    merged["summary"] = info.get("summary") or lead.get("summary")
    return merged


def handle_incoming(phone: str, text: str, profile_name: str | None = None, wa_id: str | None = None) -> str | None:
    """Process one customer message. Returns the reply sent (None = duplicate or nothing to say)."""
    db.init()
    phone = "+" + "".join(ch for ch in phone if ch.isdigit())
    if wa_id and db.one("SELECT 1 FROM messages WHERE wa_id=?", (wa_id,)):
        return None                                           # WhatsApp retries webhooks: ignore duplicates
    prof = profile.load()

    lead = db.one("SELECT * FROM leads WHERE phone=?", (phone,))
    if not lead:
        lead_id = db.execute("INSERT INTO leads (phone, name, source, created_at, updated_at) VALUES (?,?,?,?,?)",
                             (phone, profile_name, "WhatsApp", db.now(), db.now()))
        lead = db.one("SELECT * FROM leads WHERE id=?", (lead_id,))
        db.log_event("lead_created", f"{phone} ({profile_name or 'unknown'})")
    db.execute("INSERT INTO messages (lead_id, direction, body, wa_id, created_at) VALUES (?,?,?,?,?)",
               (lead["id"], "in", text, wa_id, db.now()))

    info = analyzer.analyze(text, prof)
    merged = _merge(lead, info)
    if not merged.get("name") and profile_name:
        merged["name"] = profile_name                         # WhatsApp profile name as a fallback
    count = db.one("SELECT COUNT(*) AS n FROM messages WHERE lead_id=? AND direction='in'", (lead["id"],))["n"]
    score, status, reasons = scoring.score_lead(merged, count)
    was_hot = lead["status"] == "hot"
    merged.update(score=score, status=status)

    db.execute("""UPDATE leads SET name=?, email=?, language=?, intent=?, interest=?, area=?, budget_bhd=?, urgency=?,
                  timeline=?, summary=?, score=?, status=?, updated_at=? WHERE id=?""",
               (merged.get("name"), merged.get("email"), merged["language"], merged["intent"], merged.get("interest"),
                merged.get("area"), merged.get("budget_bhd"), merged.get("urgency"), merged.get("timeline"),
                merged.get("summary"), score, status, db.now(), lead["id"]))
    db.log_event("lead_scored", f"{phone}: {score} {status} [{info.get('_source')}] " + "; ".join(reasons[:4]))

    merged["id"] = lead["id"]
    try:                                                      # a CRM outage must never lose the customer's reply
        crm_id = crm.get_crm().upsert_lead(merged)
        db.execute("UPDATE leads SET crm_id=? WHERE id=?", (crm_id, lead["id"]))
        db.log_event("crm_synced", f"{phone} -> {crm_id}")
    except Exception as exc:
        db.log_event("crm_error", f"{phone}: {type(exc).__name__}: {exc}")

    _alerts(merged, was_hot or bool(lead["alerted"]))

    merged["_last_text"] = text
    reply, source = replies.compose(merged, prof)
    if reply:
        notify.send_whatsapp(phone, reply)
        db.execute("INSERT INTO messages (lead_id, direction, body, created_at) VALUES (?,?,?,?)",
                   (lead["id"], "out", reply, db.now()))
    return reply or None


def _alerts(lead: dict, already_alerted: bool) -> None:
    label = f"{lead.get('name') or lead['phone']} ({lead['phone']})"
    if lead["status"] == "hot" and not already_alerted:
        notify.send_whatsapp(
            config.SALES_REP_PHONE,
            f"HOT LEAD {lead['score']}/100\n{label}\nInterest: {lead.get('interest')} | Area: {lead.get('area')}\n"
            f"Budget: {lead.get('budget_bhd')} BHD | Urgency: {lead.get('urgency')} | When: {lead.get('timeline')}\n"
            f"{lead.get('summary')}\nSuggested: call within 15 minutes.")
        db.execute("UPDATE leads SET alerted=1 WHERE id=?", (lead["id"],))
        db.log_event("sales_alerted", label)
    if lead["status"] == "support":
        notify.send_whatsapp(config.MANAGER_PHONE, f"COMPLAINT/SUPPORT from {label}\n{lead.get('summary')}")
        db.log_event("manager_alerted", label)


def daily_summary() -> str:
    leads = db.rows("SELECT * FROM leads")
    today = db.now()[:10]
    new_today = [lead for lead in leads if (lead["created_at"] or "").startswith(today)]
    by = {s: sum(1 for lead in leads if lead["status"] == s) for s in ("hot", "warm", "cold", "support", "spam")}
    hot = [lead for lead in leads if lead["status"] == "hot"]
    lines = [f"Lead summary {today}", f"New today: {len(new_today)} | Total leads: {len(leads)}",
             f"Hot {by['hot']} | Warm {by['warm']} | Cold {by['cold']} | Support {by['support']} | Spam {by['spam']}"]
    if hot:
        lines.append("Hot leads to call: " + ", ".join(f"{h['name'] or h['phone']} ({h['score']})" for h in hot))
    return "\n".join(lines)
