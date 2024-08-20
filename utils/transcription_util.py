from faster_whisper import WhisperModel

def transcribe_audio(audio_file, model_path, device, signals, output_file):
    try:
        signals.log.emit(f"Starting transcription using model: {model_path}")
        model = WhisperModel(model_path, device=device, compute_type="float16")
        signals.log.emit("Model loaded, beginning transcription")
        segments, info = model.transcribe(audio_file, beam_size=5, language="en")
        signals.log.emit(f"Detected language '{info.language}' with probability {info.language_probability}")
        total_duration = 0
        processed_duration = 0
        with open(output_file, 'a', encoding='utf-8') as f:
            for segment in segments:
                transcript_line = f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}\n"
                f.write(transcript_line)
                processed_duration += segment.end - segment.start
                total_duration = max(total_duration, segment.end)
                progress = min(int((processed_duration / total_duration) * 100), 99)
                signals.progress_update.emit(progress)
                signals.log.emit(f"Transcribed and wrote segment: {segment.start:.2f}s -> {segment.end:.2f}s")
        signals.log.emit("Transcription process completed.")
    except Exception as e:
        signals.log.emit(f"Error in transcribe_audio: {str(e)}")
        raise