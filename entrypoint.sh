#!/bin/bash
set -euo pipefail

# Main loop delay (seconds)
DELAY="${DELAY:-300}"
# Speedtest delay (seconds)
SPEEDTEST_DELAY="${SPEEDTEST_DELAY:-3600}"

lockfile="/tmp/arris_speedtest.lock"

run_status_events() {
  while true; do
    echo "[status/events] $(date)"
    arris-scraper status || echo "[status] failed"
    arris-scraper events || echo "[events] failed"
    sleep "$DELAY"
  done
}

run_speedtest() {
  # run immediately once, then every SPEEDTEST_DELAY seconds
  while true; do
    echo "[speedtest] $(date)"
    # prevent overlap if the previous speedtest is still running
    {
      flock -n 9 || { echo "[speedtest] already running, skipping"; }
      arris-scraper speedtest --speedtest-path /usr/local/bin/speedtest || echo "[speedtest] failed"
    } 9>"$lockfile"
    sleep "$SPEEDTEST_DELAY"
  done
}

# start both loops in background
run_status_events & pid_status=$!
run_speedtest & pid_speed=$!

# graceful shutdown: forward signals and wait
term() {
  echo "received stop signal, shutting down..."
  kill "$pid_status" "$pid_speed" 2>/dev/null || true
  wait "$pid_status" "$pid_speed" 2>/dev/null || true
}
trap term SIGINT SIGTERM

# wait for either to exit; if one dies, kill the other so container ends
wait -n "$pid_status" "$pid_speed"
kill "$pid_status" "$pid_speed" 2>/dev/null || true
wait 2>/dev/null || true