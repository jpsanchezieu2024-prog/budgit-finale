"""
Budgit — session state helpers.

Manages everything stored across Streamlit reruns:
    - logged-in user
    - live cart
    - BST for autocomplete
    - Hash Table for global item directory (latest price per supermarket)
"""

from datetime import datetime, timedelta

import streamlit as st

import database as db
from models import Cart, User
from algorithms.bst import BST
from algorithms.hash_table import HashTable

SUPERMARKETS = ["Mercadona", "Lidl", "Carrefour", "Dia", "Aldi", "Alcampo"]


# ---------------------------------------------------------------------
# Calendar-week boundaries.
#
# Budgit's weekly budget runs on a fixed Monday 00:00 → Sunday 23:59 UTC
# cycle. Using a calendar week (instead of a rolling 7-day window) means:
#   - The budget visibly *resets* every Monday morning, which is what
#     users intuitively expect.
#   - Sunday-night spending no longer "follows you into Monday".
#   - "Days left" and "this week's spending" use the same definition of
#     a week, so the dashboard is internally consistent.
# ---------------------------------------------------------------------
def start_of_current_week() -> datetime:
    """Return Monday 00:00 UTC of the current calendar week."""
    today = datetime.utcnow()
    monday_date = (today - timedelta(days=today.weekday())).date()
    return datetime(monday_date.year, monday_date.month, monday_date.day)


def days_left_in_week() -> int:
    """
    How many days remain in the current calendar week, including today.
    Monday → 7, Tuesday → 6, …, Sunday → 1.
    """
    return 7 - datetime.utcnow().weekday()


def init_state():
    """Set default session state on first load."""
    db.init_db()
    if "cart" not in st.session_state:
        st.session_state.cart = Cart()
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "shop_store" not in st.session_state:
        st.session_state.shop_store = None
    if "bst" not in st.session_state:
        st.session_state.bst = None
    if "item_directory_ht" not in st.session_state:
        st.session_state.item_directory_ht = None


def current_user():
    if not st.session_state.get("user_id"):
        return None
    row = db.get_user(st.session_state.user_id)
    return User.from_row(row) if row else None


def require_login():
    user = current_user()
    if user is None:
        st.warning("Please log in from the Home page first.")
        st.stop()
    return user


# Keys that belong to a logged-in user. Cleared on logout so two
# different users sharing the same browser tab can never see each
# other's cart, BST, or grocery list.
_USER_SCOPED_KEYS = (
    "user_id", "cart", "bst", "shop_store", "item_directory_ht",
    "grocery_items", "grocery_list_user", "first_time_user",
    "last_typed_name", "item_name", "session_just_saved",
)


def render_sidebar(user) -> None:
    """
    Standard sidebar shown on every authenticated page: user identity,
    quick links, and a log-out button. Streamlit's auto-page navigation
    already lists all the pages above this; we add identity + actions.
    """
    with st.sidebar:
        st.markdown(f"**👤 {user.name}**")
        st.caption(user.email)
        st.caption(f"🏬 {user.preferred_store or '—'}")
        st.divider()
        if st.button("🚪 Log out", use_container_width=True,
                     key=f"sidebar_logout_{user.id}"):
            for k in _USER_SCOPED_KEYS:
                st.session_state.pop(k, None)
            st.switch_page("🏠_Home.py")


def render_budget_meter(user) -> None:
    """
    Thin always-visible budget bar shown at the top of every
    authenticated page (except Home, which has its own big card).

    The bar shows "remaining this calendar week" budget with a colour
    that fades from green through yellow to red as the budget is
    consumed, plus the number of days left in the week. Anywhere in
    the app, the user can glance up and instantly answer "how much do
    I have left?" — that's the single biggest UX win in v1.
    """
    from theme import budget_color  # local import avoids circular

    week_start_iso = start_of_current_week().isoformat()
    sessions = db.get_sessions(user.id)
    spent = sum(
        s["total"] for s in sessions
        if s["created_at"] >= week_start_iso
    )
    remaining = user.weekly_budget - spent
    pct = (spent / user.weekly_budget) if user.weekly_budget > 0 else 0
    days = days_left_in_week()
    color = budget_color(pct)

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(90deg, {color}26, transparent 70%);
            border-left: 4px solid {color};
            border-radius: 0 8px 8px 0;
            padding: 0.55rem 1rem;
            margin: 0 0 1rem 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.92rem;
        ">
          <span style="color:#7FB5A0;">Remaining this week</span>
          <span>
            <b style="color:{color}; font-size:1.15rem;">€{remaining:,.2f}</b>
            <span style="color:#7FB5A0; font-size:0.78rem; margin-left:0.6rem;">
              · {days} day{'s' if days != 1 else ''} left
            </span>
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_top_items_cached(user_id: str, limit: int = 6) -> list[tuple]:
    """
    Cached accessor for the user's most-bought items.

    First call hits Firestore via `db.get_user_top_items`; subsequent
    calls within the same session reuse the cached list. The cache is
    invalidated by clearing `st.session_state.top_items`, which the
    Shop page does after saving a session.
    """
    if "top_items" not in st.session_state:
        st.session_state.top_items = db.get_user_top_items(user_id, limit=limit)
    return st.session_state.top_items


def rebuild_bst(user_id: str) -> BST:
    """Load all learned product names into a BST for autocomplete."""
    tree = BST()
    for row in db.get_all_products(user_id):
        tree.insert(row["name"], row["price"])
    st.session_state.bst = tree
    return tree


def get_bst(user_id: str) -> BST:
    if st.session_state.get("bst") is None:
        return rebuild_bst(user_id)
    return st.session_state.bst


def load_item_directory() -> HashTable:
    """
    Fetch the global item directory from Firestore and store it
    in a Hash Table in memory.

    Structure of each entry:
        key   -> product name (e.g. "milk")
        value -> { "prices": { "Mercadona": 0.89, "Lidl": 0.75 }, ... }

    Called once on login. All subsequent price lookups are O(1).
    """
    ht = HashTable()
    for item in db.get_full_directory():
        ht.put(item["name"], {
            "prices": item.get("prices", {}),
            "times_added": item.get("times_added", 0),
        })
    st.session_state.item_directory_ht = ht
    return ht


def get_item_directory() -> HashTable:
    if st.session_state.get("item_directory_ht") is None:
        return load_item_directory()
    return st.session_state.item_directory_ht


def lookup_in_directory(name: str, supermarket: str = None):
    """
    Look up the latest price for a product in the global Hash Table.
    - If supermarket is given: returns the latest price at that store.
    - If not: returns a dict of all known prices across stores.
    Returns None if not found.
    """
    ht = get_item_directory()
    result = ht.get(name.lower().strip())
    if result is None:
        return None
    prices = result.get("prices", {})
    if supermarket:
        return prices.get(supermarket)  # Latest price at this store
    return prices  # All store prices


def update_directory_in_memory(name: str, price: float, supermarket: str):
    """
    After adding an item, update the Hash Table immediately
    so the change is reflected without reloading from Firestore.
    """
    ht = get_item_directory()
    key = name.lower().strip()
    existing = ht.get(key)

    if existing:
        existing["prices"][supermarket] = round(price, 2)
        existing["times_added"] = existing.get("times_added", 0) + 1
        ht.put(key, existing)
    else:
        ht.put(key, {
            "prices": {supermarket: round(price, 2)},
            "times_added": 1,
        })
