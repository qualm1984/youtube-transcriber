import json
import sys
from faster_whisper import WhisperModel

def transcribe_audio(audio_file, model_path, device, output_file):
    model = WhisperModel(model_path, device=device, compute_type="float16")
    
    segments, info = model.transcribe(audio_file, beam_size=5, language="en")
    print(json.dumps({"status": f"Detected language '{info.language}' with probability {info.language_probability}"}))
    sys.stdout.flush()

    with open(output_file, 'w', encoding='utf-8') as f:
        for segment in segments:
            f.write(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}\n")
            print(json.dumps({"status": f"Transcribed segment: {segment.start:.2f}s -> {segment.end:.2f}s", "progress": min(int((segment.end / info.duration) * 100), 99)}))
            sys.stdout.flush()