"""
Web page for bill-decoder-agent.

Run locally:
    streamlit run app.py
"""

import datetime
import html
import os
import threading
import time

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from guardrails import INJECTION_RULE, charges_add_up, check_file

load_dotenv()

# Usage limits that protect the shared Gemini API quota on a public deployment.
MAX_BILLS_PER_VISITOR = 5
COOLDOWN_SECONDS = 20
MAX_BILLS_PER_DAY = 200  # across all visitors

# On Streamlit Community Cloud the key comes from the app's Secrets settings.
if not os.getenv("GEMINI_API_KEY"):
    try:
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
    except (KeyError, FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        pass

LANGUAGES = ["English", "ಕನ್ನಡ Kannada", "हिन्दी Hindi", "தமிழ் Tamil", "తెలుగు Telugu", "മലയാളം Malayalam"]


# ---------- Structured answer from Gemini ----------

class Charge(BaseModel):
    name: str
    amount: str
    explanation: str


class RedFlag(BaseModel):
    title: str
    detail: str


class BillReport(BaseModel):
    is_bill: bool
    bill_type: str
    provider: str
    billing_period: str
    total_amount: str
    due_date: str
    summary: str
    charges: list[Charge]
    red_flags: list[RedFlag]
    tips: list[str]


WEB_PROMPT = """You are a friendly assistant that explains Indian utility bills
(electricity, water, gas, mobile, broadband) to ordinary people.

Read the attached bill and fill in the JSON fields. Write every text value in
{language}, using simple words. Keep amounts in the form printed on the bill,
e.g. "₹ 145.00".

- is_bill: false if the file is not a utility bill (then leave other fields empty).
- summary: 1-2 sentences saying what the person needs to know or do.
- charges: every individual line item with its amount and a one-line plain
  explanation. Include credits, subsidies and arrears as negative amounts. Do not
  include subtotal or total lines, so the charges add up to total_amount.
- red_flags: late fees, interest, arrears, estimated meter readings, usage spikes,
  unknown charges, calculation mistakes or pending deposits. Empty list if none.
- tips: 2 or 3 practical money-saving tips for this bill type.

Only use information printed on the bill. Write "Not shown" when a value is missing
or unreadable instead of guessing.
""" + INJECTION_RULE


@st.cache_resource
def daily_usage() -> dict:
    """App-wide counter shared by all visitors: {"date": ..., "count": ..., "lock": ...}."""
    return {"date": datetime.date.today(), "count": 0, "lock": threading.Lock()}


def usage_problem() -> str | None:
    """Return a message if this request should be blocked by a usage limit."""
    state = st.session_state
    if state.get("bills_used", 0) >= MAX_BILLS_PER_VISITOR:
        return f"You have reached the limit of {MAX_BILLS_PER_VISITOR} bills for this visit. Please come back later."
    wait = COOLDOWN_SECONDS - (time.time() - state.get("last_request", 0))
    if wait > 0:
        return f"Please wait {int(wait) + 1} seconds before decoding another bill."
    usage = daily_usage()
    with usage["lock"]:
        if usage["date"] != datetime.date.today():
            usage["date"], usage["count"] = datetime.date.today(), 0
        if usage["count"] >= MAX_BILLS_PER_DAY:
            return "This free demo has reached its daily limit. Please try again tomorrow."
    return None


def record_usage() -> None:
    st.session_state["bills_used"] = st.session_state.get("bills_used", 0) + 1
    st.session_state["last_request"] = time.time()
    usage = daily_usage()
    with usage["lock"]:
        usage["count"] += 1


def decode_bill_report(file_bytes: bytes, mime_type: str, language: str) -> BillReport:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model=os.getenv("MODEL_NAME", "gemini-3.5-flash"),
        contents=[
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            WEB_PROMPT.format(language=language),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=BillReport,
        ),
    )
    return response.parsed




# ---------- Page style (dark mode, large text for all ages) ----------

st.set_page_config(page_title="Bill Decoder", page_icon="🧾", layout="centered")

