import ffmpeg
import os
import logging
from typing import Optional

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
