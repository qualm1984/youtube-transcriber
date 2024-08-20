from faster_whisper import WhisperModel
import torch

model_size = "large-v3"
# Run on GPU with FP16
model = WhisperModel(model_size, device="cuda", compute_type="float16")

segments, info = model.transcribe("youtube-video-audio.mp3", beam_size=5, language="en")

print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

with open('youtube-video-audio.txt', 'wb') as f:
    for segment in segments:
        f.write(("[%.2fs -> %.2fs] %s\n" % (segment.start, segment.end, segment.text)).encode('utf-8'))
