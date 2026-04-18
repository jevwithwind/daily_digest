#!/usr/bin/env bash
set -euo pipefail

# Change to the script's directory so relative paths work
cd "$(dirname "$0")"

# Ensure logs directory exists
mkdir -p logs

# Create a temp file for raw output
TMPFILE=$(mktemp)
trap 'rm -f "$TMPFILE"' EXIT

# Run the Python script via uv, capture output and exit code
set +e
uv run python main.py > "$TMPFILE" 2>&1
EXIT_CODE=$?
set -e

# Prepend timestamps and append to cron.log
while IFS= read -r line; do
    echo "$(date '+%Y-%m-%dT%H:%M:%S') $line"
done < "$TMPFILE" | tee -a logs/cron.log

exit "$EXIT_CODE"
