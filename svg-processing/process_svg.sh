#!/usr/bin/env bash

set -u

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 input.svg" >&2
  exit 1
fi

input_file="$1"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "$input_file" ]; then
  echo "Error: file not found: $input_file" >&2
  exit 1
fi

apply_output="$(python3 "$script_dir/add_white_fill.py" "$input_file" 2>&1)"
apply_status=$?

echo "$apply_output"

if [ "$apply_status" -ne 0 ]; then
  exit "$apply_status"
fi

if echo "$apply_output" | grep -q "Skipped, already has white background"; then
  echo "Cancelled: crop_and_pad.py was not run."
  exit 0
fi

python3 "$script_dir/crop_and_pad.py" "$input_file"