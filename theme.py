"""
Budgit — dark minty green theme.
Dark background with green accents and light text throughout.
"""

import streamlit as st

# Color palette
PRIMARY       = "#40B391"   # mint green (main accent)
PRIMARY_SOFT  = "#2ECC9A"   # brighter mint for gradients
PRIMARY_DARK  = "#1A7F66"   # deeper green for hover
BG_DARK       = "#0F1A16"   # near-black with green tint
BG_CARD       = "#1A2B24"   # card background
BG_ELEVATED   = "#223320"   # slightly lighter card
BORDER        = "#2A3D34"   # subtle border
TEXT          = "#E8F5EF"   # near-white text
TEXT_MUTED    = "#7FB5A0"   # muted green-grey text
DANGER        = "#FF6B5B"   # red for over budget
WARNING       = "#FFB84D"   # amber for warnings

CSS = f"""
<style>
/* ---- Base ---- */
html, body, [class*="css"] {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: {TEXT};
    background-color: {BG_DARK};
}}
.main {{
    background-color: {BG_DARK};
}}
.main .block-container {{
    padding-top: 2rem;
    padding-bottom: 4rem;
    max-width: 860px;
    background-color: {BG_DARK};
}}

/* ---- All text visible ---- */
p, span, label, div, h1, h2, h3, h4, h5, h6 {{
    color: {TEXT} !important;
}}
.stMarkdown, .stText, .stCaption {{
    color: {TEXT} !important;
}}

/* ---- Inputs ---- */
input, textarea, select {{
    background-color: {BG_CARD} !important;
    color: {TEXT} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
}}
input::placeholder {{
    color: {TEXT_MUTED} !important;
}}
.stTextInput > div > div > input,
.stNumberInput > div > div > input {{
    background-color: {BG_CARD} !important;
    color: {TEXT} !important;
    border: 1px solid {BORDER} !important;
}}

/* ---- Buttons ---- */
div.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {PRIMARY_DARK}, {PRIMARY}) !important;
    color: #0F1A16 !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.6rem 1.2rem !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 15px rgba(64,179,145,0.3) !important;
}}
div.stButton > button {{
    background-color: {BG_CARD} !important;
    color: {TEXT} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 12px !important;
    padding: 0.55rem 1.1rem !important;
    font-weight: 500 !important;
}}
div.stButton > button:hover {{
    border-color: {PRIMARY} !important;
    color: {PRIMARY} !important;
}}

/* ---- Cards ---- */
.budgit-card {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 16px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}}
.budgit-accent {{
    background: linear-gradient(135deg, {BG_ELEVATED}, {BG_CARD});
    border: 1px solid {PRIMARY_DARK};
    border-radius: 16px;
    padding: 1.6rem;
    text-align: center;
}}
.budgit-total {{
    font-size: 2.6rem;
    font-weight: 800;
    color: {PRIMARY} !important;
    margin: 0.4rem 0;
}}
.budgit-total-label {{
    color: {TEXT_MUTED} !important;
    font-size: 0.9rem;
    margin-top: 0.25rem;
}}
.budgit-item {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    border: 1px solid {BORDER};
    border-radius: 12px;
    margin-bottom: 0.5rem;
    background: {BG_CARD};
}}

/* ---- Pills ---- */
.pill {{
    display: inline-block;
    padding: 3px 12px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
}}
.pill-ok     {{ background: rgba(64,179,145,0.2); color: {PRIMARY} !important; border: 1px solid {PRIMARY_DARK}; }}
.pill-warn   {{ background: rgba(255,184,77,0.15); color: {WARNING} !important; border: 1px solid rgba(255,184,77,0.3); }}
.pill-danger {{ background: rgba(255,107,91,0.15); color: {DANGER} !important; border: 1px solid rgba(255,107,91,0.3); }}

/* ---- Progress bar ---- */
.stProgress > div > div > div > div {{
    background: linear-gradient(90deg, {PRIMARY_DARK}, {PRIMARY_SOFT}) !important;
}}

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {{
    background-color: {BG_CARD} !important;
    border-right: 1px solid {BORDER};
}}
section[data-testid="stSidebar"] * {{
    color: {TEXT} !important;
}}

/* ---- Tabs ---- */
.stTabs [data-baseweb="tab-list"] {{
    background-color: {BG_CARD} !important;
    border-radius: 10px;
    padding: 4px;
}}
.stTabs [data-baseweb="tab"] {{
    color: {TEXT_MUTED} !important;
    border-radius: 8px;
}}
.stTabs [aria-selected="true"] {{
    background-color: {BG_ELEVATED} !important;
    color: {PRIMARY} !important;
}}

/* ---- Selectbox / dropdowns ---- */
.stSelectbox > div > div {{
    background-color: {BG_CARD} !important;
    color: {TEXT} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
}}

/* ---- Metrics ---- */
[data-testid="stMetricValue"] {{
    color: {PRIMARY} !important;
    font-weight: 700 !important;
}}
[data-testid="stMetricLabel"] {{
    color: {TEXT_MUTED} !important;
}}

/* ---- Expander ---- */
.streamlit-expanderHeader {{
    background-color: {BG_CARD} !important;
    color: {TEXT} !important;
    border-radius: 10px !important;
    border: 1px solid {BORDER} !important;
}}
.streamlit-expanderContent {{
    background-color: {BG_ELEVATED} !important;
    border: 1px solid {BORDER} !important;
}}

/* ---- Alerts ---- */
.stAlert {{
    background-color: {BG_CARD} !important;
    border-radius: 12px !important;
}}

/* ---- Hide default chrome ---- */
[data-testid="stDecoration"] {{ display: none; }}
footer {{ visibility: hidden; }}
</style>
"""


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def budget_tree(pct_used: float) -> str:
    """Emoji showing how healthy the budget looks."""
    if pct_used < 0.5:
        return "🌳"
    if pct_used < 0.8:
        return "🌴"
    if pct_used < 1.0:
        return "🍂"
    return "🥀"


