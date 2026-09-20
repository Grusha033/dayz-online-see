#!/usr/bin/env bash
cd "$(dirname "$0")"

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 not found!"
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

if ! .venv/bin/python -c "import a2s" &> /dev/null; then
    echo "Installing missing dependencies..."
    .venv/bin/python -m pip install python-a2s
fi

.venv/bin/python see.py