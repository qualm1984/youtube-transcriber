import sys
import json
import os
from utils.transcription_util import transcribe_audio
from utils.claude_utils import process_with_claude, read_transcript

def main(audio_file, model_path, device, output_file, api_key):
    try:
        print(json.dumps({"status": "Starting transcription"}))
        sys.stdout.flush()

        # Verify that the audio file exists
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"Audio file not found: {audio_file}")

        transcribe_audio(audio_file, model_path, device, output_file)

        print(json.dumps({"status": "Transcription completed"}))
        sys.stdout.flush()

        transcript_text = read_transcript(output_file)
        
        print(json.dumps({"status": "Starting Claude API processing"}))
        sys.stdout.flush()

        markdown_output = process_with_claude(api_key, transcript_text)
        
        markdown_file = output_file.replace('.txt', '_analysis.md')
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(markdown_output)

        print(json.dumps({"status": "Process completed", "output_file": output_file, "markdown_file": markdown_file}))
        sys.stdout.flush()

    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.stdout.flush()

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])