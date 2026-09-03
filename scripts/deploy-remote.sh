#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PROJECT_REF="${1:-${SUPABASE_PROJECT_REF:-}}"
if [ -z "$PROJECT_REF" ]; then
  echo "Usage: $0 <supabase-project-ref>"
  exit 2
fi

command -v npx >/dev/null || { echo "Node.js/npm required"; exit 1; }

npx supabase --version
npx supabase link --project-ref "$PROJECT_REF"
echo "Previewing pending migrations..."
npx supabase db push --dry-run
echo "Applying migrations..."
npx supabase db push
echo "Remote schema deployment complete."
