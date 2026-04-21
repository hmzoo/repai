#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_REF="${1:-v1.0-base-gemini-logging}"

cd "$ROOT_DIR"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Error: reset.sh must be run from inside the project repository."
    exit 1
fi

if ! git rev-parse --verify "$TARGET_REF" >/dev/null 2>&1; then
    echo "Error: git reference '$TARGET_REF' was not found."
    echo "Usage: bash reset.sh [git-ref]"
    exit 1
fi

echo "RepaI reset"
echo "  Repository : $ROOT_DIR"
echo "  Target ref : $TARGET_REF"
echo ""
echo "This will:"
echo "  - reset tracked files to $TARGET_REF"
echo "  - remove untracked files and directories"
echo "  - preserve ignored local files such as .env"
echo ""

read -r -p "Continue? [y/N] " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Reset cancelled."
    exit 0
fi

git reset --hard "$TARGET_REF"
git clean -fd

echo ""
echo "Reset complete. Repository restored to $TARGET_REF."
echo "Tip: activate your environment again if needed: source venv/bin/activate"