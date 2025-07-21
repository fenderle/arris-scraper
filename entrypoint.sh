#!/bin/bash
# allow override of sleep delay via environment (default 300s)
DELAY="${DELAY:-300}"

while true; do
    echo "Running at $(date)"

    arris-scraper status
    arris-scraper events

    sleep "$DELAY"
done