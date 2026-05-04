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


def compute_streak(user_id: str, weekly_budget: float) -> int:
    """
    Return the user's consecutive-weeks-under-budget streak.

    Walks past completed calendar weeks (Monday → Sunday) backwards
    from last week. A week counts toward the streak if (a) it had
    at least one saved session and (b) the sum of session totals in
    that week was at most `weekly_budget`. The current (in-progress)
    week is intentionally excluded — the streak only credits weeks
    that have actually finished.
    """
    if weekly_budget <= 0:
        return 0

    sessions = db.get_sessions(user_id)
    if not sessions:
        return 0

    # Aggregate session totals by Monday-of-that-week.
    week_totals: dict = {}
    for s in sessions:
        try:
            created = datetime.fromisoformat(s["created_at"])
        except (TypeError, ValueError):
            continue
        monday = (created - timedelta(days=created.weekday())).date()
        week_totals[monday] = week_totals.get(monday, 0.0) + float(s["total"])

    # Walk back from the *previous* Monday.
    today = datetime.utcnow()
    current_monday = (today - timedelta(days=today.weekday())).date()
    week = current_monday - timedelta(days=7)

    streak = 0
    while week in week_totals and week_totals[week] <= weekly_budget:
        streak += 1
        week = week - timedelta(days=7)
    return streak


def render_budget_meter(user) -> None:
    """
    Thin always-visible budget bar shown at the top of every
    authenticated page (except Home, which has its own big card).

    Shows three things: remaining budget for the current calendar
    week (green→yellow→red gradient), days left in the week, and a
    streak chip (🔥 N) when the user has at least one full week of
    under-budget completion in their history.
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

    streak = compute_streak(user.id, user.weekly_budget)
    streak_chip = (
        f"<span style='background:rgba(255,107,91,0.18);"
        f" border:1px solid #FF6B5B; color:#FF8A70;"
        f" border-radius:999px; padding:2px 10px; font-size:0.78rem;"
        f" font-weight:700; margin-right:0.5rem;'>🔥 {streak}</span>"
        if streak > 0 else ""
    )

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
            {streak_chip}
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


def _normalise_entry(entry) -> dict:
    """
    Turn whatever a directory store entry currently looks like into
    the canonical dict shape:
        {"price": float, "size_value": float, "size_unit": str, "brand": str}

    Old entries (from before variants existed) were just a number; we
    treat those as size=1 unit, no brand. New entries are already a
    dict with the four fields.
    """
    if isinstance(entry, (int, float)):
        return {
            "price": float(entry),
            "size_value": 1.0,
            "size_unit": "unit",
            "brand": "",
        }
    return {
        "price":      float(entry.get("price", 0.0)),
        "size_value": float(entry.get("size_value", 1.0)),
        "size_unit":  entry.get("size_unit", "unit"),
        "brand":      entry.get("brand", ""),
    }


def lookup_in_directory(name: str, supermarket: str = None):
    """
    Returns just the price as a float for one store, or a flat
    {store: price} dict when no store is specified, or None if the
    item isn't on file. Backwards-compat shape for code that only
    cares about the headline number.
    """
    ht = get_item_directory()
    result = ht.get(name.lower().strip())
    if result is None:
        return None
    prices = result.get("prices", {})
    if supermarket:
        entry = prices.get(supermarket)
        if entry is None:
            return None
        return _normalise_entry(entry)["price"]
    return {
        s: _normalise_entry(e)["price"]
        for s, e in prices.items()
    }


def lookup_directory_full(name: str, supermarket: str = None):
    """
    Return the full variant info for a product:
      - When `supermarket` is given: a single dict
        {price, size_value, size_unit, brand} or None.
      - Otherwise: {store: {price, size_value, size_unit, brand}}.
    """
    ht = get_item_directory()
    result = ht.get(name.lower().strip())
    if result is None:
        return None
    prices = result.get("prices", {})
    if supermarket:
        entry = prices.get(supermarket)
        return _normalise_entry(entry) if entry is not None else None
    return {s: _normalise_entry(e) for s, e in prices.items()}


def update_directory_in_memory(name: str, price: float, supermarket: str,
                               size_value: float = 1.0,
                               size_unit: str = "unit",
                               brand: str = "") -> None:
    """
    After adding an item, mirror the change in the in-memory directory
    so subsequent same-render lookups see the new value without
    re-reading Firestore.
    """
    ht = get_item_directory()
    key = name.lower().strip()
    existing = ht.get(key)

    new_entry = {
        "price":      round(float(price), 2),
        "size_value": float(size_value),
        "size_unit":  size_unit,
        "brand":      brand,
    }
    if existing:
        existing["prices"][supermarket] = new_entry
        existing["times_added"] = existing.get("times_added", 0) + 1
        ht.put(key, existing)
    else:
        ht.put(key, {
            "prices": {supermarket: new_entry},
            "times_added": 1,
        })
