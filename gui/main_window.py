import sys
import json
import os
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTextEdit, QProgressBar, QComboBox, QLabel, QFileDialog, QMessageBox, QApplication
from PyQt6.QtCore import QProcess, QTimer
from utils.youtube_utils import download_or_use_existing_audio
from config import DEFAULT_MODEL_PATH

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.process = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle('YouTube Transcript Extractor')
        self.setGeometry(300, 300, 500, 400)

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
        self.process_button.clicked.connect(self.start_process)
        layout.addWidget(self.process_button)

        # Progress bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # Output display
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def browse_model(self):
        file_dialog = QFileDialog()
        model_path = file_dialog.getExistingDirectory(self, "Select Model Directory")
        if model_path:
            self.model_input.setText(model_path)

    def start_process(self):
        url = self.url_input.text()
        if not url:
            self.log("Please enter a valid YouTube URL.")
            return

        model_path = self.model_input.text()
        if not model_path:
            self.log("Please select a local model directory.")
            return

        api_key = self.api_key_input.text()
        if not api_key:
            self.log("Please enter a valid Claude API Key.")
            return

        self.progress_bar.setValue(0)
        self.log_text.clear()

        self.log("Downloading audio...")
        try:
            self.log("Files before download:")
            for file in os.listdir():
                self.log(file)

            audio_file, safe_title = download_or_use_existing_audio(url)
            self.log(f"Audio downloaded: {audio_file}")
            
            self.log("Files after download:")
            for file in os.listdir():
                self.log(file)
            
            # Verify that the file exists
            if not os.path.exists(audio_file):
                raise FileNotFoundError(f"Audio file not found: {audio_file}")
            else:
                self.log(f"Verified: Audio file exists at {os.path.abspath(audio_file)}")
            
        except Exception as e:
            self.log(f"Error in download_or_use_existing_audio: {str(e)}")
            # Print the full traceback for debugging
            import traceback
            self.log(traceback.format_exc())
            return

        output_file = os.path.abspath(f"{safe_title}.txt")
        self.log(f"Output file will be: {output_file}")

        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.handle_output)
        self.process.finished.connect(self.process_finished)

        python_executable = sys.executable
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'transcription_process.py')
        
        self.process.start(python_executable, [script_path, audio_file, model_path, self.device_combo.currentText(), output_file, api_key])

    def handle_output(self):
        raw_output = self.process.readAllStandardOutput().data().decode()
        try:
            output = json.loads(raw_output)
            if output['status'] == 'error':
                self.log(f"Error: {output['message']}")
            else:
                self.log(output['status'])
                if 'progress' in output:
                    self.progress_bar.setValue(output['progress'])
        except json.JSONDecodeError:
            self.log(raw_output)

    def process_finished(self):
        self.log("Process finished.")
        QMessageBox.information(self, "Process Completed", "The transcription and analysis process has finished.")

    def log(self, message):
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def closeEvent(self, event):
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            reply = QMessageBox.question(self, 'Process Running', 'A process is still running. Are you sure you want to close the window?',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.process.kill()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())