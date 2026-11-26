"""Streamlit control room for both projects.  Run:  streamlit run dashboard.py"""
import json
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from core import config, db
from lead_assistant import pipeline
from marketing_automation import campaign

st.set_page_config(page_title="AI Automation Portfolio", page_icon="🤖", layout="wide")
db.init()

st.markdown("""<style>
.block-container{padding-top:1.6rem}
.kpi{background:linear-gradient(135deg,#0f766e,#14b8a6);color:#fff;border-radius:14px;padding:16px 18px}
.kpi b{font-size:30px;display:block}.kpi span{opacity:.9;font-size:13px}
.hot{background:linear-gradient(135deg,#b91c1c,#f97316)}.mk{background:linear-gradient(135deg,#4338ca,#8b5cf6)}
</style>""", unsafe_allow_html=True)

st.title("🤖 AI Automation Portfolio")
st.caption(f"AI: **{config.LLM_PROVIDER}** · WhatsApp: **{config.WA_MODE}** · CRM: **{config.CRM_MODE}** · "
           f"Email: **{config.EMAIL_MODE}** — offline demo mode needs no keys")


def kpi(col, label, value, css=""):
    col.markdown(f'<div class="kpi {css}"><b>{value}</b><span>{label}</span></div>', unsafe_allow_html=True)


leads = pd.DataFrame(db.rows("SELECT * FROM leads ORDER BY score DESC, updated_at DESC"))
subs = pd.DataFrame(db.rows("SELECT * FROM subscribers ORDER BY id DESC"))
tabs = st.tabs(["📊 Overview", "💬 P1 · WhatsApp Leads", "📧 P2 · Marketing Drip", "📤 Outbox", "🗂 CRM view", "🧾 Activity log"])

# ---------------- Overview ----------------
with tabs[0]:
    c = st.columns(5)
    n_hot = int((leads["status"] == "hot").sum()) if len(leads) else 0
    kpi(c[0], "WhatsApp leads", len(leads))
    kpi(c[1], "Hot leads", n_hot, "hot")
    kpi(c[2], "Email subscribers", len(subs), "mk")
    f = campaign.funnel()
    kpi(c[3], "Emails sent", f["emails"].get("sent", 0), "mk")
    kpi(c[4], "Reply rate %", f["reply_rate_pct"], "mk")
    st.markdown("#### What this demo shows")
    st.markdown(
        "- **Project 1** — a customer WhatsApp message (English / Arabic / mixed) is understood by AI, scored, saved to "
        "the CRM, a hot lead alerts sales instantly, and the customer gets a reply in their own language.\n"
        "- **Project 2** — a website form lead gets a bilingual 4-email drip over 9 days; a reply, sale or "
        "unsubscribe stops it automatically.")
    if len(leads):
        st.bar_chart(leads["status"].value_counts())

# ---------------- Project 1 ----------------
with tabs[1]:
    left, right = st.columns([1, 1.4])
    with left:
        st.subheader("Try it: pretend to be a customer")
        samples = {
            "Hot English": "Hi my name is Ali Hassan, how much for AC maintenance in Riffa? Urgent, today, budget 80 BHD",
            "Arabic": "مرحبا اسمي خالد أحتاج تنظيف في المنامة كم السعر؟",
            "Complaint": "my AC is not working, worst service, I want a refund",
            "Spam": "WIN free crypto lottery click here",
        }
        pick = st.selectbox("Sample message", ["(write my own)"] + list(samples))
        phone = st.text_input("Customer phone", "+97333000111")
        text = st.text_area("Message", samples.get(pick, ""), height=100)
        if st.button("Send as customer", type="primary") and text.strip():
            reply = pipeline.handle_incoming(phone, text, None)
            st.session_state["p1_reply"] = reply or "(no reply sent — spam)"
            st.rerun()
        if "p1_reply" in st.session_state:
            st.success("🤖 Bot reply:\n\n" + st.session_state["p1_reply"])
    with right:
        st.subheader("Leads (best first)")
        if len(leads):
            show = leads[["name", "phone", "status", "score", "intent", "interest", "area", "budget_bhd",
                          "urgency", "language", "crm_id"]]
            st.dataframe(show, width="stretch", hide_index=True)
            st.text(pipeline.daily_summary())
        else:
            st.info("No leads yet — send a message on the left.")

