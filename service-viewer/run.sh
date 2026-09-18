#!/bin/bash
cd "$(dirname "$0")"

USER_SITE="$HOME/.local/lib/python3.10/site-packages"
export PYTHONPATH="$USER_SITE:$PYTHONPATH"

sudo -E PYTHONPATH="$PYTHONPATH" python3 run.py
