import os
import sys
import logging
import traceback
import anthropic
import time

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTextEdit, QProgressBar, QComboBox, QLabel, QFileDialog, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from pytubefix import YouTube
from faster_whisper import WhisperModel

# Set up logging
logging.basicConfig(filename='app.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Default model path
DEFAULT_MODEL_PATH = r"C:\Users\rober\.cache\huggingface\hub\models--Systran--faster-whisper-large-v3\snapshots\edaa852ec7e145841d8ffdb056a99866b5f0a478"

def read_transcript(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Error reading transcript file: {str(e)}")
        raise

def process_with_claude(api_key, transcript_text, max_retries=3, retry_delay=5):
    client = anthropic.Anthropic(api_key=api_key)
    
    full_prompt = f"""Please analyze the following transcript and create a detailed markdown document. 
    Include the following sections:
    1. Summary
    2. Key Points
    3. Detailed Breakdown (with timestamps if available)
    4. Conclusion
    5. Any relevant metadata (speaker names, video title, etc.)

    Transcript:
    {transcript_text}
    """

    for attempt in range(max_retries):
        try:
            logging.info(f"Sending transcript to Claude API for analysis (Attempt {attempt + 1}/{max_retries})...")
            start_time = time.time()
            
            message = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                messages=[
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ]
            )
            
            end_time = time.time()
            api_time = end_time - start_time
            logging.info(f"Claude API analysis completed in {api_time:.2f} seconds")
            
            return message.content[0].text
        except anthropic.APIError as e:
            if e.status_code == 529:
                if attempt < max_retries - 1:
                    logging.warning(f"Overloaded error: Anthropic's API is temporarily overloaded. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                else:
                    logging.error("Overloaded error: Max retries reached. Anthropic's API is temporarily overloaded.")
                    raise
            else:
                logging.error(f"API error: {str(e)}")
                raise
        except Exception as e:
            logging.error(f"Unexpected error in Claude API processing: {str(e)}")
            raise

    logging.error("Max retries reached. Failed to process with Claude API.")
    raise Exception("Failed to process with Claude API after multiple attempts.")

class WorkerThread(QThread):
    progress_update = pyqtSignal(int)
    error = pyqtSignal(str)
    output = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self, url, model_path, device, api_key):
        super().__init__()
        self.url = url
        self.model_path = model_path
        self.device = device
        self.api_key = api_key
        self.total_duration = 0
        self.processed_duration = 0

    def run(self):
        try:
            self.log.emit("Starting process...")
            self.progress_update.emit(0)

            self.log.emit("Downloading or locating audio file...")
            audio_file, video_title = self.download_or_use_existing_audio()
            self.log.emit(f"Using audio file: {audio_file}")

            self.output_file = os.path.abspath(f"{video_title}.txt")
            self.markdown_file = os.path.abspath(f"{video_title}_analysis.md")

            # Create both txt and md files
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(f"Transcript for: {video_title}\n\n")
            self.log.emit(f"Created output file: {self.output_file}")

            with open(self.markdown_file, 'w', encoding='utf-8') as f:
                f.write(f"# Analysis for: {video_title}\n\n")
            self.log.emit(f"Created markdown file: {self.markdown_file}")

            self.log.emit("Starting transcription process...")
            self.transcribe_audio(audio_file)
            self.log.emit("Transcription completed")

            self.log.emit("Preparing to send transcript to Claude API for analysis...")
            try:
                transcript_text = read_transcript(self.output_file)
                markdown_output = process_with_claude(self.api_key, transcript_text)
                
                with open(self.markdown_file, 'w', encoding='utf-8') as f:
                    f.write(markdown_output)
                self.log.emit(f"Markdown content written to file: {self.markdown_file}")
            except Exception as e:
                self.log.emit(f"Error in Claude API processing or writing markdown: {str(e)}")
                raise

            self.progress_update.emit(100)
            self.output.emit(f"Process completed successfully.\nTranscript saved to: {self.output_file}\nMarkdown analysis saved to: {self.markdown_file}")
        except Exception as e:
            logging.exception("An error occurred during processing")
            self.error.emit(f"Error: {str(e)}\n{traceback.format_exc()}")

    def download_or_use_existing_audio(self):
        try:
            self.log.emit(f"Processing video from URL: {self.url}")
            video = YouTube(self.url)
            video_title = video.title
            safe_title = "".join([c for c in video_title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
            self.total_duration = video.length
            self.log.emit(f"Video title: {safe_title}")
            self.log.emit(f"Video duration: {self.total_duration} seconds")

            mp4_file = f"{safe_title}.mp4"
            mp3_file = f"{safe_title}.mp3"

            if os.path.exists(mp3_file):
                self.log.emit(f"Using existing MP3 file: {mp3_file}")
                return mp3_file, safe_title
            elif os.path.exists(mp4_file):
                self.log.emit(f"Using existing MP4 file: {mp4_file}")
                return mp4_file, safe_title
            else:
                self.log.emit("Downloading audio...")
                audio = video.streams.filter(only_audio=True).first()
                if audio is None:
                    raise ValueError("No audio stream found for this video.")
                output = audio.download(output_path=".", filename=safe_title)
                base, _ = os.path.splitext(output)
                new_file = f"{base}.mp3"
                os.rename(output, new_file)
                self.log.emit(f"Audio download completed: {new_file}")
                return new_file, safe_title
        except Exception as e:
            self.log.emit(f"Error in download_or_use_existing_audio: {str(e)}")
            logging.exception("Error in download_or_use_existing_audio")
            raise

    def transcribe_audio(self, audio_file):
        try:
            self.log.emit(f"Starting transcription using model: {self.model_path}")
            model = WhisperModel(self.model_path, device=self.device, compute_type="float16")
            
            self.log.emit("Model loaded, beginning transcription")
            segments, info = model.transcribe(audio_file, beam_size=5, language="en")
            self.log.emit(f"Detected language '{info.language}' with probability {info.language_probability}")
            
            with open(self.output_file, 'a', encoding='utf-8') as f:
                for segment in segments:
                    transcript_line = f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}\n"
                    f.write(transcript_line)
                    self.processed_duration += segment.end - segment.start
                    progress = min(int((self.processed_duration / self.total_duration) * 100), 99)
                    self.progress_update.emit(progress)
                    self.log.emit(f"Transcribed and wrote segment: {segment.start:.2f}s -> {segment.end:.2f}s")
            
            self.log.emit("Transcription process completed.")
        except Exception as e:
            self.log.emit(f"Error in transcribe_audio: {str(e)}")
            logging.exception("Error in transcribe_audio")
            raise

class YouTubeTranscriptApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # URL input
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter YouTube URL")
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)

        # Local model selection
        model_layout = QHBoxLayout()
        self.model_input = QLineEdit(DEFAULT_MODEL_PATH)
        self.model_button = QPushButton("Browse")
        self.model_button.clicked.connect(self.browse_model)
        model_layout.addWidget(self.model_input)
        model_layout.addWidget(self.model_button)
        layout.addLayout(model_layout)

        # Device selection
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("Device:"))
        self.device_combo = QComboBox()
        self.device_combo.addItems(["cuda", "cpu"])
        device_layout.addWidget(self.device_combo)
        layout.addLayout(device_layout)

        # API Key input
        api_key_layout = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter Claude API Key")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_key_layout.addWidget(self.api_key_input)
        layout.addLayout(api_key_layout)

        # Process button
        self.process_button = QPushButton("Process")
        self.process_button.clicked.connect(self.process_video)
        layout.addWidget(self.process_button)

        # Progress bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # Output display
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        layout.addWidget(self.output_display)

        self.setLayout(layout)
        self.setWindowTitle('YouTube Transcript Extractor')
        self.setGeometry(300, 300, 500, 400)

    def browse_model(self):
        file_dialog = QFileDialog()
        model_path = file_dialog.getExistingDirectory(self, "Select Model Directory")
        if model_path:
            self.model_input.setText(model_path)

    def process_video(self):
        url = self.url_input.text()
        if not url:
            self.output_display.setText("Please enter a valid YouTube URL.")
            return

        model_path = self.model_input.text()
        if not model_path:
            self.output_display.setText("Please select a local model directory.")
            return

        api_key = self.api_key_input.text()
        if not api_key:
            self.output_display.setText("Please enter a valid Claude API Key.")
            return

        self.progress_bar.setValue(0)
        self.output_display.clear()

        device = self.device_combo.currentText()

        self.worker = WorkerThread(url, model_path, device, api_key)
        self.worker.progress_update.connect(self.update_progress)
        self.worker.error.connect(self.on_error)
        self.worker.output.connect(self.on_output)
        self.worker.log.connect(self.log_message)
        self.worker.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def on_error(self, error_msg):
        self.output_display.append(f"Error: {error_msg}")
        logging.error(f"Error in GUI: {error_msg}")

    def on_output(self, output_msg):
        self.output_display.append(output_msg)

    def log_message(self, message):
        self.output_display.append(message)
        logging.info(message)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = YouTubeTranscriptApp()
    ex.show()
    sys.exit(app.exec())