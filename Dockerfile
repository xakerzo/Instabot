FROM python:3.11-slim

# FFmpeg va tizim asboblarini o'rnatish
RUN apt-get update && \
    apt-get install -y ffmpeg curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Kutubxonalarni o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Loyiha fayllarini nusxalash
COPY . .

# Yuklamalar uchun papka yaratish
RUN mkdir -p downloads data

# Bot va Workerni ishga tushirish
CMD ["sh", "-c", "python bot.py & arq worker.task_worker.WorkerSettings"]