# ---------------- Project 2 ----------------
with tabs[2]:
    left, right = st.columns([1, 1.4])
    with left:
        st.subheader("Try it: website form lead")
        email = st.text_input("Email", "sara@example.com")
        name = st.text_input("Name", "Sara")
        lang = st.selectbox("Email language", ["en", "ar", "both"], index=2)
        interest = st.selectbox("Interest", [None] + [s["key"] for s in __import__("core.profile", fromlist=["x"]).load()["services"]])
        if st.button("Submit lead form", type="primary"):
            try:
                r = campaign.subscribe(email, name, lang, interest)
                campaign.run_due()
                st.session_state["p2_msg"] = "Duplicate — already subscribed." if r["duplicate"] else "Subscribed ✔ welcome email sent."
            except ValueError as exc:
                st.session_state["p2_msg"] = f"Error: {exc}"
            st.rerun()
        if "p2_msg" in st.session_state:
            st.info(st.session_state["p2_msg"])
        st.markdown("##### ⏩ Fast-forward time")
        days = st.slider("Days to jump ahead", 0, 12, 3)
        if st.button("Run scheduler as if it's that day"):
            r = campaign.run_due(datetime.now() + timedelta(days=days))
            st.session_state["p2_msg"] = f"Scheduler: {r['sent']} sent, {r['skipped']} skipped."
            st.rerun()
        if len(subs):
            st.markdown("##### Mark an event")
            who = st.selectbox("Subscriber", subs["email"].tolist())
            kind = st.selectbox("Event", ["replied", "converted", "unsubscribed"])
            if st.button("Apply event"):
                campaign.mark(int(subs[subs["email"] == who].iloc[0]["id"]), kind)
                st.rerun()
    with right:
        st.subheader("Funnel")
        st.json(campaign.funnel())
        if len(subs):
            st.dataframe(subs[["email", "name", "language", "interest", "status", "crm_id"]],
                         width="stretch", hide_index=True)
            drip = pd.DataFrame(db.rows("SELECT d.subscriber_id, s.email, d.step_name, d.due_at, d.status, "
                                        "d.ai_source FROM drip d JOIN subscribers s ON s.id=d.subscriber_id "
                                        "ORDER BY d.subscriber_id, d.step"))
            st.markdown("##### Drip schedule")
            st.dataframe(drip, width="stretch", hide_index=True)

# ---------------- Outbox ----------------
with tabs[3]:
    st.subheader("Everything the system sent")
    out = db.rows("SELECT * FROM outbox ORDER BY id DESC LIMIT 100")
    if not out:
        st.info("Nothing sent yet.")
    for m in out:
        icon = "💬" if m["channel"] == "whatsapp" else "📧"
        with st.expander(f"{icon} {m['created_at']} → {m['to_addr']}  ·  {m['subject'] or m['body'][:50]}  [{m['delivery']}]"):
            st.text(m["body"])

# ---------------- CRM ----------------
with tabs[4]:
    st.subheader(f"CRM records ({config.CRM_MODE} mode)")
    recs = db.rows("SELECT * FROM crm_records ORDER BY updated_at DESC")
    if recs:
        st.dataframe(pd.DataFrame([{"crm_id": r["crm_id"], "kind": r["kind"], **json.loads(r["payload"])} for r in recs]),
                     width="stretch", hide_index=True)
    else:
        st.info("No local CRM records (in Zoho mode, records live in Zoho CRM).")

# ---------------- Log ----------------
with tabs[5]:
    st.dataframe(pd.DataFrame(db.rows("SELECT ts, kind, detail FROM events ORDER BY id DESC LIMIT 200")),
                 width="stretch", hide_index=True)
