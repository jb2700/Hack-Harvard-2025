#!/usr/bin/env bash
# Start flask backend and vite dev frontend

# Start frontend
npm run dev &
VITE_PID=$!

echo "Started Vite (pid=$VITE_PID)"

# Start backend in a python venv or system python
python backend/app.py &
FLASK_PID=$!

echo "Started Flask (pid=$FLASK_PID)"

wait $VITE_PID $FLASK_PID
