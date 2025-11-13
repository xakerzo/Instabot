# bot.py
"""
Telegram bot to download public Instagram videos (no login).
For private accounts the bot will return a modified link by replacing
'instagram.com' hosts with 'kkinstagram.com' (no dot after 'kk').

Requirements:
  pip install python-telegram-bot==20.6 requests beautifulsoup4

Usage:
  1. Create config.py with a line: TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
  2. Run: python bot.py
"""

import os
import re
import tempfile
import logging
import html
from typing import Optional

import requests
from bs4 import BeautifulSoup

from telegram import Update
from telegram.constants import ChatAction
from telegram.error import TelegramError, BadRequest
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# Load TOKEN from config.py
try:
    from config import TOKEN
except Exception:
    TOKEN = None

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
DOWNLOAD_TIMEOUT = 60  # seconds
LOG_LEVEL = logging.INFO

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

INSTAGRAM_HOSTS = ["www.instagram.com", "instagram.com", "m.instagram.com"]


def modify_private_link(url: str) -> str:
    """Replace instagram host with kkinstagram.com (no dot after kk)."""
    for host in INSTAGRAM_HOSTS:
        if host in url:
            return url.replace(host, "kkinstagram.com")
    # fallback
    if "instagram" in url and not url.startswith("http"):
        return "https://kkinstagram.com/" + url
    return url


def extract_instagram_video_url(page_html: str) -> Optional[str]:
    """
    Try to extract a direct video URL from Instagram page HTML.
    Returns video URL string or None.
    """
    soup = BeautifulSoup(page_html, "html.parser")

    # 1) meta og:video
    meta = soup.find("meta", property="og:video") or soup.find("meta", property="og:video:secure_url")
    if meta and meta.get("content"):
        return meta["content"]

    # 2) JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            txt = script.string
            if not txt:
                continue
            if "contentUrl" in txt:
                m = re.search(r'"contentUrl"\s*:\s*"([^"]+)"', txt)
                if m:
                    return m.group(1)
        except Exception:
            continue

    # 3) window._sharedData or graphql blobs
    for s in soup.find_all("script"):
        if not s.string:
            continue
        text = s.string
        if "video_url" in text:
            m = re.search(r'"video_url"\s*:\s*"([^"]+)"', text)
            if m:
                return m.group(1).replace(r"\/", "/").replace(r"\u0026", "&")
        # sometimes display_url is present (best-effort)
        if "display_url" in text:
            m2 = re.search(r'"display_url"\s*:\s*"([^"]+)"', text)
            if m2:
                return m2.group(1).replace(r"\/", "/")

    return None


