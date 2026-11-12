#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

docker build -q -t labchecker-backend:test backend >/dev/null
docker run --rm --user 0 \
  -v "$PWD/backend:/src:ro" -w /src \
  -e PYTHONDONTWRITEBYTECODE=1 \
  labchecker-backend:test \
  sh -c "pip install -q --no-cache-dir --root-user-action=ignore pytest==8.3.3 httpx==0.27.2 && python -m pytest -q -p no:cacheprovider tests"
