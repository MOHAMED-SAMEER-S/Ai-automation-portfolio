"""Outbound WhatsApp + email. Every message is also saved in the `outbox` table, so the
dashboard shows exactly what was sent - even in offline "console" mode."""
import smtplib
from email.message import EmailMessage

import httpx

from . import config, db


def _digits(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit())


def send_whatsapp(to: str, body: str) -> str:
    """Returns delivery status: console | sent | failed: <reason>."""
    delivery = "console"
    try:
        if config.WA_MODE == "meta" and config.META_TOKEN and config.META_PHONE_ID:
            ver = f"/{config.META_API_VERSION}" if config.META_API_VERSION else ""
            r = httpx.post(
                f"https://graph.facebook.com{ver}/{config.META_PHONE_ID}/messages",
                headers={"Authorization": f"Bearer {config.META_TOKEN}"},
                json={"messaging_product": "whatsapp", "to": _digits(to), "type": "text",
                      "text": {"body": body[:4000]}},
                timeout=15)
            r.raise_for_status()
            delivery = "sent"
        elif config.WA_MODE == "twilio" and config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN:
            r = httpx.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{config.TWILIO_ACCOUNT_SID}/Messages.json",
                auth=(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN),
                data={"From": config.TWILIO_WHATSAPP_FROM, "To": f"whatsapp:+{_digits(to)}", "Body": body[:1500]},
                timeout=15)
            r.raise_for_status()
            delivery = "sent"
    except Exception as exc:
        delivery = f"failed: {type(exc).__name__}"
        db.log_event("whatsapp_error", f"to {to}: {exc}")
    db.execute("INSERT INTO outbox (channel, to_addr, subject, body, delivery, created_at) VALUES (?,?,?,?,?,?)",
               ("whatsapp", to, None, body, delivery, db.now()))
    print(f"[whatsapp:{delivery}] -> {to}: " + body.replace("\n", " | ")[:140])
    return delivery


def send_email(to: str, subject: str, text: str, html: str | None = None) -> str:
    delivery = "console"
    try:
        if config.EMAIL_MODE == "smtp" and config.SMTP_USER and config.SMTP_PASSWORD:
            msg = EmailMessage()
            msg["From"], msg["To"], msg["Subject"] = config.EMAIL_FROM, to, subject
            msg.set_content(text)
            if html:
                msg.add_alternative(html, subtype="html")
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as s:
                s.starttls()
                s.login(config.SMTP_USER, config.SMTP_PASSWORD)
                s.send_message(msg)
            delivery = "sent"
    except Exception as exc:
        delivery = f"failed: {type(exc).__name__}"
        db.log_event("email_error", f"to {to}: {exc}")
    db.execute("INSERT INTO outbox (channel, to_addr, subject, body, delivery, created_at) VALUES (?,?,?,?,?,?)",
               ("email", to, subject, text, delivery, db.now()))
    print(f"[email:{delivery}] -> {to}: {subject}")
    return delivery
