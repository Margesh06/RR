#!/bin/zsh
# run_ens.sh <tag> <json>
cd "$(dirname "$0")"
RR_OVERRIDES="$2" .venv/bin/python -I stage2_ratings.py "${DATA:-Data Pack}" out 9999 "$1" > "out/log$1.txt" 2>&1 && echo "done $1"
