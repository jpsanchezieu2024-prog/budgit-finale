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
    lookup_in_directory, update_directory_in_memory, load_item_directory,
    render_sidebar, render_budget_meter, start_of_current_week,
    get_top_items_cached,
)
from theme import apply_theme, budget_pill
from algorithms.greedy import greedy_fit, knapsack_fit


st.set_page_config(page_title="Budgit — Shop", page_icon="🛒", layout="centered")
apply_theme()
init_state()
user = require_login()
render_sidebar(user)
render_budget_meter(user)

if st.session_state.shop_store is None:
    st.session_state.shop_store = user.preferred_store or SUPERMARKETS[0]

# -------------------------------------------------------
# One-shot success banner after a session is saved.
# Set by the confirmation dialog further down.
# -------------------------------------------------------
if "session_just_saved" in st.session_state:
    saved_total, saved_store = st.session_state.session_just_saved
    st.success(f"✅ Session saved! Spent **€{saved_total:.2f}** at **{saved_store}** 🎉")
    st.balloons()
    del st.session_state.session_just_saved

# -------------------------------------------------------
# One-shot toast celebrations for newly-earned badges. The
# confirmation dialog populates `pending_badges` after a save;
# we surface them on the next render and clear the queue.
# -------------------------------------------------------
if st.session_state.get("pending_badges"):
    for badge_id in st.session_state.pending_badges:
        meta = db.BADGES.get(badge_id)
        if meta:
            st.toast(
                f"{meta['emoji']} New badge — {meta['name']}!",
                icon="🎉",
            )
    del st.session_state["pending_badges"]

# -------------------------------------------------------
# First-time-user welcome banner. Shown once after sign-up.
# -------------------------------------------------------
if st.session_state.pop("first_time_user", False):
    st.info(
        f"👋 **Welcome to Budgit, {user.name.split()[0]}!** Your weekly budget is "
        f"**€{user.weekly_budget:.2f}**. Add items to your cart below as you "
        "shop — Budgit will track the running total and warn you if you go over."
    )

st.markdown("### 🛒 Shopping session")
st.caption("Add items as you shop. Prices auto-fill from your history and the global directory.")

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
#
# Shows three things in priority order:
#   1. The current cart total (what you'll spend at checkout).
#   2. Your remaining budget for *this calendar week* AFTER paying
#      for everything in the cart — i.e. budget − (already spent
#      this week) − cart total. This is the number that actually
#      tells the user whether they can afford to keep adding items.
#   3. A progress bar of total weekly utilisation.
# -------------------------------------------------------
cart_total = cart.total()

# Pull this week's previously-completed sessions so the running budget
# accounts for what the user has already spent earlier this week.
_week_start_iso = start_of_current_week().isoformat()
_already_spent_this_week = sum(
    s["total"] for s in db.get_sessions(user.id)
    if s["created_at"] >= _week_start_iso
)

projected_week_spend = _already_spent_this_week + cart_total
remaining_this_week = user.weekly_budget - projected_week_spend
pct = (
    projected_week_spend / user.weekly_budget
    if user.weekly_budget > 0 else 0
)
rem_color = "#FF6B5B" if remaining_this_week < 0 else "#40B391"

