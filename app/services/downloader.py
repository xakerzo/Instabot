import yt_dlp
import asyncio
import os
import hashlib
import logging
import random
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
            # Brauzerni yanada aniqroq ko'rsatamiz
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'geo_bypass': True,
            'add_header': [
                'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language: en-US,en;q=0.9',
                'Sec-Fetch-Dest: document',
                'Sec-Fetch-Mode: navigate',
                'Sec-Fetch-Site: none',
                'Sec-Fetch-User: ?1',
                'Upgrade-Insecure-Requests: 1',
            ],
            'wait_for_video': (5, 10), # Instagram yuklanishini kutish
        }
        # Cookies faylini tekshirish (cookies.txt yoki Cookie.txt)
        cookie_file = 'cookies.txt' if os.path.exists('cookies.txt') else ('Cookie.txt' if os.path.exists('Cookie.txt') else None)
        
        if cookie_file:
            self.common_opts['cookiefile'] = cookie_file
        else:
            # Instagram uchun cookies juda muhim. Agar cookies.txt bo'lmasa, 
            # brauzerdan cookies olishga harakat qilamiz (lokal test uchun).
            try:
                self.common_opts['cookiesfrombrowser'] = ('chrome', 'edge', 'firefox', 'safari')
                logging.info("Cookies fayli topilmadi, brauzerdan cookies olishga urinib ko'ramiz.")
            except Exception as e:
                logging.warning(f"Brauzerdan cookies olishda xatolik: {e}")

    def _get_proxy(self) -> Optional[str]:
        if not Config.USE_PROXY:
            return None
        if os.path.exists(Config.PROXY_LIST_PATH):
            with open(Config.PROXY_LIST_PATH, 'r') as f:
                proxies = [l.strip() for l in f.readlines() if l.strip() and not l.startswith('#')]
                if proxies:
                    return random.choice(proxies)
        return None

    async def download(self, url: str, mode: str = 'video') -> Dict[str, Any]:
        # Har safar yangi proksi yoki proksisiz urinish
        proxy = self._get_proxy()
        
        if mode == 'audio':
            return await self._download_full_audio(url, proxy)
        
        return await self._download_video(url, proxy)

    async def _download_video(self, url: str, proxy: str = None) -> Dict[str, Any]:
        opts = self.common_opts.copy()
        opts['format'] = 'best[ext=mp4]/best'
        if proxy:
            opts['proxy'] = proxy
        
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(opts) as ydl:
            # So'rov oldidan biroz kutish (spam deb o'ylamasligi uchun)
            await asyncio.sleep(random.uniform(1, 3))
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            file_path = ydl.prepare_filename(info)
            return {
                'file_path': file_path,
                'title': info.get('title', 'Video'),
                'duration': info.get('duration', 0),
                'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
            }

    async def _download_full_audio(self, url: str, proxy: str = None) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        
        # Instagram-dan ma'lumot olish
        opts_info = self.common_opts.copy()
        if proxy:
            opts_info['proxy'] = proxy
            
        with yt_dlp.YoutubeDL(opts_info) as ydl:
            await asyncio.sleep(random.uniform(1, 2))
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            
            track = info.get('track')
            artist = info.get('artist')
            
            search_query = None
            if track and artist:
                search_query = f"ytsearch1:{artist} - {track} lyrics"
            elif track:
                search_query = f"ytsearch1:{track} full audio"
            
            if search_query:
                opts_yt = self.common_opts.copy()
                opts_yt.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                })
                # YouTube uchun proksi shart emas odatda
                try:
                    with yt_dlp.YoutubeDL(opts_yt) as ydl_yt:
                        yt_info = await loop.run_in_executor(None, lambda: ydl_yt.extract_info(search_query, download=True))
                        entries = yt_info.get('entries', [])
                        if entries:
                            video_info = entries[0]
                            file_path = ydl_yt.prepare_filename(video_info)
                            file_path = os.path.splitext(file_path)[0] + ".mp3"
                            return {
                                'file_path': file_path,
                                'title': f"{artist} - {track}" if track and artist else video_info.get('title'),
                                'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
                            }
                except Exception as e:
                    logging.warning(f"YouTube search failed: {e}")

            # Fallback
            opts_orig = opts_info.copy()
            opts_orig.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
            with yt_dlp.YoutubeDL(opts_orig) as ydl_orig:
                orig_info = await loop.run_in_executor(None, lambda: ydl_orig.extract_info(url, download=True))
                file_path = ydl_orig.prepare_filename(orig_info)
                file_path = os.path.splitext(file_path)[0] + ".mp3"
                return {
                    'file_path': file_path,
                    'title': orig_info.get('title', 'Audio'),
                    'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
                }

    @staticmethod
    def get_url_hash(url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()
