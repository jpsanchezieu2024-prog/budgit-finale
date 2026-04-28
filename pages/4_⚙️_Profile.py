"""
Profile screen — update the name, weekly budget and preferred store.
Covers User Story 1's post-registration edit flow.
"""

from __future__ import annotations
import streamlit as st

import database as db
from state import init_state, require_login, SUPERMARKETS
from theme import apply_theme


st.set_page_config(page_title="Budgit — Profile", page_icon="⚙️", layout="centered")
apply_theme()
init_state()
user = require_login()

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
