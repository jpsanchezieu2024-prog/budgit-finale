"""
Shopping history screen — User Story 4 (first half).

Sessions are ordered by created_at DESC using the MERGE SORT we
implemented in algorithms/sorting.py — deliberately NOT relying on
SQL's ORDER BY so the class algorithm gets exercised.
"""

from __future__ import annotations
import streamlit as st
from datetime import datetime

import database as db
from state import init_state, require_login, render_sidebar, render_budget_meter
from theme import apply_theme
from algorithms.sorting import merge_sort


st.set_page_config(page_title="Budgit — History", page_icon="📜", layout="centered")
apply_theme()
init_state()
user = require_login()
render_sidebar(user)
render_budget_meter(user)


# Per-supermarket visual identity. Each store gets a distinct emoji
# and accent colour so the user can tell at a glance whether a session
# happened at Mercadona, Lidl, Carrefour, etc.
STORE_STYLE = {
    "Mercadona": {"emoji": "🟢", "color": "#4DA64D"},
    "Lidl":      {"emoji": "🟡", "color": "#E5B30B"},
    "Carrefour": {"emoji": "🔵", "color": "#1F7FBF"},
    "Dia":       {"emoji": "🔴", "color": "#E32E2E"},
    "Aldi":      {"emoji": "🟠", "color": "#F58634"},
    "Alcampo":   {"emoji": "🟣", "color": "#A847BB"},
}
DEFAULT_STYLE = {"emoji": "⚪", "color": "#7FB5A0"}


def _style_for(store: str) -> dict:
    return STORE_STYLE.get(store, DEFAULT_STYLE)


st.markdown("### 📜 Shopping history")

raw = db.get_sessions(user.id)

if not raw:
    st.info(
        "No shops yet\! Complete your first shopping session and it'll appear "
        "here with date, supermarket and total."
    )
    if st.button("Start shopping now", type="primary"):
        st.switch_page("pages/1_🛒_Shop.py")
    st.stop()


# --- Summary metrics -------------------------------------------------
total_spent = sum(s["total"] for s in raw)
c1, c2, c3 = st.columns(3)
c1.metric("Sessions", len(raw))
c2.metric("Total spent", f"€{total_spent:,.2f}")
c3.metric("Avg per shop", f"€{total_spent/len(raw):,.2f}")


# --- "Where you've shopped" summary chips ---------------------------
unique_stores = sorted({s["supermarket"] for s in raw})
if len(unique_stores) > 1:
    st.markdown("##### 🏬 Stores in this history")
    chip_html = ""
    for store in unique_stores:
        style = _style_for(store)
        count = sum(1 for s in raw if s["supermarket"] == store)
        chip_html += (
            f"<span style='display:inline-block; margin:0 6px 6px 0; padding:6px 12px;"
            f" border-radius:999px; background:rgba(255,255,255,0.04);"
            f" border:1px solid {style['color']}; color:{style['color']}; font-weight:600;'>"
            f"{style['emoji']} {store} <span style='opacity:0.7;'>· {count}</span>"
            f"</span>"
        )
    st.markdown(f"<div>{chip_html}</div>", unsafe_allow_html=True)

st.divider()


# --- Sort with class MERGE SORT -------------------------------------
rows = [dict(r) for r in raw]
rows = merge_sort(rows, key=lambda r: r["created_at"], reverse=True)


# --- List of sessions ------------------------------------------------
for s in rows:
    style = _style_for(s["supermarket"])
    created = datetime.fromisoformat(s["created_at"])

    # Coloured header card *above* the expander so the supermarket
    # is unmistakable (st.expander labels can't render HTML).
    st.markdown(
        f"<div style='border-left:6px solid {style['color']};"
        f" padding:0.5rem 0.9rem; margin-top:0.6rem; margin-bottom:-0.3rem;"
        f" background:rgba(255,255,255,0.02); border-radius:8px 8px 0 0;"
        f" display:flex; justify-content:space-between; align-items:center;'>"
        f"<span><span style='color:{style['color']}; font-weight:700;'>"
        f"{style['emoji']} {s['supermarket']}</span>"
        f"<span style='color:#7FB5A0; font-size:0.85rem;'>"
        f" · {created.strftime('%d %b %Y %H:%M')}</span></span>"
        f"<span style='font-weight:700; color:#40B391;'>€{s['total']:,.2f}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    label = f"{style['emoji']} {s['supermarket']} — view items"
    with st.expander(label, expanded=False):
        items = db.get_session_items(s["id"])
        if not items:
            st.caption("_No items recorded._")
        else:
            for it in items:
                from state import lookup_in_directory

                entry = lookup_in_directory(it["name"], s["supermarket"])
                # entry is a float from the normalised directory —
                # fetch the raw entry to check verified flag
                ht = __import__('streamlit').session_state.get("item_directory_ht")
                raw = ht.get(it["name"].lower().strip()) if ht else None
                raw_store = raw.get("prices", {}).get(s["supermarket"], {}) if raw else {}
                is_verified = raw_store.get("verified", False) if isinstance(raw_store, dict) else False
                verified_badge = " ✅" if is_verified else ""
                st.markdown(
                    f"<div class='budgit-item' style='border-left:4px solid {style['color']};'>"
                    f"<div><b>{it['name'].title()}</b>{verified_badge} "
                    f"<span style='color:#5C6B66; font-size:0.85rem;'>× {it['qty']}</span></div>"
                    f"<div>€{it['price'] * it['qty']:.2f}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            st.markdown(
                f"<div style='text-align:right; font-weight:700; "
                f"color:{style['color']}; margin-top:0.5rem;'>Total €{s['total']:.2f}</div>",
                unsafe_allow_html=True,
            )
