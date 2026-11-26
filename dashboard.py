"""Streamlit control room for both projects.  Run:  streamlit run dashboard.py
Redesigned UI: Gulf-inspired palette, bilingual typography (Readex Pro), WhatsApp-style chat,
visual funnel + drip timeline, and a one-click demo reset. All business logic is unchanged."""
import html
import json
import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from core import config, db
from lead_assistant import pipeline
from marketing_automation import campaign

try:
    from core import profile as biz_profile
    PROFILE = biz_profile.load()
except Exception:  # never let a profile problem break the demo
    biz_profile, PROFILE = None, {}

BUSINESS = PROFILE.get("name") or PROFILE.get("business_name") or PROFILE.get("company") or "Al Manara Facility Services"
SERVICES = [s["key"] for s in PROFILE.get("services", []) if isinstance(s, dict) and "key" in s]

st.set_page_config(page_title="AI Automation Portfolio", page_icon="🤖", layout="wide")
db.init()

# ----------------------------------------------------------------------------------------------
# Design tokens
#   ink #0E2A35 · sea #0F5E6E · pearl #F2F5F4 · Bahrain red #C8102E · sand #B8893A · WhatsApp #1FA855
# ----------------------------------------------------------------------------------------------
STATUS_COLORS = {"hot": "#C8102E", "warm": "#B8893A", "cold": "#5F8794", "support": "#0F5E6E", "spam": "#9AA5A8"}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Readex+Pro:wght@300;400;500;600;700&display=swap');
:root{
  --ink:#0E2A35; --ink-2:#3D5A64; --muted:#6E868D; --line:#D5E0E1;
  --pearl:#F2F5F4; --surface:#FFFFFF; --sea:#0F5E6E; --sea-soft:#E1EEEF;
  --red:#C8102E; --red-soft:#FBE7EA; --sand:#B8893A; --wa:#1FA855; --wa-bubble:#D9FDD3;
}
html, body, h1, h2, h3, h4, h5, p, li, label, input, textarea, button, .stMarkdown,
[data-baseweb="tab"], [data-testid="stMetricValue"]{font-family:'Readex Pro', 'Segoe UI', Tahoma, sans-serif !important;}
.block-container{padding-top:1.4rem; max-width:1320px}
h1,h2,h3,h4{color:var(--ink); letter-spacing:-0.01em}
textarea, .bubble, .bidi{unicode-bidi:plaintext; text-align:start}

