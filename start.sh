#!/bin/bash

# 1. Workerni fonda ishga tushirish
echo "Starting Worker..."
arq worker.task_worker.WorkerSettings &

# 2. Botni asosiy jarayon sifatida ishga tushirish
echo "Starting Bot..."
python bot.py
