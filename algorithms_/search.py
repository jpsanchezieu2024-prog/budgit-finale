"""
Search algorithms — Session 1 (Search).

Used for quick lookups over the sorted list of known product names.
"""

from __future__ import annotations
from typing import Sequence, Any


def binary_search(arr: Sequence, target: Any) -> int:
    """Return the index of target in sorted arr, or -1 if absent."""
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        if arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def linear_search(arr: Sequence, target: Any) -> int:
    for i, item in enumerate(arr):
        if item == target:
            return i
    return -1
