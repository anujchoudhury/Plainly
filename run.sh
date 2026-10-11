#!/usr/bin/env bash
# One-command start (macOS/Linux): creates a venv, installs deps, copies .env, runs on :8000
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q --disable-pip-version-check -r requirements.txt
pip install -q --disable-pip-version-check asyncpg || echo "Note: asyncpg didn't install, so Tiger Data trends will use memory instead."
[ -f .env ] || cp .env.example .env
echo "Open http://localhost:8000  (for your iPhone: run 'cloudflared tunnel --protocol http2 --url http://127.0.0.1:8000' in another tab)"
python main.py
