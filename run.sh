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

# PortAudio is a *system* library that `sounddevice` binds to at runtime; pip does
# not install it. Without it the app dies with "PortAudio library not found".
portaudio_present() {
    case "$(uname -s)" in
        Darwin)
            if command -v brew >/dev/null 2>&1 && brew list --versions portaudio >/dev/null 2>&1; then
                return 0
            fi
            ls /usr/local/lib/libportaudio*.dylib /opt/homebrew/lib/libportaudio*.dylib >/dev/null 2>&1
            ;;
        *)
            if command -v ldconfig >/dev/null 2>&1 && ldconfig -p 2>/dev/null | grep -q 'libportaudio\.so'; then
                return 0
            fi
            ls /usr/lib/libportaudio.so* /usr/lib/*/libportaudio.so* >/dev/null 2>&1
            ;;
    esac
}

install_portaudio() {
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update && sudo apt-get install -y libportaudio2
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y portaudio
    elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -S --noconfirm portaudio
    elif command -v brew >/dev/null 2>&1; then
        brew install portaudio
    else
        echo "!! Could not detect a package manager to install PortAudio." >&2
        echo "   Install it manually (e.g. 'libportaudio2' on Debian/Ubuntu) and re-run." >&2
        return 1
    fi
}

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

# 3. Ensure the PortAudio system library is present (needed by sounddevice).
if portaudio_present; then
    echo ">> PortAudio found"
else
    echo ">> PortAudio not found; installing it"
    install_portaudio
fi

# 4. Make sure a .env exists (copy from the example on first run).
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo ">> No .env found; creating one from .env.example"
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo "   Edit .env to set PERUCA_API_URL, TTS_ENABLED, PIPER_VOICE_PATH, etc."
fi

# 5. Run the head. Forward any CLI arguments (run / chat / listen).
echo ">> Starting peruca-head ${*:-(default: run)}"
exec "$VENV_PY" src/main.py "$@"
