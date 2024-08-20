import os
from pytubefix import YouTube



def video_to_audio(video_URL, destination, final_filename):

  # Get the video
  video = YouTube(video_URL)

  # Convert video to Audio
  audio = video.streams.filter(only_audio=True).first()

  # Save to destination
  output = audio.download(output_path = destination)

  _, ext = os.path.splitext(output)
  new_file = final_filename + '.mp3'

  # Change the name of the file
  os.rename(output, new_file)

# Video to audio
video_URL = 'https://www.youtube.com/watch?v=RRBKv38Pm2c'
destination = "."
final_filename = "youtube-video"
video_to_audio(video_URL, destination, final_filename)