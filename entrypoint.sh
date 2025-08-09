#!/bin/bash
# Main loop delay (seconds)
DELAY="${DELAY:-300}"
# Speedtest delay (seconds)
SPEEDTEST_DELAY="${SPEEDTEST_DELAY:-3600}"

last_speedtest=0

while true; do
    now=$(date +%s)
    echo "Running at $(date)"

    arris-scraper status
    arris-scraper events

    # Run speedtest if enough time has passed
    if [[ $last_speedtest -eq 0 || $(( now - last_speedtest )) -ge $SPEEDTEST_DELAY ]]; then
        echo "Running speedtest at $(date)"
        arris-scraper speedtest --speedtest_path /usr/local/bin/speedtest
        last_speedtest=$now
    fi

    sleep "$DELAY"
done