#\!/bin/bash
# Double-click me to start Budgit.

# Jump to the folder this script lives in.
cd "$(dirname "$0")"

echo ""
echo "  🛒  Starting Budgit..."
echo ""

# 1. Find a usable Python.
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "❌ Python isn't installed on this Mac."
    echo "   Install it from https://www.python.org/downloads/ and try again."
    echo ""
    read -n 1 -s -r -p "Press any key to close this window..."
    exit 1
fi

# 2. Make sure Streamlit is installed. First run only; silent afterwards.
if \! $PY -c "import streamlit" >/dev/null 2>&1; then
    echo "  Installing Streamlit (first run only, takes ~30 seconds)..."
    $PY -m pip install --user streamlit --quiet
    echo "  ✅ Done."
    echo ""
fi

# 3. Open the browser after a short delay and launch the app.
( sleep 3 && open "http://localhost:8501" ) &

echo "  The app will open in your browser in a moment."
echo "  To stop it later, close this Terminal window or press Ctrl+C."
echo ""

$PY -m streamlit run "🏠_Home.py" --server.headless=true
