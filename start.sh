#!/bin/bash

cleanup() {
    echo "Stopping worker and bot..."
    kill -TERM "$WORKER_PID" 2>/dev/null
    kill -TERM "$BOT_PID" 2>/dev/null
    wait "$WORKER_PID" 2>/dev/null
    wait "$BOT_PID" 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "Starting arq worker..."
arq worker.task_worker.WorkerSettings &
WORKER_PID=$!

echo "Starting Telegram bot..."
python bot.py &
BOT_PID=$!

# Agar ulardan biri to'xtasa, konteyner to'xtaydi va qayta ishga tushadi
wait -n "$WORKER_PID" "$BOT_PID"
cleanup