st.markdown(
    f"""
    <div class="budgit-accent">
      <div style="color:#7FB5A0; font-size:0.9rem; margin-bottom:0.2rem;">Cart total</div>
      <p class="budgit-total">€{cart_total:,.2f}</p>
      <div class="budgit-total-label" style="margin-top:0.6rem;">
        After this shop you'll have
        <b style="color:{rem_color};">€{remaining_this_week:,.2f}</b>
        left of your <b>€{user.weekly_budget:,.2f}</b> weekly budget
        &nbsp; {budget_pill(pct)}
      </div>
      <div style="color:#7FB5A0; font-size:0.78rem; margin-top:0.4rem;">
        Already spent this week: €{_already_spent_this_week:,.2f}
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
# -------------------------------------------------------
# Quick-add chips — your most frequently bought items.
#
# A row of one-tap buttons that append the user's top items
# (across all sessions) directly to the cart, using the latest
# known price at the current store. Goes from 4 taps → 1 tap
# for the items the user buys all the time.
# -------------------------------------------------------
top_items = get_top_items_cached(user.id, limit=6)

if top_items:
    # Filter to items we have a known price for at the current store.
    chips = []
    for name, _qty_total in top_items:
        price = db.lookup_product_price(user.id, name, store)
        if price is None:
            price = lookup_in_directory(name, store)
        if price is not None and price > 0:
            chips.append((name, float(price)))

    if chips:
        st.markdown("##### ⚡ Quick add — your favourites")
        # Render in rows of 3 so chips stay readable on narrower screens.
        for row_start in range(0, len(chips), 3):
            row = chips[row_start:row_start + 3]
            cols = st.columns(len(row))
            for col, (name, price) in zip(cols, row):
                if col.button(
                    f"➕ {name.title()}\n€{price:.2f}",
                    key=f"quick_{name}",
                    use_container_width=True,
                ):
                    existing = cart._items.get(name)
                    if existing is not None:
                        cart.update(name, price=price, qty=existing.qty + 1)
                    else:
                        cart.add(name, price, 1)
                    # Learn the price (in case the directory's value changed
                    # since the user last logged this item).
                    db.upsert_product(user.id, name, price, store)
                    db.add_to_directory(name, price, store)
                    update_directory_in_memory(name, price, store)
                    # Award the "Quick adder" badge on first use.
                    if db.award_badge(user.id, "first_quick_add"):
                        st.session_state.setdefault(
                            "pending_badges", []).append("first_quick_add")
                    st.toast(f"Added {name.title()} — €{price:.2f}", icon="🛍️")
                    st.rerun()

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
        # Autofill: check user's own memory first, then global
        # directory. Always clamped to >= 0 so the number_input's
        # min_value constraint can't be violated by stale or weird
        # data in the database.
        autofill = 0.0
        if name_in:
            user_price = db.lookup_product_price(user.id, name_in, store)
            if user_price is not None:
                autofill = float(user_price)
            else:
                global_price = lookup_in_directory(name_in, store)
                if global_price is not None:
                    autofill = float(global_price)
        autofill = max(0.0, autofill)

        price_in = st.number_input(
            "Price (€)", min_value=0.0, step=0.1,
            value=autofill, format="%.2f",
            key="add_item_price",
        )

    with qty_col:
        qty_in = st.number_input("Qty", min_value=1, value=1, step=1,
                                 key="add_item_qty")

    submitted = st.form_submit_button("➕ Add to Cart",
                                      type="primary",
                                      use_container_width=True)

    if submitted:
        # Validate name and price separately so the user gets a
        # specific message about what's wrong rather than the old
        # combined "name OR price" error which read as "negative"
        # when it was really just a 0.0-default price field.
        clean_name = name_in.strip() if name_in else ""
        clean_brand = (brand_in or "").strip()
        try:
            clean_price = float(price_in or 0.0)
        except (TypeError, ValueError):
            clean_price = 0.0

        if not clean_name:
            st.error("Please enter a product name.")
        elif clean_price <= 0:
            st.error("Please enter a price greater than €0.00.")
        else:
            key = clean_name.lower()

            # Check if item already in cart
            existing = cart._items.get(key)
            if existing is not None:
                # UPDATE the existing cart row — don't add a duplicate
                cart.update(
                    clean_name, price=clean_price,
                    qty=existing.qty + int(qty_in),
                    brand=clean_brand,
                )
                st.toast(
                    f"Updated {clean_name.title()} — now "
                    f"{existing.qty + int(qty_in)}× at €{clean_price:.2f}",
                    icon="✏️",
                )
            else:
                cart.add(
                    clean_name, clean_price, int(qty_in),
                    brand=clean_brand,
                )
                st.toast(
                    f"Added {clean_name.title()} — €{clean_price:.2f}",
                    icon="🛍️",
                )

            # Save to user's price memory and the global directory,
            # carrying the brand alongside the price so different
            # variants of the same product can be told apart.
            db.upsert_product(
                user.id, clean_name, clean_price, store,
                brand=clean_brand,
            )
            db.add_to_directory(
                clean_name, clean_price, store, brand=clean_brand,
            )
            update_directory_in_memory(
                clean_name, clean_price, store, brand=clean_brand,
            )
            rebuild_bst(user.id)

            st.session_state.last_typed_name = clean_name
            # NOTE: no explicit st.rerun() here. Streamlit reruns the
            # script automatically after a form submit, and an explicit
            # rerun() inside the handler interferes with the form's
            # `clear_on_submit=True` reset, leaving the price field in
            # a stale state that surfaces as a "value < min_value"
            # warning on the next interaction.

# -------------------------------------------------------
# Live autocomplete + cross-store price comparison.
#
# As soon as the user types in the name field, we:
#   1. Pull prefix-matching product names out of the BST and surface
#      them as a "From your history" hint.
#   2. Show the latest known price for that product at every store
#      in the global directory, with a 👑 crown on the cheapest, the
#      current store's price labelled "(here)", and an explicit
#      "Save €X by going to Y" call-out when a cheaper alternative
#      exists. Turns the global Hash Table into actionable advice
#      at the moment of the user's decision.
# -------------------------------------------------------
typed = st.session_state.get("item_name", "")
if typed:
    suggestions = get_bst(user.id).prefix_search(typed, limit=5)
    clean = [s["name"] if isinstance(s, dict) else s for s in suggestions]
    if clean:
        st.caption("📂 From your history: " + ", ".join(clean))

    # Pull full variant info per store so we can show the brand chip
    # underneath each store's price. Comparison is by absolute price;
    # the per-unit math was rolled back as too complex for the form.
    full_entries = lookup_directory_full(typed)
    if full_entries:
        ranked = sorted(full_entries.items(), key=lambda kv: kv[1]["price"])
        cheapest_store, cheapest_entry = ranked[0]
        current_entry = full_entries.get(store)

        # Render each store as a chip — green crown on the cheapest,
        # bold "(here)" on the user's current store, dim grey for
        # everything else. Brand is shown as a secondary line under
        # the price when the directory has it.
        chip_html = []
        for s_name, entry in ranked:
            sub = (
                f"<div style='font-size:0.72rem; color:#7FB5A0;'>{entry['brand']}</div>"
                if entry.get("brand") else ""
            )
            if s_name == cheapest_store and len(ranked) > 1:
                chip_html.append(
                    f"<div style='display:inline-block; margin:0 10px 4px 0; color:#40B391; font-weight:700;'>"
                    f"👑 {s_name} €{entry['price']:.2f}{sub}</div>"
                )
            elif s_name == store:
                chip_html.append(
                    f"<div style='display:inline-block; margin:0 10px 4px 0; color:#E8F5EF; font-weight:600;'>"
                    f"{s_name} €{entry['price']:.2f} (here){sub}</div>"
                )
            else:
                chip_html.append(
                    f"<div style='display:inline-block; margin:0 10px 4px 0; color:#7FB5A0;'>"
                    f"{s_name} €{entry['price']:.2f}{sub}</div>"
                )

        savings_msg = ""
        if (
            current_entry is not None
            and cheapest_store != store
            and current_entry["price"] > cheapest_entry["price"]
        ):
            savings = current_entry["price"] - cheapest_entry["price"]
            savings_msg = (
                f"<div style='color:#FFB84D; font-size:0.82rem; margin-top:0.4rem;'>"
                f"💡 Save <b>€{savings:.2f}</b> by going to {cheapest_store}"
                f"</div>"
            )
        elif current_entry is None and len(ranked) >= 1:
            savings_msg = (
                f"<div style='color:#7FB5A0; font-size:0.78rem; margin-top:0.25rem;'>"
                f"No price on file for this item at {store}."
                f"</div>"
            )

        st.markdown(
            f"<div style='background:rgba(255,255,255,0.02); "
            f"border:1px solid #2A3D34; border-radius:10px; "
            f"padding:0.5rem 0.8rem; margin-top:0.4rem; "
            f"font-size:0.85rem;'>"
            f"🌍 " + "".join(chip_html) +
            f"{savings_msg}"
            f"</div>",
            unsafe_allow_html=True,
        )



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
                    # Award the "List importer" badge on first import.
                    if db.award_badge(user.id, "first_import"):
                        st.session_state.setdefault(
                            "pending_badges", []).append("first_import")
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
    st.markdown(
        "<div class='budgit-card' style='text-align:center; padding:1.6rem;'>"
        "<div style='font-size:2.5rem; margin-bottom:0.4rem;'>🛒</div>"
        "<div style='font-weight:700; margin-bottom:0.3rem;'>Your cart is empty</div>"
        "<div style='color:#7FB5A0; font-size:0.9rem;'>"
        "Use the <b>Add an item</b> form above to start shopping. "
        "Or import a saved grocery list with the panel below."
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )
else:
    for item in list(cart):
        c1, c2, c3, c4, c5 = st.columns([3, 1.2, 1, 1.2, 0.8])

        # Brand renders as a secondary line under the item name when
        # the user actually filled it in; otherwise the row stays
        # exactly as it was before brands existed.
        brand_line = (
            f"<span style='color:#7FB5A0; font-size:0.78rem;'>{item.brand}</span><br>"
            if item.brand else ""
        )

        c1.markdown(
            f"<div style='padding-top:0.6rem;'>"
            f"<b>{item.name.title()}</b><br>"
            f"{brand_line}"
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
        new_qty = c3.number_input("Qty", 1, 999, item.qty, step=1,
                                  key=f"{key_base}_qty", label_visibility="collapsed")
        new_price = c4.number_input("€", 0.0, 9999.0, item.price, step=0.1,
                                    key=f"{key_base}_price", label_visibility="collapsed",
                                    format="%.2f")
        if new_qty != item.qty or abs(new_price - item.price) > 0.001:
            cart.update(item.name, price=new_price, qty=new_qty)
            db.upsert_product(
                user.id, item.name, new_price, store, brand=item.brand,
            )
            db.add_to_directory(
                item.name, new_price, store, brand=item.brand,
            )
            update_directory_in_memory(
                item.name, new_price, store, brand=item.brand,
            )
            st.rerun()

        if c5.button("❌", key=f"{key_base}_rm", help="Remove item"):
            cart.remove(item.name)
            st.rerun()

    st.markdown(
        f"<div class='budgit-card' style='text-align:right;'>"
        f"<span style='color:#7FB5A0;'>Cart total: </span>"
        f"<span style='color:#40B391; font-size:1.4rem; font-weight:800;'>€{cart_total:.2f}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


# -------------------------------------------------------
# Budget Rescue
#
# The budget the rescue algorithms target is "what's left of this
# week's budget", not the full weekly budget — otherwise a user who
# already spent €30 of a €40 weekly budget wouldn't get rescued until
# their cart hit €40, by which point they'd already be €30 over.
# -------------------------------------------------------
_rescue_budget = max(0.0, user.weekly_budget - _already_spent_this_week)

if cart_total > _rescue_budget and user.weekly_budget > 0:
    st.divider()
    st.markdown("### 💡 Budget Rescue")
    over = cart_total - _rescue_budget
    st.warning(
        f"You're **€{over:.2f}** over what's left of your weekly budget "
        f"(**€{_rescue_budget:.2f}** remaining)."
    )

    mode = st.radio(
        "Strategy:",
        ("⚡ Greedy — drop biggest items first (fast)",
         "🧠 Optimal — keep as much value as possible (DP)"),
    )

    dicts = cart.to_session_dicts()
    if mode.startswith("⚡"):
        result = greedy_fit(dicts, _rescue_budget)
        st.caption("Uses a max-heap to greedily remove the most expensive items — O(n log n).")
    else:
        result = knapsack_fit(dicts, _rescue_budget)
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
        # Award a badge the first time the user picks each rescue
        # algorithm — gives them a tangible nudge to try the other one.
        badge_id = "greedy_used" if mode.startswith("⚡") else "knapsack_used"
        if db.award_badge(user.id, badge_id):
            st.session_state.setdefault("pending_badges", []).append(badge_id)
        st.rerun()


# -------------------------------------------------------
# End session — with a confirmation modal so a misclick can't
# accidentally close the cart and wipe it.
# -------------------------------------------------------
@st.dialog("Confirm end of session")
def _confirm_end_session():
    """
    Two-step save: the user has to explicitly approve clearing the cart
    and saving the session to history. Triggered by the "End & Save"
    button below.
    """
    items = list(cart)
    st.markdown(f"### Save this shopping session?")
    st.write("")
    c1, c2, c3 = st.columns(3)
    c1.metric("Store", store)
    c2.metric("Items", cart.count())
    c3.metric("Total", f"€{cart.total():.2f}")

    with st.expander(f"View the {len(items)} item{'s' if len(items) != 1 else ''} in this session"):
        for it in items:
            st.markdown(
                f"<div class='budgit-item'>"
                f"<span><b>{it.name.title()}</b> "
                f"<span style='color:#7FB5A0; font-size:0.82rem;'>× {it.qty}</span></span>"
                f"<span>€{it.line_total:.2f}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.caption(
        "Once saved, this session goes into your shopping history and "
        "your cart is emptied so you can start a new shop."
    )

    btn_save, btn_cancel = st.columns(2)
    if btn_save.button("✅ Save & end session", type="primary",
                       use_container_width=True, key="dlg_confirm_save"):
        # Capture totals BEFORE clearing the cart so we can show them
        # in the post-save success banner.
        final_total = cart.total()
        final_store = store

        db.save_session(
            user.id, store,
            cart.to_session_dicts(), cart.total(),
            directory=get_item_directory(),
        )
        cart.clear()
        # Saved session changes the user's "most-bought" stats — drop
        # the cache so the quick-add chips refresh on next render.
        st.session_state.pop("top_items", None)
        st.session_state.session_just_saved = (final_total, final_store)

        # Run the post-save milestone check and queue any newly-earned
        # badges so the next render of the page shows toasts for them.
        newly_earned = db.check_session_milestones(user.id)
        if newly_earned:
            existing = st.session_state.get("pending_badges", [])
            st.session_state.pending_badges = existing + newly_earned

        st.rerun()

    if btn_cancel.button("❌ Cancel", use_container_width=True,
                         key="dlg_confirm_cancel"):
        st.rerun()


st.divider()
col1, col2 = st.columns(2)
with col1:
    if st.button("🧹 Clear cart", use_container_width=True,
                 disabled=len(cart) == 0):
        cart.clear()
        st.rerun()
with col2:
    if st.button("💾 End & Save Session", type="primary",
                 use_container_width=True, disabled=len(cart) == 0):
        _confirm_end_session()