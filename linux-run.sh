#!/usr/bin/env bash
cd "$(dirname "$0")"

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 not found!"
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "First run detected, setting up environment..."
    python3 -m venv .venv
    .venv/bin/python -m pip install --upgrade pip >/dev/null 2>&1
    .venv/bin/python -m pip install python-a2s
fi

.venv/bin/python see.py