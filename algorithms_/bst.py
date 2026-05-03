"""
Binary Search Tree — Session 17.

Used by Budgit to keep the list of known product names sorted
so we can do prefix-matching for the autocomplete as the user
types in the Add Item form.

Operations implemented:
    insert(key, value)  -> O(log n) average, O(n) worst
    search(key)         -> returns value or None
    prefix_search(pfx)  -> returns every key starting with pfx (sorted)
    in_order()          -> alphabetical traversal
"""

from __future__ import annotations
from typing import Any, Optional


class _Node:
    __slots__ = ("key", "value", "left", "right")

    def __init__(self, key: str, value: Any) -> None:
        self.key = key
        self.value = value
        self.left: Optional["_Node"] = None
        self.right: Optional["_Node"] = None


class BST:
    """Simple unbalanced BST, good enough for a few hundred product names."""

    def __init__(self) -> None:
        self._root: Optional[_Node] = None
        self._size = 0

    def __len__(self) -> int:
        return self._size

    # --- insert -------------------------------------------------------
    def insert(self, key: str, value: Any = None) -> None:
        key = key.lower()
        self._root, inserted = self._insert(self._root, key, value)
        if inserted:
            self._size += 1

    def _insert(self, node, key, value):
        if node is None:
            return _Node(key, [value] if value is not None else []), True

        if key < node.key:
            node.left, ins = self._insert(node.left, key, value)
            return node, ins

        elif key > node.key:
            node.right, ins = self._insert(node.right, key, value)
            return node, ins

        else:
            if value is not None:
                if isinstance(node.value, list):
                    node.value.append(value)
                else:
                    node.value = [node.value, value]
            return node, False

    # --- search -------------------------------------------------------
    def search(self, key: str) -> Optional[Any]:
        key = key.lower()
        node = self._root
        while node is not None:
            if key == node.key:
                return node.value
            node = node.left if key < node.key else node.right
        return None

    # --- in-order traversal ------------------------------------------
    def in_order(self) -> list[str]:
        result: list[str] = []
        self._in_order(self._root, result)
        return result

    def _in_order(self, node, out):
        if node is None:
            return
        self._in_order(node.left, out)
        out.append(node.key)
        self._in_order(node.right, out)

    # --- prefix search (used by the autocomplete in Shop page) -------
    def prefix_search(self, prefix: str, limit: int = 8) -> list[str]:
        prefix = prefix.lower()
        if not prefix:
            return []
        results: list[str] = []
        self._prefix(self._root, prefix, results, limit)
        return results

    def prefix_search(self, prefix: str, limit: int = 8) -> list[dict]:
        prefix = prefix.lower()
        if not prefix:
            return []

        results: list[dict] = []
        self._prefix(self._root, prefix, results, limit)
        return results

    def _prefix(self, node, prefix, out, limit):
        if node is None or len(out) >= limit:
            return

        if prefix <= node.key:
            self._prefix(node.left, prefix, out, limit)

        if len(out) >= limit:
            return

        if node.key.startswith(prefix):
            out.append({
                "name": node.key,
                "values": node.value if isinstance(node.value, list) else [node.value]
            })

        if len(out) >= limit:
            return

        if prefix >= node.key[: len(prefix)]:
            self._prefix(node.right, prefix, out, limit)