def budget_color(pct_used: float) -> str:
    """
    Smooth gradient colour for the "remaining" amount on the dashboard.

    Interpolates linearly through three RGB anchor points:
        pct = 0.0  -> mint green   (#40B391)
        pct = 0.5  -> warm yellow  (#FFD93D)
        pct = 1.0+ -> alert red    (#FF6B5B)

    Anything beyond 100% stays clamped at the red anchor.
    """
    # Clamp into [0, 1] so over-budget just stays full-red.
    p = max(0.0, min(1.0, pct_used))

    # Anchor RGB triples
    green  = (0x40, 0xB3, 0x91)
    yellow = (0xFF, 0xD9, 0x3D)
    red    = (0xFF, 0x6B, 0x5B)

    if p <= 0.5:
        t = p / 0.5
        a, b = green, yellow
    else:
        t = (p - 0.5) / 0.5
        a, b = yellow, red

    r = round(a[0] + (b[0] - a[0]) * t)
    g = round(a[1] + (b[1] - a[1]) * t)
    bl = round(a[2] + (b[2] - a[2]) * t)
    return f"#{r:02X}{g:02X}{bl:02X}"


def budget_pill(pct_used: float) -> str:
    if pct_used < 0.5:
        return '<span class="pill pill-ok">Healthy</span>'
    if pct_used < 0.8:
        return '<span class="pill pill-ok">On track</span>'
    if pct_used < 1.0:
        return '<span class="pill pill-warn">Watch out</span>'
    return '<span class="pill pill-danger">Over budget</span>'


def budget_advice(pct_used: float, remaining: float, days_left: int) -> str:
    """Return a friendly tip based on how the budget is doing."""
    daily = remaining / days_left if days_left > 0 else 0
    if pct_used < 0.3:
        return f"🟢 You're well under budget. You can spend up to **€{daily:.2f}/day** for the rest of the week."
    if pct_used < 0.6:
        return f"🟡 Halfway through your budget. Try to keep it under **€{daily:.2f}/day** to stay on track."
    if pct_used < 0.85:
        return f"🟠 Getting tight! Aim for **€{daily:.2f}/day** max. Stick to essentials."
    if pct_used < 1.0:
        return f"🔴 Almost out! Only **€{remaining:.2f}** left — be very selective."
    return "💸 You've gone over budget this week. Consider the Budget Rescue feature when shopping."
