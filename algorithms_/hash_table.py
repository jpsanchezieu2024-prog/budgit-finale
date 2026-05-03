"""
HashTable — implementation from Session 9 (Hash Tables).

Used by Budgit as the PRICE LEARNING ENGINE:
    key   -> (product_name_normalised, supermarket)
    value -> last recorded price (float)

Collision resolution: separate chaining (each bucket is a list of pairs).
Load-factor aware: rehashes to a larger table when alpha > 0.75.
"""

from __future__ import annotations
from typing import Any, Iterator


class HashTable:
    """Hash table with separate chaining + dynamic resizing."""

    def __init__(self, initial_capacity: int = 16) -> None:
        self._capacity = initial_capacity
        self._size = 0
        self._buckets: list[list[list]] = [[] for _ in range(self._capacity)]

    # --- core hashing -------------------------------------------------
    def _hash(self, key: Any) -> int:
        # Python's built-in hash is fine for this course-level implementation.
        return hash(key) % self._capacity

    def _load_factor(self) -> float:
        return self._size / self._capacity

    def _rehash(self, new_capacity: int) -> None:
        old_items = list(self.items())
        self._capacity = new_capacity
        self._buckets = [[] for _ in range(self._capacity)]
        self._size = 0
        for k, v in old_items:
            self.put(k, v)

    # --- public API ---------------------------------------------------
    def put(self, key: Any, value: Any) -> None:
        idx = self._hash(key)
        bucket = self._buckets[idx]
        for pair in bucket:
            if pair[0] == key:
                pair[1] = value           # update
                return
        bucket.append([key, value])       # insert
        self._size += 1
        if self._load_factor() > 0.75:
            self._rehash(self._capacity * 2)

    def get(self, key: Any, default: Any = None) -> Any:
        idx = self._hash(key)
        for pair in self._buckets[idx]:
            if pair[0] == key:
                return pair[1]
        return default

    def remove(self, key: Any) -> bool:
        idx = self._hash(key)
        bucket = self._buckets[idx]
        for i, pair in enumerate(bucket):
            if pair[0] == key:
                bucket.pop(i)
                self._size -= 1
                return True
        return False

    def __contains__(self, key: Any) -> bool:
        return self.get(key, _SENTINEL) is not _SENTINEL

    def __len__(self) -> int:
        return self._size

    def items(self) -> Iterator[tuple]:
        for bucket in self._buckets:
            for pair in bucket:
                yield (pair[0], pair[1])

    def keys(self) -> Iterator:
        for k, _ in self.items():
            yield k

    def __repr__(self) -> str:
        return f"HashTable(size={self._size}, capacity={self._capacity})"


_SENTINEL = object()
