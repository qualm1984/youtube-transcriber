import os
import traceback
import sys
import threading
import time
from PyQt6.QtCore import QObject, pyqtSignal
from utils.youtube_utils import download_or_use_existing_audio
from utils.transcription_util import transcribe_audio
from utils.claude_utils import process_with_claude, read_transcript

class WorkerSignals(QObject):
    log = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    finished = pyqtSignal()
    output = pyqtSignal(str)
    error = pyqtSignal(str)

class Worker(threading.Thread):
    def __init__(self, url, model_path, device, api_key):
        super().__init__()
        self.url = url
        self.model_path = model_path
        self.device = device
        self.api_key = api_key
        self.signals = WorkerSignals()

    def run(self):
        try:
            self.log_and_print("Worker: Starting process...")
            self.signals.progress_update.emit(0)

            self.log_and_print("Worker: Downloading or locating audio file...")
            audio_file, video_title = download_or_use_existing_audio(self.url, self.signals)
            self.log_and_print(f"Worker: Using audio file: {audio_file}")

            self.output_file = os.path.abspath(f"{video_title}.txt")
            self.markdown_file = os.path.abspath(f"{video_title}_analysis.md")

            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(f"Transcript for: {video_title}\n\n")
            self.log_and_print(f"Worker: Created output file: {self.output_file}")

            self.log_and_print("Worker: Starting transcription process...")
            transcribe_audio(audio_file, self.model_path, self.device, self.signals, self.output_file)
            self.log_and_print("Worker: Transcription process completed.")

            self.log_and_print("Worker: Waiting for 5 seconds...")
            time.sleep(5)  # Add a 5-second delay
            self.log_and_print("Worker: 5-second wait completed.")

            self.log_and_print("Worker: Preparing to send transcript to Claude API for analysis...")
            try:
                self.log_and_print("Worker: Attempting to read transcript...")
                transcript_text = read_transcript(self.output_file)
                self.log_and_print(f"Worker: Transcript read successfully. Length: {len(transcript_text)}")
                
                self.log_and_print("Worker: Checking API key...")
                if not self.api_key:
                    raise ValueError("API key is empty or invalid")
                
                self.log_and_print("Worker: Sending to Claude API...")
                self.log_and_print(f"Worker: API Key (first 5 chars): {self.api_key[:5]}...")
                markdown_output = process_with_claude(self.api_key, transcript_text)
                self.log_and_print("Worker: Received response from Claude API. Writing to file...")
                
                with open(self.markdown_file, 'w', encoding='utf-8') as f:
                    f.write(markdown_output)
                self.log_and_print(f"Worker: Markdown content written to file: {self.markdown_file}")
            except Exception as e:
                self.log_and_print(f"Worker: Error in Claude API processing or writing markdown: {str(e)}")
                self.log_and_print(traceback.format_exc())
                self.signals.error.emit(f"Error in Claude API processing: {str(e)}")
                raise

            self.signals.progress_update.emit(100)
            self.signals.output.emit(f"Process completed successfully.\nTranscript saved to: {self.output_file}\nMarkdown analysis saved to: {self.markdown_file}")
        except Exception as e:
            self.log_and_print(f"Worker: An error occurred during processing: {str(e)}")
            self.log_and_print(traceback.format_exc())
            self.signals.error.emit(f"Error: {str(e)}\n{traceback.format_exc()}")
        finally:
            self.log_and_print("Worker: Finished execution.")
            self.signals.finished.emit()

        sys.stdout.flush()  # Ensure all print statements are flushed to console

    def log_and_print(self, message):
        print(message, flush=True)
        self.signals.log.emit(message)