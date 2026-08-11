#!/usr/bin/env bash
# Decode the ENV_BUNDLE_B64 GitLab variable back into the three service .env files.
# Usage: ENV_BUNDLE_B64=<value> bash scripts/env-unbundle.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "${ENV_BUNDLE_B64:-}" ]]; then
    echo "error: ENV_BUNDLE_B64 is not set" >&2
    exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "$ENV_BUNDLE_B64" | base64 -d > "$TMP/bundle.txt"

python3 - "$REPO_ROOT" "$TMP/bundle.txt" <<'PY'
import os
import sys

root, bundle = sys.argv[1], sys.argv[2]
with open(bundle, "r", encoding="utf-8") as f:
    text = f.read()

chunks = text.split("### FILE: ")[1:]
for chunk in chunks:
    header, content = chunk.split("\n", 1)
    rel = header.strip()
    if not rel:
        continue
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print(f"wrote {rel}")
PY
