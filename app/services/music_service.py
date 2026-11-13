import os
import asyncio
import logging
from typing import Dict, Any, Optional, List
import yt_dlp
import ffmpeg
from config import Config

try:
    from shazamio import Shazam
    HAS_SHAZAM = True
except Exception as e:
    logging.warning(f"Shazamio kutubxonasi mavjud emas yoki yuklanmadi: {e}")
    HAS_SHAZAM = False

class MusicService:
    def __init__(self):
        self.shazam = Shazam() if HAS_SHAZAM else None

    async def recognize_audio(self, audio_or_video_path: str) -> Optional[Dict[str, str]]:
        """
        Audio yoki video fayldan musiqani Shazam orqali aniqlaydi.
        Natija: {'title': 'Shape of My Heart', 'artist': 'Sting'} yoki None
        """
        if not HAS_SHAZAM or not self.shazam or not os.path.exists(audio_or_video_path):
            return None

        # Videodan tezkor 12-sekundlik audio fragment qirqib olish (Shazam tez tanishi uchun)
        sample_path = f"{os.path.splitext(audio_or_video_path)[0]}_sample.mp3"
        try:
            (
                ffmpeg
                .input(audio_or_video_path, ss=0.0, t=12)
                .output(sample_path, vn=None, acodec='libmp3lame', audio_bitrate='128k')
                .overwrite_output()
                .run(quiet=True)
            )
            target_file = sample_path if (os.path.exists(sample_path) and os.path.getsize(sample_path) > 0) else audio_or_video_path

            out = await self.shazam.recognize(target_file)
            track = out.get('track')
            if track:
                title = track.get('title')
                artist = track.get('subtitle')
                if title:
                    return {
                        'title': title,
                        'artist': artist or "Noma'lum ijrochi"
                    }
        except Exception as e:
            logging.warning(f"Musiqani Shazam orqali aniqlashda xatolik: {e}")
        finally:
            if os.path.exists(sample_path):
                try:
                    os.remove(sample_path)
                except Exception:
                    pass

        return None

    async def get_music_info_from_url(self, url: str) -> Optional[Dict[str, str]]:
        """
        Havoladan (Instagram, TikTok, YouTube) musiqani aniqlash:
        1. Avval postning rasmiy metadata (track, artist) sini tekshiradi.
        2. Topilmasa yoki 'Original audio' bo'lsa, audio fragmentini olib Shazam orqali taniydi.
        """
        loop = asyncio.get_event_loop()
        cookie_file = 'cookies.txt' if os.path.exists('cookies.txt') else ('Cookie.txt' if os.path.exists('Cookie.txt') else None)

        opts = {
            'quiet': True,
            'extract_flat': False,
            'socket_timeout': 10,
        }
        if cookie_file:
            opts['cookiefile'] = cookie_file

        if Config.TIKTOK_PROXY and any(d in url.lower() for d in ['tiktok.com', 'douyin.com']):
            proxy = Config.TIKTOK_PROXY
            if proxy.startswith('socks5://'):
                proxy = 'socks5h://' + proxy[9:]
            opts['proxy'] = proxy

        def _get_info():
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            info = await loop.run_in_executor(None, _get_info)
            if info:
                track = info.get('track')
                artist = info.get('artist')
                
                # Agar aniq qo'shiq nomi bo'lsa
                if track and track.lower() not in ['original audio', 'original sound', 'audio']:
                    return {
                        'title': track,
                        'artist': artist or ""
                    }
        except Exception as e:
            logging.warning(f"URL metadatasini olishda xatolik ({url}): {e}")

        # 2-bosqich: Agar Shazam mavjud bo'lsa, audioni eshitib ko'rish
        if HAS_SHAZAM and self.shazam:
            prefix = f"{Config.DOWNLOAD_PATH}/shazam_{abs(hash(url)) % 100000}"
            opts_audio = {
                'quiet': True,
                'no_warnings': True,
                'format': 'bestaudio/best',
                'outtmpl': f"{prefix}.%(ext)s",
                'socket_timeout': 15,
                'postprocessor_args': {'ffmpeg': ['-t', '15']},
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '128',
                }],
            }
            if cookie_file:
                opts_audio['cookiefile'] = cookie_file

            if Config.TIKTOK_PROXY and any(d in url.lower() for d in ['tiktok.com', 'douyin.com']):
                proxy = Config.TIKTOK_PROXY
                if proxy.startswith('socks5://'):
                    proxy = 'socks5h://' + proxy[9:]
                opts_audio['proxy'] = proxy

            def _download_sample():
                with yt_dlp.YoutubeDL(opts_audio) as ydl_s:
                    return ydl_s.extract_info(url, download=True)

            try:
                await loop.run_in_executor(None, _download_sample)
                target_mp3 = f"{prefix}.mp3"
                if os.path.exists(target_mp3):
                    res = await self.recognize_audio(target_mp3)
                    try:
                        os.remove(target_mp3)
                    except Exception:
                        pass
                    if res:
                        return res
            except Exception as ex:
                logging.warning(f"Shazam orqali audio yuklab aniqlashda xatolik: {ex}")

        return None

    async def search_tracks(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        YouTube'dan 5 tagacha eng mos treklarni qidiradi.
        """
        loop = asyncio.get_event_loop()
        opts = {
            'quiet': True,
            'extract_flat': True,
            'socket_timeout': 10,
            'extractor_args': {
                'youtube': {'player_client': ['ios', 'android', 'web']}
            }
        }
        
        def _search():
            with yt_dlp.YoutubeDL(opts) as ydl:
                res = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
                entries = res.get('entries', []) if res else []
                results = []
                for e in entries:
                    if not e or not e.get('id'):
                        continue
                    dur = e.get('duration') or 0
                    m, s = divmod(int(dur), 60)
                    dur_str = f"{m}:{s:02d}" if dur else ""
                    results.append({
                        'id': e.get('id'),
                        'title': e.get('title') or query,
                        'duration_str': dur_str,
                        'duration': dur,
                        'url': f"https://www.youtube.com/watch?v={e.get('id')}"
                    })
                return results

        try:
            return await loop.run_in_executor(None, _search)
        except Exception as e:
            logging.warning(f"YouTube musiqalarni qidirishda xatolik: {e}")
            return []

    async def download_track(self, yt_id: str) -> Optional[Dict[str, Any]]:
        """
        Berilgan YouTube video ID bo'yicha audio MP3 ni sifatli yuklab oladi.
        """
        loop = asyncio.get_event_loop()
        output_template = f"{Config.DOWNLOAD_PATH}/music_{yt_id}.%(ext)s"
        target_mp3 = f"{Config.DOWNLOAD_PATH}/music_{yt_id}.mp3"

        opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'socket_timeout': 15,
            'extractor_args': {
                'youtube': {'player_client': ['ios', 'android', 'web']}
            },
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        def _download():
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={yt_id}", download=True)
                title = info.get('title') or "Audio"
                artist = info.get('artist') or info.get('uploader') or ""
                return {
                    'file_path': target_mp3,
                    'title': title,
                    'artist': artist,
                    'duration': info.get('duration', 0)
                }

        try:
            res = await loop.run_in_executor(None, _download)
            if os.path.exists(target_mp3) and os.path.getsize(target_mp3) > 0:
                return res
        except Exception as e:
            logging.error(f"YouTube audioni yuklab olishda xatolik ({yt_id}): {e}")

        return None
