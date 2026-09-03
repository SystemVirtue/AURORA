#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

npx supabase --version
npx supabase db reset
python3 -m pytest -q
python3 -m compileall -q aurora apps

echo "AURORA local verification passed."
echo "Note: provider-backed /v1/ask requires DATABASE_URL, a workspace and a configured model API key."
