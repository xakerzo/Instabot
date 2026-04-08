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
        }
        
    def _get_proxy(self) -> Optional[str]:
        if not Config.USE_PROXY:
            return None
        # Bu yerda oddiy proxy rotation mantiqini qo'shish mumkin
        # Masalan, proxies.txt faylidan tasodifiy bittasini olish
        if os.path.exists(Config.PROXY_LIST_PATH):
            with open(Config.PROXY_LIST_PATH, 'r') as f:
                proxies = f.readlines()
                if proxies:
                    import random
                    return random.choice(proxies).strip()
        return None

    async def extract_info(self, url: str) -> Dict[str, Any]:
        """Video haqida ma'lumot olish (yuklamasdan)"""
        opts = self.common_opts.copy()
        proxy = self._get_proxy()
        if proxy:
            opts['proxy'] = proxy

        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(opts) as ydl:
            # extract_info bloklovchi funksiya, shuning uchun run_in_executor ishlatamiz
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            return info

    async def download(self, url: str, mode: str = 'video') -> Dict[str, Any]:
        """Videoni yoki audioni yuklab olish"""
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
            # Eng yaxshi sifat, lekin max_file_size dan oshmasligi kerak (ixtiyoriy)
            opts['format'] = f'bestvideo[ext=mp4]+bestaudio[m4a]/best[ext=mp4]/best'

        proxy = self._get_proxy()
        if proxy:
            opts['proxy'] = proxy

        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            
            file_path = ydl.prepare_filename(info)
            if mode == 'audio':
                file_path = os.path.splitext(file_path)[0] + ".mp3"
            
            return {
                'file_path': file_path,
                'title': info.get('title', 'No Title'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail'),
                'ext': 'mp3' if mode == 'audio' else info.get('ext', 'mp4'),
                'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
            }

    @staticmethod
    def get_url_hash(url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()
