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
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'noplaylist': True,
            'outtmpl': f'{Config.DOWNLOAD_PATH}/%(id)s.%(ext)s',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'geo_bypass': True,
        }
        if os.path.exists('cookies.txt'):
            self.common_opts['cookiefile'] = 'cookies.txt'

    async def download(self, url: str, mode: str = 'video') -> Dict[str, Any]:
        if mode == 'audio':
            return await self._download_full_audio(url)
        
        return await self._download_video(url)

    async def _download_video(self, url: str) -> Dict[str, Any]:
        opts = self.common_opts.copy()
        opts['format'] = 'best[ext=mp4]/best'
        
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            file_path = ydl.prepare_filename(info)
            return {
                'file_path': file_path,
                'title': info.get('title', 'Video'),
                'duration': info.get('duration', 0),
                'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
            }

    async def _download_full_audio(self, url: str) -> Dict[str, Any]:
        """
        Dastlab Instagram metama'lumotlaridan qo'shiqni qidiradi, 
        sandra uni to'liq holda YouTube-dan yuklaydi.
        """
        loop = asyncio.get_event_loop()
        
        # 1. Instagram ma'lumotlarini olish
        with yt_dlp.YoutubeDL(self.common_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            
            # Instagram-dan qo'shiq nomini qidirish
            track = info.get('track')
            artist = info.get('artist')
            
            search_query = None
            if track and artist:
                search_query = f"ytsearch1:{artist} - {track} lyrics"
            elif track:
                search_query = f"ytsearch1:{track} full audio"
            
            # 2. Agar qo'shiq nomi bo'lsa, YouTube-dan qidirib yuklaymiz
            if search_query:
                opts = self.common_opts.copy()
                opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                })
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl_yt:
                        yt_info = await loop.run_in_executor(None, lambda: ydl_yt.extract_info(search_query, download=True))
                        entries = yt_info.get('entries', [])
                        if entries:
                            video_info = entries[0]
                            file_path = ydl_yt.prepare_filename(video_info)
                            # yt-dlp mp3 ga o'girganda ext o'zgaradi
                            file_path = os.path.splitext(file_path)[0] + ".mp3"
                            
                            return {
                                'file_path': file_path,
                                'title': f"{artist} - {track}" if track and artist else video_info.get('title'),
                                'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
                            }
                except Exception as e:
                    logging.warning(f"YouTube search failed: {e}")

            # 3. Fallback: Agar YouTube-dan topilmasa, videoning o'z audiosini olamiz
            opts = self.common_opts.copy()
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
            with yt_dlp.YoutubeDL(opts) as ydl_orig:
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
