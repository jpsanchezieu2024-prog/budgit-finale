"""
Budgit — session state helpers.

Manages everything stored across Streamlit reruns:
    - logged-in user
    - live cart
    - BST for autocomplete
    - Hash Table for global item directory (latest price per supermarket)
"""

import streamlit as st

import database as db
from models import Cart, User
from algorithms.bst import BST
from algorithms.hash_table import HashTable

SUPERMARKETS = ["Mercadona", "Lidl", "Carrefour", "Dia", "Aldi", "Alcampo"]


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