st.markdown(
    """
    <style>
    :root {
        --bg: #0f1117;
        --surface: #1a1d29;
        --surface-2: #232736;
        --border: #2f3445;
        --text: #f3f4f6;
        --muted: #b4bac8;
        --blue: #3b82f6;
        --blue-dark: #1e40af;
        --red: #f87171;
        --green: #4ade80;
        --amber: #fbbf24;
    }

    /* Bigger base text so it is easy to read for everyone */
    html { font-size: 18px; }
    .stApp { background: var(--bg); color: var(--text); }
    .block-container { max-width: 760px; padding-top: 1.5rem; padding-bottom: 3rem; }
    p, li, label, .stMarkdown { line-height: 1.6; }

    /* Header */
    .hero {
        background: linear-gradient(135deg, #1e3a8a 0%, #4c1d95 100%);
        border: 1px solid #3b4a8a; border-radius: 22px;
        padding: 28px 26px 22px; margin-bottom: 28px;
        box-shadow: 0 12px 30px rgba(0,0,0,.45);
    }
    .hero h1 { color: #fff; font-size: 2.3rem; margin: 0 0 8px; padding: 0; }
    .hero p { color: #dbe4ff; font-size: 1.15rem; margin: 0 0 16px; }
    .badge {
        display: inline-block; background: rgba(255,255,255,.14); color: #fff;
        border-radius: 999px; padding: 6px 14px; margin: 0 8px 8px 0; font-size: .9rem;
    }

    /* Numbered steps */
    .step { display: flex; align-items: center; gap: 12px; margin: 22px 0 6px; }
    .step .num {
        flex: none; width: 40px; height: 40px; border-radius: 50%;
        background: var(--blue); color: #fff; font-weight: 800; font-size: 1.15rem;
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 4px 0 var(--blue-dark);
    }
    .step .title { font-size: 1.3rem; font-weight: 700; color: var(--text); }
    .hint { color: var(--muted); font-size: .95rem; margin: 0 0 10px 52px; }

    /* Upload box */
    [data-testid="stFileUploaderDropzone"] {
        background: var(--surface); border: 2px dashed var(--blue);
        border-radius: 16px; padding: 26px 18px;
    }
    [data-testid="stFileUploaderDropzone"]:hover { background: var(--surface-2); }

    /* Language choices as big tappable pills */
    div[role="radiogroup"] { gap: 10px; flex-wrap: wrap; }
    div[role="radiogroup"] > label {
        background: var(--surface); border: 2px solid var(--border);
        border-radius: 14px; padding: 10px 16px; margin: 0 !important;
        cursor: pointer; transition: border-color .15s, background .15s;
    }
    div[role="radiogroup"] > label:hover { border-color: var(--blue); }
    div[role="radiogroup"] > label:has(input:checked) {
        border-color: var(--blue); background: rgba(59,130,246,.18);
    }

    /* 3D buttons: raised, lift on hover, press down on click */
    .stButton > button, .stDownloadButton > button {
        width: 100%; min-height: 64px; font-size: 1.25rem; font-weight: 800;
        border-radius: 16px; border: none; color: #fff;
        background: linear-gradient(180deg, #60a5fa 0%, #2563eb 100%);
        box-shadow: 0 7px 0 var(--blue-dark), 0 12px 24px rgba(0,0,0,.5);
        transform: translateY(0);
        transition: transform .12s ease, box-shadow .12s ease, filter .12s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        color: #fff; border: none; filter: brightness(1.1);
        transform: translateY(-3px);
        box-shadow: 0 10px 0 var(--blue-dark), 0 18px 30px rgba(0,0,0,.55);
    }
    .stButton > button:active, .stDownloadButton > button:active {
        transform: translateY(6px);
        box-shadow: 0 1px 0 var(--blue-dark), 0 4px 8px rgba(0,0,0,.4);
    }
    .stButton > button:focus-visible, .stDownloadButton > button:focus-visible {
        outline: 3px solid var(--amber); outline-offset: 4px;
    }
    .stButton > button:disabled {
        background: var(--surface-2); color: #8a90a0;
        box-shadow: 0 5px 0 #11131b; transform: none; filter: none; cursor: not-allowed;
    }
    .stDownloadButton > button {
        background: linear-gradient(180deg, #4ade80 0%, #16a34a 100%);
        box-shadow: 0 7px 0 #14532d, 0 12px 24px rgba(0,0,0,.5);
    }
    .stDownloadButton > button:hover { box-shadow: 0 10px 0 #14532d, 0 18px 30px rgba(0,0,0,.55); }
    .stDownloadButton > button:active { box-shadow: 0 1px 0 #14532d, 0 4px 8px rgba(0,0,0,.4); }

    /* Result cards */
    .section { font-size: 1.45rem; font-weight: 800; margin: 30px 0 12px; color: var(--text); }
    .summary {
        background: rgba(59,130,246,.14); border: 1px solid rgba(59,130,246,.45);
        border-radius: 16px; padding: 16px 18px; font-size: 1.1rem; margin-bottom: 14px;
    }
    .card {
        background: var(--surface); border: 1px solid var(--border);
        border-radius: 16px; padding: 16px 18px; margin-bottom: 12px;
    }
    .card .label { font-size: .85rem; color: var(--muted); font-weight: 600; letter-spacing: .03em; }
    .card .value { font-size: 1.4rem; font-weight: 800; margin-top: 4px; color: var(--text); }
    .card.big { border: 2px solid var(--blue); background: rgba(59,130,246,.10); }
    .card.big .value { font-size: 1.8rem; }
    .charge { display: flex; justify-content: space-between; gap: 14px; align-items: baseline; }
    .charge .name { font-weight: 700; font-size: 1.1rem; }
    .charge .amt { font-weight: 800; font-size: 1.15rem; white-space: nowrap; color: #93c5fd; }
    .why { color: var(--muted); font-size: 1rem; margin-top: 4px; }
    .flag { border-left: 6px solid var(--red); background: rgba(248,113,113,.10); }
    .flag .name { color: #fecaca; font-size: 1.1rem; }
    .tip, .ok { border-left: 6px solid var(--green); background: rgba(74,222,128,.08); font-size: 1.05rem; }
    .footer { color: var(--muted); font-size: .9rem; text-align: center; margin-top: 30px; }

    /* Phones */
    @media (max-width: 640px) {
        html { font-size: 17px; }
        .hero h1 { font-size: 1.9rem; }
        .hint { margin-left: 0; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def card(label: str, value: str, extra_class: str = "") -> str:
    return (
        f'<div class="card {extra_class}"><div class="label">{html.escape(label)}</div>'
        f'<div class="value">{html.escape(value)}</div></div>'
    )


def step(number: int, title: str, hint: str) -> None:
    st.markdown(
        f'<div class="step"><span class="num">{number}</span><span class="title">{title}</span></div>'
        f'<div class="hint">{hint}</div>',
        unsafe_allow_html=True,
    )


# ---------- Header ----------

st.markdown(
    """
    <div class="hero">
      <h1>🧾 Bill Decoder</h1>
      <p>Don't understand your bill? Upload a photo. We explain every charge in
      simple words and warn you about anything unusual.</p>
      <span class="badge">📷 Photo or PDF</span>
      <span class="badge">🗣️ 6 Indian languages</span>
      <span class="badge">🚩 Finds hidden charges</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- Input ----------

step(1, "Upload your bill", "Electricity, water, gas, mobile or broadband. Take the photo in good light and show the whole bill.")
uploaded = st.file_uploader(
    "Upload your bill",
    type=["jpg", "jpeg", "png", "webp", "pdf"],
    label_visibility="collapsed",
)

if uploaded and uploaded.type.startswith("image/"):
    with st.expander("👀 Check your photo"):
        st.image(uploaded, width="stretch")

step(2, "Choose your language", "The explanation will be written in this language.")
language_choice = st.radio(
    "Language", LANGUAGES, horizontal=True, label_visibility="collapsed"
)
language = language_choice.split()[-1]

step(3, "Get your explanation", "It takes about 10–30 seconds.")
decode = st.button(
    "✨ Explain my bill" if uploaded else "⬆️ Upload a bill first",
    type="primary",
    disabled=uploaded is None,
)

# ---------- Result ----------

if decode and uploaded:
    if not os.getenv("GEMINI_API_KEY"):
        st.error("GEMINI_API_KEY is not set. Add it to .env (local) or the app's Secrets (cloud).")
        st.stop()
    problem = check_file(uploaded.type, uploaded.size)
    if problem:
        st.error(f"📄 {problem}")
        st.stop()
    problem = usage_problem()
    if problem:
        st.warning(f"⏳ {problem}")
        st.stop()

    record_usage()
    with st.spinner("🔍 Reading your bill… please wait"):
        try:
            report = decode_bill_report(uploaded.getvalue(), uploaded.type, language)
        except errors.APIError as e:
            if e.code == 503:
                st.warning("⏳ The AI is busy right now. Please wait one minute and press the button again.")
            else:
                st.error(f"Something went wrong with the AI service ({e.code}): {e.message}")
            st.stop()

    if report is None:
        st.error("😕 We could not read this bill. Please try a clearer photo.")
        st.stop()
    if not report.is_bill:
        st.warning("🤔 This doesn't look like a bill. Please upload a photo or PDF of a bill.")
        st.stop()

    # 1. The most important facts first
    st.markdown('<div class="section">📋 Your bill at a glance</div>', unsafe_allow_html=True)
    if report.summary:
        st.markdown(f'<div class="summary">{html.escape(report.summary)}</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    c1.markdown(card("💵 AMOUNT TO PAY", report.total_amount, "big"), unsafe_allow_html=True)
    c2.markdown(card("📅 PAY BEFORE", report.due_date, "big"), unsafe_allow_html=True)
    c3, c4 = st.columns(2)
    c3.markdown(card("🏢 BILL FROM", f"{report.provider} · {report.bill_type}"), unsafe_allow_html=True)
    c4.markdown(card("🗓️ BILLING PERIOD", report.billing_period), unsafe_allow_html=True)

    # Math check: the AI can misread numbers, so verify the charges add up.
    if charges_add_up([c.amount for c in report.charges], report.total_amount) is False:
        st.warning(
            "🧮 The charges we read don't add up to the total. The photo may be unclear, "
            "so please double-check the amounts on your paper bill."
        )

    # 2. Warnings next, so nobody misses them
    st.markdown(
        f'<div class="section">🚩 Things to check ({len(report.red_flags)})</div>', unsafe_allow_html=True
    )
    if report.red_flags:
        for f in report.red_flags:
            st.markdown(
                f'<div class="card flag"><div class="name"><b>⚠️ {html.escape(f.title)}</b></div>'
                f'<div class="why">{html.escape(f.detail)}</div></div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown('<div class="card ok">✅ Nothing unusual found. Your bill looks normal.</div>', unsafe_allow_html=True)

    # 3. Every charge explained
    st.markdown(
        f'<div class="section">💰 What you are paying for ({len(report.charges)})</div>', unsafe_allow_html=True
    )
    for c in report.charges:
        st.markdown(
            f'<div class="card"><div class="charge"><span class="name">{html.escape(c.name)}</span>'
            f'<span class="amt">{html.escape(c.amount)}</span></div>'
            f'<div class="why">{html.escape(c.explanation)}</div></div>',
            unsafe_allow_html=True,
        )

    # 4. Tips
    st.markdown('<div class="section">💡 Ways to save money</div>', unsafe_allow_html=True)
    for t in report.tips:
        st.markdown(f'<div class="card tip">💡 {html.escape(t)}</div>', unsafe_allow_html=True)

    # Plain-text copy the user can save or share
    lines = [
        f"Bill: {report.bill_type} ({report.provider})",
        f"Period: {report.billing_period}",
        f"Amount to pay: {report.total_amount}",
        f"Due date: {report.due_date}",
        "",
        "Things to check:",
        *([f"- {f.title}: {f.detail}" for f in report.red_flags] or ["- None"]),
        "",
        "Charges:",
        *[f"- {c.name}: {c.amount} — {c.explanation}" for c in report.charges],
        "",
        "Tips:",
        *[f"- {t}" for t in report.tips],
    ]
    st.write("")
    st.download_button(
        "⬇️ Save this explanation",
        "\n".join(lines),
        file_name="bill-explanation.txt",
        width="stretch",
    )

st.markdown(
    '<div class="footer">🔒 Your bill is sent to Google Gemini to be read and is not stored by this app.<br>'
    "This is for information only, not financial advice.</div>",
    unsafe_allow_html=True,
)
