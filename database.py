"""
Budgit — Firebase Firestore database layer.

Collections:
    users/            -> one document per user
    products/         -> per-user price memory
    sessions/         -> one completed shop per document
    session_items/    -> items inside each session
    item_directory/   -> GLOBAL catalogue: latest price per supermarket
    grocery_lists/    -> per-user saved grocery lists
"""

import hashlib
import os
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, firestore


def _load_firebase_credentials():
    """
    Load Firebase service-account credentials from whatever source is
    available, in priority order:

      1. `st.secrets["firebase"]` — used on Streamlit Community Cloud
         (or anywhere Streamlit secrets are configured). The whole
         service-account JSON is stored as a [firebase] TOML table in
         the app's Secrets settings.
      2. Environment variable `FIREBASE_KEY_JSON` — useful for
         non-Streamlit hosts (Render, Railway, Fly, etc.) where the
         JSON is provided as a single env var.
      3. Local file `firebase_key.json` next to this script — local
         development fallback. This file is in .gitignore and must
         never be committed to a public repository.
    """
    # 1. Streamlit secrets (production on Streamlit Cloud)
    secrets_problem = None
    try:
        import streamlit as st  # type: ignore
    except ImportError:
        st = None

    if st is not None:
        try:
            # Touching st.secrets raises if there's no secrets.toml
            # or if the file is malformed. Treat both as "not set".
            if "firebase" in st.secrets:
                return credentials.Certificate(dict(st.secrets["firebase"]))
        except Exception as e:
            secrets_problem = e  # remember to surface in the final error

    # 2. Single environment variable holding the JSON blob
    raw = os.environ.get("FIREBASE_KEY_JSON")
    if raw:
        import json
        return credentials.Certificate(json.loads(raw))

    # 3. Local file (development) — only attempt if it actually exists,
    #    so deployments don't crash with a misleading FileNotFoundError.
    if os.path.exists("firebase_key.json"):
        return credentials.Certificate("firebase_key.json")

    # Nothing worked. Raise a clear, actionable error instead of letting
    # firebase_admin crash with a generic FileNotFoundError.
    hint = (
        "No Firebase credentials were found.\n\n"
        "On Streamlit Cloud: open Manage app → Settings → Secrets and add "
        "your service-account JSON as a [firebase] TOML table. After "
        "saving, the app reboots automatically.\n\n"
        "On other hosts: set the FIREBASE_KEY_JSON environment variable "
        "to the contents of your service-account JSON.\n\n"
        "For local development: place firebase_key.json next to "
        "database.py (it's already in .gitignore)."
    )
    if secrets_problem is not None:
        hint += f"\n\nWhile reading st.secrets we got: {secrets_problem!r}"
    raise RuntimeError(hint)


# Connect to Firebase once
if not firebase_admin._apps:
    firebase_admin.initialize_app(
        _load_firebase_credentials(),
        {"projectId": "budgit-b0281"},
    )

db = firestore.client()


# -------------------------------------------------------
# Password helpers
# -------------------------------------------------------
def hash_password(password: str, salt: str = None):
    if salt is None:
        salt = os.urandom(16).hex()
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return hashed, salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    hashed, _ = hash_password(password, salt)
    return hashed == stored_hash


def init_db():
    pass  # Firestore creates collections automatically


# -------------------------------------------------------
# USER functions
# -------------------------------------------------------
def create_user(name, email, password, weekly_budget=0.0, preferred_store=""):
    pw_hash, salt = hash_password(password)
    _, doc_ref = db.collection("users").add({
        "name": name,
        "email": email.lower().strip(),
        "password_hash": pw_hash,
        "salt": salt,
        "weekly_budget": float(weekly_budget),
        "preferred_store": preferred_store,
    })
    return doc_ref.id


def get_user_by_email(email):
    results = (
        db.collection("users")
        .where("email", "==", email.lower().strip())
        .limit(1).stream()
    )
    for doc in results:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    return None


def get_user(user_id):
    doc = db.collection("users").document(user_id).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    return None


def update_user_profile(user_id, weekly_budget=None, preferred_store=None, name=None):
    updates = {}
    if weekly_budget is not None:
        updates["weekly_budget"] = float(weekly_budget)
    if preferred_store is not None:
        updates["preferred_store"] = preferred_store
    if name is not None:
        updates["name"] = name
    if updates:
        db.collection("users").document(user_id).update(updates)