def download_to_temp(url: str, headers: dict, timeout: int = DOWNLOAD_TIMEOUT) -> Optional[str]:
    """Download a URL to a temporary file and return the file path, or None on failure."""
    try:
        with requests.get(url, headers=headers, timeout=timeout, stream=True) as r:
            r.raise_for_status()
            suffix = ".mp4"
            fd, tmp_path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return tmp_path
    except Exception as e:
        logger.exception("Failed to download file: %s", e)
        return None


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Instagramdan video link yuboring! Men uni yuklab beraman!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("Link yuboring.")
        return

    # find instagram url
    m = re.search(r"(https?://[\w\./\-\?=&%]+instagram\.com[\w\./\-\?=&%]*)", text)
    if not m:
        # also try without scheme
        m2 = re.search(r"(instagram\.com/[\w\./\-\?=&%]+)", text)
        if m2:
            url = "https://" + m2.group(1)
        else:
            await update.message.reply_text(
                "Instagram linkini yuboring (misol: https://www.instagram.com/p/POST_ID/ yoki https://www.instagram.com/reel/REEL_ID/)"
            )
            return
    else:
        url = m.group(0)

    chat_id = update.effective_chat.id

    # show upload action
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_VIDEO)
    except Exception:
        # not fatal, continue
        pass

    # fetch page
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
    except Exception as e:
        logger.exception("Request failed: %s", e)
        await update.message.reply_text(f"URL ga ulanishda xatolik bo'ldi: {e}")
        return

    if resp.status_code != 200:
        # can't access page -> treat as private
        modified = modify_private_link(url)
        escaped = html.escape(modified, quote=True)
        msg = f"<b>VIDEO YUKLANDI! KO'CHIRIB OLISHINGIZ MUMKIN</b>\nLink: <a href=\"{escaped}\">Video Link</a>"
        # send as HTML (escaped)
        try:
            await update.message.reply_text(msg, parse_mode="HTML")
        except BadRequest as e:
            logger.warning("Failed to send modified link (BadRequest): %s", e)
            await update.message.reply_text(f"Link: {modified}")
        return

    page_text = resp.text
    # quick heuristic: if instagram returns login wall HTML it often contains 'login' and 'required' / 'Log in'
    if ("login" in page_text.lower() and ("required" in page_text.lower() or "log in" in page_text.lower())):
        modified = modify_private_link(url)
        escaped = html.escape(modified, quote=True)
        msg = f"<b>VIDEO YUKLANDI! KO'CHIRIB OLISHINGIZ MUMKIN</b>\nLink: <a href=\"{escaped}\">Video Link</a>"
        try:
            await update.message.reply_text(msg, parse_mode="HTML")
        except BadRequest:
            await update.message.reply_text(f"Link: {modified}")
        return

    # try to extract direct video url
    video_url = extract_instagram_video_url(page_text)

    if not video_url:
        # couldn't find a direct video URL -> treat as private / complex
        modified = modify_private_link(url)
        escaped = html.escape(modified, quote=True)
        msg = f"<b>VIDEO YUKLANDI! KO'CHIRIB OLISHINGIZ MUMKIN</b>\nLink: <a href=\"{escaped}\">Video Link</a>"
        try:
            await update.message.reply_text(msg, parse_mode="HTML")
        except BadRequest:
            await update.message.reply_text(f"Link: {modified}")
        return

    # we have a direct video url -> download and send
    tmp_path = download_to_temp(video_url, HEADERS, timeout=DOWNLOAD_TIMEOUT)
    if not tmp_path:
        # download failed -> fallback to modified link
        modified = modify_private_link(url)
        escaped = html.escape(modified, quote=True)
        msg = f"<b>VIDEO YUKLANDI! KO'CHIRIB OLISHINGIZ MUMKIN</b>\nLink: <a href=\"{escaped}\">Video Link</a>"
        try:
            await update.message.reply_text(msg, parse_mode="HTML")
        except BadRequest:
            await update.message.reply_text(f"Link: {modified}")
        return

    # try to send video; if fails, send fallback message with link
    try:
        # use reply_video which supports file handle
        with open(tmp_path, "rb") as video_file:
            await update.message.reply_video(video=video_file)
    except BadRequest as e:
        # usually entity parsing errors or file issues -> send fallback message
        logger.exception("BadRequest when sending video: %s", e)
        modified = modify_private_link(url)
        escaped = html.escape(modified, quote=True)
        msg = f"<b>VIDEO YUKLANDI! KO'CHIRIB OLISHINGIZ MUMKIN</b>\nLink: <a href=\"{escaped}\">Video Link</a>"
        try:
            await update.message.reply_text(msg, parse_mode="HTML")
        except Exception:
            await update.message.reply_text(f"Link: {modified}")
    except TelegramError as e:
        logger.exception("Telegram error sending video: %s", e)
        modified = modify_private_link(url)
        try:
            await update.message.reply_text(f"Videoni yuborishda xatolik yuz berdi. Link: {modified}")
        except Exception:
            pass
    finally:
        # cleanup
        try:
            os.remove(tmp_path)
        except Exception:
            pass


def main():
    if not TOKEN:
        print('Iltimos config.py faylida TOKEN ni sozlang: TOKEN = "YOUR_BOT_TOKEN"')
        return

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
