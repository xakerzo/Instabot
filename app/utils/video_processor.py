import ffmpeg
import os
import logging
from typing import Optional, Dict, Any

def get_video_info(video_path: str) -> Dict[str, Any]:
    """
    Videodan davomiylik (duration), o'lchamlar (width, height) va 
    Telegram uchun chiroyli preview thumbnail (.jpg) hosil qiladi.
    Bu video Telegramda oppoq bo'lib qolmasligini va davomiyligi (masalan 1:01) to'g'ri chiqishini ta'minlaydi.
    """
    thumb_path = None
    width = None
    height = None
    duration = 0
    
    if not os.path.exists(video_path):
        return {'duration': 0, 'width': None, 'height': None, 'thumb_path': None}
        
    try:
        probe = ffmpeg.probe(video_path)
        format_info = probe.get('format', {})
        duration = int(float(format_info.get('duration', 0)))
        
        video_stream = next((s for s in probe.get('streams', []) if s.get('codec_type') == 'video'), None)
        if video_stream:
            width = int(video_stream.get('width', 0)) or None
            height = int(video_stream.get('height', 0)) or None
            
            # Agar formatda duration bo'lmasa, streamdan olish
            if not duration:
                stream_dur = video_stream.get('duration')
                if stream_dur:
                    try:
                        duration = int(float(stream_dur))
                    except Exception:
                        pass
                    
            # Rotatsiya tekshirish (90 yoki 270 gradus bo'lsa width va height almashadi)
            rotation = 0
            for sd in video_stream.get('side_data_list', []):
                if 'rotation' in sd:
                    try:
                        rotation = abs(int(sd['rotation']))
                    except Exception:
                        pass
            if not rotation:
                tags = video_stream.get('tags', {})
                try:
                    rotation = abs(int(tags.get('rotate', 0)))
                except Exception:
                    pass
            if rotation in (90, 270) and width and height:
                width, height = height, width

        base_name, _ = os.path.splitext(video_path)
        thumb_candidate = f"{base_name}_thumb.jpg"
        
        # 1-sekunddagi kadrni olish (video 2s dan qisqa bo'lsa 0.5s yoki 0s)
        if duration >= 2:
            ss_time = 1.0
        elif duration >= 1:
            ss_time = 0.5
        else:
            ss_time = 0.0
            
        # Telegram Bot API qoidasi:
        # Thumbnail JPEG formatda bo'lishi, 200KB dan oshmasligi va 
        # ENI ham, BO'YI ham 320px dan oshmasligi SHART!
        # Aks holda Telegram thumbnailni qabul qilmaydi va video oppoq bo'lib qoladi.
        try:
            (
                ffmpeg
                .input(video_path, ss=ss_time)
                .filter('scale', 'if(gt(iw,ih),320,-2)', 'if(gt(iw,ih),-2,320)')
                .output(thumb_candidate, vframes=1, **{'q:v': 2})
                .overwrite_output()
                .run(quiet=True)
            )
        except Exception:
            pass
            
        # Agar ss_time da kadr olinmasa, 0.0s dan olishga urinish
        if not os.path.exists(thumb_candidate) or os.path.getsize(thumb_candidate) == 0:
            try:
                (
                    ffmpeg
                    .input(video_path, ss=0.0)
                    .filter('scale', 'if(gt(iw,ih),320,-2)', 'if(gt(iw,ih),-2,320)')
                    .output(thumb_candidate, vframes=1, **{'q:v': 2})
                    .overwrite_output()
                    .run(quiet=True)
                )
            except Exception:
                pass

        if os.path.exists(thumb_candidate) and os.path.getsize(thumb_candidate) > 0:
            # Telegram 200KB limitidan oshmasligini tekshirish
            if os.path.getsize(thumb_candidate) <= 200 * 1024:
                thumb_path = thumb_candidate
            else:
                try:
                    (
                        ffmpeg
                        .input(video_path, ss=ss_time)
                        .filter('scale', 'if(gt(iw,ih),320,-2)', 'if(gt(iw,ih),-2,320)')
                        .output(thumb_candidate, vframes=1, **{'q:v': 8})
                        .overwrite_output()
                        .run(quiet=True)
                    )
                    if os.path.exists(thumb_candidate) and os.path.getsize(thumb_candidate) <= 200 * 1024:
                        thumb_path = thumb_candidate
                except Exception:
                    pass
    except Exception as e:
        logging.warning(f"Video preview yoki metadata olishda xatolik: {e}")
        
    return {
        'duration': duration,
        'width': width,
        'height': height,
        'thumb_path': thumb_path
    }

def compress_video(input_path: str, target_size_mb: int = 48) -> str:
    """
    Videoni Telegram limitiga (masalan 48-49MB) moslab sifatli siqish.
    Agar fayl belgilangan hajmdan kichik bo'lsa, asl fayl yo'li qaytariladi.
    """
    if not os.path.exists(input_path):
        return input_path
        
    file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
    if file_size_mb <= target_size_mb:
        return input_path

    base_name, _ = os.path.splitext(input_path)
    output_path = f"{base_name}_compressed.mp4"
    
    try:
        probe = ffmpeg.probe(input_path)
        format_info = probe.get('format', {})
        duration = float(format_info.get('duration', 0))
        
        if duration <= 0:
            logging.warning(f"Video davomiyligini aniqlab bo'lmadi: {input_path}")
            return input_path
        
        # Maqsadli umumiy bitrate (bits per second)
        target_total_bitrate = (target_size_mb * 1024 * 1024 * 8) / duration
        video_bitrate = int(target_total_bitrate * 0.88)
        audio_bitrate = int(min(target_total_bitrate * 0.12, 128000))
        
        (
            ffmpeg
            .input(input_path)
            .output(
                output_path,
                vcodec='libx264',
                video_bitrate=video_bitrate,
                acodec='aac',
                audio_bitrate=audio_bitrate,
                preset='veryfast',
                movflags='+faststart'
            )
            .overwrite_output()
            .run(quiet=True)
        )
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logging.info(f"Video muvaffaqiyatli siqildi: {output_path} ({os.path.getsize(output_path)/(1024*1024):.1f}MB)")
            return output_path
            
        return input_path
    except Exception as e:
        logging.warning(f"Video siqishda xatolik: {e}")
        return input_path
