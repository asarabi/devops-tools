#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "🚀 Starting Repo Manager on http://localhost:8081 ..."
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload
