#!/usr/bin/env bash
#
# run.sh — bootstrap and launch the peruca voice head.
#
# Creates the virtualenv (if missing), installs the project in editable mode,
# makes sure a .env exists, then runs peruca-head. Any arguments are forwarded
# to the CLI, so you can pick the mode:
#
#   ./run.sh            # default mode: the full voice loop (= run)
#   ./run.sh chat       # text-only chat
#   ./run.sh listen     # STT diagnostic
#   ./run.sh run        # voice loop (explicit)
#
# Re-running is cheap: the venv and install steps are skipped when already done.
# Force a reinstall of dependencies with: REINSTALL=1 ./run.sh
#
set -euo pipefail

# Always operate from the project root (the directory this script lives in).
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

VENV_DIR="$PROJECT_ROOT/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

# 1. Create the virtualenv if it does not exist yet.
if [ ! -d "$VENV_DIR" ]; then
    echo ">> Creating virtualenv at $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# Use the venv's interpreter/pip directly (no need to 'activate' in a script).
VENV_PY="$VENV_DIR/bin/python"

# 2. Install the project (and its dependencies) in editable mode.
# Skipped on subsequent runs unless REINSTALL=1 is set or the package is missing.
if [ "${REINSTALL:-0}" = "1" ] || ! "$VENV_PY" -c "import config" >/dev/null 2>&1; then
    echo ">> Installing dependencies (editable install)"
    "$VENV_PY" -m pip install --upgrade pip
    "$VENV_PY" -m pip install -e .
else
    echo ">> Dependencies already installed (set REINSTALL=1 to force)"
fi

# 3. Make sure a .env exists (copy from the example on first run).
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo ">> No .env found; creating one from .env.example"
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo "   Edit .env to set PERUCA_API_URL, TTS_ENABLED, PIPER_VOICE_PATH, etc."
fi

# 4. Run the head. Forward any CLI arguments (run / chat / listen).
echo ">> Starting peruca-head ${*:-(default: run)}"
exec "$VENV_PY" src/main.py "$@"
