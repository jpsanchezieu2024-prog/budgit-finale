"""
OOP domain model — Session 11 (Object-Oriented Programming).

Every real-world concept in Budgit is a class:
    User, Product, CartItem, Cart, Session

The Cart is backed by the HashTable from algorithms.hash_table so that
adding / removing / looking up items is O(1) average, and by the
MaxHeapPQ for the "most expensive items" view.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterator

from algorithms.hash_table import HashTable
from algorithms.priority_queue import MaxHeapPQ, top_k_expensive


# -------------------------- User ------------------------------------
@dataclass
class User:
    id: int
    name: str
    email: str
    weekly_budget: float
    preferred_store: str

    @classmethod
    def from_row(cls, row) -> "User":
        return cls(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            weekly_budget=row["weekly_budget"],
            preferred_store=row["preferred_store"] or "",
        )


# -------------------------- Product ---------------------------------
@dataclass
class Product:
    name: str
    price: float
    supermarket: str

    def normalised(self) -> str:
        return self.name.lower().strip()


# -------------------------- Cart ------------------------------------
@dataclass
class CartItem:
    """
    A single line in the shopping cart. Just the basics: name, price,
    quantity. Earlier iterations tried to track brand, size, and unit
    for variant comparison; that added too much UI complexity for the
    benefit and was rolled back.
    """
    name: str
    price: float
    qty: int = 1

    @property
    def line_total(self) -> float:
        return self.price * self.qty

    def to_dict(self) -> dict:
        return {"name": self.name, "price": self.price, "qty": self.qty}


class Cart:
    """
    Shopping cart backed by a HashTable (class implementation).

    Key by item name so the *same* product added twice bumps qty rather
    than creating a duplicate line.
    """

    def __init__(self) -> None:
        self._items: HashTable = HashTable()
        self._order: list[str] = []      # preserve insertion order for the UI

    # --- mutators -----------------------------------------------------
    def add(self, name: str, price: float, qty: int = 1) -> None:
        key = name.lower().strip()
        existing: CartItem | None = self._items.get(key)
        if existing is not None:
            existing.qty += qty
            existing.price = price        # last seen price wins
            self._items.put(key, existing)
        else:
            self._items.put(key, CartItem(name=name.strip(), price=price, qty=qty))
            self._order.append(key)

    def remove(self, name: str) -> None:
        key = name.lower().strip()
        if self._items.remove(key) and key in self._order:
            self._order.remove(key)

    def update(self, name: str, *, price: float | None = None,
               qty: int | None = None) -> None:
        key = name.lower().strip()
        item: CartItem | None = self._items.get(key)
        if item is None:
            return
        if price is not None:
            item.price = float(price)
        if qty is not None:
            item.qty = max(1, int(qty))
        self._items.put(key, item)

    def clear(self) -> None:
        self._items = HashTable()
        self._order = []

    # --- accessors ----------------------------------------------------
    def items(self) -> list[CartItem]:
        return [self._items.get(k) for k in self._order]

    def total(self) -> float:
        return round(sum(it.line_total for it in self.items()), 2)

    def count(self) -> int:
        return sum(it.qty for it in self.items())

    def __iter__(self) -> Iterator[CartItem]:
        return iter(self.items())

    def __len__(self) -> int:
        return len(self._order)

    # --- algorithmic helpers -----------------------------------------
    def top_expensive(self, k: int = 3) -> list[CartItem]:
        """Uses the class-built max-heap priority queue."""
        dicts = [it.to_dict() for it in self.items()]
        top = top_k_expensive(dicts, k=k)
        # Return the CartItem instances, preserving order.
        out = []
        for d in top:
            ci = self._items.get(d["name"].lower().strip())
            if ci is not None:
                out.append(ci)
        return out

    def to_session_dicts(self) -> list[dict]:
        return [it.to_dict() for it in self.items()]


# -------------------------- Session ---------------------------------
@dataclass
class Session:
    id: int
    supermarket: str
    total: float
    created_at: datetime
    items: list[CartItem] = field(default_factory=list)

    @classmethod
    def from_rows(cls, session_row, item_rows) -> "Session":
        return cls(
            id=session_row["id"],
            supermarket=session_row["supermarket"],
            total=session_row["total"],
            created_at=datetime.fromisoformat(session_row["created_at"]),
            items=[
                CartItem(name=r["name"], price=r["price"], qty=r["qty"])
                for r in item_rows
            ],
        )
