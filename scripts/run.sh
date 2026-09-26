#!/bin/sh
# Launch the game from source, creating a local virtual environment on first run.
set -e
cd "$(dirname "$0")/.."
if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
    .venv/bin/python -m pip install -e .
fi
exec .venv/bin/python -m cars "$@"
