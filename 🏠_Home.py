"""
Budgit — main entry point.
Run with: streamlit run "🏠_Home.py"

The filename matters: Streamlit's multipage navigation in the sidebar uses
the script's filename as the page label. Naming this file `🏠_Home.py`
makes the sidebar say "🏠 Home" instead of "app".
"""

import streamlit as st
from datetime import datetime, timedelta

import database as db
from models import Cart
from state import (
    init_state, current_user, SUPERMARKETS,
    rebuild_bst, load_item_directory, render_sidebar,
    start_of_current_week, days_left_in_week,
)
from theme import apply_theme, budget_pill, budget_advice, budget_color


# Keys that belong to the *previous* user and must never leak into the
# next session in the same browser tab.
_USER_SCOPED_KEYS = (
    "cart", "bst", "shop_store", "item_directory_ht",
    "grocery_items", "grocery_list_user", "last_typed_name",
    "item_name",
)


def _switch_user(new_uid: str) -> None:
    """Clear everything tied to the previous user, then load the new one."""
    for k in _USER_SCOPED_KEYS:
        st.session_state.pop(k, None)
    st.session_state.cart = Cart()
    st.session_state.user_id = new_uid
    rebuild_bst(new_uid)
    load_item_directory()


st.set_page_config(page_title="🏠 Home", page_icon="🏠", layout="centered")
apply_theme()
init_state()


