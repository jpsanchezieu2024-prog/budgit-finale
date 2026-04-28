# Budgit 🛒

> Smart grocery companion for university students on a budget.

Budgit helps students track spending, compare supermarket prices in real
time, and never panic at the checkout again. It's the final project for
**Algorithms & Data Structures — PPLE & BDBA, IE University**, and every
non-trivial operation in the app is powered by a data structure or
algorithm we built from scratch in class.

**Team:** Sofia Wiedemann · Tomás Bunge · Paolo Massihi · Juan Pablo Sánchez

---

## Table of contents

1. [What Budgit does](#what-budgit-does)
2. [Tech stack](#tech-stack)
3. [Where the class algorithms actually run](#where-the-class-algorithms-actually-run)
4. [Project structure](#project-structure)
5. [Data model](#data-model)
6. [Local setup](#local-setup)
7. [Deployment to Streamlit Community Cloud](#deployment-to-streamlit-community-cloud)
8. [How key features work under the hood](#how-key-features-work-under-the-hood)
9. [Coverage against the assignment user stories](#coverage-against-the-assignment-user-stories)
10. [Privacy and security notes](#privacy-and-security-notes)
11. [Roadmap](#roadmap)

---

## What Budgit does

Budgit is a multi-page Streamlit web app aimed at university students
who shop on a tight weekly grocery budget. The app does five things:

- **Tracks the weekly budget** with a colour-changing remaining-amount
  card on the home dashboard, plus a daily-spend recommendation that
  adjusts as the week progresses.
- **Runs a live shopping session** where the user adds items by name
  and price as they walk through the store; prices auto-fill from
  history; the running cart total stays visible at the top.
- **Rescues over-budget carts** using two contrasting algorithms — a
  fast Greedy heuristic and an optimal 0/1 Knapsack DP — and shows the
  trade-off side by side so the user (and the rubric) can see both
  paradigms in action.
- **Remembers prices across users** in a global Firestore directory,
  so when one Budgit user logs that "milk costs €0.89 at Mercadona",
  every other user typing "milk" gets that price as an autofill.
- **Builds a savings leaderboard** ranking users by the percentage of
  money they've saved by shopping at the cheaper supermarket relative
  to the most expensive option on file for each item.

It also includes a grocery-list builder that pre-shopping recommends
the cheapest supermarket for the user's full basket, a per-store
shopping history with colour-coded supermarket badges, and a profile
page for editing the weekly budget and preferred store.

---

## Tech stack

| Layer        | Choice                                  | Why                                                                            |
| ------------ | --------------------------------------- | ------------------------------------------------------------------------------ |
| UI           | Streamlit (`>=1.32`)                    | Pure Python, multi-page out of the box, hosted free on Streamlit Cloud         |
| Persistence  | Firebase Firestore                      | Free tier, schemaless, real-time-ish, syncs prices across all users            |
| Auth         | Custom SHA-256 + per-user salt          | Demonstrates password hashing without third-party magic                        |
| Algorithms   | Pure Python, all hand-implemented       | Mandated by the course brief — no `dict`, `heapq`, or `sorted()` shortcuts     |
| Theming      | Custom CSS injected via `theme.py`      | Dark mint-green palette, locked to dark mode via `.streamlit/config.toml`      |
| Hosting      | Streamlit Community Cloud               | Free, GitHub-native, redeploys on every push                                   |

Required packages are pinned in `requirements.txt`:

```
streamlit>=1.32
firebase-admin>=6.5
```

---

## Where the class algorithms actually run

Every data structure below was implemented from scratch under
`algorithms/` and has at least one production code path that exercises
it. None of them are demos — removing any one breaks the app.

| Class topic                  | Implementation                  | Production use                                                                                                                                        |
| ---------------------------- | ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Hash Tables (Session 9)      | `algorithms/hash_table.py`      | (a) Backs `Cart._items` so re-adding the same product bumps quantity in O(1). (b) Holds the in-memory mirror of the global price directory.           |
| Binary Search Tree (S. 17)   | `algorithms/bst.py`             | Loaded on login with every product name the user has ever bought. Powers the prefix-match autocomplete on the Add-Item form.                          |
| Merge Sort (Sessions 3 / 7)  | `algorithms/sorting.py`         | (a) History page orders sessions by `created_at` DESC. (b) Compare page produces the full ranked savings leaderboard.                                 |
| Quick Sort (Sessions 3 / 7)  | `algorithms/sorting.py`         | Available alongside merge sort for completeness; merge_sort is preferred where stability matters.                                                     |
| Max-Heap Priority Queue (13) | `algorithms/priority_queue.py`  | (a) "Top-k expensive items" view. (b) Greedy budget rescue. (c) Top-K extraction on the savings leaderboard.                                          |
| Greedy Method                | `algorithms/greedy.py`          | Budget Rescue's "drop the priciest items first" mode — fast, may not be optimal.                                                                      |
| Dynamic Programming (0/1 KP) | `algorithms/greedy.py`          | Budget Rescue's "Optimal" mode — picks the subset of items maximising kept value within the remaining budget. O(n · W) over cents.                    |
| Binary Search (Session 1)    | `algorithms/search.py`          | Helper for sorted-list lookups; included for completeness.                                                                                            |
| OOP (Session 11)             | `models.py`                     | `User`, `Product`, `CartItem`, `Cart`, `Session` are all real classes with encapsulation, computed properties, and dataclasses where appropriate.     |
| Pure compute (composition)   | `algorithms/leaderboard.py`     | Combines the Hash Table (price lookup), the Priority Queue (top-K), and Merge Sort (full ranking) to power the savings leaderboard.                   |

The two algorithm classes the course contrasted — **Greedy vs Dynamic
Programming** — are deliberately exposed side-by-side in the Budget
Rescue UI so the trade-off is tangible: the Greedy answer is instant
but potentially leaves money on the table; the DP answer is provably
optimal but takes O(n · W) time.

---

## Project structure

```
Budgit/
├── 🏠_Home.py                     # Streamlit entry — welcome / login / dashboard
├── pages/                          # Streamlit auto-discovers these as nav pages
│   ├── 0_📝_List.py                # Pre-shop grocery list + cheapest-store recommendation
│   ├── 1_🛒_Shop.py                # Live shopping session + Budget Rescue
│   ├── 2_📜_History.py             # Past sessions sorted with merge_sort, badged per store
│   ├── 3_📊_Compare.py             # Savings leaderboard + global product-level prices
│   └── 4_⚙️_Profile.py              # Edit budget / preferred store, view learned prices
├── algorithms/                     # All hand-built data structures
│   ├── __init__.py
│   ├── hash_table.py               # Separate-chaining hash table with dynamic resizing
│   ├── bst.py                      # Binary search tree + prefix search
│   ├── sorting.py                  # Merge sort + quick sort
│   ├── priority_queue.py           # Max-heap PQ + top_k_expensive helper
│   ├── greedy.py                   # Greedy fit + 0/1 Knapsack DP
│   ├── search.py                   # Binary + linear search
│   └── leaderboard.py              # Savings computation + heap-based ranking
├── models.py                       # User / Product / CartItem / Cart / Session
├── database.py                     # Firestore wrapper + auth helpers
├── state.py                        # Streamlit session-state plumbing
├── theme.py                        # Dark mint-green CSS + budget colour helpers
├── requirements.txt
├── .streamlit/
│   └── config.toml                 # Pins the app to dark theme
├── .gitignore                      # Excludes firebase_key.json, __pycache__, etc.
├── firebase_key.json               # Service-account credentials — NOT in git
└── Launch Budgit.command           # Double-clickable macOS launcher for local dev
```

---

## Data model

The app uses six Firestore collections. None of the documents reference
each other directly — joins happen in the application layer.

| Collection         | Document shape                                                                                                                                            | Purpose                                                                                                                          |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `users`            | `{ name, email, password_hash, salt, weekly_budget, preferred_store, lifetime_saved, lifetime_could_have_spent, lifetime_sessions_counted }`              | One per user. The three `lifetime_*` counters are denormalised aggregates that power the savings leaderboard without extra reads. |
| `products`         | `{ user_id, name, price, supermarket, updated_at }` keyed by `<user_id>_<name>_<store>`                                                                   | Per-user price memory: the last price *this* user paid for *this* item at *this* store. Drives the personal autofill.            |
| `item_directory`   | `{ name, prices: { Mercadona: 0.89, Lidl: 0.75, … }, last_updated, times_added }` keyed by normalised item name                                            | Global price directory shared by all users. The "milk costs X at Y" knowledge graph.                                              |
| `sessions`         | `{ user_id, supermarket, total, created_at }`                                                                                                             | One completed shopping trip per document.                                                                                         |
| `session_items`    | `{ session_id, name, price, qty }`                                                                                                                        | The line items of each session.                                                                                                  |
| `grocery_lists`    | `{ user_id, items: [{name, qty}], updated_at }` keyed by `user_id`                                                                                        | One pre-shop list per user. Imported into the cart and decremented as items are imported.                                         |

The legacy `budgit.db` SQLite file is no longer used and is included
in `.gitignore`. Earlier prototypes used SQLite; the move to Firestore
made price-sharing across users trivial.

---

## Local setup

### 1. Prerequisites

- Python 3.10 or newer
- A Firebase project with Firestore enabled (free tier is fine)
- A Firebase service-account key JSON file

### 2. Clone and install

```bash
git clone https://github.com/<your-username>/budgit-final.git
cd budgit-final
pip install -r requirements.txt
```

### 3. Add your Firebase credentials

Create a Firebase project at <https://console.firebase.google.com>,
enable Firestore, and download a service-account key from
**Project settings → Service accounts → Generate new private key**.
Save the JSON as `firebase_key.json` in the project root.

> ⚠️ **`firebase_key.json` is in `.gitignore` and must never be
> committed.** Anyone with this file has full read/write access to
> your Firestore database. If it ever leaks, immediately rotate the
> key in the Firebase console and revoke the old one.

### 4. Run

```bash
streamlit run 🏠_Home.py
```

Streamlit prints a local URL (typically <http://localhost:8501>).
Open it, sign up, enter a weekly budget and a preferred supermarket,
and start shopping.

macOS users can also double-click **Launch Budgit.command** to
auto-install Streamlit on first run and start the app in one step.

---

## Deployment to Streamlit Community Cloud

The hosted version uses Streamlit's free cloud, which redeploys on
every push to `main`.

1. Push the project to a GitHub repo. **Make sure
   `firebase_key.json` is excluded** — the included `.gitignore`
   handles this.
2. Go to <https://share.streamlit.io>, sign in with GitHub, and
   click **Create app → Deploy a public app from GitHub**.
3. Fill in:
   - Repository: `<your-username>/budgit-final`
   - Branch: `main`
   - Main file path: `🏠_Home.py`
   - App URL: pick any subdomain
4. Click **Advanced settings** and paste your service-account
   credentials in the **Secrets** box, formatted as TOML under a
   `[firebase]` table:

```toml
[firebase]
type                        = "service_account"
project_id                  = "your-project-id"
private_key_id              = "..."
private_key                 = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email                = "firebase-adminsdk-xxxxx@your-project-id.iam.gserviceaccount.com"
client_id                   = "..."
auth_uri                    = "https://accounts.google.com/o/oauth2/auth"
token_uri                   = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url        = "..."
universe_domain             = "googleapis.com"
```

The `private_key` field is the awkward one: copy the value out of
your JSON file *as-is*, keeping the literal `\n` escape sequences,
and surround it with double quotes in TOML.

5. Click **Deploy**. First build takes 1-2 minutes while
   `firebase-admin` installs.

`database.py` automatically prefers `st.secrets["firebase"]` in
hosted mode and falls back to the local `firebase_key.json` for
development, so the same code runs in both environments.

---

## How key features work under the hood

### Price learning across users

Every time anyone adds an item with a price, three writes happen
in lock-step:

1. `products/{user_id}_{name}_{store}` — the user's personal memory.
2. `item_directory/{name}` — the global directory's `prices` map for
   that store gets updated, plus a `times_added` counter.
3. `state.update_directory_in_memory()` — the in-memory `HashTable`
   mirror is patched immediately so subsequent autofill on the same
   page render is O(1) without re-reading Firestore.

When the user types in the Add-Item form, autofill priority is:
personal memory → global directory → blank.

### Budget Rescue (Greedy vs DP)

When `cart.total() > user.weekly_budget`, the Shop page exposes two
algorithms via a radio toggle:

- **Greedy** (`greedy_fit` in `algorithms/greedy.py`) repeatedly pops
  the most expensive item off a max-heap until the cart fits. O(n log n).
- **0/1 Knapsack DP** (`knapsack_fit` in the same module) treats item
  prices as both weight and value, runs in cents to keep weights
  integer, and back-tracks through the DP table to recover the optimal
  kept subset. O(n · W).

The UI shows "Keep" and "Put back" columns side by side so the user
can apply the result with one click. Both algorithms write to the
same data structure, so toggling between them is instantaneous.

### Savings leaderboard

The leaderboard ranks users by *percentage of money saved by shopping
at the cheaper supermarket*, computed lifetime across every session
they've completed.

For each session item:

```
ceiling   = max(prices[item] across all stores in the directory)
ceiling   = max(ceiling, price_paid)        # never go negative
saved    += (ceiling - price_paid) * qty
could_have += ceiling * qty
```

Items only ever seen at one store are excluded — there's nothing to
compare against, so they would distort the percentage.

The numbers are stored as three denormalised counters on each user
document (`lifetime_saved`, `lifetime_could_have_spent`,
`lifetime_sessions_counted`) so the leaderboard reads N user docs
once instead of recomputing across every session on every view.
Counters increment atomically on `save_session()` via Firestore's
`Increment(...)`, and a one-shot lazy `backfill_user_savings()` runs
the first time a user is encountered without the counters set, so
existing accounts get migrated transparently.

The ranking itself uses both class algorithms:

- **Top-K extraction** with `MaxHeapPQ` — semantically the right
  choice when N >> K. O(N log K).
- **Full ranking** with `merge_sort` for finding the current user's
  rank when they fall outside the top 10.

A user needs at least three counted sessions to qualify, so a single
lucky shop can't dominate.

### Smart store recommendation (List page)

The grocery list page asks one question: "where should I buy this
basket?" For each item, it does an O(1) lookup in the in-memory
directory `HashTable` for the prices map, then sums per-store totals
and ranks ascending. The cheapest store wins; coverage (how many
items have a price at that store) is shown as a confidence indicator.

### Smooth budget colour gradient

`theme.budget_color(pct_used)` interpolates linearly between three
RGB anchor points — mint green at 0% spent, warm yellow at 50%, soft
red at 100%+ — so the dashboard's "remaining" amount fades through
every shade in between as the week progresses. Beyond 100% the
colour clamps at red.

### Per-supermarket badges in History

Each supermarket has a deterministic emoji + accent colour
(Mercadona green, Lidl yellow, Carrefour blue, etc.) defined in
`pages/2_📜_History.py`. The History page renders a chip row at the
top showing every store the user has shopped at; each session card
gets a coloured left-border so the visual rhythm of multi-store
shoppers is unmistakable.

### Cross-user state isolation

When a user logs in or signs up, `_switch_user()` in `🏠_Home.py`
explicitly wipes every key in Streamlit's session state that holds
data tied to the previous account — cart, BST, item directory,
shop store, grocery list, autocomplete typing buffer. Without this,
two users sharing the same browser tab can leak each other's data.

---

## Coverage against the assignment user stories

| Story                                            | Where it lives                       | Status |
| ------------------------------------------------ | ------------------------------------ | ------ |
| 1. Registration & weekly budget setup            | `🏠_Home.py` + Profile page          | ✅     |
| 2. Add item + price learning                     | Shop page                            | ✅     |
| 3. Live cart, edit, remove, end session          | Shop page                            | ✅     |
| 4. Shopping history + supermarket comparison     | History + Compare pages              | ✅     |

**Bonus features** that go beyond the brief:

- **Budget Rescue** (Greedy vs DP) for the over-budget case.
- **Pre-shop grocery list** with cheapest-store recommendation.
- **Cross-user price directory** so the autofill works for new users
  on day one.
- **Savings leaderboard** with multi-algorithm ranking.
- **Smooth colour-coded budget gradient** on the dashboard.

---

## Privacy and security notes

- **Passwords** are hashed with SHA-256 and a random per-user salt.
  This is fine for a class project but is **not** what we'd ship to
  real users — production would use Firebase Authentication for
  password handling, email verification, and reset flows out of the
  box.
- **The Firebase service-account key** lives only on developer
  machines (`firebase_key.json`, gitignored) and in Streamlit Cloud's
  Secrets store (`[firebase]` table). It is never in source control.
- **Names on the leaderboard** are rendered as "First L." (first name
  + last initial) by `algorithms.leaderboard.display_name` so users
  can recognise themselves without exposing identities to strangers.
- **No third-party data** is collected, sold, or shared. The app
  speaks only to your own Firestore.

---

## Roadmap

Things we'd build if this were a v2:

- **Friends and household mode** — shared grocery lists and budgets
  for roommates, with a friend graph that would let us reuse BFS
  from a future class session.
- **Streaks and achievements** — gamify weekly under-budget
  performance with badges, weekly challenges, and a "lifetime saved"
  counter on the dashboard.
- **Move auth to Firebase Authentication** — password reset, email
  verification, optional 2FA, OAuth providers.
- **Memoised DP for daily budget caps** — given remaining budget and
  remaining days in the week, suggest an optimal per-day spending
  cap that minimises overshoot probability.
- **Bilingual UI (EN / ES)** — the user base is mostly Spain-based
  students, so translating the chrome would be a quick win.
- **Receipt OCR** — scan a receipt with the phone camera and let the
  app extract items and prices into a session automatically.

---

Built with care for the Algorithms & Data Structures course at IE
University. Pull requests, bug reports, and theme remixes are all
welcome.
