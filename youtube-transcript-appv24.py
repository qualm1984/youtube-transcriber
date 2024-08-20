import os
import sys
import logging
import traceback
import anthropic
import time

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTextEdit, QProgressBar, QComboBox, QLabel, QFileDialog, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer, QEventLoop
from pytubefix import YouTube
from faster_whisper import WhisperModel

# Set up logging
logging.basicConfig(filename='app.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add a stream handler to print logs to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
logging.getLogger('').addHandler(console_handler)

# Default model path
DEFAULT_MODEL_PATH = r"C:\Users\rober\.cache\huggingface\hub\models--Systran--faster-whisper-large-v3\snapshots\edaa852ec7e145841d8ffdb056a99866b5f0a478"

class WorkerThread(QThread):
    progress_update = pyqtSignal(int)
    error = pyqtSignal(str)
    output = pyqtSignal(str)
    log = pyqtSignal(str)
    finished = pyqtSignal()

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
            logging.info("Starting process...")
            self.progress_update.emit(0)

            logging.info("Downloading or locating audio file...")
            audio_file, video_title = self.download_or_use_existing_audio()
            logging.info(f"Using audio file: {audio_file}")

            self.output_file = os.path.abspath(f"{video_title}.txt")
            self.markdown_file = os.path.abspath(f"{video_title}_analysis.md")

            # Create both txt and md files
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(f"Transcript for: {video_title}\n\n")
            logging.info(f"Created output file: {self.output_file}")

            with open(self.markdown_file, 'w', encoding='utf-8') as f:
                f.write(f"# Analysis for: {video_title}\n\n")
            logging.info(f"Created markdown file: {self.markdown_file}")

            logging.info("Starting transcription process...")
            self.transcribe_audio(audio_file)
            logging.info("Transcription completed")

            logging.info("Preparing to send transcript to Claude API for analysis...")
            try:
                logging.info("Reading transcript file...")
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    transcript_text = f.read()
                logging.info("Transcript file read successfully")

                logging.info("Starting Claude API call timer...")
                start_time = time.time()
                logging.info(f"Using API key: {self.api_key[:5]}...{self.api_key[-5:]}")  # Log part of the API key
                markdown_output = self.process_with_claude()
                end_time = time.time()
                api_time = end_time - start_time
                logging.info(f"Claude API analysis completed in {api_time:.2f} seconds")

                # Append markdown content to file
                with open(self.markdown_file, 'a', encoding='utf-8') as f:
                    f.write(markdown_output)
                logging.info(f"Markdown content appended to file: {self.markdown_file}")
            except Exception as e:
                logging.error(f"Error in Claude API processing or writing markdown: {str(e)}")
                raise

            self.progress_update.emit(100)
            self.output.emit(f"Process completed successfully.\nTranscript saved to: {self.output_file}\nMarkdown analysis saved to: {self.markdown_file}")
        except Exception as e:
            logging.exception("An error occurred during processing")
            self.error.emit(f"Error: {str(e)}\n{traceback.format_exc()}")
        finally:
            logging.info("WorkerThread.run completed")
            self.finished.emit()

    def download_or_use_existing_audio(self):
        try:
            logging.info(f"Processing video from URL: {self.url}")
            video = YouTube(self.url)
            video_title = video.title
            safe_title = "".join([c for c in video_title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
            self.total_duration = video.length
            logging.info(f"Video title: {safe_title}")
            logging.info(f"Video duration: {self.total_duration} seconds")

            mp4_file = f"{safe_title}.mp4"
            mp3_file = f"{safe_title}.mp3"

            if os.path.exists(mp3_file):
                logging.info(f"Using existing MP3 file: {mp3_file}")
                return mp3_file, safe_title
            elif os.path.exists(mp4_file):
                logging.info(f"Using existing MP4 file: {mp4_file}")
                return mp4_file, safe_title
            else:
                logging.info("Downloading audio...")
                audio = video.streams.filter(only_audio=True).first()
                if audio is None:
                    raise ValueError("No audio stream found for this video.")
                output = audio.download(output_path=".", filename=safe_title)
                base, _ = os.path.splitext(output)
                new_file = f"{base}.mp3"
                os.rename(output, new_file)
                logging.info(f"Audio download completed: {new_file}")
                return new_file, safe_title
        except Exception as e:
            logging.exception("Error in download_or_use_existing_audio")
            raise

    def transcribe_audio(self, audio_file):
        try:
            logging.info(f"Starting transcription using model: {self.model_path}")
            model = WhisperModel(self.model_path, device=self.device, compute_type="float16")
            
            logging.info("Model loaded, beginning transcription")
            segments, info = model.transcribe(audio_file, beam_size=5, language="en")
            logging.info(f"Detected language '{info.language}' with probability {info.language_probability}")
            
            with open(self.output_file, 'a', encoding='utf-8') as f:
                for segment in segments:
                    transcript_line = f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}\n"
                    f.write(transcript_line)
                    self.processed_duration += segment.end - segment.start
                    progress = min(int((self.processed_duration / self.total_duration) * 100), 99)
                    self.progress_update.emit(progress)
                    logging.debug(f"Transcribed and wrote segment: {segment.start:.2f}s -> {segment.end:.2f}s")
            
            logging.info("Transcription process completed.")
        except Exception as e:
            logging.exception("Error in transcribe_audio")
            raise

    def process_with_claude(self):
        try:
            logging.info("Reading transcript file...")
            with open(self.output_file, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
            logging.info("Transcript file read successfully")
            
            logging.info("Sending transcript to Claude API for analysis...")
            client = anthropic.Anthropic(api_key=self.api_key)
            message = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                messages=[
                    {
                        "role": "user",
                        "content": f"""Please analyze the following transcript and create a detailed markdown document. 
                        Include the following sections:
                        1. Summary
                        2. Key Points
                        3. Detailed Breakdown (with timestamps if available)
                        4. Conclusion
                        5. Any relevant metadata (speaker names, video title, etc.)

                        Transcript:
                        {transcript_text}
                        """
                    }
                ]
            )
            markdown_output = message.content[0].text
            logging.info("Received analysis from Claude API")
            
            return markdown_output
        except Exception as e:
            logging.exception("Error in process_with_claude")
            raise

class YouTubeTranscriptApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.worker = None

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

        # Add a status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

        # Add a close button
        self.close_button = QPushButton("Close Application")
        self.close_button.clicked.connect(self.close)
        layout.addWidget(self.close_button)

        self.setLayout(layout)
        self.setWindowTitle('YouTube Transcript Extractor')
        self.setGeometry(300, 300, 500, 400)

    def browse_model(self):
        file_dialog = QFileDialog()
        model_path = file_dialog.getExistingDirectory(self, "Select Model Directory")
        if model_path:
            self.model_input.setText(model_path)

    def process_video(self):
        self.log_current_directory()
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

        try:
            self.worker = WorkerThread(url, model_path, device, api_key)
            self.worker.progress_update.connect(self.update_progress)
            self.worker.error.connect(self.on_error)
            self.worker.output.connect(self.on_output)
            self.worker.log.connect(self.log_message)
            self.worker.finished.connect(self.on_process_finished)
            
            # Disable the process button while working
            self.process_button.setEnabled(False)
            self.status_label.setText("Processing...")
            logging.info("Worker thread started")
            
            self.worker.start()
            
            # Use an event loop to keep the main thread responsive
            loop = QEventLoop()
            self.worker.finished.connect(loop.quit)
            loop.exec()
        except Exception as e:
            logging.exception("Error in process_video")
            self.on_error(f"Error starting worker thread: {str(e)}\n{traceback.format_exc()}")

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def on_error(self, error_msg):
        self.output_display.append(f"Error: {error_msg}")
        logging.error(f"Error in GUI: {error_msg}")
        QMessageBox.critical(self, "Error", error_msg)
        self.process_button.setEnabled(True)
        self.status_label.setText("Error occurred")

    def on_output(self, output_msg):
        self.output_display.append(output_msg)
        logging.info(f"Output: {output_msg}")
        QMessageBox.information(self, "Process Completed", "Markdown document successfully generated!\n\n" + output_msg)
        self.process_button.setEnabled(True)
        self.status_label.setText("Ready")

    def log_message(self, message):
        self.output_display.append(message)
        logging.info(message)
        QApplication.processEvents()  # Ensure UI updates in real-time

    def on_process_finished(self):
        self.process_button.setEnabled(True)
        self.status_label.setText("Ready")
        logging.info("Process finished")
        self.log_message("Process finished. You can now process another video or close the application.")

    def log_current_directory(self):
        current_dir = os.getcwd()
        logging.info(f"Current working directory: {current_dir}")
        logging.info(f"Directory contents: {os.listdir(current_dir)}")

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Window Close', 'Are you sure you want to close the window?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            event.accept()
            logging.info("Application closed by user")
        else:
            event.ignore()

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        ex = YouTubeTranscriptApp()
        ex.show()
        sys.exit(app.exec())
    except Exception as e:
        logging.exception("Unhandled exception in main")
        print(f"An unexpected error occurred: {str(e)}")
        print("Please check the 'app.log' file for more details.")