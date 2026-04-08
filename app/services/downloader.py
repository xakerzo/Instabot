import yt_dlp
import asyncio
import os
import hashlib
import logging
from typing import Dict, Any, Optional
from config import Config

class DownloaderService:
    def __init__(self):
        self.common_opts = {
            'quiet': False, # Xatoliklarni ko'rish uchun True-dan False-ga
            'no_warnings': False,
            'nocheckcertificate': True,
            'noplaylist': True,
            'outtmpl': f'{Config.DOWNLOAD_PATH}/%(id)s.%(ext)s',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'geo_bypass': True,
            'source_address': '0.0.0.0',
        }
        
        if os.path.exists('cookies.txt'):
            self.common_opts['cookiefile'] = 'cookies.txt'
        
    def _get_proxy(self) -> Optional[str]:
        if not Config.USE_PROXY:
            return None
        if os.path.exists(Config.PROXY_LIST_PATH):
            with open(Config.PROXY_LIST_PATH, 'r') as f:
                proxies = [l.strip() for l in f.readlines() if l.strip() and not l.startswith('#')]
                if proxies:
                    import random
                    return random.choice(proxies)
        return None

    async def download(self, url: str, mode: str = 'video') -> Dict[str, Any]:
        opts = self.common_opts.copy()
        
        if mode == 'audio':
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            # Eng xavfsiz format: bitta mp4 faylni olish (merge talab qilmaydi)
            opts['format'] = 'best[ext=mp4]/best'

        proxy = self._get_proxy()
        if proxy:
            opts['proxy'] = proxy

        loop = asyncio.get_event_loop()
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
                file_path = ydl.prepare_filename(info)
                
                # Agar audio bo'lsa, ext o'zgaradi
                if mode == 'audio':
                    file_path = os.path.splitext(file_path)[0] + ".mp3"
                
                # Fayl borligini qayta tekshirish
                if not os.path.exists(file_path):
                    # Ba'zan extension o'zgargan bo'lishi mumkin
                    base = os.path.splitext(file_path)[0]
                    for f in os.listdir(Config.DOWNLOAD_PATH):
                        if f.startswith(os.path.basename(base)):
                            file_path = os.path.join(Config.DOWNLOAD_PATH, f)
                            break
                            
                return {
                    'file_path': file_path,
                    'title': info.get('title', 'No Title'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail'),
                    'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
                }
        except Exception as e:
            # Agar proksi bilan xato bersa, proksisiz urinib ko'ramiz
            if proxy:
                logging.warning(f"Proxy failed, retrying without proxy: {e}")
                opts.pop('proxy', None)
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
                    file_path = ydl.prepare_filename(info)
                    return {
                        'file_path': file_path,
                        'title': info.get('title', 'No Title'),
                        'duration': info.get('duration', 0),
                        'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    }
            raise e

    @staticmethod
    def get_url_hash(url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()
