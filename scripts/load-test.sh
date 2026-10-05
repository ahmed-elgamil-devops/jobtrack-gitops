#!/usr/bin/env bash
# Generates traffic so you can watch the Grafana dashboard move and the HPA scale up.
# Usage: ./scripts/load-test.sh [base_url] [seconds]
set -euo pipefail
URL=${1:-http://jobtrack.local}
DURATION=${2:-120}
END=$((SECONDS + DURATION))
COMPANIES=(Careem Emirates du "e&" Talabat Noon Majid-Al-Futtaim ADNOC)

echo "Sending traffic to $URL for ${DURATION}s (Ctrl+C to stop)..."
while [ $SECONDS -lt $END ]; do
  for _ in $(seq 1 20); do
    c=${COMPANIES[$RANDOM % ${#COMPANIES[@]}]}
    curl -s -o /dev/null -X POST "$URL/api/jobs" -H 'Content-Type: application/json' \
      -d "{\"company\":\"$c\",\"title\":\"Junior DevOps Engineer\",\"source\":\"LinkedIn\"}" &
    curl -s -o /dev/null "$URL/api/jobs" &
    curl -s -o /dev/null "$URL/api/stats" &
  done
  wait
done
echo "Done. Check: kubectl -n jobtrack get hpa"
