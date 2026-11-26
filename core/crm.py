"""CRM adapters. LocalCRM stores records in SQLite (works offline, shown in the dashboard);
ZohoCRM talks to Zoho CRM's REST API v2. Both expose the same two methods, so swapping CRMs
(HubSpot, Odoo...) means writing one more small class."""
import json
import time

import httpx

from . import config, db


class LocalCRM:
    name = "local"

    def upsert_lead(self, lead: dict) -> str:
        crm_id = f"LOCAL-{lead['id']}"
        db.execute(
            "INSERT INTO crm_records (crm_id, kind, payload, updated_at) VALUES (?,?,?,?) "
            "ON CONFLICT(crm_id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at",
            (crm_id, "lead", json.dumps(_lead_payload(lead), ensure_ascii=False), db.now()))
        return crm_id

    def upsert_contact(self, sub: dict) -> str:
        crm_id = f"LOCAL-SUB-{sub['id']}"
        db.execute(
            "INSERT INTO crm_records (crm_id, kind, payload, updated_at) VALUES (?,?,?,?) "
            "ON CONFLICT(crm_id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at",
            (crm_id, "subscriber", json.dumps({k: sub.get(k) for k in
                                               ("name", "email", "language", "interest", "source", "status")},
                                              ensure_ascii=False), db.now()))
        return crm_id


def _lead_payload(lead: dict) -> dict:
    keys = ("name", "phone", "email", "language", "interest", "area", "budget_bhd", "urgency",
            "timeline", "score", "status", "summary", "source")
    return {k: lead.get(k) for k in keys}


class ZohoCRM:
    """Zoho CRM v2 REST API. Needs a Self Client refresh token (see docs/ZOHO_SETUP.md)."""
    name = "zoho"

    def __init__(self, http: httpx.Client | None = None):
        self.http = http or httpx.Client(timeout=20)
        self._token, self._expires = "", 0.0

    def _access_token(self) -> str:
        if self._token and time.time() < self._expires - 60:
            return self._token
        r = self.http.post(f"{config.ZOHO_ACCOUNTS_URL}/oauth/v2/token", params={
            "refresh_token": config.ZOHO_REFRESH_TOKEN, "client_id": config.ZOHO_CLIENT_ID,
            "client_secret": config.ZOHO_CLIENT_SECRET, "grant_type": "refresh_token"})
        r.raise_for_status()
        data = r.json()
        if "access_token" not in data:
            raise RuntimeError(f"Zoho token error: {data}")
        self._token = data["access_token"]
        self._expires = time.time() + float(data.get("expires_in", 3600))
        return self._token

    def _upsert(self, module: str, record: dict, dedupe: list[str]) -> str:
        r = self.http.post(
            f"{config.ZOHO_API_URL}/crm/v2/{module}/upsert",
            headers={"Authorization": f"Zoho-oauthtoken {self._access_token()}"},
            json={"data": [record], "duplicate_check_fields": dedupe})
        r.raise_for_status()
        result = r.json()["data"][0]
        if result.get("status") != "success":
            raise RuntimeError(f"Zoho rejected record: {result}")
        return result["details"]["id"]

    def upsert_lead(self, lead: dict) -> str:
        # Last_Name is the only required Leads field in Zoho.
        desc = (f"[AI lead assistant] score {lead.get('score')} ({lead.get('status')}) | "
                f"interest: {lead.get('interest')} | area: {lead.get('area')} | "
                f"budget BHD: {lead.get('budget_bhd')} | urgency: {lead.get('urgency')} | "
                f"timeline: {lead.get('timeline')}\n{lead.get('summary') or ''}")
        record = {"Last_Name": lead.get("name") or f"WhatsApp {lead['phone']}", "Phone": lead["phone"],
                  "Description": desc}
        if lead.get("email"):
            record["Email"] = lead["email"]
        return self._upsert("Leads", record, ["Phone"])

    def upsert_contact(self, sub: dict) -> str:
        record = {"Last_Name": sub.get("name") or sub["email"], "Email": sub["email"],
                  "Description": f"[AI marketing] interest: {sub.get('interest')} | lang: {sub.get('language')} "
                                 f"| source: {sub.get('source')} | status: {sub.get('status')}"}
        return self._upsert("Leads", record, ["Email"])


_zoho: ZohoCRM | None = None


def get_crm():
    global _zoho
    if config.CRM_MODE == "zoho" and config.ZOHO_REFRESH_TOKEN:
        _zoho = _zoho or ZohoCRM()
        return _zoho
    return LocalCRM()
