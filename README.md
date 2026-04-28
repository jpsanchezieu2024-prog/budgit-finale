# Budgit 🛒

Smart grocery companion for university students on a budget.
Final project for **Algorithms & Data Structures — PPLE & BDBA, IE University.**

Team: Sofia Wiedemann, Tomás Bunge, Paolo Massihi, Juan Pablo Sánchez.

---

## Run it

```bash
pip install -r requirements.txt
streamlit run 🏠_Home.py
```

Then open the URL Streamlit prints (usually http://localhost:8501).

On first launch, click **Sign up**, enter a weekly budget and your
favourite supermarket, then **Start Shopping**.

---

## What's inside

| Layer       | File                          | What it does                                     |
|-------------|-------------------------------|--------------------------------------------------|
| UI          | `🏠_Home.py`                  | Welcome / login / dashboard                      |
|             | `pages/1_🛒_Shop.py`          | Live cart + Budget Rescue (Greedy vs DP)         |
|             | `pages/2_📜_History.py`       | Past sessions, sorted with **Merge Sort**        |
|             | `pages/3_📊_Compare.py`       | Per-store averages + product-level comparison    |
|             | `pages/4_⚙️_Profile.py`       | Edit budget / store / view learned prices        |
|             | `theme.py`                    | Shared Streamlit CSS                             |
| Domain      | `models.py`                   | `User`, `Product`, `Cart`, `CartItem`, `Session` |
| Persistence | `database.py`                 | SQLite (built into Python) — 4 tables            |
| Algorithms  | `algorithms/hash_table.py`    | HashTable with chaining (Session 9)              |
|             | `algorithms/bst.py`           | Binary Search Tree + prefix search (Session 17)  |
|             | `algorithms/sorting.py`       | Merge Sort & Quick Sort (Sessions 3 / 7)         |
|             | `algorithms/priority_queue.py`| Max-Heap Priority Queue (Session 13)             |
|             | `algorithms/greedy.py`        | Greedy + 0/1 Knapsack DP                         |
|             | `algorithms/search.py`        | Binary Search (Session 1)                        |

---

## Where the class algorithms actually run

* **Hash Table** → every `Cart` is backed by our own `HashTable`
  (`models.Cart._items`). Adding the same product twice bumps the
  quantity in O(1) average instead of scanning a list.
* **Binary Search Tree** → loaded on login with every learned product
  name. When the user starts typing in the Add-Item form, we call
  `bst.prefix_search("mi")` to surface "milk (1L)" instantly.
* **Merge Sort** → `pages/2_📜_History.py` sorts the sessions by
  `created_at` DESC using our own `merge_sort`, not SQL's `ORDER BY`.
* **Priority Queue (Max Heap)** → `top_k_expensive` in
  `algorithms/priority_queue.py` powers the "biggest expenses in your
  cart" view.
* **Greedy Method** → when the cart overshoots the budget we pop the
  priciest items off the PQ until it fits.
* **Dynamic Programming (0/1 Knapsack)** → the alternative "Optimal"
  mode in Budget Rescue picks the subset of items of maximum total
  price that still fits the budget.
* **OOP (Session 11)** → `User`, `Cart`, `CartItem`, `Session` are
  proper Python classes with `@dataclass`, encapsulated state, and
  computed properties like `CartItem.line_total`.

---

## Coverage against Submission 2 user stories

| Story                                       | Page                 | Status |
|---------------------------------------------|----------------------|--------|
| 1. Registration & budget setup              | `🏠_Home.py` / Profile | ✅   |
| 2. Add item + price learning                | Shop                 | ✅     |
| 3. Live cart, edit, remove, end session     | Shop                 | ✅     |
| 4. Shopping history & supermarket comparison| History + Compare    | ✅     |

Plus a bonus **Budget Rescue** feature (Greedy vs DP) that highlights
the trade-off between the two classes of algorithms covered in class.

---

## Data model

```
users            (id, name, email, password_hash, salt, weekly_budget, preferred_store)
products         (id, user_id, name, price, supermarket, updated_at)
sessions         (id, user_id, supermarket, total, created_at)
session_items    (id, session_id, name, price, qty)
```

The DB file `budgit.db` is created automatically next to `🏠_Home.py`.

