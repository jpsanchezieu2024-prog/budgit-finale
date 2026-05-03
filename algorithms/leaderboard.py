#leaderboard
# ranks Budgit users by how much money they've saved by
# shopping at the cheaper supermarket, aggregated across every session
# We reuse two of the data structures:

# HashTable(algorithms/hash_table.py)
# used here as an O(1) "what's the highest price this item was ever logged at any store?" lookup

# MaxHeapPQ(algorithms/priority_queue.py)
# used here to extract the top-K savers without sorting every user

# Merge_sort(algorithms/sorting.py)
# used once to produce the full ranking so the page can show the current user's rank even when they're outside the top 10.

from __future__ import annotations

from .priority_queue import MaxHeapPQ
from .sorting import merge_sort


# Per-session computation
def compute_session_savings(items: list[dict], directory) -> tuple[float, float]:

    if directory is None:
        return 0.0, 0.0

    saved = 0.0
    could_have = 0.0

    for item in items:
        name = item["name"].lower().strip()
        paid = float(item["price"])
        qty = int(item.get("qty", 1))

        entry = directory.get(name)
        if not entry:
            continue
        prices = entry.get("prices", {})
        # An item needs prices at 2+ stores to be comparable. Items
        # only ever seen at one store don't count toward either the
        # numerator or the denominator
        if len(prices) < 2:
            continue

        ceiling = max(prices.values())
        if ceiling < paid:
            # The user paid more than any recorded price elsewhere no
            # savings on this line so the baseline is the price they paid
            ceiling = paid

        saved += (ceiling - paid) * qty
        could_have += ceiling * qty

    return round(saved, 2), round(could_have, 2)


# Ranking
def rank_savers(candidates: list[dict], top_k: int = 10) -> tuple[list[dict], list[dict]]:

    # Each candidate dict is expected to contain at least "pct" (% saved) and "saved" (€ saved)

    # The fully-sorted list comes from merge_sort and is used to look up a specific user's rank when they are outside the top K.

    # top K via priority queue
    pq = MaxHeapPQ()
    for c in candidates:
        # tiny tiebreaker on absolute € saved. The 1e-9 multiplier keeps
        # the tiebreaker far below any realistic % difference so it only matters when pcts are equal
        priority = c["pct"] + c["saved"] * 1e-9
        pq.push(priority, c)

    top: list[dict] = []
    while pq and len(top) < top_k:
        _, payload = pq.pop()
        top.append(payload)

    # full ranking via merge_sort (for current-user rank lookup)
    full = merge_sort(
        candidates,
        key=lambda c: (c["pct"], c["saved"]),
        reverse=True,
    )
    return top, full

# Display helpers
def display_name(full_name: str) -> str:

    if not full_name:
        return "Anonymous"
    parts = full_name.strip().split()
    if not parts:
        return "Anonymous"
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][0].upper()}."
