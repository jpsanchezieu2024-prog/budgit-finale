"""
Budgit — Supermarket comparison page.

Two sections:

    1. 💰 Savings leaderboard
       Ranks every Budgit user by lifetime % saved (€ saved ÷ € the
       same baskets would have cost at the most expensive store on
       file). Top 10 extracted with the Max-Heap Priority Queue
       (algorithms/priority_queue.py); the full ordering uses Merge
       Sort (algorithms/sorting.py) to find the current user's rank.

    2. Global product prices
       Per-item, side-by-side prices across supermarkets, pulled
       directly from the in-memory global Hash Table directory.
"""

import streamlit as st

import database as db
from state import (
    init_state, require_login, get_item_directory, SUPERMARKETS,
    render_sidebar, render_budget_meter,
)
from theme import apply_theme, PRIMARY
from algorithms.leaderboard import rank_savers, display_name


st.set_page_config(page_title="Budgit — Compare", page_icon="📊", layout="centered")
apply_theme()
init_state()
user = require_login()
render_sidebar(user)
render_budget_meter(user)

st.markdown("### 📊 Price comparison")

# Refresh button — reloads global directory from Firestore
col1, col2 = st.columns([4, 1])
with col1:
    st.caption("Prices update as users shop. Hit refresh to see the latest.")
with col2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.session_state.item_directory_ht = None  # force reload
        st.rerun()


# -------------------------------------------------------
# 1. Savings leaderboard
#
# Ranks users by % of money saved across all their lifetime sessions
# (compared with the most expensive store on file for each item).
# Top-K is extracted with a Max-Heap Priority Queue; the full ranking
# uses Merge Sort so we can find the current user's rank when they're
# outside the top 10.
# -------------------------------------------------------
st.markdown("#### 💰 Savings leaderboard")
st.caption(
    "Ranked by % of money saved by shopping at the cheaper supermarket, "
    "across every shop you've completed. Need at least 3 counted shops to qualify."
)

# Pull every user's lifetime counters (lazy-backfilled the first time).
directory = get_item_directory()
candidates = db.get_leaderboard_users(directory, min_sessions=3)

if not candidates:
    st.info(
        "No one's qualified for the leaderboard yet — keep shopping and "
        "you'll be the first one up there!"
    )