/* ---------- hero ---------- */
.hero{background:var(--ink); color:#fff; border-radius:22px; padding:30px 34px 26px; position:relative; overflow:hidden}
.hero:after{content:""; position:absolute; right:-80px; top:-120px; width:360px; height:360px; border-radius:50%;
  border:1px solid rgba(255,255,255,.08); box-shadow:0 0 0 46px rgba(255,255,255,.025), 0 0 0 92px rgba(255,255,255,.02)}
.hero h1{color:#fff; font-size:2.35rem; font-weight:600; margin:0 0 6px; line-height:1.15}
.hero p.lede{color:#B9CDD2; font-size:1.02rem; max-width:62ch; margin:0 0 18px; font-weight:300}
.modes{display:flex; flex-wrap:wrap; gap:8px; margin-bottom:24px}
.mode{display:inline-flex; align-items:center; gap:7px; padding:5px 12px; border-radius:999px; font-size:.82rem;
  background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.12); color:#DCE8EA}
.mode i{width:7px; height:7px; border-radius:50%; background:#E0B357; display:inline-block}
.mode.live i{background:#3DDC84}
.mode b{font-weight:500; color:#fff}

/* pipeline strip: the one orchestrated motion on the page */
.pipe{position:relative; display:grid; grid-template-columns:repeat(5,1fr); gap:10px; z-index:1}
.pipe .rail{position:absolute; left:16px; right:16px; top:15px; height:2px; background:rgba(255,255,255,.14)}
.pipe .pulse{position:absolute; top:10px; left:16px; width:12px; height:12px; border-radius:50%; background:var(--wa);
  box-shadow:0 0 0 6px rgba(31,168,85,.18); opacity:0}
.stage{position:relative}
.stage .dot{width:32px; height:32px; border-radius:50%; background:#16404D; border:1px solid rgba(255,255,255,.18);
  display:flex; align-items:center; justify-content:center; font-size:.85rem; font-weight:500; color:#BFD3D8; position:relative; z-index:2}
.stage b{display:block; font-weight:500; font-size:.92rem; margin-top:10px; color:#fff}
.stage span{display:block; font-size:.8rem; color:#9DB7BD; font-weight:300; margin-top:2px}
@media (prefers-reduced-motion: no-preference){
  .pipe .pulse{animation:travel 2.6s cubic-bezier(.45,.05,.3,1) .5s 1 forwards}
  .stage .dot{animation:light .45s ease-out forwards}
  .stage:nth-child(3) .dot{animation-delay:.7s} .stage:nth-child(4) .dot{animation-delay:1.25s}
  .stage:nth-child(5) .dot{animation-delay:1.8s} .stage:nth-child(6) .dot{animation-delay:2.35s}
  .stage:nth-child(7) .dot{animation-delay:2.9s}
  .bubble.new{animation:pop .35s ease-out}
}
@media (prefers-reduced-motion: reduce){ .stage .dot{background:var(--wa); color:#fff; border-color:var(--wa)} }
@keyframes travel{0%{opacity:1; left:16px} 92%{opacity:1} 100%{opacity:0; left:calc(100% - 28px)}}
@keyframes light{to{background:var(--wa); color:#fff; border-color:var(--wa)}}
@keyframes pop{from{opacity:0; transform:translateY(6px) scale(.98)} to{opacity:1; transform:none}}

/* ---------- stat band ---------- */
.band{display:grid; grid-template-columns:repeat(5,1fr); background:var(--surface); border:1px solid var(--line);
  border-radius:18px; margin:18px 0 6px}
.band div{padding:16px 22px; border-left:1px solid var(--line)}
.band div:first-child{border-left:none}
.band b{display:block; font-size:2rem; font-weight:600; color:var(--ink); line-height:1.1; font-variant-numeric:tabular-nums}
.band b.hot{color:var(--red)}
.band span{font-size:.85rem; color:var(--muted)}

/* ---------- generic panel + text ---------- */
.panel{background:var(--surface); border:1px solid var(--line); border-radius:16px; padding:18px 20px}
.panel h4{margin:0 0 6px; font-size:1.05rem; font-weight:500}
.panel p{margin:0; color:var(--ink-2); font-size:.93rem; line-height:1.6}
[data-testid="stMarkdownContainer"] p.hint, p.hint{color:var(--muted); font-size:.86rem; margin:-4px 0 10px; line-height:1.5}
[data-testid="stMarkdownContainer"] .panel p{font-size:.93rem}

/* ---------- WhatsApp phone ---------- */
.phone{border:1px solid var(--line); border-radius:20px; overflow:hidden; background:#EFEAE2}
.phone-head{display:flex; align-items:center; gap:10px; background:var(--ink); color:#fff; padding:11px 14px}
.avatar{width:34px; height:34px; border-radius:50%; background:var(--wa); display:flex; align-items:center;
  justify-content:center; font-weight:600; font-size:.85rem}
.phone-head b{display:block; font-weight:500; font-size:.92rem}
.phone-head span{font-size:.75rem; color:#A9C3C9}
.chat{padding:14px 12px; min-height:220px; display:flex; flex-direction:column; gap:8px}
.bubble{max-width:82%; padding:8px 11px 6px; border-radius:10px; font-size:.9rem; line-height:1.5; color:#111B21;
  box-shadow:0 1px 0 rgba(11,20,26,.08); white-space:pre-wrap; word-wrap:break-word}
.bubble small{display:block; font-size:.7rem; color:#667781; margin-top:3px; text-align:end}
.bubble.in{align-self:flex-end; background:var(--wa-bubble); border-top-right-radius:2px}
.bubble.out{align-self:flex-start; background:#fff; border-top-left-radius:2px}
.bubble.sys{align-self:center; background:#FFF6D6; color:#54656F; font-size:.8rem; max-width:90%}
.chat .empty{margin:auto; color:#54656F; font-size:.85rem; background:rgba(255,255,255,.75); padding:6px 12px; border-radius:8px}

/* ---------- call list ---------- */
.call{display:flex; align-items:center; justify-content:space-between; padding:9px 0; border-top:1px solid var(--line)}
.call:first-of-type{border-top:none}
.call b{font-weight:500; color:var(--ink)} .call span{color:var(--muted); font-size:.85rem}
.score{font-variant-numeric:tabular-nums; font-weight:600; color:var(--red)}
.counts{display:flex; flex-wrap:wrap; gap:6px; margin-top:12px}
.chip{font-size:.8rem; padding:3px 10px; border-radius:999px; border:1px solid var(--line); color:var(--ink-2)}
.chip i{display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:6px}

/* ---------- funnel ---------- */
.frow{display:grid; grid-template-columns:120px 1fr 64px; align-items:center; gap:12px; margin:9px 0}
.frow label{font-size:.88rem; color:var(--ink-2)}
.ftrack{height:12px; background:var(--sea-soft); border-radius:999px; overflow:hidden}
.fbar{height:100%; border-radius:999px; background:var(--sea); transition:width .6s ease}
.fval{text-align:right; font-variant-numeric:tabular-nums; font-weight:500; color:var(--ink)}
.rates{display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-top:14px}
.rates div{background:var(--pearl); border-radius:12px; padding:10px 12px}
.rates b{display:block; font-size:1.35rem; font-weight:600; color:var(--ink)} .rates span{font-size:.8rem; color:var(--muted)}

/* ---------- drip timeline ---------- */
.trow{padding:14px 0 10px; border-top:1px solid var(--line)}
.trow:first-child{border-top:none}
.who{display:flex; align-items:baseline; gap:10px; margin-bottom:12px}
.who b{font-weight:500; color:var(--ink); font-size:.95rem}
.who span{font-size:.8rem; color:var(--muted)}
.steps{display:grid; grid-template-columns:repeat(4,1fr); position:relative}
.steps:before{content:""; position:absolute; left:12.5%; right:12.5%; top:9px; height:2px; background:var(--line)}
.step{text-align:center; position:relative}
.step i{display:block; width:18px; height:18px; border-radius:50%; margin:0 auto 6px; background:#fff; border:2px solid var(--sea)}
.step.sent i{background:var(--sea)}
.step.skipped i{border-color:#B7C3C5; background:repeating-linear-gradient(45deg,#E4EBEC,#E4EBEC 3px,#fff 3px,#fff 6px)}
.step.failed i{border-color:var(--red); background:var(--red-soft)}
.step b{display:block; font-size:.8rem; font-weight:500; color:var(--ink)}
.step span{font-size:.72rem; color:var(--muted)}
.step.skipped b{color:#9AA5A8; text-decoration:line-through}
.legend{display:flex; gap:16px; font-size:.78rem; color:var(--muted); margin-top:8px}
.legend i{display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:5px; vertical-align:-1px; border:2px solid var(--sea)}

/* ---------- outbox ---------- */
.msgbody{background:var(--pearl); border-radius:12px; padding:12px 14px; white-space:pre-wrap; font-size:.9rem;
  line-height:1.6; color:var(--ink)}

@media (max-width:900px){
  .band{grid-template-columns:repeat(2,1fr)} .band div{border-left:none; border-top:1px solid var(--line)}
  .pipe{grid-template-columns:1fr 1fr} .pipe .rail, .pipe .pulse{display:none}
}
</style>""", unsafe_allow_html=True)


def blank(x) -> bool:
    try:
        return x is None or bool(pd.isna(x)) or str(x) in ("", "None")
    except (TypeError, ValueError):
        return False


def esc(x) -> str:
    return html.escape("" if blank(x) else str(x))


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Show missing values as a dash instead of the word 'None'."""
    df = df.copy()
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            s = df[col].astype(object)
            df[col] = s.where(s.notna() & ~s.astype(str).isin(["None", "nan", ""]), "—")
    return df


def mode_chip(label: str, value: str, demo_values: set) -> str:
    live = "" if value in demo_values else " live"
    state = "demo" if value in demo_values else "live"
    return f'<span class="mode{live}"><i></i>{label}: <b>{esc(value)}</b> ({state})</span>'


def reset_demo_data():
    """Delete every row from the demo database (tables stay, so the app keeps working)."""
    con = sqlite3.connect(config.DB_PATH)
    try:
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        for t in tables:
            con.execute(f'DELETE FROM "{t}"')
        con.commit()
    finally:
        con.close()
    for k in ("p1_reply", "p2_msg", "p1_chat"):
        st.session_state.pop(k, None)


leads = pd.DataFrame(db.rows("SELECT * FROM leads ORDER BY score DESC, updated_at DESC"))
subs = pd.DataFrame(db.rows("SELECT * FROM subscribers ORDER BY id DESC"))
f = campaign.funnel()

# ---------------- Sidebar: demo controls ----------------
with st.sidebar:
    st.markdown("### Demo controls")
    st.caption("Start every client or interview demo from a clean slate.")
    sure = st.checkbox("Yes, delete all demo data")
    if st.button("Reset demo data", disabled=not sure, width="stretch"):
        reset_demo_data()
        st.toast("Demo data cleared — dashboard is back to zero.")
        st.rerun()
    st.divider()
    st.markdown("### Go live")
    st.caption("Switch each service in `.env` — no code changes:\n\n"
               "- `LLM_PROVIDER` = anthropic / openai\n- `WA_MODE` = meta / twilio\n"
               "- `CRM_MODE` = zoho\n- `EMAIL_MODE` = smtp")

# ---------------- Hero ----------------
modes = "".join([
    mode_chip("AI", config.LLM_PROVIDER, {"mock"}),
    mode_chip("WhatsApp", config.WA_MODE, {"console"}),
    mode_chip("CRM", config.CRM_MODE, {"local"}),
    mode_chip("Email", config.EMAIL_MODE, {"console"}),
])
stages = [
    ("1", "Customer messages", "WhatsApp, English or Arabic"),
    ("2", "AI reads it", "Name, service, area, budget"),
    ("3", "Lead is scored", "Hot, warm, cold, support, spam"),
    ("4", "Saved to CRM", "One record per customer"),
    ("5", "Sales alerted", "Customer answered in seconds"),
]
stage_html = "".join(f'<div class="stage"><div class="dot">{n}</div><b>{t}</b><span>{s}</span></div>'
                     for n, t, s in stages)
st.markdown(f"""
<div class="hero">
  <h1>AI Automation Portfolio</h1>
  <p class="lede">Two working automations for {esc(BUSINESS)}: a WhatsApp lead assistant that answers
  every customer in their language, and a bilingual email follow-up that stops the moment someone replies or buys.</p>
  <div class="modes">{modes}</div>
  <div class="pipe"><div class="rail"></div><div class="pulse"></div>{stage_html}</div>
</div>""", unsafe_allow_html=True)

n_hot = int((leads["status"] == "hot").sum()) if len(leads) else 0
st.markdown(f"""
<div class="band">
  <div><b>{len(leads)}</b><span>WhatsApp leads</span></div>
  <div><b class="hot">{n_hot}</b><span>Hot leads to call</span></div>
  <div><b>{len(subs)}</b><span>Email subscribers</span></div>
  <div><b>{f["emails"].get("sent", 0)}</b><span>Emails sent</span></div>
  <div><b>{f["reply_rate_pct"]}%</b><span>Reply rate</span></div>
</div>""", unsafe_allow_html=True)

tabs = st.tabs(["Overview", "WhatsApp leads", "Email drip", "Outbox", "CRM", "Activity log"])

# ---------------- Overview ----------------
with tabs[0]:
    a, b, c = st.columns([1, 1, 1.15], gap="medium")
    a.markdown("""<div class="panel"><h4>Project 1 · WhatsApp lead assistant</h4>
      <p>A customer writes in English, Arabic or both. AI pulls out what they need, scores the lead from 0 to 100,
      saves it to the CRM, alerts sales for hot leads, and replies in the customer's own language.</p></div>""",
               unsafe_allow_html=True)
    b.markdown("""<div class="panel"><h4>Project 2 · Bilingual email drip</h4>
      <p>A website lead gets four emails over nine days: welcome, tip, offer, last call. A reply, a purchase
      or an unsubscribe stops the sequence immediately, so nobody gets a sales email after they've bought.</p></div>""",
               unsafe_allow_html=True)
    with c:
        if len(leads):
            counts = leads["status"].value_counts()
            top = max(int(counts.max()), 1)
            order = [s for s in STATUS_COLORS if s in counts] + [s for s in counts.index if s not in STATUS_COLORS]
            bars = "".join(
                f'<div class="frow"><label>{esc(s)}</label><div class="ftrack"><div class="fbar" style="width:'
                f'{100 * counts[s] / top:.0f}%; background:{STATUS_COLORS.get(s, "#9AA5A8")}"></div></div>'
                f'<div class="fval">{int(counts[s])}</div></div>' for s in order)
            st.markdown(f'<div class="panel"><h4>Leads by status</h4>{bars}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="panel"><h4>No leads yet</h4><p>Open the WhatsApp leads tab and send a message '
                        'as a customer to watch the numbers move.</p></div>', unsafe_allow_html=True)

# ---------------- Project 1 ----------------
with tabs[1]:
    left, right = st.columns([1, 1.35], gap="large")
    with left:
        st.markdown("#### Message the business as a customer")
        st.markdown('<p class="hint">Pick a sample or write your own. Use a new phone number for each new customer.</p>',
                    unsafe_allow_html=True)
        samples = {
            "Hot English": "Hi my name is Ali Hassan, how much for AC maintenance in Riffa? Urgent, today, budget 80 BHD",
            "Arabic": "مرحبا اسمي خالد أحتاج تنظيف في المنامة كم السعر؟",
            "Complaint": "my AC is not working, worst service, I want a refund",
            "Spam": "WIN free crypto lottery click here",
        }
        pick = st.selectbox("Sample message", ["(write my own)"] + list(samples))
        phone = st.text_input("Customer phone", "+97333000111")
        text = st.text_area("Message", samples.get(pick, ""), height=100)
        if st.button("Send as customer", type="primary"):
            if not text.strip():
                st.warning("Type a message first, then press Send as customer.")
            else:
                reply = pipeline.handle_incoming(phone, text, None)
                chat = st.session_state.setdefault("p1_chat", [])
                chat.append(("in", text.strip(), phone))
                chat.append(("out", reply, phone) if reply else ("sys", "No reply sent — marked as spam.", phone))
                st.session_state["p1_chat"] = chat[-8:]
                st.session_state["p1_reply"] = reply or "(no reply sent — spam)"
                st.rerun()

        chat = st.session_state.get("p1_chat", [])
        now = datetime.now().strftime("%H:%M")
        bubbles = ""
        for i, (kind, body, who) in enumerate(chat):
            new = " new" if i >= len(chat) - 2 else ""
            meta = f"{esc(who)} · {now}" if kind == "in" else ("bot · " + now if kind == "out" else "")
            bubbles += f'<div class="bubble {kind}{new}" dir="auto">{esc(body)}<small>{meta}</small></div>'
        if not bubbles:
            bubbles = '<div class="empty">Send a message to start the chat</div>'
        initials = "".join(w[0] for w in BUSINESS.split()[:2]).upper()
        st.markdown(f"""<div class="phone"><div class="phone-head"><div class="avatar">{esc(initials)}</div>
            <div><b>{esc(BUSINESS)}</b><span>WhatsApp Business · {esc(config.WA_MODE)} mode</span></div></div>
            <div class="chat">{bubbles}</div></div>""", unsafe_allow_html=True)

    with right:
        st.markdown("#### Leads, best first")
        if len(leads):
            cols = [c for c in ["name", "phone", "status", "score", "intent", "interest", "area", "budget_bhd",
                                "urgency", "language", "crm_id"] if c in leads.columns]
            show = clean(leads[cols])

            def tint(v):
                col = STATUS_COLORS.get(str(v))
                return f"color:{col}; font-weight:600" if col else ""

            st.dataframe(show.style.map(tint, subset=["status"]) if "status" in show else show,
                         width="stretch", hide_index=True,
                         column_config={
                             "score": st.column_config.ProgressColumn("score", min_value=0, max_value=100, format="%d"),
                             "budget_bhd": st.column_config.TextColumn("budget (BHD)"),
                         })
            hot = leads[leads["status"] == "hot"].sort_values("score", ascending=False)
            calls = "".join(
                f'<div class="call"><div><b class="bidi" dir="auto">{esc("Name not given" if blank(r.get("name")) else r.get("name"))}</b><br>'
                f'<span>{esc(r.get("phone"))} · {esc("—" if blank(r.get("interest")) else r.get("interest"))}</span></div>'
                f'<div class="score">{int(0 if blank(r.get("score")) else r.get("score"))}</div></div>'
                for _, r in hot.head(5).iterrows()) or '<p>No hot leads yet.</p>'
            chips = "".join(
                f'<span class="chip"><i style="background:{STATUS_COLORS.get(s, "#9AA5A8")}"></i>{esc(s)} {n}</span>'
                for s, n in leads["status"].value_counts().items())
            st.markdown(f'<div class="panel"><h4>Call these first</h4>{calls}<div class="counts">{chips}</div></div>',
                        unsafe_allow_html=True)
        else:
            st.markdown('<div class="panel"><h4>No leads yet</h4><p>Send a message on the left. The lead appears '
                        'here with its score, and hot leads move to the top.</p></div>', unsafe_allow_html=True)

# ---------------- Project 2 ----------------
with tabs[2]:
    left, right = st.columns([1, 1.35], gap="large")
    with left:
        st.markdown("#### Fill the website form as a lead")
        email = st.text_input("Email", "sara@example.com")
        name = st.text_input("Name", "Sara")
        lang = st.selectbox("Email language", ["en", "ar", "both"], index=2,
                            format_func={"en": "English", "ar": "Arabic", "both": "English + Arabic"}.get)
        interest = st.selectbox("Interest", [None] + SERVICES, format_func=lambda v: "Not specified" if v is None else v)
        if st.button("Submit lead form", type="primary"):
            try:
                r = campaign.subscribe(email, name, lang, interest)
                campaign.run_due()
                st.session_state["p2_msg"] = ("warn", "Already subscribed — no duplicate emails sent.") if r["duplicate"] \
                    else ("ok", "Subscribed. Welcome email sent and 3 follow-ups scheduled.")
            except ValueError as exc:
                st.session_state["p2_msg"] = ("err", f"{exc}. Check the email address and try again.")
            st.rerun()
        msg = st.session_state.get("p2_msg")
        if msg:
            kind, body = msg if isinstance(msg, tuple) else ("ok", msg)
            {"ok": st.success, "warn": st.warning, "err": st.error}.get(kind, st.info)(body)

        st.markdown("#### Fast-forward time")
        st.markdown('<p class="hint">The real scheduler runs daily. Jump ahead to see which emails go out.</p>',
                    unsafe_allow_html=True)
        days = st.slider("Days to jump ahead", 0, 12, 3)
        if st.button(f"Run scheduler for day {days}"):
            r = campaign.run_due(datetime.now() + timedelta(days=days))
            st.session_state["p2_msg"] = ("ok", f"Day {days}: {r['sent']} sent, {r['skipped']} skipped.")
            st.rerun()
        if len(subs):
            st.markdown("#### Record what the lead did")
            who = st.selectbox("Subscriber", subs["email"].tolist())
            kind = st.selectbox("Event", ["replied", "converted", "unsubscribed"],
                                format_func={"replied": "Replied to an email", "converted": "Bought the service",
                                             "unsubscribed": "Unsubscribed"}.get)
            if st.button("Save event"):
                campaign.mark(int(subs[subs["email"] == who].iloc[0]["id"]), kind)
                st.session_state["p2_msg"] = ("ok", f"Saved. Remaining emails to {who} are stopped.")
                st.rerun()

    with right:
        by = f.get("by_status", {})
        total = max(int(f.get("subscribers", 0)), 1)
        rows = [("Subscribers", f.get("subscribers", 0)), ("Replied", by.get("replied", 0)),
                ("Bought", by.get("converted", 0)), ("Unsubscribed", by.get("unsubscribed", 0))]
        bars = "".join(f'<div class="frow"><label>{lbl}</label><div class="ftrack"><div class="fbar" '
                       f'style="width:{min(100, 100 * v / total):.0f}%"></div></div><div class="fval">{v}</div></div>'
                       for lbl, v in rows)
        em = f.get("emails", {})
        st.markdown(f"""<div class="panel"><h4>Funnel</h4>{bars}
          <div class="rates"><div><b>{f.get("reply_rate_pct", 0)}%</b><span>Reply rate</span></div>
          <div><b>{f.get("conversion_rate_pct", 0)}%</b><span>Conversion rate</span></div>
          <div><b>{f.get("unsubscribe_rate_pct", 0)}%</b><span>Unsubscribe rate</span></div></div>
          <p class="hint" style="margin-top:12px">Emails: {em.get("sent", 0)} sent · {em.get("pending", 0)} scheduled ·
          {em.get("skipped", 0)} stopped</p></div>""", unsafe_allow_html=True)

        st.markdown("#### Follow-up timeline")
        if len(subs):
            drip = pd.DataFrame(db.rows("SELECT d.subscriber_id, s.email, s.name, d.step, d.step_name, d.due_at, "
                                        "d.status FROM drip d JOIN subscribers s ON s.id=d.subscriber_id "
                                        "ORDER BY d.subscriber_id DESC, d.step"))
            rows_html = ""
            if len(drip):
                drip["due"] = pd.to_datetime(drip["due_at"], errors="coerce")
                for sid, g in drip.groupby("subscriber_id", sort=False):
                    start = g["due"].min()
                    steps = ""
                    for _, s in g.iterrows():
                        day = int(round((s["due"] - start).total_seconds() / 86400)) if pd.notna(s["due"]) else "?"
                        state = str(s["status"])
                        label = {"sent": "sent", "pending": "scheduled", "skipped": "stopped"}.get(state, state)
                        steps += (f'<div class="step {esc(state)}"><i></i><b>{esc(str(s["step_name"]).replace("_", " "))}</b>'
                                  f'<span>day {day} · {esc(label)}</span></div>')
                    first = g.iloc[0]
                    rows_html += (f'<div class="trow"><div class="who"><b dir="auto">{esc(first["email"] if blank(first["name"]) else first["name"])}</b>'
                                  f'<span>{esc(first["email"])}</span></div><div class="steps">{steps}</div></div>')
            st.markdown(f'<div class="panel">{rows_html}<div class="legend">'
                        '<span><i style="background:#0F5E6E"></i>sent</span><span><i></i>scheduled</span>'
                        '<span><i style="border-color:#B7C3C5"></i>stopped</span></div></div>',
                        unsafe_allow_html=True)
        else:
            st.markdown('<div class="panel"><p>No subscribers yet. Submit the form to schedule a 4-email follow-up.</p>'
                        '</div>', unsafe_allow_html=True)

# ---------------- Outbox ----------------
with tabs[3]:
    st.markdown("#### Everything the system sent")
    st.markdown('<p class="hint">Customer replies, sales and manager alerts, and every marketing email, newest first.</p>',
                unsafe_allow_html=True)
    out = db.rows("SELECT * FROM outbox ORDER BY id DESC LIMIT 100")
    if not out:
        st.markdown('<div class="panel"><p>Nothing sent yet. Send a WhatsApp message or submit the email form.</p></div>',
                    unsafe_allow_html=True)
    for m in out:
        channel = "WhatsApp" if m["channel"] == "whatsapp" else "Email"
        title = m["subject"] or m["body"][:60].replace("\n", " ")
        with st.expander(f"{m['created_at']}  ·  {channel} to {m['to_addr']}  ·  {title}"):
            st.markdown(f'<div class="msgbody" dir="auto">{esc(m["body"])}</div>', unsafe_allow_html=True)
            st.caption(f"Delivery: {m['delivery']}")

# ---------------- CRM ----------------
with tabs[4]:
    st.markdown(f"#### CRM records · {config.CRM_MODE} mode")
    recs = db.rows("SELECT * FROM crm_records ORDER BY updated_at DESC")
    if recs:
        st.dataframe(clean(pd.DataFrame([{"crm_id": r["crm_id"], "kind": r["kind"], **json.loads(r["payload"])}
                                         for r in recs])), width="stretch", hide_index=True)
    else:
        st.markdown('<div class="panel"><p>No local CRM records yet. In Zoho mode, records live in Zoho CRM.</p></div>',
                    unsafe_allow_html=True)

# ---------------- Log ----------------
with tabs[5]:
    st.markdown("#### Every decision, with its reason")
    st.markdown('<p class="hint">Scores, alerts and emails are logged with why they happened, so nothing is a black box.</p>',
                unsafe_allow_html=True)
    log = pd.DataFrame(db.rows("SELECT ts, kind, detail FROM events ORDER BY id DESC LIMIT 200"))
    if len(log):
        st.dataframe(log, width="stretch", hide_index=True,
                     column_config={"ts": st.column_config.TextColumn("time", width="small"),
                                    "kind": st.column_config.TextColumn("event", width="small"),
                                    "detail": st.column_config.TextColumn("detail", width="large")})
    else:
        st.markdown('<div class="panel"><p>No activity yet.</p></div>', unsafe_allow_html=True)