# -------------------------------------------------------
# Auth screen
# -------------------------------------------------------
def _welcome():
    st.markdown(
        """
        <div style="text-align:center; padding: 2rem 0 1rem;">
          <div style="font-size:4rem">🛒</div>
          <h1 style="color:#40B391; margin:0.2rem 0; font-size:2.5rem;">Budgit</h1>
          <p style="color:#7FB5A0; font-size:1.1rem;">Never panic at the checkout again.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

        with tab_login:
            with st.form("login"):
                email = st.text_input("Email")
                pw = st.text_input("Password", type="password")
                if st.form_submit_button("Log in", type="primary", use_container_width=True):
                    row = db.get_user_by_email(email)
                    if row is None or not db.verify_password(pw, row["password_hash"], row["salt"]):
                        st.error("Wrong email or password.")
                    else:
                        _switch_user(row["id"])
                        # Drop the user straight into the shopping page —
                        # that's the primary action of the app.
                        st.switch_page("pages/1_🛒_Shop.py")

        with tab_signup:
            with st.form("signup"):
                name = st.text_input("Name")
                email = st.text_input("Email")
                pw = st.text_input("Password", type="password")
                budget = st.number_input(
                    "Weekly grocery budget (€)",
                    min_value=1.0, max_value=1000.0, value=40.0, step=5.0,
                    help="How much do you want to spend on groceries per week?"
                )
                store = st.selectbox("Preferred supermarket", SUPERMARKETS)

                if st.form_submit_button("Create account", type="primary", use_container_width=True):
                    if not name or not email or not pw:
                        st.error("All fields are required.")
                    elif db.get_user_by_email(email) is not None:
                        st.error("An account with that email already exists.")
                    else:
                        uid = db.create_user(
                            name=name, email=email, password=pw,
                            weekly_budget=budget, preferred_store=store,
                        )
                        _switch_user(uid)
                        # Flag this user as brand-new so the Shop page
                        # can show a one-shot welcome banner.
                        st.session_state.first_time_user = True
                        st.switch_page("pages/1_🛒_Shop.py")


# -------------------------------------------------------
# Dashboard
# -------------------------------------------------------
def _dashboard():
    user = current_user()

    # --- Week stats ---
    # Use a fixed Monday→Sunday calendar week so the budget resets
    # every Monday at 00:00 UTC. This was the user-reported bug: the
    # previous rolling 7-day window meant that a Sunday-night grocery
    # run still counted on Monday morning, so the budget never visibly
    # reset.
    sessions = db.get_sessions(user.id)
    week_start_iso = start_of_current_week().isoformat()
    week_sessions = [s for s in sessions if s["created_at"] >= week_start_iso]
    week_spend = sum(s["total"] for s in week_sessions)
    remaining = user.weekly_budget - week_spend
    pct = (week_spend / user.weekly_budget) if user.weekly_budget > 0 else 0

    # Days left in the same calendar week (Monday → 7, Sunday → 1)
    days_left = days_left_in_week()

    # --- Header ---
    first_name = user.name.split(" ")[0]
    st.markdown(f"## Hey, {first_name}! 👋")

    # --- Budget card (remaining changes colour as you eat into the budget) ---
    rem_color = budget_color(pct)

    import base64

    def _tree_image(pct: float) -> str:
        if pct < 0.25:
            path = "static/tree1.png"
        elif pct < 0.50:
            path = "static/tree2.png"
        elif pct < 0.75:
            path = "static/tree3.png"
        else:
            path = "static/tree4.png"
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f"data:image/png;base64,{data}"

    st.markdown(
        f"""
        <div class="budgit-accent">
          <div style="text-align:center; margin-bottom:0.8rem;">
            <img src="app/static/tree{1 if pct < 0.25 else 2 if pct < 0.50 else 3 if pct < 0.75 else 4}.png" 
                 width="120" style="pointer-events:none; user-select:none;">
          </div>
          <div style="color:#7FB5A0; font-size:0.95rem; margin-bottom:0.3rem;">Remaining this week</div>
          <p class="budgit-total" style="color:{rem_color} !important;">€{remaining:,.2f}
            <span style="color:#4A7A6A; font-size:1.1rem;"> / €{user.weekly_budget:,.2f}</span>
          </p>
          <div style="margin: 0.5rem 0;">{budget_pill(pct)}</div>
          <div class="budgit-total-label">{min(pct,1.0)*100:.0f}% of weekly budget used</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(min(pct, 1.0))

    # --- Budget advice ---
    advice = budget_advice(pct, remaining, days_left)
    st.info(advice)

    # --- Breakdown ---
    st.markdown("#### This week at a glance")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spent", f"€{week_spend:,.2f}")
    c2.metric("Remaining", f"€{remaining:,.2f}")
    c3.metric("Shops", len(week_sessions))
    c4.metric("Days left", days_left)

    # --- Daily budget tip ---
    if days_left > 0 and remaining > 0:
        daily_budget = remaining / days_left
        st.markdown(
            f"<div class='budgit-card' style='text-align:center;'>"
            f"💡 You can spend <b style='color:#40B391;'>€{daily_budget:.2f}/day</b> "
            f"for the next {days_left} day{'s' if days_left != 1 else ''} to stay on track."
            f"</div>",
            unsafe_allow_html=True,
        )

    # --- Navigation ---
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("🛒 Shop", type="primary", use_container_width=True):
            st.switch_page("pages/1_🛒_Shop.py")
    with c2:
        if st.button("📝 List", use_container_width=True):
            st.switch_page("pages/0_📝_List.py")
    with c3:
        if st.button("📜 History", use_container_width=True):
            st.switch_page("pages/2_📜_History.py")
    with c4:
        if st.button("📊 Compare", use_container_width=True):
            st.switch_page("pages/3_📊_Compare.py")

    # --- Lifetime stats ---
    st.divider()
    st.markdown("#### All time")

    # Pull lifetime counters used by the savings leaderboard so we
    # can also show the "you've saved €X" headline here. Big number,
    # small effort — strongest motivator on the dashboard.
    lt_saved, lt_could_have, lt_counted = db.get_user_savings_totals(user.id)
    lt_pct = (lt_saved / lt_could_have * 100) if lt_could_have > 0 else 0
    badges = db.get_user_badges(user.id)

    if lt_saved > 0:
        st.markdown(
            f"<div class='budgit-card' style='text-align:center;"
            f" background:linear-gradient(135deg, rgba(64,179,145,0.18), rgba(64,179,145,0.02));"
            f" border:1px solid #40B391;'>"
            f"<div style='color:#7FB5A0; font-size:0.85rem;'>You've saved with Budgit</div>"
            f"<div style='font-size:2.2rem; font-weight:800; color:#40B391; margin:0.2rem 0;'>"
            f"€{lt_saved:,.2f}</div>"
            f"<div style='color:#7FB5A0; font-size:0.78rem;'>"
            f"That's {lt_pct:.1f}% off vs the most expensive store on file"
            f" · across {lt_counted} counted shop{'s' if lt_counted != 1 else ''}"
            f"</div></div>",
            unsafe_allow_html=True,
        )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total sessions", len(sessions))
    c2.metric("Total spent", f"€{sum(s['total'] for s in sessions):,.2f}")
    c3.metric("Products learned", len(db.get_all_products(user.id)))
    c4.metric("Badges earned", len(badges))


# -------------------------------------------------------
# Entry point
# -------------------------------------------------------
if st.session_state.user_id is None:
    _welcome()
else:
    user = current_user()
    if user is not None:
        render_sidebar(user)
    _dashboard()