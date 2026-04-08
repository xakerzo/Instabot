# Production-Ready Media Downloader Bot

Ushbu bot Instagram, TikTok, YouTube Shorts va Pinterest-dan media yuklash uchun mo'ljallangan.

## 🛠 Texnologiyalar:
- **Framework:** Aiogram 3.x
- **Downloader:** yt-dlp
- **Queue:** Redis + arq
- **Database:** SQLite (Async SQLAlchemy)
- **Processing:** FFmpeg (video compression)

## 🚀 O'rnatish:

1.  **Kutubxonalarni o'rnatish:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **FFmpeg va Redis o'rnatish:**
    - Ubuntu: `sudo apt update && sudo apt install ffmpeg redis-server -y`
    - Windows: Redis-ni MSI orqali, FFmpeg-ni esa rasmiy saytidan yuklab `Path`ga qo'shing.

3.  **Konfiguratsiya:**
    `.env.example` faylini `.env` deb o'zgartiring va bot tokeningizni kiriting.

4.  **Ishga tushirish:**

    **Worker-ni ishga tushirish (bu videolarni yuklaydi):**
    ```bash
    arq worker.task_worker.WorkerSettings
    ```

    **Botni ishga tushirish (bu foydalanuvchi bilan muloqot qiladi):**
    ```bash
    python bot.py
    ```

## 📂 Loyiha Strukturasi:
- `bot.py` - Asosiy kirish nuqtasi.
- `worker/` - Fon topshiriqlari.
- `app/services/downloader.py` - Yuklash mantiqi.
- `app/utils/video_processor.py` - Video siqish.
- `database.py` - DB mantiqi.

## 🔑 Proxy (Ixtiyoriy):
Agar Instagram sizni bloklasa, `proxies.txt` fayliga proxylarni qatorma-qator yozing va `.env`da `USE_PROXY=True` qiling.

## 🍪 Instagram Cookies (Juda Muhim):
Instagram ko'p hollarda botlarni bloklaydi yoki "Requested content is not available" xatosini beradi. Buni oldini olish uchun:
1. Brauzeringizda (Chrome/Edge) [Get Cookie.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookietxt-locally/ccjbbpchehhonacpaolfmhonghlhbaln) kengaytmasini o'rnating.
2. Instagram.com ga kiring va profilga login qiling.
3. Kengaytmani ochib, "Export" tugmasini bosing va faylni `cookies.txt` nomi bilan bot papkasiga saqlang.
4. Botni qayta ishga tushiring.
