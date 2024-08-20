import os
import logging
from pytubefix import YouTube

def download_or_use_existing_audio(url, signals):
    try:
        signals.log.emit(f"Processing video from URL: {url}")
        video = YouTube(url)
        video_title = video.title
        safe_title = "".join([c for c in video_title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        total_duration = video.length
        signals.log.emit(f"Video title: {safe_title}")
        signals.log.emit(f"Video duration: {total_duration} seconds")
        mp4_file = f"{safe_title}.mp4"
        mp3_file = f"{safe_title}.mp3"
        if os.path.exists(mp3_file):
            signals.log.emit(f"Using existing MP3 file: {mp3_file}")
            return mp3_file, safe_title
        elif os.path.exists(mp4_file):
            signals.log.emit(f"Using existing MP4 file: {mp4_file}")
            return mp4_file, safe_title
        else:
            signals.log.emit("Downloading audio...")
            audio = video.streams.filter(only_audio=True).first()
            if audio is None:
                raise ValueError("No audio stream found for this video.")
            output = audio.download(output_path=".", filename=safe_title)
            base, ext = os.path.splitext(output)
            new_file = f"{base}.mp3"
            os.rename(output, new_file)
            signals.log.emit(f"Audio download completed: {new_file}")
            return new_file, safe_title
    except Exception as e:
        signals.log.emit(f"Error in download_or_use_existing_audio: {str(e)}")
        logging.exception("Error in download_or_use_existing_audio")
        raise