# -------------------------------------------------------
# PRODUCT functions (per-user price memory)
# -------------------------------------------------------
def upsert_product(user_id, name, price, supermarket,
                   size_value: float = 1.0, size_unit: str = "unit",
                   brand: str = ""):
    doc_id = f"{user_id}_{name.lower().strip()}_{supermarket}"
    db.collection("products").document(doc_id).set({
        "user_id": user_id,
        "name": name.lower().strip(),
        "price": float(price),
        "supermarket": supermarket,
        "size_value": float(size_value),
        "size_unit": size_unit,
        "brand": brand,
        "updated_at": datetime.utcnow().isoformat(),
    })


def lookup_product_price(user_id, name, supermarket):
    doc_id = f"{user_id}_{name.lower().strip()}_{supermarket}"
    doc = db.collection("products").document(doc_id).get()
    if doc.exists:
        return doc.to_dict()["price"]
    return None


def get_all_products(user_id):
    docs = db.collection("products").where("user_id", "==", user_id).stream()
    products = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        products.append(data)
    products.sort(key=lambda p: p["name"])
    return products


# -------------------------------------------------------
# GLOBAL ITEM DIRECTORY
#
# Stores the LATEST price paid per product per supermarket.
# Document ID: normalised product name (e.g. "milk")
# Inside the document, prices are stored per supermarket:
#   { "name": "milk", "prices": { "Mercadona": 0.89, "Lidl": 0.75 }, ... }
#
# This way when someone types "milk" at Mercadona, they get
# the latest price anyone paid for milk at Mercadona.
# -------------------------------------------------------
def add_to_directory(name: str, price: float, supermarket: str,
                     size_value: float = 1.0, size_unit: str = "unit",
                     brand: str = ""):
    """
    Update the global directory with the latest price for this product
    at this supermarket.

    Each store entry is stored as a dict so we can carry size + brand
    alongside the price:

        prices = {
          "Mercadona": {"price": 0.89, "size_value": 1, "size_unit": "L", "brand": "Pascual"},
          "Lidl":      {"price": 0.50, "size_value": 0.5, "size_unit": "L", "brand": "Milbona"},
        }

    Old entries that were just floats (`prices["Mercadona"] = 0.89`)
    are still readable — the parser in state.py treats them as
    `size_value=1, size_unit="unit", brand=""`.
    """
    key = name.lower().strip()
    doc_ref = db.collection("item_directory").document(key)
    doc = doc_ref.get()
    now = datetime.utcnow().isoformat()

    new_entry = {
        "price":      round(float(price), 2),
        "size_value": float(size_value),
        "size_unit":  size_unit,
        "brand":      brand,
    }

    if doc.exists:
        data = doc.to_dict()
        prices = data.get("prices", {})
        prices[supermarket] = new_entry
        doc_ref.update({
            "prices": prices,
            "last_updated": now,
            "times_added": data.get("times_added", 0) + 1,
        })
    else:
        doc_ref.set({
            "name": key,
            "prices": {supermarket: new_entry},
            "last_updated": now,
            "times_added": 1,
        })


def get_full_directory() -> list:
    """
    Load all products from the global directory.
    Called once on login — stored in a Hash Table in memory.
    """
    docs = db.collection("item_directory").stream()
    items = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        items.append(data)
    return items


# -------------------------------------------------------
# SESSION functions
# -------------------------------------------------------
def save_session(user_id, supermarket, items, total, directory=None):
    """
    Persist a completed shopping session.

    If `directory` (the in-memory global HashTable) is provided, we also
    bump the user's lifetime savings counters used by the leaderboard.
    Passing it explicitly keeps this module free of any dependency on
    Streamlit session state.
    """
    now = datetime.utcnow().isoformat()
    _, session_ref = db.collection("sessions").add({
        "user_id": user_id,
        "supermarket": supermarket,
        "total": float(total),
        "created_at": now,
    })
    for item in items:
        db.collection("session_items").add({
            "session_id":  session_ref.id,
            "name":        item["name"],
            "price":       float(item["price"]),
            "qty":         int(item.get("qty", 1)),
            "size_value":  float(item.get("size_value", 1.0)),
            "size_unit":   item.get("size_unit", "unit"),
            "brand":       item.get("brand", ""),
        })

    # Update the leaderboard counters for this user.
    if directory is not None:
        from algorithms.leaderboard import compute_session_savings
        saved, could_have = compute_session_savings(items, directory)
        if could_have > 0:
            increment_user_savings(user_id, saved, could_have)

    return session_ref.id


def get_sessions(user_id):
    docs = db.collection("sessions").where("user_id", "==", user_id).stream()
    sessions = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        sessions.append(data)
    sessions.sort(key=lambda s: s["created_at"], reverse=True)
    return sessions


def get_session_items(session_id):
    docs = db.collection("session_items").where("session_id", "==", session_id).stream()
    items = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        items.append(data)
    return items


