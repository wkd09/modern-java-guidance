#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/wkd09/modern-java-guidance.git"

echo "Installing modern-java-guidance (mjg)..."

if command -v uv >/dev/null 2>&1; then
  uv tool install --force "git+${REPO_URL}"
elif command -v pipx >/dev/null 2>&1; then
  pipx install --force "git+${REPO_URL}"
elif command -v python3 >/dev/null 2>&1; then
  python3 -m pip install --user --upgrade "git+${REPO_URL}"
else
  echo "Error: Python 3.11+ (or uv / pipx) is required." >&2
  exit 1
fi

echo ""
echo "Installed! Verify with:"
echo "  mjg --help"
echo ""
echo "Enable Skill + PostToolUse hook in your Java/Spring Boot project:"
echo "  mjg setup --target all --dir /path/to/your/project"
