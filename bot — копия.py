"""
Telegram bot to download public Instagram videos (no login). For private accounts the bot will return a modified link
by replacing 'www.instagram.com' or 'instagram.com' with 'kkinstagram.com' (no dot after 'kk').

Requirements:
  pip install python-telegram-bot==20.6 requests beautifulsoup4

Usage:
  1. Create config.py with a line: TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
  2. Run: python insta_video_bot.py

Notes:
 - This bot DOES NOT attempt to login to Instagram. It only downloads content that is publicly accessible.
 - If Instagram changes their page layout the extractor may fail; in that case the bot will return the modified link.
"""

import os
import re
import tempfile
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# Load TOKEN from config.py
try:
    from config import TOKEN
except ImportError:
    TOKEN = None

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
DOWNLOAD_TIMEOUT = 60  # seconds
LOG_LEVEL = logging.INFO

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

INSTAGRAM_HOSTS = ["www.instagram.com", "instagram.com", "m.instagram.com"]

def modify_private_link(url: str) -> str:
    for host in INSTAGRAM_HOSTS:
        if host in url:
            return url.replace(host, 'kkinstagram.com')
    return url.replace('https://', 'https://kkinstagram.com/') if 'instagram' in url else url


def extract_instagram_video_url(page_html: str) -> str | None:
    soup = BeautifulSoup(page_html, 'html.parser')
    meta = soup.find('meta', property='og:video') or soup.find('meta', property='og:video:secure_url')
    if meta and meta.get('content'):
        return meta['content']
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            txt = script.string
            if not txt:
                continue
            if 'contentUrl' in txt:
                m = re.search(r'"contentUrl"\s*:\s*"([^"]+)"', txt)
                if m:
                    return m.group(1)
        except Exception:
            continue
    scripts = soup.find_all('script')
    for s in scripts:
        if s.string and ('edge_sidecar_to_children' in s.string or 'graphql' in s.string):
            text = s.string
            m = re.search(r'"video_url"\s*:\s*"([^"]+)"', text)
            if m:
                return m.group(1).replace('\\u0026', '&').replace('\\/', '/')
            m2 = re.search(r'"display_url"\s*:\s*"([^"]+)"', text)
            if m2:
                return m2.group(1).replace('\\/', '/')
    return None

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Instagramdan video link yuboring! Men uni yuklab beraman!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or '').strip()
    if not text:
        await update.message.reply_text("Link yuboring.")
        return

    m = re.search(r'(https?://[\w\./\-?=&%]+instagram\.com[\w\./\-?=&%]*)|(https?://[\w\./\-?=&%]*instagram\.com[\w\./\-?=&%]*)', text)
    if not m:
        await update.message.reply_text("Instagram linkini yuboring (misol: https://www.instagram.com/p/POST_ID/ yoki https://www.instagram.com/reel/REEL_ID/)")
        return

    url = m.group(0)
    await update.message.chat.send_action(action='upload_video')

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
    except Exception as e:
        logger.exception('Request failed')
        await update.message.reply_text("URL ga ulanishda xatolik bo'ldi: %s" % str(e))
        return

    page_text = resp.text
    if resp.status_code != 200 or ('login' in page_text.lower() and 'required' in page_text.lower()):
        modified = modify_private_link(url)
        await update.message.reply_text(f"VIDEO YUKLANDI! KO'CHIRIB OLISHINGIZ MUMKIN sizni link: {modified}")
        return

    video_url = extract_instagram_video_url(page_text)
    if not video_url:
        modified = modify_private_link(url)
        await update.message.reply_text(f"Video topilmadi (ehtimol private). Mana o'zgartirilgan link: {modified}")
        return

    try:
        dl_resp = requests.get(video_url, headers=HEADERS, timeout=DOWNLOAD_TIMEOUT, stream=True)
        dl_resp.raise_for_status()
    except Exception as e:
        logger.exception('Download failed')
        await update.message.reply_text("Videoni yuklab olishda xatolik yuz berdi. Mana o'zgartirilgan link: %s" % modify_private_link(url))
        return

    suffix = '.mp4'
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        with open(tmp_path, 'wb') as f:
            for chunk in dl_resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        await update.message.reply_video(video=open(tmp_path, 'rb'))
    except Exception as e:
        logger.exception('Send failed')
        await update.message.reply_text("Videoni yuborishda xatolik yuz berdi: %s" % str(e))
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

def main():
    if not TOKEN:
        print('Iltimos config.py faylida TOKEN ni sozlang: TOKEN = "YOUR_BOT_TOKEN"')
        return

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print('Bot ishga tushdi...')
    app.run_polling()

if __name__ == '__main__':
    main()
