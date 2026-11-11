FROM python:3.11-slim

# FFmpeg va tizim asboblarini o'rnatish
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Kutubxonalarni o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Loyiha fayllarini nusxalash
COPY . .

# Papkalarni yaratish va ruxsatlarni berish
RUN mkdir -p downloads data && chmod +x start.sh

# Ishga tushirish
CMD ["bash", "start.sh"]