def get_user_top_items(user_id: str, limit: int = 6) -> list[tuple]:
    """
    Return the user's most-purchased items by total quantity across
    every saved session, as a list of (name, total_qty) tuples sorted
    descending by quantity.

    Used by the Shop page to render quick-add chips for the user's
    favourite items. The result is cached in session state by
    `state.get_top_items_cached`, so this is only computed once per
    login (or after a session is saved, which invalidates the cache).
    """
    counter: dict[str, int] = {}
    for s in get_sessions(user_id):
        for it in get_session_items(s["id"]):
            name = it["name"].lower().strip()
            counter[name] = counter.get(name, 0) + int(it.get("qty", 1))
    return sorted(counter.items(), key=lambda kv: -kv[1])[:limit]


# -------------------------------------------------------
# GROCERY LIST functions
#
# Users build a list of items they need to buy.
# The app then checks the global directory to find
# which supermarket is cheapest for the full basket.
# -------------------------------------------------------
def save_grocery_list(user_id: str, items: list):
    """
    Save or overwrite the user's current grocery list.
    items = [{"name": "milk", "qty": 2}, ...]
    """
    db.collection("grocery_lists").document(user_id).set({
        "user_id": user_id,
        "items": items,
        "updated_at": datetime.utcnow().isoformat(),
    })


def get_grocery_list(user_id: str) -> list:
    """Return the user's saved grocery list, or empty list."""
    doc = db.collection("grocery_lists").document(user_id).get()
    if doc.exists:
        return doc.to_dict().get("items", [])
    return []


# -------------------------------------------------------
# LEADERBOARD — lifetime savings counters per user.
#
# Three denormalised fields live on each user doc:
#   lifetime_saved              € saved across all counted sessions
#   lifetime_could_have_spent   € the same baskets would have cost at
#                               the most expensive store seen for each
#                               item (the baseline)
#   lifetime_sessions_counted   number of sessions that contributed
#                               (i.e. had at least one item with a
#                               cross-store price comparison available)
#
# Percent saved = lifetime_saved / lifetime_could_have_spent.
# -------------------------------------------------------
def increment_user_savings(user_id: str, saved: float, could_have: float) -> None:
    """
    Atomically add to the three lifetime savings counters on the user
    doc. Called from `save_session` whenever a session completes with
    at least one comparable item.
    """
    if could_have <= 0:
        return
    db.collection("users").document(user_id).update({
        "lifetime_saved":            firestore.Increment(round(saved, 2)),
        "lifetime_could_have_spent": firestore.Increment(round(could_have, 2)),
        "lifetime_sessions_counted": firestore.Increment(1),
    })


def get_user_savings_totals(user_id: str) -> tuple[float, float, int]:
    """Return (saved, could_have_spent, sessions_counted) for a user."""
    doc = db.collection("users").document(user_id).get()
    if not doc.exists:
        return 0.0, 0.0, 0
    u = doc.to_dict()
    return (
        float(u.get("lifetime_saved", 0.0)),
        float(u.get("lifetime_could_have_spent", 0.0)),
        int(u.get("lifetime_sessions_counted", 0)),
    )


def backfill_user_savings(user_id: str, directory) -> None:
    """
    One-shot recomputation of a user's lifetime savings from scratch.

    Walks every saved session, looks up each item's max cross-store
    price in the supplied global directory (HashTable), and writes the
    summed counters back to the user doc. Called lazily the first time
    a user is encountered without their lifetime fields populated, so
    existing accounts get migrated transparently.
    """
    from algorithms.leaderboard import compute_session_savings

    sessions = get_sessions(user_id)
    total_saved = 0.0
    total_could_have = 0.0
    counted = 0

    for s in sessions:
        items = get_session_items(s["id"])
        saved, could_have = compute_session_savings(items, directory)
        if could_have > 0:
            total_saved += saved
            total_could_have += could_have
            counted += 1

    db.collection("users").document(user_id).update({
        "lifetime_saved":            round(total_saved, 2),
        "lifetime_could_have_spent": round(total_could_have, 2),
        "lifetime_sessions_counted": counted,
    })


