#!/usr/bin/env bash
cd "$(dirname "$0")"

# Use only the project venv (guarantees fastapi is found if installed)
if ! ./venv/bin/python -c "import fastapi" 2>/dev/null; then
  echo "Installing dependencies into venv (run once): ./venv/bin/pip install -r requirements.txt"
  ./venv/bin/pip install -r requirements.txt || { echo "Run: ./venv/bin/pip install -r requirements.txt"; exit 1; }
fi

./venv/bin/uvicorn main:app --reload --host 127.0.0.1
