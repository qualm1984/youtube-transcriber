import os
import re
import yt_dlp
import glob

def sanitize_filename(filename):
    # Remove invalid characters
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)
    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')
    return sanitized

def download_or_use_existing_audio(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': '%(title)s.%(ext)s',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            print("Starting download process...")
            info = ydl.extract_info(url, download=True)
            video_title = info['title']
            safe_title = sanitize_filename(video_title)
            print(f"Video title: {video_title}")
            print(f"Sanitized title: {safe_title}")

            print("Searching for downloaded file...")
            mp3_files = glob.glob("*.mp3")
            print(f"MP3 files found: {mp3_files}")

            if not mp3_files:
                raise FileNotFoundError(f"Could not find any MP3 files after download.")

            # Use the first MP3 file found
            downloaded_file = mp3_files[0]
            print(f"Using file: {downloaded_file}")

            # Rename the file if it's not already in the desired format
            audio_file = f"{safe_title}.mp3"
            if downloaded_file != audio_file:
                os.rename(downloaded_file, audio_file)
                print(f"Renamed {downloaded_file} to {audio_file}")

            if not os.path.exists(audio_file):
                raise FileNotFoundError(f"Could not find or create audio file: {audio_file}")

            print(f"Final audio file: {audio_file}")
            return audio_file, safe_title

        except Exception as e:
            print(f"Error in download_or_use_existing_audio: {str(e)}")
            raise