# -------------------------------------------------------
# BADGES — passive achievements awarded on milestones.
#
# Each user document carries a `badges` array of badge IDs. Awarding
# is idempotent: re-running the milestone checks never duplicates.
# The Profile page reads this array to render the user's wall of
# achievements; the Shop page surfaces newly-earned ones as toasts.
# -------------------------------------------------------
BADGES: dict[str, dict] = {
    "first_shop":          {"emoji": "🛒", "name": "First shop",        "desc": "Saved your first shopping session."},
    "10_sessions":         {"emoji": "📜", "name": "Regular",            "desc": "Completed 10 shopping sessions."},
    "all_stores":          {"emoji": "🏪", "name": "Explorer",           "desc": "Shopped at all 6 supermarkets."},
    "saved_50":            {"emoji": "💰", "name": "Saver — €50",        "desc": "Saved €50 with Budgit."},
    "saved_100":           {"emoji": "💵", "name": "Saver — €100",       "desc": "Saved €100 with Budgit."},
    "saved_500":           {"emoji": "💸", "name": "Big saver — €500",   "desc": "Saved €500 with Budgit."},
    "greedy_used":         {"emoji": "⚡", "name": "Greedy",             "desc": "Used Greedy budget rescue."},
    "knapsack_used":       {"emoji": "🧠", "name": "Optimal",            "desc": "Used 0/1 Knapsack budget rescue."},
    "streak_4":            {"emoji": "🔥", "name": "4-week streak",      "desc": "Stayed under budget 4 weeks in a row."},
    "first_quick_add":     {"emoji": "⚡", "name": "Quick adder",        "desc": "Used your first quick-add chip."},
    "first_import":        {"emoji": "📝", "name": "List importer",     "desc": "Imported a grocery list into your cart."},
    "week_under_budget":   {"emoji": "✅", "name": "Under budget",      "desc": "Finished a week under your weekly budget."},
}


def get_user_badges(user_id: str) -> list[str]:
    doc = db.collection("users").document(user_id).get()
    if not doc.exists:
        return []
    return list(doc.to_dict().get("badges", []))


def award_badge(user_id: str, badge_id: str) -> bool:
    """
    Idempotent badge award. Returns True if the badge was just earned
    (i.e. wasn't on the user before this call), False otherwise. The
    Shop page uses this to know when to show the milestone toast.
    """
    if badge_id not in BADGES:
        return False
    ref = db.collection("users").document(user_id)
    snap = ref.get()
    if not snap.exists:
        return False
    earned = list(snap.to_dict().get("badges", []))
    if badge_id in earned:
        return False
    earned.append(badge_id)
    ref.update({"badges": earned})
    return True


def check_session_milestones(user_id: str) -> list[str]:
    """
    Run after a session is saved. Returns a list of badge IDs that
    were *newly earned* by this save (so the caller can toast them).

    Cheap to call: one users-doc read + one sessions read. Skipped
    badges that depend on user input (greedy/knapsack/quick-add/import)
    are awarded directly from the relevant button handlers, not here.
    """
    snap = db.collection("users").document(user_id).get()
    if not snap.exists:
        return []
    user = snap.to_dict()
    earned = set(user.get("badges", []))
    sessions = get_sessions(user_id)
    newly: list[str] = []

    def _try(badge_id: str, condition: bool):
        if condition and badge_id not in earned:
            if award_badge(user_id, badge_id):
                newly.append(badge_id)
                earned.add(badge_id)

    _try("first_shop",  len(sessions) >= 1)
    _try("10_sessions", len(sessions) >= 10)
    _try("all_stores",  len({s.get("supermarket") for s in sessions}) >= 6)

    saved = float(user.get("lifetime_saved", 0.0))
    _try("saved_50",  saved >= 50)
    _try("saved_100", saved >= 100)
    _try("saved_500", saved >= 500)

    return newly


def get_leaderboard_users(directory, min_sessions: int = 3) -> list[dict]:
    """
    Read all users, lazy-backfill any missing lifetime counters, and
    return a list of qualifying candidates ready for ranking.

    A user qualifies if they've completed at least `min_sessions`
    *counted* sessions (i.e. sessions that had at least one cross-store
    comparison available).

    Each returned dict contains:
        id, name, saved, could_have, sessions, pct
    """
    docs = list(db.collection("users").stream())
    candidates = []

    for doc in docs:
        u = doc.to_dict() or {}
        uid = doc.id

        # Lazy backfill: existing users from before the leaderboard
        # feature shipped won't have these fields yet.
        if "lifetime_sessions_counted" not in u:
            backfill_user_savings(uid, directory)
            refreshed = db.collection("users").document(uid).get().to_dict() or {}
            u = refreshed

        sessions = int(u.get("lifetime_sessions_counted", 0))
        if sessions < min_sessions:
            continue

        could_have = float(u.get("lifetime_could_have_spent", 0.0))
        if could_have <= 0:
            continue
        saved = float(u.get("lifetime_saved", 0.0))
        pct = (saved / could_have) * 100.0

        candidates.append({
            "id":         uid,
            "name":       u.get("name", "Anonymous"),
            "saved":      round(saved, 2),
            "could_have": round(could_have, 2),
            "sessions":   sessions,
            "pct":        round(pct, 1),
        })

    return candidates
