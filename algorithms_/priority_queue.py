"""
Priority Queue — Session 13 (Trees & Priority Queues).

Implemented as a binary MAX-heap stored in an array.
Budgit uses it to answer "what are my most expensive items?" and
to power the budget-rescue feature: peek() the top until the cart
total fits the remaining budget.
"""

from __future__ import annotations
from typing import Any


class MaxHeapPQ:
    """Max-heap priority queue keyed by numeric priority."""

    def __init__(self) -> None:
        # Each entry is (priority, payload). Higher priority = closer to root.
        self._heap: list[tuple[float, Any]] = []

    def __len__(self) -> int:
        return len(self._heap)

    def is_empty(self) -> bool:
        return len(self._heap) == 0

    # --- public API ---------------------------------------------------
    def push(self, priority: float, payload: Any) -> None:
        self._heap.append((priority, payload))
        self._sift_up(len(self._heap) - 1)

    def peek(self) -> tuple[float, Any]:
        if not self._heap:
            raise IndexError("peek from empty PQ")
        return self._heap[0]

    def pop(self) -> tuple[float, Any]:
        if not self._heap:
            raise IndexError("pop from empty PQ")
        top = self._heap[0]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._sift_down(0)
        return top

    # --- internals ----------------------------------------------------
    def _sift_up(self, i: int) -> None:
        while i > 0:
            parent = (i - 1) // 2
            if self._heap[i][0] > self._heap[parent][0]:
                self._heap[i], self._heap[parent] = self._heap[parent], self._heap[i]
                i = parent
            else:
                break

    def _sift_down(self, i: int) -> None:
        n = len(self._heap)
        while True:
            left = 2 * i + 1
            right = 2 * i + 2
            largest = i
            if left < n and self._heap[left][0] > self._heap[largest][0]:
                largest = left
            if right < n and self._heap[right][0] > self._heap[largest][0]:
                largest = right
            if largest == i:
                break
            self._heap[i], self._heap[largest] = self._heap[largest], self._heap[i]
            i = largest


def top_k_expensive(items: list[dict], k: int = 3) -> list[dict]:
    """Return the k most expensive items from a cart list (unit total)."""
    pq = MaxHeapPQ()
    for it in items:
        pq.push(it["price"] * it.get("qty", 1), it)
    out = []
    while pq and len(out) < k:
        _, payload = pq.pop()
        out.append(payload)
    return out
