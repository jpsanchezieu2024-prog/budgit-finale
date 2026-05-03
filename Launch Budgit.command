#!/bin/bash
# Double-click me to start Budgit.
#
# This script does everything required to run the app from a fresh
# unzip: locates Python, installs the dependencies on first run,
# verifies the Firebase credentials are present, and then opens the
# app in your default browser.

# Jump to the folder this script lives in.
cd "$(dirname "$0")"

clear
echo ""
echo "  🛒  Starting Budgit..."
echo ""

# ---------------------------------------------------------------------
# 1. Find a usable Python interpreter.
# ---------------------------------------------------------------------
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "❌ Python isn't installed on this Mac."
    echo "   Download it from https://www.python.org/downloads/ and try again."
    echo ""
    read -n 1 -s -r -p "Press any key to close this window..."
    exit 1
fi

# ---------------------------------------------------------------------
# 2. Make sure the required packages are installed.
#    Runs once on the first launch; silent on subsequent launches.
# ---------------------------------------------------------------------
need_install=0
$PY -c "import streamlit"      >/dev/null 2>&1 || need_install=1
$PY -c "import firebase_admin" >/dev/null 2>&1 || need_install=1

if [ $need_install -eq 1 ]; then
    echo "  Installing required packages (first run only, ~30 seconds)..."
    $PY -m pip install --user --quiet streamlit firebase-admin
    echo "  ✅ Dependencies installed."
    echo ""
fi

# ---------------------------------------------------------------------
# 3. Verify the Firebase service-account key is present.
# ---------------------------------------------------------------------
if [ ! -f "firebase_key.json" ]; then
    echo "❌ firebase_key.json is missing from this folder."
    echo ""
    echo "   Budgit uses Firebase Firestore to share prices across users."
    echo "   Please place the firebase_key.json file in the same folder as"
    echo "   this script and try again."
    echo ""
    read -n 1 -s -r -p "Press any key to close this window..."
    exit 1
fi

# ---------------------------------------------------------------------
# 4. Open the browser after a short delay and launch Streamlit.
# ---------------------------------------------------------------------
( sleep 3 && open "http://localhost:8501" ) &

echo "  The app will open in your browser in a moment."
echo "  To stop it later, close this Terminal window or press Ctrl+C."
echo ""

$PY -m streamlit run "🏠_Home.py" --server.headless=true