else:
    top, full = rank_savers(candidates, top_k=10)

    # Render the top 10
    for rank, c in enumerate(full[:len(top)], start=1):
        # `top` is the heap-sorted slice; `full` is the merge-sorted list.
        # They agree on the top K but `full` keeps a stable order for
        # rank lookup below. Prefer `full` for display so rank numbers
        # match across the page.
        is_me = c["id"] == user.id
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"

        bg = "rgba(64,179,145,0.18)" if is_me else "rgba(255,255,255,0.02)"
        border = PRIMARY if is_me else "#2A3D34"
        you_tag = " <span style='color:#40B391; font-weight:700;'>(you)</span>" if is_me else ""

        st.markdown(
            f"<div style='background:{bg}; border:1px solid {border};"
            f" border-radius:12px; padding:0.8rem 1rem; margin-bottom:0.45rem;"
            f" display:flex; justify-content:space-between; align-items:center;'>"
            f"<div>"
            f"  <span style='font-size:1.15rem; margin-right:0.55rem; min-width:2.2rem; display:inline-block;'>{medal}</span>"
            f"  <b style='font-size:1.05rem;'>{display_name(c['name'])}</b>{you_tag}"
            f"  <br>"
            f"  <span style='color:#7FB5A0; font-size:0.78rem; margin-left:2.75rem;'>"
            f"     {c['sessions']} shop{'s' if c['sessions'] != 1 else ''}"
            f"     · €{c['saved']:.2f} saved of €{c['could_have']:.2f} possible"
            f"  </span>"
            f"</div>"
            f"<div style='font-size:1.6rem; font-weight:800; color:#40B391;'>"
            f"  {c['pct']:.1f}%"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Show the current user's rank explicitly when they're outside top 10.
    top_ids = {c["id"] for c in full[:len(top)]}
    me = next((c for c in full if c["id"] == user.id), None)
    if me is not None and me["id"] not in top_ids:
        my_rank = next(i + 1 for i, c in enumerate(full) if c["id"] == user.id)
        st.markdown(
            f"<div style='background:rgba(64,179,145,0.12);"
            f" border:1px dashed {PRIMARY}; border-radius:12px;"
            f" padding:0.7rem 1rem; margin-top:0.6rem;"
            f" display:flex; justify-content:space-between; align-items:center;'>"
            f"<div><b>You — #{my_rank}</b>"
            f" <span style='color:#7FB5A0; font-size:0.8rem;'>"
            f"  · {me['sessions']} shops · €{me['saved']:.2f} saved</span></div>"
            f"<div style='font-weight:800; color:#40B391;'>{me['pct']:.1f}%</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

# If the user hasn't reached the 3-session threshold, tell them how
# many more shops they need before they show up on the board.
my_saved, my_could, my_sessions_counted = db.get_user_savings_totals(user.id)
if my_sessions_counted < 3:
    needed = 3 - my_sessions_counted
    st.info(
        f"🌱 Complete **{needed} more shop{'s' if needed != 1 else ''}** "
        "with at least one item that has prices logged at multiple stores "
        "to appear on the leaderboard."
    )

with st.expander("ℹ️ How is this calculated?"):
    st.markdown(
        """
For every shopping session you save, Budgit looks at each item in your
basket and checks the **highest price that item has been logged at any
supermarket** in the global directory. The difference between that
ceiling and what you actually paid, multiplied by quantity, is your
savings on that line.

- **% saved** = total € saved across all your sessions ÷ total € the
  same baskets would have cost at the most expensive option on file.
- Items that have only ever been seen at one store don't count
  (there's nothing to compare against).
- Sessions where every item is one-store-only also don't count, which
  is why the *counted* shops figure can be lower than your total shops.
- You need **3 counted shops** to qualify for the leaderboard, so a
  single lucky trip doesn't dominate the rankings.

Top 10 is extracted with a Max-Heap Priority Queue
(`algorithms/priority_queue.py`); the full ranking uses Merge Sort
(`algorithms/sorting.py`) so we can show your rank even when you're
outside the top 10.
        """
    )

# -------------------------------------------------------
# 2. Global product-level comparison (from Hash Table)
#
# Pull all products from the in-memory Hash Table and show
# the latest price per store side by side.
# -------------------------------------------------------
st.divider()
st.markdown("#### Global product prices")
st.caption("Latest price logged by any Budgit user at each store. ✅ means the price was verified against a receipt photo.")

ht = get_item_directory()

# Collect all products that have prices at 2+ stores
all_products = []
for key in ht.keys():
    entry = ht.get(key)
    if entry and len(entry.get("prices", {})) >= 1:
        all_products.append({
            "name": key,
            "prices": entry["prices"],
            "times_added": entry.get("times_added", 0),
        })

# Sort alphabetically
all_products.sort(key=lambda p: p["name"])

if not all_products:
    st.info(
        "No global price data yet. As users shop and add items, "
        "prices will appear here automatically."
    )
else:
    # Search filter
    q = st.text_input("🔍 Search product", placeholder="e.g. milk, bread...")

    multi_store = [p for p in all_products if len(p["prices"]) >= 2]
    single_store = [p for p in all_products if len(p["prices"]) == 1]

    # Filter by search query
    if q:
        multi_store = [p for p in multi_store if q.lower() in p["name"]]
        single_store = [p for p in single_store if q.lower() in p["name"]]

    if multi_store:
        st.markdown(f"**{len(multi_store)} product{'s' if len(multi_store)>1 else ''} "
                    f"with prices at multiple stores:**")
        for product in multi_store:
            prices = product["prices"]
            cheapest = min(prices, key=prices.get)
            most_expensive = max(prices, key=prices.get)
            saving = prices[most_expensive] - prices[cheapest]

            st.markdown(f"**{product['name'].title()}**"
                        f"<span style='color:#7FB5A0; font-size:0.8rem;'>"
                        f" · logged {product['times_added']}×"
                        f" · save up to €{saving:.2f}</span>",
                        unsafe_allow_html=True)

            sorted_stores = sorted(prices.keys(), key=lambda s: prices[s])
            cols = st.columns(len(sorted_stores))
            for col, store in zip(cols, sorted_stores):
                if store in prices:
                    is_min = store == cheapest
                    color = "#40B391" if is_min else "#E8F5EF"
                    weight = "800" if is_min else "400"
                    crown = " 👑" if is_min else ""
                    entry = prices[store]
                    is_verified = entry.get("verified", False) if isinstance(entry, dict) else False
                    price_val = entry.get("price", entry) if isinstance(entry, dict) else entry
                    verified_badge = "<span style='font-size:0.7rem;'> ✅</span>" if is_verified else ""
                    col.markdown(
                        f"<div class='budgit-card' style='text-align:center; padding:0.8rem;'>"
                        f"<div style='color:#7FB5A0; font-size:0.75rem;'>{store}{crown}</div>"
                        f"<div style='color:{color}; font-weight:{weight}; font-size:1.3rem;'>"
                        f"€{price_val:.2f}{verified_badge}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    col.markdown(
                        f"<div class='budgit-card' style='text-align:center; padding:0.8rem; opacity:0.3;'>"
                        f"<div style='font-size:0.75rem;'>{store}</div>"
                        f"<div style='font-size:0.9rem;'>—</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
    else:
        st.caption("No products found at multiple stores yet. Shop at different stores to unlock comparisons!")

    if single_store and not q:
        with st.expander(f"📦 {len(single_store)} products seen at only one store"):
            for product in single_store:
                store, entry = list(product["prices"].items())[0]
                price_val = entry.get("price", entry) if isinstance(entry, dict) else entry
                is_verified = entry.get("verified", False) if isinstance(entry, dict) else False
                verified_badge = " ✅" if is_verified else ""
                st.markdown(
                    f"<div class='budgit-item'>"
                    f"<span>{product['name'].title()}</span>"
                    f"<span style='color:#7FB5A0; font-size:0.85rem;'>{store}: €{price_val:.2f}{verified_badge}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
