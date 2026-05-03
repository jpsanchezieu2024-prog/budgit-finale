# Budgit 🛒

> Smart grocery companion for university students on a budget.

Budgit is the final project for **Algorithms & Data Structures — PPLE & BDBA, IE University**. Every non-trivial operation in the app is powered by a data structure or algorithm we implemented from scratch in class — no `dict`, `heapq`, `sorted()`, or library shortcuts.

---

## Table of contents

1. [Description of the app](#1-description-of-the-app)
2. [Features](#2-features)
3. [Files](#3-files)
4. [Prerequisites and environment](#4-prerequisites-and-environment)
5. [Installation and execution](#5-installation-and-execution)
6. [Further improvements](#6-further-improvements)
7. [Bibliography and webgraphy](#7-bibliography-and-webgraphy)
8. [Credits](#8-credits)

---

## 1. Description of the app

Budgit is a multi-page Streamlit web application aimed at university students who shop on a tight weekly grocery budget. The app gives a student five things they currently don't have:

- **A live cart that respects a weekly budget**, with a colour-changing remaining-amount card that shifts smoothly from green through yellow to red as the week's spending approaches the limit.
- **Cross-user price intelligence.** When any Budgit user records the price of milk at Mercadona, every other user typing "milk" gets that price as an autofill — backed by a global Firestore directory and an in-memory hash table.
- **An over-budget rescue mode** that shows two algorithms side by side: a fast Greedy heuristic that drops the priciest items first, and a 0/1 Knapsack DP that finds the optimal subset within the remaining budget. The user can pick either result with one click.
- **Pre-shop store recommendation.** Build a grocery list on the List page; Budgit instantly tells you which supermarket gives the cheapest total basket using the global price directory.
- **A savings leaderboard** ranking users by the percentage of money they've saved by shopping at the cheaper supermarket relative to the most expensive option on file for each item — extracted with a Max-Heap Priority Queue and ranked in full with Merge Sort.

The interactive shopping flow is split across five pages: Home (welcome, login, dashboard), List (pre-shop list builder), Shop (live cart + Budget Rescue), History (past sessions, colour-coded per supermarket), Compare (savings leaderboard + global product prices), and Profile (edit budget and learned prices).

---

## 2. Features

### 2.1 Account and budget management

- **Sign-up and log-in** with SHA-256 password hashing and per-user random salts.
- **Weekly budget configuration** with a default of €40 and a per-user preferred supermarket.
- **Editable profile** — change your name, weekly budget, and preferred store at any time.

### 2.2 Live shopping session

- **Add items by name and price**, with quantity. Same item added twice bumps the quantity in O(1) (via the Cart's hash-table backing).
- **Smart autofill** of prices using a two-tier lookup: your own price memory at this store first, then the global directory.
- **Prefix-match autocomplete** on the item name field — typing "mi" surfaces "milk" instantly via a Binary Search Tree.
- **Live running total** with a percent-of-budget indicator and progress bar.

### 2.3 Budget Rescue (over-budget)

- **Greedy mode.** Drops the most expensive items first, using a Max-Heap Priority Queue. Fast (O(n log n)) but may leave money on the table.
- **Optimal mode.** Runs 0/1 Knapsack DP in cents to find the subset of items of maximum total value that still fits the budget.
- **Side-by-side display** of "keep" vs "put back" so the user can see the trade-off and apply the result with one click.

### 2.4 Pre-shop grocery list

- **Build a list** of items you need to buy with quantities.
- **Cheapest-store recommendation** — Budgit checks the global directory and tells you which supermarket gives the smallest total basket, plus per-item price breakdown.
- **One-click import to cart** with selectable items and editable prices; imported items are removed from the list automatically.

### 2.5 Shopping history

- **Past sessions sorted by date descending** using our own Merge Sort (deliberately not `ORDER BY`).
- **Per-supermarket colour-coded badges** so multi-store shoppers can tell at a glance where each session happened.
- **Expandable session detail** showing every line item and total.

### 2.6 Compare and leaderboard

- **Savings leaderboard.** Ranks users by lifetime % saved, with medals for the top 3 and a highlighted row for the current user. The user's exact rank is shown explicitly when they fall outside the top 10.
- **Global product prices** side-by-side across supermarkets, with a search box and a "save up to €X" indicator per item.

### 2.7 Visual polish

- **Dark mint-green theme** locked via `.streamlit/config.toml` so light-mode browsers don't break contrast.
- **Smooth budget gradient** interpolating between green, yellow, and red.
- **Cross-user state isolation** — logging in or signing up wipes all session-state from any previous user, preventing data leaks across browser sessions.

---

## 3. Files

The project is organised by responsibility. Each file is documented below.

### 3.1 Entry point and launcher

| File | Purpose |
| ---- | ------- |
| **`Launch Budgit.command`** | Double-click on macOS to install dependencies, verify the Firebase key, and launch the app in your browser. |
| **`🏠_Home.py`** | Streamlit entry point. Renders the welcome / log-in / sign-up tabs and the post-login dashboard with the budget card and weekly metrics. |

### 3.2 UI pages

Streamlit auto-discovers files in the `pages/` directory and turns each into a sidebar nav item.

| File | Purpose |
| ---- | ------- |
| **`pages/0_📝_List.py`** | Pre-shop grocery list builder; recommends the cheapest supermarket for the full basket. |
| **`pages/1_🛒_Shop.py`** | Live shopping session. Add items, edit quantities and prices, see the running total, trigger Budget Rescue when over budget, and end a session. |
| **`pages/2_📜_History.py`** | Past sessions sorted with our Merge Sort. Each session is colour-coded by supermarket. |
| **`pages/3_📊_Compare.py`** | Savings leaderboard plus per-item price comparison across stores from the global directory. |
| **`pages/4_⚙️_Profile.py`** | Edit name, weekly budget, preferred supermarket; view the user's learned prices. |

### 3.3 Core domain and data layer

| File | Purpose |
| ---- | ------- |
| **`models.py`** | OOP domain model. `User`, `Product`, `CartItem`, `Cart`, `Session` — all built as proper Python classes with `@dataclass`, encapsulated state, and computed properties. The `Cart` is backed by our hash table. |
| **`database.py`** | Firebase Firestore wrapper. Reads credentials from Streamlit secrets, an environment variable, or a local file. Defines all CRUD functions on the `users`, `products`, `sessions`, `session_items`, `item_directory`, and `grocery_lists` collections, plus the leaderboard counters. |
| **`state.py`** | Streamlit session-state plumbing. Initialises the cart, the in-memory hash table mirroring the global directory, and the BST of learned product names. |
| **`theme.py`** | Dark mint-green CSS injection plus the `budget_color()` helper that interpolates green→yellow→red as the budget is consumed. |
| **`requirements.txt`** | Pinned Python dependencies: `streamlit>=1.32`, `firebase-admin>=6.5`. |

### 3.4 Algorithms

Every data structure below is implemented from scratch using concepts covered in class. Each module has at least one production code path that exercises it; remove any one and the app breaks.

| File | Algorithm | Class session | Production use |
| ---- | --------- | ------------- | -------------- |
| **`algorithms/__init__.py`** | (package marker) | — | Marks `algorithms` as an importable Python package. |
| **`algorithms/hash_table.py`** | Hash Table with separate chaining + dynamic resizing | Session 9 | Backs `Cart._items` (O(1) item lookup); mirrors the global product directory in memory. |
| **`algorithms/bst.py`** | Binary Search Tree with prefix search | Session 17 | Powers the autocomplete on the Add-Item form. |
| **`algorithms/sorting.py`** | Merge Sort and Quick Sort | Sessions 3 / 7 | Sorts shopping history by date, ranks the leaderboard. |
| **`algorithms/priority_queue.py`** | Max-Heap Priority Queue | Session 13 | Top-k expensive items, Greedy budget rescue, top-K leaderboard extraction. |
| **`algorithms/greedy.py`** | Greedy Method + 0/1 Knapsack DP | Greedy / DP lectures | The two contrasting Budget Rescue modes. |
| **`algorithms/search.py`** | Binary Search and Linear Search | Session 1 | Helper utilities for sorted-list lookups. |
| **`algorithms/leaderboard.py`** | Composition of HashTable + PQ + Merge Sort | — | Computes per-session savings against the global directory and ranks all users. |

### 3.5 Configuration and secrets

| File | Purpose |
| ---- | ------- |
| **`.streamlit/config.toml`** | Streamlit configuration — pins the app to dark theme so light-mode browsers don't break the UI. |
| **`.gitignore`** | Excludes `firebase_key.json`, `__pycache__/`, `budgit.db` (legacy SQLite, no longer used), `.DS_Store`, and IDE folders. |
| **`firebase_key.json`** | Firebase service-account credentials. **NOT in the public repo** — must be present locally for the app to connect to Firestore. |
| **`README.md`** | This document. |

---

## 4. Prerequisites and environment

### 4.1 Operating system

Developed and tested on **macOS Sonoma (14.x) and Sequoia (15.x)** with Apple Silicon. The launcher script (`Launch Budgit.command`) is macOS-specific. Linux users can run `streamlit run "🏠_Home.py"` from a terminal directly. Windows users can use a `python -m streamlit run "🏠_Home.py"` command from PowerShell after installing the dependencies.

### 4.2 Python

- **Python 3.10 or newer** (tested on 3.10, 3.11, 3.12, 3.13).
- Comes pre-installed on most macOS systems via Xcode Command Line Tools, otherwise download from <https://www.python.org/downloads/>.

### 4.3 Python libraries

Pinned in `requirements.txt` and installed automatically by the launcher on first run:

| Library | Minimum version | Purpose |
| ------- | --------------- | ------- |
| **`streamlit`** | 1.32 | Multi-page web framework that powers the UI, sessions, navigation, and theming. |
| **`firebase-admin`** | 6.5 | Firebase Admin SDK; talks to Firestore for persistence and to Google's auth servers for service-account authentication. |

The Firebase Admin SDK transitively pulls in `google-cloud-firestore`, `google-auth`, `grpcio`, and a few other Google libraries. They are installed automatically.

### 4.4 External services

- **Firebase project with Firestore enabled** (free tier is plenty). The project's service-account JSON must be placed in the project root as `firebase_key.json` — it will not be in the ZIP for security reasons and is provided separately.

---

## 5. Installation and execution

The launcher does everything for you. No commands need to be typed in a terminal.

### 5.1 What you need beforehand

- A Mac running macOS 14 (Sonoma) or newer with Python 3.10+ installed.
- An internet connection (only required on the very first launch, to download `streamlit` and `firebase-admin`).
- The `firebase_key.json` file (provided separately to your professor — see the submission cover page).

### 5.2 Step-by-step

#### Step 1 — Download the project

Click **Code → Download ZIP** on the project's GitHub page (or use the ZIP attached to the submission). Save it somewhere convenient like the Desktop.

#### Step 2 — Unzip

Double-click the downloaded `.zip` file. Finder will create a folder called `Budgit` (or `Budgit-main`) next to the ZIP.

#### Step 3 — Drop the Firebase key into the folder

Move the `firebase_key.json` file (provided separately) into the unzipped `Budgit` folder, alongside `🏠_Home.py` and `Launch Budgit.command`. The folder should now contain that file at the root level.

#### Step 4 — Launch the app

Double-click **`Launch Budgit.command`**.

A Terminal window opens and shows messages like *"Starting Budgit"*. On the very first launch only, it spends ~30 seconds installing `streamlit` and `firebase-admin`. On every subsequent launch it skips straight to opening the app, which usually takes ~3 seconds.

#### Step 5 — Use the app

Your default browser opens automatically at **<http://localhost:8501>** showing the Budgit welcome screen. Click **Sign up**, enter a name, email, password, weekly budget and preferred supermarket, then **Create account**. You're in.

#### Step 6 — Stop the app when you're done

Close the Terminal window that the launcher opened, or focus it and press `Ctrl + C`. The browser tab can be closed at any time.

### 5.3 First-time-only macOS Gatekeeper warning

The first time you double-click `Launch Budgit.command`, macOS may show a warning saying the file is from an unidentified developer. To allow it:

1. Right-click (or `Ctrl`-click) the `Launch Budgit.command` file.
2. Choose **Open** from the menu.
3. In the dialog that appears, click **Open** again.

You only need to do this once — subsequent double-clicks work normally.

### 5.4 Troubleshooting

| Symptom | Cause | Fix |
| ------- | ----- | --- |
| Terminal shows "Python isn't installed" | macOS without Xcode CLT | Install Python from <https://www.python.org/downloads/>, then re-launch. |
| Terminal shows "firebase_key.json is missing" | Step 3 was skipped | Place `firebase_key.json` in the same folder as `Launch Budgit.command` and re-launch. |
| Browser opens but page won't load | Streamlit hasn't finished booting | Wait 5 more seconds and refresh `http://localhost:8501`. |
| App starts but sign-up hangs | First-time Firestore connection (cold start) | Wait up to 10 seconds — subsequent operations are fast. |

---

## 6. Further improvements

If this were a v2, the priorities would be:

- **Friends and household mode.** Shared grocery lists and shared budgets for roommates, with a friend graph powered by BFS over a Firestore `friendships` collection — exercising another graph algorithm we touched on in class.
- **Streaks and achievements.** Gamify weekly under-budget performance with badges, weekly challenges, and a "lifetime saved" counter on the dashboard. Strong retention driver.
- **Migration to Firebase Authentication.** Replace the homemade SHA-256 password hashing with managed auth — gives password reset, email verification, and OAuth providers (Google, Apple) for free.
- **Memoised DP for daily budget caps.** Given remaining budget and remaining days in the week, suggest an optimal per-day spending cap that minimises overshoot probability.
- **Receipt OCR.** Scan a paper receipt with the phone camera and extract items + prices into a session automatically. Uses Apple Vision or Tesseract.
- **Bilingual UI (EN / ES).** The user base is mostly Spain-based students, so translating the chrome would land well.
- **A live demo URL.** The Streamlit Community Cloud deployment is straightforward but requires the Firebase secret to be configured server-side; we kept the project local-only for the academic submission so no credentials need to leak.

---

## 7. Bibliography and webgraphy

### 7.1 Course materials

- **Algorithms & Data Structures**, PPLE & BDBA, IE University. Sessions 1, 3, 7, 9, 11, 13, 17 are referenced in the source code where each algorithm appears.

### 7.2 Books

- Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C. (2022). *Introduction to Algorithms* (4th ed.). MIT Press. — Reference for Merge Sort, Quick Sort, BST, Binary Heap, Greedy Method, and 0/1 Knapsack Dynamic Programming.
- Sedgewick, R., & Wayne, K. (2011). *Algorithms* (4th ed.). Addison-Wesley. — Reference for hash tables with separate chaining and priority queue implementation idioms.

### 7.3 Software documentation

- Streamlit official documentation. <https://docs.streamlit.io>
- Firebase Admin Python SDK documentation. <https://firebase.google.com/docs/admin/setup>
- Cloud Firestore Python client reference. <https://googleapis.dev/python/firestore/latest/index.html>
- Python 3 standard library reference. <https://docs.python.org/3/library/>

### 7.4 Articles and blog posts consulted

- "How to deploy Streamlit apps with Firebase backends." Streamlit Community Forum. <https://discuss.streamlit.io>
- "Service account authentication best practices." Google Cloud documentation. <https://cloud.google.com/iam/docs/best-practices-service-accounts>

### 7.5 Course-level inspiration

The Greedy-vs-DP juxtaposition in the Budget Rescue feature is directly inspired by the comparative discussion of greedy algorithms and dynamic programming in the course's lecture series. The Hash Table and BST implementations follow the structures presented in class with no external modifications.

---

## 8. Credits

### 8.1 Project team

- **Sofia Wiedemann**
- **Tomás Bunge**
- **Paolo Massihi**
- **Juan Pablo Sánchez**

### 8.2 Course

- **Algorithms & Data Structures**
- Programmes: PPLE (Politics, Philosophy, Law and Economics) & BDBA (Bachelor in Data and Business Analytics)
- Institution: **IE University**, Madrid / Segovia
- Academic year: 2025–2026

### 8.3 Acknowledgements

Thanks to the course teaching team for the structured progression from basic search algorithms to dynamic programming over the semester — the depth made it possible to ship a project where every algorithm has a real production purpose, not just a tutorial-style demo.

---

*Built with care for the Algorithms & Data Structures course at IE University.*
