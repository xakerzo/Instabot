import yt_dlp
import asyncio
import os
import hashlib
from typing import Dict, Any, Optional
from config import Config

class DownloaderService:
    def __init__(self):
        self.common_opts = {
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'noplaylist': True,
            'outtmpl': f'{Config.DOWNLOAD_PATH}/%(id)s.%(ext)s',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'geo_bypass': True,
            # IPv4 ni majburiy qilish (Blokdan qochish uchun juda muhim)
            'source_address': '0.0.0.0',
            'socket_timeout': 30,
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
            # Soddaroq format: agar murakkab format o'xshamasa, oddiy mp4-ni oladi
            opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'

        proxy = self._get_proxy()
        if proxy:
            # SOCKS5 yoki HTTP-ni avtomatik aniqlash uchun
            opts['proxy'] = proxy

        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(opts) as ydl:
            # Eng kamida 5 marta qayta urinish
            ydl.params['retries'] = 5
            ydl.params['fragment_retries'] = 10
            
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            
            file_path = ydl.prepare_filename(info)
            if mode == 'audio':
                file_path = os.path.splitext(file_path)[0] + ".mp3"
            
            # Agar fayl nomi o'zgarib ketgan bo'lsa (ext sababli)
            if not os.path.exists(file_path):
                # Faylni qidirib ko'ramiz
                base_name = os.path.splitext(file_path)[0]
                for f in os.listdir(Config.DOWNLOAD_PATH):
                    if f.startswith(os.path.basename(base_name)):
                        file_path = os.path.join(Config.DOWNLOAD_PATH, f)
                        break

            return {
                'file_path': file_path,
                'title': info.get('title', 'No Title'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail'),
                'ext': info.get('ext', 'mp4'),
                'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
            }

    @staticmethod
    def get_url_hash(url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()
