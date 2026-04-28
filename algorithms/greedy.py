"""
Budget-rescue algorithms.

When the cart total exceeds the user's remaining budget, Budgit
suggests which items to put back. Two strategies, both from class:

    1. GREEDY                 (Greedy_Method lecture)
       Repeatedly drop the most expensive item until we fit.
       Fast (O(n log n)), but not always optimal.

    2. 0/1 KNAPSACK  (DP)     (Dynamic_Programming lecture)
       Choose the SUBSET of items with maximum total value that
       still fits the budget. Here "value" = price of the item
       (we want to keep as much of the cart as we can).
       Complexity: O(n * W) where W is budget in cents.

The UI lets the user toggle between the two and see the trade-off.
"""

from __future__ import annotations
from typing import Any

from .priority_queue import MaxHeapPQ


# --------------------------- Greedy ---------------------------------
def greedy_fit(items: list[dict], budget: float) -> dict:
    """
    Drop the most expensive items one by one until total <= budget.
    Uses a max-heap internally (Session 13).
    """
    pq = MaxHeapPQ()
    for it in items:
        pq.push(it["price"] * it.get("qty", 1), it)

    total = sum(it["price"] * it.get("qty", 1) for it in items)
    keep_ids = {id(it) for it in items}
    dropped: list[dict] = []

    while total > budget and not pq.is_empty():
        amount, payload = pq.pop()
        keep_ids.discard(id(payload))
        dropped.append(payload)
        total -= amount

    kept = [it for it in items if id(it) in keep_ids]
    return {"kept": kept, "dropped": dropped, "total": round(total, 2)}


# --------------------------- 0/1 Knapsack (DP) ----------------------
def knapsack_fit(items: list[dict], budget: float) -> dict:
    """
    0/1 Knapsack with DP. Works in cents to keep weights integer.
    Returns the subset maximising total kept value within budget.
    """
    # Convert to integer cents for a clean DP table.
    W = int(round(budget * 100))
    weights = [int(round(it["price"] * it.get("qty", 1) * 100)) for it in items]
    values = weights[:]                          # price IS the value
    n = len(items)

    if W <= 0 or n == 0:
        return {"kept": [], "dropped": list(items), "total": 0.0}

    # dp[i][w] = max value using first i items with capacity w
    dp = [[0] * (W + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        wi, vi = weights[i - 1], values[i - 1]
        for w in range(W + 1):
            dp[i][w] = dp[i - 1][w]
            if wi <= w and dp[i - 1][w - wi] + vi > dp[i][w]:
                dp[i][w] = dp[i - 1][w - wi] + vi

    # Backtrack to find which items were kept.
    kept: list[dict] = []
    w = W
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:
            kept.append(items[i - 1])
            w -= weights[i - 1]

    kept_ids = {id(it) for it in kept}
    dropped = [it for it in items if id(it) not in kept_ids]
    total = sum(it["price"] * it.get("qty", 1) for it in kept)
    return {"kept": kept, "dropped": dropped, "total": round(total, 2)}
