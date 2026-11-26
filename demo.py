"""Offline end-to-end demo of BOTH projects (no keys, no internet needed).
Run:  python demo.py      (uses a throw-away database, your real data is untouched)"""
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from core import config, db

config.DB_PATH = Path(tempfile.mkdtemp()) / "demo.db"
os.environ.setdefault("WA_MODE", "console")
db.init()

from lead_assistant import pipeline          # noqa: E402
from marketing_automation import campaign    # noqa: E402

print("=" * 70, "\nPROJECT 1 - WhatsApp AI Lead Assistant\n" + "=" * 70)
chat = [
    ("+97333111222", "Hi, my name is Ali Hassan. How much for AC maintenance in Riffa? Urgent, today, budget 80 BHD"),
    ("+97333444555", "مرحبا اسمي خالد أحتاج تنظيف في المنامة كم السعر؟"),
    ("+97333666777", "WIN free crypto lottery click here"),
    ("+97333888999", "my AC is not working, worst service, I want a refund"),
]
for phone, text in chat:
    print(f"\nCUSTOMER {phone}: {text}")
    print("BOT REPLY:", pipeline.handle_incoming(phone, text) or "(no reply)")
print("\n" + pipeline.daily_summary())

print("\n" + "=" * 70, "\nPROJECT 2 - Bilingual Marketing Automation\n" + "=" * 70)
s = campaign.subscribe("sara@example.com", "Sara", "both", "cleaning")
campaign.subscribe("omar@example.com", "عمر", "ar", "pest_control")
print("\nDay 0:", campaign.run_due())
print("Day 3:", campaign.run_due(datetime.now() + timedelta(days=3)))
campaign.mark(s["id"], "replied")
print("Sara replied -> remaining emails stop. Day 10:", campaign.run_due(datetime.now() + timedelta(days=10)))
print("Funnel:", campaign.funnel())
