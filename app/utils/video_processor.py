import ffmpeg
import os
import math
from config import Config

def compress_video(input_path: str, target_size_mb: int = 49) -> str:
    """Videoni Telegram limitiga (masalan 49MB) moslab siqish"""
    if not os.path.exists(input_path):
        return input_path
        
    file_size = os.path.getsize(input_path) / (1024 * 1024)
    if file_size <= target_size_mb:
        return input_path

    output_path = input_path.replace(".mp4", "_compressed.mp4")
    
    try:
        probe = ffmpeg.probe(input_path)
        duration = float(probe['format']['duration'])
        
        # Maqsadli bitrate hisoblash
        # bit_rate = target_size / duration
        target_total_bitrate = (target_size_mb * 1024 * 1024 * 8) / duration
        video_bitrate = target_total_bitrate * 0.9 # 90% videoga
        audio_bitrate = target_total_bitrate * 0.1 # 10% audyoga
        
        (
            ffmpeg
            .input(input_path)
            .output(output_path, video_bitrate=video_bitrate, audio_bitrate=audio_bitrate)
            .overwrite_output()
            .run(quiet=True)
        )
        return output_path
    except Exception as e:
        print(f"Compression error: {e}")
        return input_path
