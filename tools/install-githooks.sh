#!/usr/bin/env bash
# Point this repo at .githooks/ so pre-push (etc.) are active locally.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
chmod +x "${root}/.githooks/pre-push"
git -C "$root" config core.hooksPath .githooks
echo "Installed git hooks from .githooks/ (core.hooksPath=.githooks)"
