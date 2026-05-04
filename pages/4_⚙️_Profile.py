"""
Profile screen — update the name, weekly budget and preferred store.
Covers User Story 1's post-registration edit flow.
"""

from __future__ import annotations
import streamlit as st

import database as db
from state import init_state, require_login, SUPERMARKETS, render_sidebar, render_budget_meter
from theme import apply_theme


st.set_page_config(page_title="Budgit — Profile", page_icon="⚙️", layout="centered")
apply_theme()
init_state()
user = require_login()
render_sidebar(user)
render_budget_meter(user)

st.markdown("### ⚙️ Profile & budget")

with st.form("profile"):
    name = st.text_input("Name", value=user.name)
    budget = st.number_input(
        "Weekly grocery budget (€)",
        min_value=1.0, max_value=1000.0,
        value=float(user.weekly_budget), step=5.0,
    )
    store_idx = (
        SUPERMARKETS.index(user.preferred_store)
        if user.preferred_store in SUPERMARKETS else 0
    )
    store = st.selectbox("Preferred supermarket", SUPERMARKETS, index=store_idx)

    if st.form_submit_button("Save changes", type="primary"):
        if budget <= 0:
            st.error("Budget must be greater than €0.")
        else:
            db.update_user_profile(
                user.id,
                name=name,
                weekly_budget=budget,
                preferred_store=store,
            )
            st.success("Profile updated\!")
            st.rerun()


st.divider()

# -----------------------------------------------------
# Badge wall — every achievement currently defined,
# split into "earned" (full colour) and "locked" (dimmed).
# Hover on each badge to read the description.
# -----------------------------------------------------
st.markdown("#### 🏆 Achievements")
earned_ids = set(db.get_user_badges(user.id))
total = len(db.BADGES)
st.caption(f"{len(earned_ids)} of {total} unlocked.")

cols = st.columns(4)
for i, (bid, meta) in enumerate(db.BADGES.items()):
    is_earned = bid in earned_ids
    bg     = "rgba(64,179,145,0.18)" if is_earned else "rgba(255,255,255,0.02)"
    border = "#40B391" if is_earned else "#2A3D34"
    color  = "#E8F5EF" if is_earned else "#5C6B66"
    emoji_opacity = "1.0" if is_earned else "0.35"
    desc = meta["desc"].replace('"', "&quot;")
    cols[i % 4].markdown(
        f"<div title='{desc}' style='background:{bg};"
        f" border:1px solid {border}; border-radius:12px;"
        f" padding:0.7rem 0.5rem; margin-bottom:0.5rem;"
        f" text-align:center;'>"
        f"<div style='font-size:1.6rem; opacity:{emoji_opacity};'>{meta['emoji']}</div>"
        f"<div style='font-size:0.78rem; color:{color}; font-weight:600;'>"
        f"{meta['name']}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

st.divider()

# -----------------------------------------------------
# Lifetime savings summary so the Profile page mirrors
# what the Home dashboard shows.
# -----------------------------------------------------
lt_saved, lt_could_have, lt_counted = db.get_user_savings_totals(user.id)
if lt_counted > 0:
    pct = (lt_saved / lt_could_have * 100) if lt_could_have > 0 else 0
    st.markdown(
        f"<div class='budgit-card' style='text-align:center;'>"
        f"<div style='color:#7FB5A0; font-size:0.85rem;'>Lifetime savings</div>"
        f"<div style='font-size:1.6rem; font-weight:800; color:#40B391;'>"
        f"€{lt_saved:,.2f}</div>"
        f"<div style='color:#7FB5A0; font-size:0.78rem;'>"
        f"{pct:.1f}% off vs the most expensive store on file"
        f" · {lt_counted} counted shop{'s' if lt_counted != 1 else ''}"
        f"</div></div>",
        unsafe_allow_html=True,
    )

st.divider()
st.markdown("#### Learned prices")

products = db.get_all_products(user.id)
if not products:
    st.caption("You haven't logged any prices yet.")
else:
    st.caption(f"Budgit has learned {len(products)} product-price pairs "
               "across your supermarkets. They auto-fill as you shop.")
    for p in products[:25]:
        st.markdown(
            f"<div class='budgit-item'>"
            f"<div><b>{p['name'].title()}</b> <span style='color:#5C6B66;'>· {p['supermarket']}</span></div>"
            f"<div>€{p['price']:.2f}</div></div>",
            unsafe_allow_html=True,
        )
    if len(products) > 25:
        st.caption(f"…and {len(products) - 25} more.")
