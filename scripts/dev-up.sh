#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

command -v docker >/dev/null || { echo "Docker-compatible runtime required"; exit 1; }
command -v npx >/dev/null || { echo "Node.js/npm required"; exit 1; }

npx supabase start
npx supabase db reset

if [ -z "${DATABASE_URL:-}" ]; then
  export DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres"
fi

echo "AURORA database ready. API: http://127.0.0.1:8000"
python3 -m uvicorn apps.api.main:app --host "${AURORA_HOST:-127.0.0.1}" --port "${AURORA_PORT:-8000}"
