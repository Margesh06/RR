#!/bin/zsh
cd "$(dirname "$0")"
RR_OVERRIDES="$2" .venv/bin/python -I stage2_ratings.py "${DATA:-Data Pack}" out 2024 "_to2024$1" > "out/log24$1.txt" 2>&1 && echo "done $1"
