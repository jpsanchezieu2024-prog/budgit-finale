# Budgit 🛒

> No more checkout panic. Ever.

Budgit is the final project for **Algorithms & Data Structures — PPLE & BDBA, IE University**. Every non-trivial operation in the app is powered by a data structure or algorithm implemented from scratch — no `dict`, `heapq`, `sorted()`, or library shortcuts.

---

## 🌐 Live app — no installation needed

**[https://budgit.up.railway.app/](https://budgit.up.railway.app/)**

The app is hosted on Railway and connects to a live Firebase Firestore database shared across all users. No setup, no installation, no credentials needed.

### Getting started in 60 seconds

1. Open **[https://budgit.up.railway.app/](https://budgit.up.railway.app/)**
2. Click **Sign up**
3. Enter your name, email, password, weekly grocery budget, and preferred supermarket
4. Click **Create account** — you're in

---

## Table of contents

1. [Description of the app](#1-description-of-the-app)
2. [Features](#2-features)
3. [Files](#3-files)
4. [Running the app yourself](#4-running-the-app-yourself)
5. [Further improvements](#5-further-improvements)
6. [Bibliography and webgraphy](#6-bibliography-and-webgraphy)
7. [Credits](#7-credits)

---

## 1. Description of the app

Budgit is a multi-page Streamlit web application aimed at university students who shop on a tight weekly grocery budget. The app gives a student five things they currently don't have:

- **A live cart that respects a weekly budget**, with a colour-changing remaining-amount card that shifts smoothly from green through yellow to red as the week's spending approaches the limit.
- **Cross-user price intelligence.** When any Budgit user records the price of milk at Mercadona, every other user typing "milk" gets that price as an autofill — backed by a global Firestore directory and an in-memory hash table.
- **Receipt verification.** Upload a photo of your receipt after shopping — Google Vision OCR extracts the items and prices and cross-checks them against what you entered, marking verified prices with ✅ in the shared database.
- **An over-budget rescue mode** that shows two algorithms side by side: a fast Greedy heuristic that drops the priciest items first, and a 0/1 Knapsack DP that finds the optimal subset within the remaining budget.
- **Pre-shop store recommendation.** Build a grocery list on the List page; Budgit instantly tells you which supermarket gives the cheapest total basket using the global price directory.
- **A savings leaderboard** ranking users by the percentage of money they've saved by shopping at the cheaper supermarket — extracted with a Max-Heap Priority Queue and ranked with Merge Sort.


---

## 2. Features

### 2.1 Account and budget management

- **Sign-up and log-in** with SHA-256 password hashing and per-user random salts.
- **Weekly budget configuration** with a per-user preferred supermarket.
- **Editable profile** — change name, weekly budget, and preferred store at any time.

### 2.2 Live shopping session

- **Add items by name and price** with quantity. Same item added twice bumps the quantity in O(1) via the Cart's hash-table backing.
- **Smart autofill** of prices using a two-tier lookup: your own price memory at this store first, then the global directory.
- **Prefix-match autocomplete** — typing "mi" surfaces "milk" instantly via a Binary Search Tree.
- **Live running total** with a percent-of-budget indicator and progress bar.
- **Cross-store price comparison** chips showing the cheapest store for each product as you type, with ✅ on receipt-verified prices.

### 2.3 Receipt verification (OCR)

- Upload a receipt photo in the End Session dialog.
- Google Cloud Vision reads the receipt and extracts item names and prices.
- Budgit fuzzy-matches receipt lines against your cart items.
- Matched items are marked **✅ verified** in the shared global price database.
- Works best with a flat, well-lit, straight-on photo of the receipt.

### 2.4 Budget Rescue (over-budget)

- **Greedy mode.** Drops the most expensive items first using a Max-Heap. Fast (O(n log n)) but may leave money on the table.
- **Optimal mode.** Runs 0/1 Knapsack DP to find the subset of maximum total value that fits the budget.
- **Side-by-side display** of keep vs put back — apply the result with one click.

### 2.5 Pre-shop grocery list

- **Build a list** of items with quantities before going to the shop.
- **Cheapest-store recommendation** based on the global price directory.
- **One-click import to cart** — imported items are removed from the list automatically.

### 2.6 Shopping history

- **Past sessions sorted by date** using Merge Sort (deliberately not `ORDER BY`).
- **Per-supermarket colour-coded badges** so multi-store shoppers can tell sessions apart at a glance.
- **Expandable session detail** showing every line item and total.

### 2.7 Compare and leaderboard

- **Savings leaderboard** ranking users by lifetime % saved, with medals for the top 3.
- **Global product prices** side-by-side across supermarkets, with ✅ on verified prices.


---

## 3. Files

```
Budgit/
├── 🏠_Home.py                  ← Streamlit entry point, login, dashboard
├── Launch Budgit.command       ← macOS one-click launcher
├── database.py                 ← Firebase Firestore wrapper
├── state.py                    ← Session state, BST, hash table init
├── ocr.py                      ← Google Vision receipt parser
├── models.py                   ← User, Cart, CartItem, Session classes
├── theme.py                    ← Dark mint-green CSS and colour helpers
├── requirements.txt            ← Python dependencies
├── Procfile                    ← Railway deployment config
├── README.md                   ← This file
├── firebase_key.json           ← NOT in repo (.gitignore) — provided separately
├── assets/                     ← Tree PNG images for budget visualisation
│   ├── tree1.png               ← Healthy (0–25% of budget spent)
│   ├── tree2.png               ← OK (25–50% spent)
│   ├── tree3.png               ← Low (50–75% spent)
│   └── tree4.png               ← Critical (75–100%+ spent)
├── pages/
│   ├── 0_📝_List.py            ← Pre-shop grocery list
│   ├── 1_🛒_Shop.py            ← Live cart + Budget Rescue + OCR
│   ├── 2_📜_History.py         ← Past sessions
│   ├── 3_📊_Compare.py         ← Leaderboard + price comparison
│   └── 4_⚙️_Profile.py          ← User profile editor
├── algorithms/
│   ├── hash_table.py           ← Hash Table (separate chaining + resizing)
│   ├── bst.py                  ← Binary Search Tree + prefix search
│   ├── sorting.py              ← Merge Sort + Quick Sort
│   ├── priority_queue.py       ← Max-Heap Priority Queue
│   ├── greedy.py               ← Greedy method + 0/1 Knapsack DP
│   ├── search.py               ← Binary Search + Linear Search
│   └── leaderboard.py          ← Savings computation + ranking
├── .streamlit/
│   └── config.toml             ← Pins dark theme
└── .devcontainer/
    └── devcontainer.json       ← GitHub Codespaces configuration
```

### Algorithm → production use map

| File | Algorithm | Production use |
| ---- | --------- | -------------- |
| `hash_table.py` | Hash Table with separate chaining | Backs `Cart._items` (O(1) lookup); mirrors global price directory in memory |
| `bst.py` | Binary Search Tree with prefix search | Powers autocomplete on the Add-Item form |
| `sorting.py` | Merge Sort and Quick Sort | Sorts shopping history by date; ranks leaderboard |
| `priority_queue.py` | Max-Heap Priority Queue | Top-k expensive items; Greedy budget rescue; leaderboard top-K |
| `greedy.py` | Greedy method + 0/1 Knapsack DP | The two Budget Rescue modes |
| `search.py` | Binary Search and Linear Search | Sorted-list lookup helpers |
| `leaderboard.py` | HashTable + PQ + Merge Sort | Computes per-session savings and ranks all users |

---

## 4. Running the app yourself

There are three ways to run Budgit, in order of ease:

| Option | Requires installation | Requires Firebase key |
| ------ | -------------------- | --------------------- |
| **Live app** (recommended) | ❌ | ❌ |
| **GitHub Codespaces** | ❌ | ✅ |
| **Run locally** | ✅ | ✅ |

---

### Option A — Live app (recommended)

Open **[https://budgit.up.railway.app/](https://budgit.up.railway.app/)** in any browser. Nothing to install.

---

### Option B — GitHub Codespaces (browser-based, no local install)

Codespaces runs the app inside a cloud container directly from GitHub — no Python, no pip, no terminal needed on your machine. The `.devcontainer` configuration handles everything automatically.

#### What you need

- A GitHub account (free)
- The `firebase_key.json` file (provided separately)

#### Steps

1. Go to the GitHub repository page.
2. Click the green **Code** button → **Codespaces** tab → **Create codespace on main**.
3. GitHub provisions a Python 3.11 container. This takes ~2 minutes on the first launch.
4. Once ready, a VS Code interface opens in your browser. The terminal at the bottom automatically runs `streamlit run 🏠_Home.py`.
5. Wait for the message: `You can now view your Streamlit app in your browser`.
6. A popup appears: **Open in Browser** — click it. The app opens in a new tab.

#### Adding the Firebase key in Codespaces

The `firebase_key.json` is not in the repo for security reasons. Add it manually:

1. In the VS Code file explorer (left panel), right-click the root folder.
2. Select **Upload**.
3. Upload your `firebase_key.json` file — it should appear at the project root next to `🏠_Home.py`.
4. In the terminal, restart the app:
   ```bash
   streamlit run "🏠_Home.py"
   ```

#### Stopping a Codespace

Close the browser tab. To avoid consuming your free Codespaces hours, go to [github.com/codespaces](https://github.com/codespaces), find the codespace, click the **⋯** menu, and select **Stop codespace**.

---

### Option C — Run locally

Github repository link: https://github.com/jpsanchezieu2024-prog/budgit-finale

#### Prerequisites

| Requirement | How to check | How to install |
| ----------- | ------------ | -------------- |
| Python 3.10+ | `python3 --version` | [python.org/downloads](https://www.python.org/downloads/) |
| pip | `pip --version` | Bundled with Python 3.10+ |
| `firebase_key.json` | — | Provided separately |
| Internet connection | — | Required for Firestore |

---

#### macOS

**Step 1 — Download the project**

```bash
git clone https://github.com/jpsanchezieu2024-prog/budgit-finale
cd budgit
```

Or download the ZIP from GitHub → **Code → Download ZIP** → unzip it.

**Step 2 — Add the Firebase key**

Move `firebase_key.json` into the project root folder, next to `🏠_Home.py`:

```
Budgit/
├── 🏠_Home.py
├── firebase_key.json    ← place it here
└── ...
```

**Step 3 — Launch**

Double-click **`Launch Budgit.command`**.

On the first run it installs all dependencies (~60 seconds). On subsequent runs it starts in ~3 seconds. Your default browser opens automatically at **http://localhost:8501**.

**First-time Gatekeeper warning:** macOS may show *"Launch Budgit.command can't be opened because it is from an unidentified developer."* To allow it: right-click the file → **Open** → **Open**. You only need to do this once.

**Step 4 — Stop the app**

Close the Terminal window, or click inside it and press `Ctrl + C`.

---

#### Windows

**Step 1 — Download and extract**

Download the ZIP from GitHub (Code → Download ZIP) and extract it to a convenient location, for example `C:\Users\YourName\Desktop\Budgit`.

**Step 2 — Add the Firebase key**

Place `firebase_key.json` at the root of the extracted folder, next to `🏠_Home.py`.

**Step 3 — Open PowerShell in the folder**

Hold `Shift` and right-click inside the `Budgit` folder in File Explorer:
- Windows 10: choose **Open PowerShell window here**
- Windows 11: choose **Open in Terminal**

**Step 4 — Create a virtual environment**

```powershell
python -m venv venv
.\venv\Scripts\activate
```

You should see `(venv)` at the start of the prompt. If `python` is not found, reinstall Python from [python.org](https://www.python.org/downloads/) and make sure to tick **"Add Python to PATH"** during setup.

**Step 5 — Install dependencies**

```powershell
pip install -r requirements.txt
```

Takes ~1–2 minutes on first run.

**Step 6 — Run the app**

```powershell
python -m streamlit run "🏠_Home.py"
```

Always use quotes around the filename — the emoji causes issues without them. Your browser opens at **http://localhost:8501**.

**Step 7 — Stop the app**

Press `Ctrl + C` in the PowerShell window.

---

#### Linux

**Step 1 — Clone and enter the project**

```bash
git clone https://github.com/jpsanchezieu2024-prog/budgit-finale
cd budgit
```

**Step 2 — Add the Firebase key**

```bash
cp /path/to/firebase_key.json .
```

**Step 3 — Create a virtual environment**

```bash
python3 -m venv venv
source venv/bin/activate
```

**Step 4 — Install dependencies**

```bash
pip install -r requirements.txt
```

**Step 5 — Run the app**

```bash
streamlit run "🏠_Home.py"
```

Browser opens at **http://localhost:8501**.

**Step 6 — Stop the app**

Press `Ctrl + C` in the terminal.

---

### Troubleshooting

| Symptom | Most likely cause | Fix |
| ------- | ----------------- | --- |
| `RuntimeError: No Firebase credentials were found` | `firebase_key.json` missing or wrong location | Place it at the project root next to `🏠_Home.py` |
| `ModuleNotFoundError: No module named 'streamlit'` | Dependencies not installed | Run `pip install -r requirements.txt` |
| `ModuleNotFoundError: No module named 'google.cloud.vision'` | Vision package missing | Run `pip install google-cloud-vision` |
| Browser opens but shows a blank page | Streamlit still booting | Wait 5 seconds and refresh `http://localhost:8501` |
| Login or signup hangs indefinitely | Firestore cold start or no internet | Check your connection; wait up to 15 seconds on the first operation |
| macOS: *"can't be opened — unidentified developer"* | Gatekeeper blocking the launcher | Right-click → Open → Open (once only) |
| Windows: `python` not recognised | Python not on PATH | Reinstall Python from python.org and tick **"Add Python to PATH"** |
| Windows: emoji in filename causes errors | PowerShell encoding | Always use quotes: `python -m streamlit run "🏠_Home.py"` |
| Receipt OCR returns no items | Blurry or angled photo | Lay the receipt flat and photograph straight down in good light |
| Receipt OCR returns wrong matches | Shadows or low contrast | Use flash or brighter lighting; avoid curved or crumpled receipts |
| Codespaces: app not starting automatically | Auto-start failed | Open the terminal and run `streamlit run "🏠_Home.py"` manually |
| Codespaces: Firebase error after upload | Key in wrong location | Ensure `firebase_key.json` is at the project root, not inside a subfolder |

---

## 5. Further improvements

- **Friends and household mode.** Shared grocery lists and budgets for roommates, with a friend graph powered by BFS over a Firestore `friendships` collection.
- **Migration to Firebase Authentication.** Replace SHA-256 hashing with managed auth — password reset, email verification, and OAuth (Google, Apple) for free.
- **Improved OCR.** Switch to GPT-4o Vision or Google Document AI for better receipt structure understanding on low-quality or angled photos.
- **Memoised DP for daily budget caps.** Given remaining budget and days left in the week, suggest an optimal per-day spending cap that minimises overshoot probability.
- **Bilingual UI (EN / ES).** Most users are Spain-based students.

---

## 6. Bibliography and webgraphy

### 6.1 Course materials

- **Algorithms & Data Structures**, PPLE & BDBA, IE University. Sessions 1, 3, 7, 9, 11, 13, 17 are referenced in the source code where each algorithm appears.

### 6.2 Books

- Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C. (2022). *Introduction to Algorithms* (4th ed.). MIT Press.
- Sedgewick, R., & Wayne, K. (2011). *Algorithms* (4th ed.). Addison-Wesley.

### 6.3 Software documentation

- Streamlit. <https://docs.streamlit.io>
- Firebase Admin Python SDK. <https://firebase.google.com/docs/admin/setup>
- Cloud Firestore Python client. <https://googleapis.dev/python/firestore/latest/index.html>
- Google Cloud Vision API. <https://cloud.google.com/vision/docs>
- GitHub Codespaces. <https://docs.github.com/en/codespaces>
- Python 3 standard library. <https://docs.python.org/3/library/>

### 6.4 Articles consulted

- "How to deploy Streamlit apps with Firebase backends." Streamlit Community Forum. <https://discuss.streamlit.io>
- "Service account authentication best practices." Google Cloud. <https://cloud.google.com/iam/docs/best-practices-service-accounts>

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

*Built with effort, dedication, and tears for you*
