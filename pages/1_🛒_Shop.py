"""
Budgit — Shopping session screen.

Fixes:
- Adding same product updates price/qty in existing cart row (no duplicates)
- Price autofill correctly reads from global directory per store
"""

import streamlit as st

import database as db
from state import (
    init_state, require_login, SUPERMARKETS,
    get_bst, rebuild_bst, get_item_directory,
    lookup_in_directory, update_directory_in_memory, load_item_directory
)
from theme import apply_theme, budget_pill
from algorithms.greedy import greedy_fit, knapsack_fit


st.set_page_config(page_title="Budgit — Shop", page_icon="🛒", layout="centered")
apply_theme()
init_state()
user = require_login()

if st.session_state.shop_store is None:
    st.session_state.shop_store = user.preferred_store or SUPERMARKETS[0]

st.markdown("### 🛒 Shopping session")

store = st.selectbox(
    "Shopping at",
    SUPERMARKETS,
    index=SUPERMARKETS.index(st.session_state.shop_store)
    if st.session_state.shop_store in SUPERMARKETS else 0,
)
st.session_state.shop_store = store
cart = st.session_state.cart


# -------------------------------------------------------
# Running total
# -------------------------------------------------------
total = cart.total()
pct = (total / user.weekly_budget) if user.weekly_budget > 0 else 0

