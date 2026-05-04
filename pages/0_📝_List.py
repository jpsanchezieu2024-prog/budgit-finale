"""
Budgit — Grocery List page.

Build your shopping list before you go.
Budgit checks the global price directory and tells you
which supermarket is cheapest for your whole basket.
"""

import streamlit as st

import database as db
from state import init_state, require_login, SUPERMARKETS, get_item_directory, render_sidebar
from theme import apply_theme, PRIMARY


st.set_page_config(page_title="Budgit — Grocery List", page_icon="📝", layout="centered")
apply_theme()
init_state()
user = require_login()
render_sidebar(user)

st.markdown("### 📝 Grocery List")
st.caption("Build your list and we'll tell you where to shop.")

# Load saved list from Firestore.
# Track which user the list belongs to — reload if a different user logs in.
if "grocery_items" not in st.session_state or \
        st.session_state.get("grocery_list_user") != user.id:
    st.session_state.grocery_items = db.get_grocery_list(user.id)
    st.session_state.grocery_list_user = user.id

items = st.session_state.grocery_items


# -------------------------------------------------------
# Add item to list
# -------------------------------------------------------
st.markdown("#### Add to list")
with st.form("add_to_list", clear_on_submit=True):
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        new_name = st.text_input("Item name", placeholder="e.g. pasta, chicken, yogurt")
    with col2:
        new_qty = st.number_input("Qty", min_value=1, value=1, step=1)
    with col3:
        st.markdown("<div style='margin-top:1.8rem;'></div>", unsafe_allow_html=True)
        add = st.form_submit_button("Add", type="primary", use_container_width=True)

    if add and new_name.strip():
        # Check if already in list
        existing = next((i for i in items if i["name"] == new_name.lower().strip()), None)
        if existing:
            existing["qty"] += new_qty
        else:
            items.append({"name": new_name.lower().strip(), "qty": new_qty})
        db.save_grocery_list(user.id, items)
        st.rerun()


# -------------------------------------------------------
# Current list
# -------------------------------------------------------
if not items:
    st.info("Your list is empty. Add some items above to get started!")
    st.stop()

st.markdown(f"#### Your list ({len(items)} items)")

to_remove = []
for i, item in enumerate(items):
    c1, c2, c3 = st.columns([4, 1, 1])
    c1.markdown(
        f"<div style='padding-top:0.5rem;'><b>{item['name'].title()}</b></div>",
        unsafe_allow_html=True,
    )
    new_qty = c2.number_input(
        "Qty", min_value=1, value=item["qty"], step=1,
        key=f"list_qty_{i}", label_visibility="collapsed"
    )
    if new_qty != item["qty"]:
        items[i]["qty"] = new_qty
        db.save_grocery_list(user.id, items)
        st.rerun()

    if c3.button("❌", key=f"list_rm_{i}", help="Remove"):
        to_remove.append(i)

if to_remove:
    st.session_state.grocery_items = [
        item for j, item in enumerate(items) if j not in to_remove
    ]
    db.save_grocery_list(user.id, st.session_state.grocery_items)
    st.rerun()


# -------------------------------------------------------
# Supermarket comparison
#
# For each item in the list, look up its latest price at
# every supermarket using the global Hash Table (O(1) each).
# Then total up per store to find the cheapest basket.
# -------------------------------------------------------
st.divider()
st.markdown("#### 🏆 Where should you shop?")
st.caption("Based on the latest prices logged by all Budgit users.")

ht = get_item_directory()

# Build a price table: store -> total cost
store_totals = {store: 0.0 for store in SUPERMARKETS}
store_coverage = {store: 0 for store in SUPERMARKETS}  # how many items have a price
missing_items = []

item_rows = []  # for the detailed table below

for item in items:
    key = item["name"].lower().strip()
    result = ht.get(key)
    prices = result.get("prices", {}) if result else {}
    qty = item["qty"]

    row = {"name": item["name"].title(), "qty": qty, "prices": {}}

    if not prices:
        missing_items.append(item["name"].title())
    else:
        for store in SUPERMARKETS:
            if store in prices:
                cost = prices[store] * qty
                store_totals[store] += cost
                store_coverage[store] += 1
                row["prices"][store] = prices[store]

    item_rows.append(row)

# Only rank stores that have at least one price
ranked = [
    (store, total)
    for store, total in store_totals.items()
    if store_coverage[store] > 0
]
ranked.sort(key=lambda x: x[1])

if not ranked:
    st.warning(
        "No price data found yet for these items. "
        "Start shopping and Budgit will learn prices automatically!"
    )
else:
    # Winner banner
    cheapest_store, cheapest_total = ranked[0]
    coverage_count = store_coverage[cheapest_store]
    total_items = len(items)

    st.markdown(
        f"""
        <div class="budgit-accent" style="margin-bottom:1rem;">
          <div style="font-size:2.5rem;">🏆</div>
          <div style="color:#7FB5A0; font-size:0.9rem;">Cheapest for your basket</div>
          <div style="font-size:1.8rem; font-weight:800; color:#40B391; margin:0.3rem 0;">
            {cheapest_store}
          </div>
          <div style="font-size:1.3rem; font-weight:600;">~€{cheapest_total:.2f}</div>
          <div style="color:#7FB5A0; font-size:0.8rem; margin-top:0.3rem;">
            based on {coverage_count}/{total_items} items with known prices
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # All stores ranked
    st.markdown("**All stores:**")
    for rank, (store, total) in enumerate(ranked):
        is_best = rank == 0
        saving = total - cheapest_total if not is_best else 0
        badge = "🥇" if rank == 0 else "🥈" if rank == 1 else "🥉" if rank == 2 else "  "
        extra = f" (+€{saving:.2f})" if saving > 0 else ""
        cov = store_coverage[store]
        st.markdown(
            f"<div class='budgit-item'>"
            f"<div><b>{badge} {store}</b>"
            f"<br><span style='color:#7FB5A0; font-size:0.8rem;'>"
            f"{cov}/{total_items} items tracked</span></div>"
            f"<div style='font-weight:700; color:{'#40B391' if is_best else '#E8F5EF'};'>"
            f"€{total:.2f}<span style='color:#7FB5A0; font-size:0.8rem;'>{extra}</span>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

    # Per-item price breakdown
    st.divider()
    st.markdown("**Price breakdown by item:**")
    for row in item_rows:
        if not row["prices"]:
            st.markdown(
                f"<div class='budgit-item'>"
                f"<span>{row['name']} ×{row['qty']}</span>"
                f"<span style='color:#7FB5A0; font-size:0.8rem;'>No data yet</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            best_store = min(row["prices"], key=row["prices"].get)
            prices_text = " · ".join(
                f"<b style='color:#40B391;'>{s}: €{p:.2f}</b>"
                if s == best_store
                else f"{s}: €{p:.2f}"
                for s, p in sorted(row["prices"].items())
            )
            st.markdown(
                f"<div class='budgit-item'>"
                f"<div><b>{row['name']}</b> ×{row['qty']}</div>"
                f"<div style='font-size:0.82rem; color:#7FB5A0;'>{prices_text}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    if missing_items:
        st.caption(f"⚠️ No price data yet for: {', '.join(missing_items)}. "
                   "These aren't included in store totals.")

# -------------------------------------------------------
# Send list to cart
# -------------------------------------------------------
st.divider()
if ranked and st.button(f"🛒 Start shopping at {ranked[0][0]}", type="primary", use_container_width=True):
    st.session_state.shop_store = ranked[0][0]
    st.switch_page("pages/1_🛒_Shop.py")