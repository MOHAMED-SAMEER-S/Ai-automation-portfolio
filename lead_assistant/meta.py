"""WhatsApp Cloud API (Meta) webhook helpers: payload parsing and signature check."""
import hashlib
import hmac


def parse_messages(payload: dict) -> list[dict]:
    """Extract incoming customer messages from a Meta webhook payload (status updates are ignored)."""
    out = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            names = {c.get("wa_id"): c.get("profile", {}).get("name") for c in value.get("contacts", [])}
            for m in value.get("messages", []):
                kind = m.get("type", "text")
                text = m.get("text", {}).get("body") if kind == "text" else \
                    m.get("button", {}).get("text") if kind == "button" else f"[{kind} message]"
                out.append({"phone": "+" + m.get("from", ""), "text": text or "", "wa_id": m.get("id"),
                            "name": names.get(m.get("from"))})
    return out


def valid_signature(raw_body: bytes, header: str | None, app_secret: str) -> bool:
    """Meta signs the raw body: X-Hub-Signature-256 = 'sha256=' + HMAC_SHA256(app_secret, body)."""
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header[7:])
