import os
import sys
import logging
import traceback

# Check for required libraries
try:
    from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTextEdit, QProgressBar, QComboBox, QLabel, QFileDialog, QMessageBox
    from PyQt6.QtCore import QThread, pyqtSignal, Qt
    from pytubefix import YouTube
    from faster_whisper import WhisperModel
except ImportError as e:
    print(f"Error: Missing required library. {str(e)}")
    print("Please ensure all required libraries are installed.")
    sys.exit(1)

# Set up logging
logging.basicConfig(filename='app.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Default model path
DEFAULT_MODEL_PATH = r"C:\Users\rober\.cache\huggingface\hub\models--Systran--faster-whisper-large-v3\snapshots\edaa852ec7e145841d8ffdb056a99866b5f0a478"

class WorkerThread(QThread):
    progress_update = pyqtSignal(int)
    error = pyqtSignal(str)
    output = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self, url, model_path, device):
        super().__init__()
        self.url = url
        self.model_path = model_path
        self.device = device
        self.output_file = os.path.abspath("transcript.txt")
        self.total_duration = 0
        self.processed_duration = 0

    def run(self):
        try:
            self.log.emit("Starting process...")
            self.progress_update.emit(0)

            # Create the output file at the beginning
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write("Transcript:\n\n")
            self.log.emit(f"Created output file: {self.output_file}")

            audio_file = self.download_audio(self.url)
            self.log.emit(f"Audio downloaded: {audio_file}")

            self.log.emit("Starting transcription process...")
            self.transcribe_audio(audio_file)
            self.log.emit("Transcription completed")

            self.progress_update.emit(100)
            self.output.emit(f"Process completed. Output saved to: {self.output_file}")
        except Exception as e:
            logging.exception("An error occurred during processing")
            self.error.emit(f"Error: {str(e)}\n{traceback.format_exc()}")
        finally:
            self.log.emit("WorkerThread.run completed")

    def download_audio(self, url):
        try:
            self.log.emit(f"Attempting to download audio from URL: {url}")
            video = YouTube(url)
            self.total_duration = video.length  # Get video duration in seconds
            self.log.emit(f"Video duration: {self.total_duration} seconds")
            audio = video.streams.filter(only_audio=True).first()
            if audio is None:
                raise ValueError("No audio stream found for this video.")
            output = audio.download(output_path=".")
            base, _ = os.path.splitext(output)
            new_file = f"{base}.mp3"
            os.rename(output, new_file)
            self.log.emit(f"Audio download completed: {new_file}")
            return new_file
        except Exception as e:
            self.log.emit(f"Error in download_audio: {str(e)}")
            logging.exception("Error in download_audio")
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
        self.log_current_directory()
        url = self.url_input.text()
        if not url:
            self.output_display.setText("Please enter a valid YouTube URL.")
            return

        model_path = self.model_input.text()
        if not model_path:
            self.output_display.setText("Please select a local model directory.")
            return

        self.progress_bar.setValue(0)
        self.output_display.clear()

        device = self.device_combo.currentText()

        try:
            self.worker = WorkerThread(url, model_path, device)
            self.worker.progress_update.connect(self.update_progress)
            self.worker.error.connect(self.on_error)
            self.worker.output.connect(self.on_output)
            self.worker.log.connect(self.log_message)
            self.worker.finished.connect(self.on_process_finished)
            self.worker.start()
            
            # Disable the process button while working
            self.process_button.setEnabled(False)
            self.log_message("Worker thread started")
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

    def on_output(self, output_msg):
        self.output_display.append(output_msg)
        QMessageBox.information(self, "Process Completed", output_msg)

    def log_message(self, message):
        self.output_display.append(message)
        logging.info(message)

    def on_process_finished(self):
        self.process_button.setEnabled(True)
        logging.info("Process finished")

    def log_current_directory(self):
        current_dir = os.getcwd()
        self.log_message(f"Current working directory: {current_dir}")
        self.log_message(f"Directory contents: {os.listdir(current_dir)}")

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
