#!/usr/bin/env bash
# Launches the setup wizard on Linux / macOS:  bash setup_wizard.sh
cd "$(dirname "$0")" || exit 1
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)' 2>/dev/null; then
    exec "$c" setup_wizard.py "$@"
  fi
done
echo "Python 3.9+ was not found. Install it from https://www.python.org/downloads/ (macOS: brew install python)."
exit 1
