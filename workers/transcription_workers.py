import os
import traceback
import logging
from PyQt6.QtCore import QRunnable, pyqtSignal, QObject
from utils.youtube_utils import download_or_use_existing_audio
from utils.transcription_util import transcribe_audio
from utils.claude_utils import process_with_claude, read_transcript

class WorkerSignals(QObject):
    log = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    finished = pyqtSignal()
    output = pyqtSignal(str)
    error = pyqtSignal(str)

class Worker(QRunnable):
    def __init__(self, url, model_path, device, api_key):
        super().__init__()
        self.url = url
        self.model_path = model_path
        self.device = device
        self.api_key = api_key
        self.signals = WorkerSignals()
        self.total_duration = 0
        self.processed_duration = 0

    def run(self):
        try:
            self.signals.log.emit("Starting process...")
            self.signals.progress_update.emit(0)

            self.signals.log.emit("Downloading or locating audio file...")
            audio_file, video_title = download_or_use_existing_audio(self.url, self.signals)
            self.signals.log.emit(f"Using audio file: {audio_file}")

            self.output_file = os.path.abspath(f"{video_title}.txt")
            self.markdown_file = os.path.abspath(f"{video_title}_analysis.md")

            # Create txt file
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(f"Transcript for: {video_title}\n\n")
            self.signals.log.emit(f"Created output file: {self.output_file}")

            self.signals.log.emit("Starting transcription process...")
            transcribe_audio(audio_file, self.model_path, self.device, self.signals, self.output_file)
            self.signals.log.emit("Transcription completed")

            self.signals.log.emit("Preparing to send transcript to Claude API for analysis...")
            try:
                transcript_text = read_transcript(self.output_file)
                self.signals.log.emit("Transcript read successfully. Sending to Claude API...")
                markdown_output = process_with_claude(self.api_key, transcript_text)
                self.signals.log.emit("Received response from Claude API. Writing to file...")
                
                with open(self.markdown_file, 'w', encoding='utf-8') as f:
                    f.write(markdown_output)
                self.signals.log.emit(f"Markdown content written to file: {self.markdown_file}")
            except Exception as e:
                self.signals.log.emit(f"Error in Claude API processing or writing markdown: {str(e)}")
                self.signals.error.emit(f"Error in Claude API processing: {str(e)}")
                raise

            self.signals.progress_update.emit(100)
            self.signals.output.emit(f"Process completed successfully.\nTranscript saved to: {self.output_file}\nMarkdown analysis saved to: {self.markdown_file}")
        except Exception as e:
            logging.exception("An error occurred during processing")
            self.signals.error.emit(f"Error: {str(e)}\n{traceback.format_exc()}")
        finally:
            self.signals.finished.emit()