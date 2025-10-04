#!/usr/bin/env bash
# Start flask backend and vite dev frontend

set -o errexit
set -o pipefail
set -o nounset

# Start frontend
npm run dev -- --host 0.0.0.0 &
VITE_PID=$!

echo "Started Vite (pid=$VITE_PID)"

# Start backend in a python venv or system python
python backend/app.py &
FLASK_PID=$!

echo "Started Flask (pid=$FLASK_PID)"
CLEANED=0
cleanup() {
	# idempotent cleanup
	if [ "$CLEANED" -ne 0 ]; then
		return
	fi
	CLEANED=1
	echo "Cleaning up..."
	if kill -0 "$VITE_PID" 2>/dev/null; then
		echo "Stopping Vite (pid=$VITE_PID)"
		kill "$VITE_PID" 2>/dev/null || true
	fi

	if kill -0 "$FLASK_PID" 2>/dev/null; then
		echo "Stopping Flask (pid=$FLASK_PID)"
		kill "$FLASK_PID" 2>/dev/null || true
	fi

	wait "$VITE_PID" 2>/dev/null || true
	wait "$FLASK_PID" 2>/dev/null || true

	echo "Cleanup complete."
}

trap 'echo "Received interrupt/termination"; cleanup; exit 0' INT TERM
trap 'cleanup' EXIT

while true; do
	if ! kill -0 "$VITE_PID" 2>/dev/null; then
		echo "Vite (pid=$VITE_PID) exited. Stopping Flask (pid=$FLASK_PID)"
		kill "$FLASK_PID" 2>/dev/null || true
		break
	fi

	if ! kill -0 "$FLASK_PID" 2>/dev/null; then
		echo "Flask (pid=$FLASK_PID) exited. Stopping Vite (pid=$VITE_PID)"
		kill "$VITE_PID" 2>/dev/null || true
		break
	fi
    
	sleep 1
done

