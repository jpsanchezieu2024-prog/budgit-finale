"""
Sorting algorithms — Sessions 3 (Sort) and 7 (Divide & Conquer).

We expose merge_sort (stable, O(n log n)) and quick_sort.
Budgit uses merge_sort to sort shopping history by date descending
(we sort a list of Session dict-like objects by a key).
"""

from __future__ import annotations
from typing import Callable, Any


# ------------------- Merge Sort (Divide & Conquer) -------------------
def merge_sort(
    arr: list,
    key: Callable[[Any], Any] = lambda x: x,
    reverse: bool = False,
) -> list:
    """Stable merge sort — returns a NEW sorted list."""
    if len(arr) <= 1:
        return list(arr)
    mid = len(arr) // 2
    left = merge_sort(arr[:mid], key, reverse)
    right = merge_sort(arr[mid:], key, reverse)
    return _merge(left, right, key, reverse)


def _merge(left, right, key, reverse):
    merged = []
    i = j = 0
    while i < len(left) and j < len(right):
        # Compare according to direction.
        a, b = key(left[i]), key(right[j])
        take_left = (a > b) if reverse else (a <= b)
        if take_left:
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1
    merged.extend(left[i:])
    merged.extend(right[j:])
    return merged


# ------------------- Quick Sort (Divide & Conquer) -------------------
def quick_sort(arr: list, key: Callable[[Any], Any] = lambda x: x) -> list:
    """Classic Lomuto partition variant, returns NEW list."""
    arr = list(arr)
    _quick(arr, 0, len(arr) - 1, key)
    return arr


def _quick(arr, lo, hi, key):
    if lo >= hi:
        return
    p = _partition(arr, lo, hi, key)
    _quick(arr, lo, p - 1, key)
    _quick(arr, p + 1, hi, key)


def _partition(arr, lo, hi, key):
    pivot = key(arr[hi])
    i = lo - 1
    for j in range(lo, hi):
        if key(arr[j]) <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    arr[i + 1], arr[hi] = arr[hi], arr[i + 1]
    return i + 1
