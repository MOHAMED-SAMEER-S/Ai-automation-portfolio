"""Settings from environment / .env. Everything is optional: with no keys the whole
portfolio runs offline (mock AI, console WhatsApp/email, local CRM)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
_e = os.getenv

# ---- AI: mock | anthropic | openai  (openai = ANY OpenAI-compatible API: OpenAI, Gemini, Groq...)
LLM_PROVIDER = _e("LLM_PROVIDER", "mock").lower()
ANTHROPIC_API_KEY = _e("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = _e("ANTHROPIC_MODEL", "claude-sonnet-5-5")
OPENAI_API_KEY = _e("OPENAI_API_KEY", "")
OPENAI_BASE_URL = _e("OPENAI_BASE_URL", "") or None
OPENAI_MODEL = _e("OPENAI_MODEL", "gpt-4o-mini")
LLM_TIMEOUT = float(_e("LLM_TIMEOUT", "20"))           # seconds - never hang on a slow API

# ---- Business profile (swap the JSON to demo for any company)
PROFILE_PATH = Path(_e("PROFILE_PATH", BASE_DIR / "business_profile.json"))
PUBLIC_BASE_URL = _e("PUBLIC_BASE_URL", "http://localhost:8000")
SECRET_KEY = _e("SECRET_KEY", "change-me-in-env")      # signs unsubscribe links

# ---- WhatsApp: console | meta | twilio
WA_MODE = _e("WA_MODE", "console").lower()
META_TOKEN = _e("META_TOKEN", "")                       # WhatsApp Cloud API access token
META_PHONE_ID = _e("META_PHONE_ID", "")                 # phone number ID (not the phone number)
META_VERIFY_TOKEN = _e("META_VERIFY_TOKEN", "verify-me")
META_APP_SECRET = _e("META_APP_SECRET", "")             # if set, webhook signatures are enforced
META_API_VERSION = _e("META_API_VERSION", "")           # e.g. v23.0 ; empty = Meta's default
TWILIO_ACCOUNT_SID = _e("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = _e("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = _e("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
SALES_REP_PHONE = _e("SALES_REP_PHONE", "+97330000001")
MANAGER_PHONE = _e("MANAGER_PHONE", "+97330000002")

# ---- CRM: local | zoho
CRM_MODE = _e("CRM_MODE", "local").lower()
ZOHO_CLIENT_ID = _e("ZOHO_CLIENT_ID", "")
ZOHO_CLIENT_SECRET = _e("ZOHO_CLIENT_SECRET", "")
ZOHO_REFRESH_TOKEN = _e("ZOHO_REFRESH_TOKEN", "")
ZOHO_ACCOUNTS_URL = _e("ZOHO_ACCOUNTS_URL", "https://accounts.zoho.com")   # .sa / .eu / .in per your data centre
ZOHO_API_URL = _e("ZOHO_API_URL", "https://www.zohoapis.com")

# ---- Email: console | smtp
EMAIL_MODE = _e("EMAIL_MODE", "console").lower()
SMTP_HOST = _e("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(_e("SMTP_PORT", "587"))
SMTP_USER = _e("SMTP_USER", "")
SMTP_PASSWORD = _e("SMTP_PASSWORD", "")                 # Gmail: an "App password", not your login
EMAIL_FROM = _e("EMAIL_FROM", "") or SMTP_USER

# ---- Storage
DB_PATH = Path(_e("DB_PATH", BASE_DIR / "data" / "portfolio.db"))
