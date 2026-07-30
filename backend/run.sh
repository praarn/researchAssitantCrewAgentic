#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created backend/.env - add your GROQ_API_KEY before running research."
fi
uvicorn app.main:app --reload --port 8000
