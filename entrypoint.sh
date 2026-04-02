#!/bin/bash
set -e

echo "==> Initialising database..."
python main.py init

echo "==> Starting pipeline loop (interval: ${LOOP_INTERVAL:-1800}s)..."
python main.py loop --interval "${LOOP_INTERVAL:-1800}" &
LOOP_PID=$!

echo "==> Starting dashboard on 0.0.0.0:8000..."
python main.py dashboard --host 0.0.0.0 --port 8000 &
DASH_PID=$!

echo "==> Both processes running. Dashboard PID=$DASH_PID  Loop PID=$LOOP_PID"

# If either process dies, exit so Fly.io restarts the machine
wait -n $LOOP_PID $DASH_PID
EXIT_CODE=$?
echo "==> A process exited with code $EXIT_CODE — shutting down"
kill $LOOP_PID $DASH_PID 2>/dev/null || true
exit $EXIT_CODE
