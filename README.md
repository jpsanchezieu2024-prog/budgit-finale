# Budgit 🛒

> No more checkout panic. Ever.

Budgit is the final project for **Algorithms & Data Structures — PPLE & BDBA, IE University**. Every non-trivial operation in the app is powered by a data structure or algorithm implemented from scratch — no `dict`, `heapq`, `sorted()`, or library shortcuts.

---

## 🌐 Live app

**[https://budgit.up.railway.app/](https://budgit.up.railway.app/)**

The app is hosted on Railway and connects to a live Firebase Firestore database. No installation required. Open the link, create an account, and start shopping.

### Getting started in 60 seconds

1. Open **[https://budgit.up.railway.app/](https://budgit.up.railway.app/)**
2. Click **Sign up**
3. Enter your name, email, password, weekly grocery budget, and preferred supermarket
4. Click **Create account** — you're in!

---

## Table of contents

1. [Description of the app](#1-description-of-the-app)
2. [Features](#2-features)
3. [Files](#3-files)
4. [Running locally](#4-running-locally)
5. [Further improvements](#6-further-improvements)
6. [Bibliography and webgraphy](#7-bibliography-and-webgraphy)
7. [Credits](#8-credits)

---

## 1. Description of the app

Budgit is a multi-page Streamlit web application aimed at university students who shop on a tight weekly grocery budget. The app gives a student five things they currently don't have:

- **A live cart that respects a weekly budget**, with a colour-changing remaining-amount card that shifts smoothly from green through yellow to red as the week's spending approaches the limit.
- **Cross-user price intelligence.** When any Budgit user records the price of milk at Mercadona, every other user typing "milk" gets that price as an autofill — backed by a global Firestore directory and an in-memory hash table.
- **Receipt verification.** Upload a photo of your receipt after shopping — Google Vision OCR extracts the items and prices and cross-checks them against what you entered, marking verified prices with a ✅ in the shared database.
- **An over-budget rescue mode** that shows two algorithms side by side: a fast Greedy heuristic that drops the priciest items first, and a 0/1 Knapsack DP that finds the optimal subset within the remaining budget. The user can pick either result with one click.
- **Pre-shop store recommendation.** Build a grocery list on the List page; Budgit instantly tells you which supermarket gives the cheapest total basket using the global price directory.
- **A savings leaderboard** ranking users by the percentage of money they've saved by shopping at the cheaper supermarket relative to the most expensive option on file for each item — extracted with a Max-Heap Priority Queue and ranked in full with Merge Sort.


The interactive shopping flow is split across five pages: Home (welcome, login, dashboard), List (pre-shop list builder), Shop (live cart + Budget Rescue), History (past sessions, colour-coded per supermarket), and Compare (savings leaderboard + global product prices).

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
- **Cross-store price comparison** chips showing the cheapest store for each product as you type, with a ✅ badge on receipt-verified prices.

### 2.3 Receipt verification (OCR)

- **Upload a receipt photo** in the End Session dialog after shopping.
- Google Cloud Vision reads the receipt and extracts item names and prices.
- Budgit fuzzy-matches the receipt lines against your cart items.
- Matched items are marked **verified (✅)** in the shared global price database.
- Unverified prices still appear for all users — the ✅ badge simply signals receipt-confirmed accuracy.
- Works best with a clear, flat photo of the receipt in good lighting.

### 2.4 Budget Rescue (over-budget)

- **Greedy mode.** Drops the most expensive items first using a Max-Heap Priority Queue. Fast (O(n log n)) but may leave money on the table.
- **Optimal mode.** Runs 0/1 Knapsack DP in cents to find the subset of items of maximum total value that still fits the budget.
- **Side-by-side display** of "keep" vs "put back" so the user can see the trade-off and apply the result with one click.

### 2.5 Pre-shop grocery list

- **Build a list** of items you need to buy with quantities.
- **Cheapest-store recommendation** — Budgit checks the global directory and tells you which supermarket gives the smallest total basket, plus per-item price breakdown.
- **One-click import to cart** with selectable items and editable prices; imported items are removed from the list automatically.

### 2.6 Shopping history

- **Past sessions sorted by date descending** using our own Merge Sort (deliberately not `ORDER BY`).
- **Per-supermarket colour-coded badges** so multi-store shoppers can tell at a glance where each session happened.
- **Expandable session detail** showing every line item and total.

### 2.7 Compare and leaderboard

- **Savings leaderboard.** Ranks users by lifetime % saved, with medals for the top 3 and a highlighted row for the current user. The user's exact rank is shown when they fall outside the top 10.
- **Global product prices** side-by-side across supermarkets, with a search box and a "save up to €X" indicator per item. Verified prices are marked ✅.



---

## 3. Files

### 3.1 Entry point and launcher

| File | Purpose |
| ---- | ------- |
| **`🏠_Home.py`** | Streamlit entry point. Renders the welcome / log-in / sign-up tabs and the post-login dashboard. |
| **`Launch Budgit.command`** | macOS double-click launcher. Installs dependencies and opens the app. |

### 3.2 UI pages

| File | Purpose |
| ---- | ------- |
| **`pages/0_📝_List.py`** | Pre-shop grocery list builder; recommends the cheapest supermarket for the full basket. |
| **`pages/1_🛒_Shop.py`** | Live shopping session, Budget Rescue, and receipt verification. |
| **`pages/2_📜_History.py`** | Past sessions sorted with Merge Sort, colour-coded by supermarket. |
| **`pages/3_📊_Compare.py`** | Savings leaderboard and per-item price comparison across stores. |
| **`pages/4_⚙️_Profile.py`** | Edit name, weekly budget, preferred supermarket; view learned prices. |

### 3.3 Core domain and data layer

| File | Purpose |
| ---- | ------- |
| **`models.py`** | `User`, `Product`, `CartItem`, `Cart`, `Session` — all proper Python classes. The `Cart` is backed by the hash table. |
| **`database.py`** | Firebase Firestore wrapper. All CRUD functions for users, products, sessions, items, the global directory, grocery lists, leaderboard counters, badges, and receipt uploads. |
| **`state.py`** | Streamlit session-state plumbing. Initialises the cart, the in-memory hash table, and the BST of learned product names. |
| **`ocr.py`** | Google Cloud Vision receipt parser. Extracts item names and prices from a receipt photo and fuzzy-matches them against the cart. |
| **`theme.py`** | Dark mint-green CSS injection and the `budget_color()` gradient helper. |

### 3.4 Algorithms

| File | Algorithm | Production use |
| ---- | --------- | -------------- |
| **`algorithms/hash_table.py`** | Hash Table with separate chaining + dynamic resizing | Backs `Cart._items` (O(1) lookup); mirrors global price directory in memory |
| **`algorithms/bst.py`** | Binary Search Tree with prefix search | Powers autocomplete on the Add-Item form |
| **`algorithms/sorting.py`** | Merge Sort and Quick Sort | Sorts shopping history by date; ranks leaderboard |
| **`algorithms/priority_queue.py`** | Max-Heap Priority Queue | Top-k expensive items; Greedy budget rescue; top-K leaderboard extraction |
| **`algorithms/greedy.py`** | Greedy Method + 0/1 Knapsack DP | The two contrasting Budget Rescue modes |
| **`algorithms/search.py`** | Binary Search and Linear Search | Sorted-list lookup helpers |
| **`algorithms/leaderboard.py`** | HashTable + PQ + Merge Sort | Computes per-session savings and ranks all users |

---

## 4. Running locally

The live app at **[https://budgit.up.railway.app/](https://budgit.up.railway.app/)** is the recommended way to use Budgit. Running locally is only necessary if you want to inspect or modify the source code.

### 4.1 What you need

| Requirement | Notes |
| ----------- | ----- |
| **Python 3.10 or newer** | Download from [python.org](https://www.python.org/downloads/) if not installed. Check with `python3 --version` in a terminal. |
| **pip** | Comes bundled with Python 3.10+. Check with `pip --version`. |
| **`firebase_key.json`** | The Firebase service-account credentials file. **Not included in the repo for security reasons.** Provided separately to the professor if requested. |
| **Internet connection** | Required on first run to install dependencies and connect to Firestore. |

### 4.2 Step-by-step — macOS (recommended)

#### Step 1 — Download the project

GitHub repository link: https://github.com/jpsanchezieu2024-prog/budgit-finale

Go to the GitHub repository and click **Code → Download ZIP**. Save the ZIP to your Desktop or Downloads folder.

Alternatively, if you have Git installed:
```bash
git clone https://github.com/jpsanchezieu2024-prog/budgit-finale
cd budgit
```

#### Step 2 — Unzip

Double-click the downloaded `.zip` file. Finder creates a folder called `Budgit` (or `Budgit-main`) next to the ZIP.

#### Step 3 — Add the Firebase key

Move the `firebase_key.json` file into the unzipped `Budgit` folder, **at the root level** alongside `🏠_Home.py` and `Launch Budgit.command`. The folder structure should look like this:

```
Budgit/
├── 🏠_Home.py
├── Launch Budgit.command   ← launcher
├── firebase_key.json       ← place it here
├── database.py
├── state.py
├── ocr.py
├── requirements.txt
├── pages/
└── algorithms/
```

If `firebase_key.json` is in the wrong location, the app will crash with a `RuntimeError: No Firebase credentials were found` message.

#### Step 4 — Launch the app

Double-click **`Launch Budgit.command`**.

A Terminal window opens. On the **very first launch only**, it installs `streamlit`, `firebase-admin`, `google-cloud-vision`, and their dependencies (~30–60 seconds depending on your connection). On every subsequent launch it goes straight to starting the app (~3 seconds).

Your default browser opens automatically at **http://localhost:8501**.

#### Step 5 — macOS Gatekeeper warning (first time only)

macOS may show a warning: *"Launch Budgit.command" can't be opened because it is from an unidentified developer.*

To allow it:
1. Right-click (or `Ctrl`-click) the `Launch Budgit.command` file.
2. Choose **Open** from the context menu.
3. In the dialog that appears, click **Open** again.

You only need to do this once.

#### Step 6 — Stop the app

Close the Terminal window, or click inside it and press `Ctrl + C`.

---

### 4.3 Step-by-step — Windows

Windows does not support the `.command` launcher. Run the app manually from PowerShell or Command Prompt.

#### Step 1 — Download and unzip the project

Download the ZIP from GitHub and extract it to a folder, for example `C:\Users\YourName\Desktop\Budgit`.

#### Step 2 — Add the Firebase key

Place `firebase_key.json` at the root of the extracted folder, next to `🏠_Home.py`.

#### Step 3 — Open PowerShell in the project folder

Hold `Shift` and right-click inside the `Budgit` folder in File Explorer. Choose **Open PowerShell window here** (or **Open in Terminal** on Windows 11).

#### Step 4 — Create a virtual environment (recommended)

```powershell
python -m venv venv
.\venv\Scripts\activate
```

You should see `(venv)` at the start of the prompt.

#### Step 5 — Install dependencies

```powershell
pip install -r requirements.txt
```

This installs Streamlit, Firebase Admin SDK, Google Cloud Vision, and all dependencies. Takes ~1–2 minutes on first run.

#### Step 6 — Run the app

```powershell
python -m streamlit run "🏠_Home.py"
```

Your browser opens at **http://localhost:8501**.

#### Step 7 — Stop the app

Press `Ctrl + C` in the PowerShell window.

---

### 4.4 Step-by-step — Linux

#### Step 1 — Clone or extract the project

```bash
git clone https://github.com/jpsanchezieu2024-prog/budgit-finale
cd budgit
```

Or extract the ZIP:
```bash
unzip Budgit.zip
cd Budgit
```

#### Step 2 — Add the Firebase key

```bash
mv /path/to/firebase_key.json .
```

#### Step 3 — Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

#### Step 4 — Install dependencies

```bash
pip install -r requirements.txt
```

#### Step 5 — Run the app

```bash
streamlit run "🏠_Home.py"
```

The app opens at **http://localhost:8501**.

---

### 4.5 Troubleshooting

| Symptom | Most likely cause | Fix |
| ------- | ----------------- | --- |
| `RuntimeError: No Firebase credentials were found` | `firebase_key.json` is missing or in the wrong folder | Place `firebase_key.json` at the project root, next to `🏠_Home.py` |
| `ModuleNotFoundError: No module named 'streamlit'` | Dependencies not installed | Run `pip install -r requirements.txt` in the project folder |
| `ModuleNotFoundError: No module named 'google.cloud.vision'` | Google Cloud Vision not installed | Run `pip install google-cloud-vision` |
| Browser opens but shows a blank page | Streamlit hasn't finished booting | Wait 5 seconds and refresh `http://localhost:8501` |
| App starts but login/signup hangs indefinitely | Firestore cold-start or no internet | Check your connection; wait up to 15 seconds on first operation |
| macOS: *"can't be opened — unidentified developer"* | Gatekeeper blocking the launcher | Right-click → Open → Open (only needed once) |
| Windows: `python` not found | Python not on PATH | Reinstall Python from python.org and tick **"Add Python to PATH"** during setup |
| Windows: emoji in filename causes issues | PowerShell encoding | Use `python -m streamlit run "🏠_Home.py"` with quotes around the filename |
| Receipt OCR returns no items | Blurry or low-contrast photo | Use a flat, well-lit photo. Avoid shadows and angles. |
| Receipt OCR returns wrong items | Photo taken at an angle | Lay the receipt flat and photograph straight down |

---

## 5. Further improvements

If this were a v2, the priorities would be:

- **Friends and household mode.** Shared grocery lists and budgets for roommates, with a friend graph powered by BFS over a Firestore `friendships` collection.
- **Migration to Firebase Authentication.** Replace homemade SHA-256 hashing with managed auth — gives password reset, email verification, and OAuth (Google, Apple) for free.
- **Memoised DP for daily budget caps.** Given remaining budget and remaining days in the week, suggest an optimal per-day spending cap.
- **Bilingual UI (EN / ES).** The user base is mostly Spain-based students.
- **Improved OCR for low-quality photos.** Switch from Google Vision text detection to GPT-4o vision or Google Document AI for better receipt structure understanding.

---

## 6. Bibliography and webgraphy

### 6.1 Course materials

- **Algorithms & Data Structures**, PPLE & BDBA, IE University. Sessions 1, 3, 7, 9, 11, 13, 17 are referenced in the source code where each algorithm appears.

### 6.2 Books

- Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C. (2022). *Introduction to Algorithms* (4th ed.). MIT Press.
- Sedgewick, R., & Wayne, K. (2011). *Algorithms* (4th ed.). Addison-Wesley.

### 6.3 Software documentation

- Streamlit official documentation. <https://docs.streamlit.io>
- Firebase Admin Python SDK. <https://firebase.google.com/docs/admin/setup>
- Cloud Firestore Python client. <https://googleapis.dev/python/firestore/latest/index.html>
- Google Cloud Vision API. <https://cloud.google.com/vision/docs>
- Python 3 standard library. <https://docs.python.org/3/library/>

### 6.4 Articles and blog posts

- "How to deploy Streamlit apps with Firebase backends." Streamlit Community Forum. <https://discuss.streamlit.io>
- "Service account authentication best practices." Google Cloud documentation. <https://cloud.google.com/iam/docs/best-practices-service-accounts>
- "Receipt OCR best practices." Google Cloud Vision documentation. <https://cloud.google.com/vision/docs/ocr>

---

## 7. Credits

### 7.1 Project team

- **Sofia Wiedemann**
- **Tomás Bunge**
- **Paolo Massihi**
- **Juan Pablo Sánchez**

### 7.2 Course

- **Algorithms & Data Structures**
- Programmes: PPLE (Politics, Philosophy, Law and Economics) & BDBA (Bachelor in Data and Business Analytics)
- Institution: **IE University**, Madrid / Segovia
- Academic year: 2025–2026

### 7.3 Acknowledgements

Thank you Toni!

---

*Budgit: No more checkout panic. Ever.*