st.markdown(
    f"""
    <div class="budgit-accent">
      <p class="budgit-total">€{total:,.2f}</p>
      <div class="budgit-total-label">
        {min(pct,1.0)*100:.0f}% of €{user.weekly_budget:,.2f} weekly budget
        &nbsp; {budget_pill(pct)}
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.progress(min(pct, 1.0))


# -------------------------------------------------------
# Add item
#
# FIX: We track the "last added name" in session state so
# that when the form clears, we can still show the autofill
# hint. The cart.add() method already handles duplicates by
# updating qty — but here we also update the price in place
# if the same product is added again with a new price.
# -------------------------------------------------------
st.markdown("#### Add an item")

# Keep track of what's being typed for autofill hints
if "last_typed_name" not in st.session_state:
    st.session_state.last_typed_name = ""

with st.form("add_item", clear_on_submit=True):
    col_name, col_price, col_qty = st.columns([3, 1.2, 1])

    with col_name:
        name_in = st.text_input(
            "Product name",
            placeholder="e.g. milk, bread, eggs",
            key="item_name",
        )

    with col_price:
        # Autofill: check user's own memory first, then global directory
        autofill = 0.0
        if name_in:
            user_price = db.lookup_product_price(user.id, name_in, store)
            if user_price is not None:
                autofill = float(user_price)
            else:
                global_price = lookup_in_directory(name_in, store)
                if global_price is not None:
                    autofill = float(global_price)

        price_in = st.number_input(
            "Price (€)", min_value=0.0, step=0.1,
            value=autofill, format="%.2f"
        )

    with col_qty:
        qty_in = st.number_input("Qty", min_value=1, value=1, step=1)

    submitted = st.form_submit_button("➕ Add to Cart", type="primary")

    if submitted:
        if not name_in.strip() or price_in <= 0:
            st.error("Please enter a product name and a positive price.")
        else:
            key = name_in.lower().strip()

            # Check if item already in cart
            existing = cart._items.get(key)
            if existing is not None:
                # UPDATE the existing cart row — don't add a duplicate
                # Add the new qty, update to the latest price
                cart.update(name_in, price=float(price_in), qty=existing.qty + int(qty_in))
                st.toast(f"Updated {name_in.title()} — now {existing.qty + int(qty_in)}× at €{price_in:.2f}", icon="✏️")
            else:
                cart.add(name_in, float(price_in), int(qty_in))
                st.toast(f"Added {name_in.title()} — €{price_in:.2f}", icon="🛍️")

            # Save to user's price memory and global directory
            db.upsert_product(user.id, name_in, float(price_in), store)
            db.add_to_directory(name_in, float(price_in), store)
            update_directory_in_memory(name_in, float(price_in), store)
            rebuild_bst(user.id)

            st.session_state.last_typed_name = name_in
            st.rerun()

# Autocomplete hints below the form
typed = st.session_state.get("item_name", "")
if typed:
    suggestions = get_bst(user.id).prefix_search(typed, limit=5)
    clean = [s["name"] if isinstance(s, dict) else s for s in suggestions]
    if clean:
        st.caption("📂 From your history: " + ", ".join(clean))

    all_prices = lookup_in_directory(typed)
    if all_prices:
        sorted_prices = sorted(all_prices.items(), key=lambda x: x[1])
        price_hints = " · ".join(
            f"**{s}**: €{p:.2f}" for s, p in sorted_prices
        )
        st.caption(f"🌍 Latest prices — {price_hints}")



# -------------------------------------------------------
# Import grocery list into cart
#
# For each item on the saved list the user can:
#   - tick or untick whether to import it,
#   - set/override the price (prefilled from their own price memory
#     or the global directory; 0.00 if we have nothing on file),
#   - bump the quantity.
#
# When they hit "Add selected to cart":
#   1. every ticked item with price > 0 is added to the cart,
#   2. the price is learned (per-user + global directory),
#   3. that item is REMOVED from the saved grocery list.
# Items left unticked stay on the list for next time.
# -------------------------------------------------------
grocery_items = db.get_grocery_list(user.id)
if grocery_items:
    with st.expander(f"📝 Import from grocery list ({len(grocery_items)} items)"):
        st.caption(
            f"Pick the items to add to your cart at **{store}** and confirm "
            "their prices. Anything you import will be removed from your list."
        )

        with st.form("import_grocery_list"):
            # Header row so the columns are self-explanatory.
            h0, h1, h2, h3 = st.columns([0.5, 2.5, 1.3, 1])
            h0.markdown("<div style='color:#7FB5A0; font-size:0.75rem;'>Import</div>",
                        unsafe_allow_html=True)
            h1.markdown("<div style='color:#7FB5A0; font-size:0.75rem;'>Item</div>",
                        unsafe_allow_html=True)
            h2.markdown("<div style='color:#7FB5A0; font-size:0.75rem;'>Price (€)</div>",
                        unsafe_allow_html=True)
            h3.markdown("<div style='color:#7FB5A0; font-size:0.75rem;'>Qty</div>",
                        unsafe_allow_html=True)

            choices = []  # collected on submit

            for i, item in enumerate(grocery_items):
                # Price priority: user memory → global directory → 0 (force input)
                user_price = db.lookup_product_price(user.id, item["name"], store)
                if user_price is not None:
                    default_price = float(user_price)
                    hint = "from your history"
                else:
                    global_price = lookup_in_directory(item["name"], store)
                    if global_price is not None:
                        default_price = float(global_price)
                        hint = "from global directory"
                    else:
                        default_price = 0.0
                        hint = "⚠️ no price on file — please enter one"

                c0, c1, c2, c3 = st.columns([0.5, 2.5, 1.3, 1])
                checked = c0.checkbox(
                    "import", value=True,
                    key=f"imp_chk_{i}", label_visibility="collapsed",
                )
                c1.markdown(
                    f"<div style='padding-top:0.3rem;'>"
                    f"<b>{item['name'].title()}</b><br>"
                    f"<span style='color:#7FB5A0; font-size:0.75rem;'>{hint}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                price_in = c2.number_input(
                    "price", min_value=0.0, step=0.1,
                    value=default_price, format="%.2f",
                    key=f"imp_price_{i}", label_visibility="collapsed",
                )
                qty_in = c3.number_input(
                    "qty", min_value=1, value=int(item["qty"]), step=1,
                    key=f"imp_qty_{i}", label_visibility="collapsed",
                )
                choices.append({
                    "name": item["name"],
                    "selected": checked,
                    "price": float(price_in),
                    "qty": int(qty_in),
                })

            submitted = st.form_submit_button(
                "🛒 Add selected to cart",
                type="primary", use_container_width=True,
            )

            if submitted:
                added, no_price = 0, []
                imported_names: set[str] = set()

                for ch in choices:
                    if not ch["selected"]:
                        continue
                    if ch["price"] <= 0:
                        no_price.append(ch["name"])
                        continue

                    name, price, qty = ch["name"], ch["price"], ch["qty"]
                    existing = cart._items.get(name.lower().strip())
                    if existing:
                        cart.update(name, price=price, qty=existing.qty + qty)
                    else:
                        cart.add(name, price, qty)

                    # Learn the price everywhere, just like a manual add.
                    db.upsert_product(user.id, name, price, store)
                    db.add_to_directory(name, price, store)
                    update_directory_in_memory(name, price, store)
                    imported_names.add(name.lower().strip())
                    added += 1

                # Remove successfully-imported items from the saved list.
                if imported_names:
                    remaining = [
                        it for it in grocery_items
                        if it["name"].lower().strip() not in imported_names
                    ]
                    db.save_grocery_list(user.id, remaining)
                    # Keep session state in sync so the List page reflects
                    # the removal immediately on next visit.
                    if st.session_state.get("grocery_list_user") == user.id:
                        st.session_state.grocery_items = remaining
                    rebuild_bst(user.id)

                if added:
                    st.success(
                        f"Added {added} item{'s' if added != 1 else ''} to cart "
                        "and removed them from your list."
                    )
                if no_price:
                    pretty = ", ".join(n.title() for n in no_price)
                    st.warning(
                        f"Skipped {pretty} — set a price greater than €0 "
                        "to import these."
                    )
                if added:
                    st.rerun()

# -------------------------------------------------------
# Cart list
# -------------------------------------------------------
st.markdown(f"#### Cart ({cart.count()} items)")

if len(cart) == 0:
    st.info("Your cart is empty. Add your first item above! 👆")
else:
    for item in list(cart):
        c1, c2, c3, c4, c5 = st.columns([3, 1.2, 1, 1.2, 0.8])
        c1.markdown(
            f"<div style='padding-top:0.6rem;'>"
            f"<b>{item.name.title()}</b><br>"
            f"<span style='color:#7FB5A0; font-size:0.82rem;'>€{item.price:.2f} × {item.qty}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        c2.markdown(
            f"<div style='padding-top:0.9rem; font-weight:700; color:#40B391;'>"
            f"€{item.line_total:.2f}</div>",
            unsafe_allow_html=True,
        )
        key_base = f"it_{item.name}"
        new_qty = c3.number_input("Qty", 1, 99, item.qty, step=1,
                                  key=f"{key_base}_qty", label_visibility="collapsed")
        new_price = c4.number_input("€", 0.0, 9999.0, item.price, step=0.1,
                                    key=f"{key_base}_price", label_visibility="collapsed",
                                    format="%.2f")
        if new_qty != item.qty or abs(new_price - item.price) > 0.001:
            cart.update(item.name, price=new_price, qty=new_qty)
            db.upsert_product(user.id, item.name, new_price, store)
            db.add_to_directory(item.name, new_price, store)
            update_directory_in_memory(item.name, new_price, store)
            st.rerun()

        if c5.button("❌", key=f"{key_base}_rm", help="Remove item"):
            cart.remove(item.name)
            st.rerun()

    st.markdown(
        f"<div class='budgit-card' style='text-align:right;'>"
        f"<span style='color:#7FB5A0;'>Cart total: </span>"
        f"<span style='color:#40B391; font-size:1.4rem; font-weight:800;'>€{total:.2f}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


# -------------------------------------------------------
# Budget Rescue
# -------------------------------------------------------
if total > user.weekly_budget and user.weekly_budget > 0:
    st.divider()
    st.markdown("### 💡 Budget Rescue")
    over = total - user.weekly_budget
    st.warning(f"You're **€{over:.2f}** over your weekly budget.")

    mode = st.radio(
        "Strategy:",
        ("⚡ Greedy — drop biggest items first (fast)",
         "🧠 Optimal — keep as much value as possible (DP)"),
    )

    dicts = cart.to_session_dicts()
    if mode.startswith("⚡"):
        result = greedy_fit(dicts, user.weekly_budget)
        st.caption("Uses a max-heap to greedily remove the most expensive items — O(n log n).")
    else:
        result = knapsack_fit(dicts, user.weekly_budget)
        st.caption("0/1 Knapsack DP — finds the optimal subset that fits the budget — O(n·W).")

    colK, colD = st.columns(2)
    with colK:
        st.markdown("**✅ Keep**")
        for it in result["kept"]:
            st.markdown(
                f"<div class='budgit-item'>{it['name'].title()}"
                f"<span style='color:#40B391;'>€{it['price']*it.get('qty',1):.2f}</span></div>",
                unsafe_allow_html=True,
            )
    with colD:
        st.markdown("**❌ Put back**")
        for it in result["dropped"]:
            st.markdown(
                f"<div class='budgit-item'>{it['name'].title()}"
                f"<span style='color:#FF6B5B;'>€{it['price']*it.get('qty',1):.2f}</span></div>",
                unsafe_allow_html=True,
            )
    st.success(f"Suggested total: **€{result['total']:.2f}**")

    if st.button("Apply — remove these from cart", type="primary"):
        for it in result["dropped"]:
            cart.remove(it["name"])
        st.rerun()


# -------------------------------------------------------
# End session
# -------------------------------------------------------
st.divider()
col1, col2 = st.columns(2)
with col1:
    if st.button("🧹 Clear cart", use_container_width=True):
        cart.clear()
        st.rerun()
with col2:
    if st.button("💾 End & Save Session", type="primary",
                 use_container_width=True, disabled=len(cart) == 0):
        # Pass the in-memory directory so save_session can update the
        # lifetime savings counters that power the leaderboard.
        sid = db.save_session(
            user.id, store,
            cart.to_session_dicts(), cart.total(),
            directory=get_item_directory(),
        )
        st.success(f"Session saved! Spent **€{cart.total():.2f}** at {store} 🎉")
        cart.clear()
        st.balloons()
        st.rerun()