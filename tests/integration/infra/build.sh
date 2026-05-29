#!/usr/bin/env bash
# Build the Lambda deployment package: handler.py + Linux wheels for the deps.
# Called by Terraform via null_resource. Idempotent within a triggers cycle.

set -euo pipefail

DIR="${1:-$(dirname "$0")}"
PKG="$DIR/.build/package"

rm -rf "$PKG"
mkdir -p "$PKG"
cp "$DIR/handler.py" "$PKG/"

# Lambda runtime is python3.12 on x86_64 — install matching manylinux wheels
# so the package is portable from whatever host runs `terraform apply`.
PIP="${PIP:-python3 -m pip}"
$PIP install --quiet \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --python-version 3.12 \
    --target "$PKG" \
    -r "$DIR/requirements.txt"
