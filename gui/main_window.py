import logging
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTextEdit, QProgressBar, QComboBox, QLabel, QFileDialog
from PyQt6.QtCore import QThreadPool
from workers.transcription_workers import Worker
from config import DEFAULT_MODEL_PATH

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
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

        self.threadpool = QThreadPool()
        self.log("Application initialized")

    def browse_model(self):
        file_dialog = QFileDialog()
        model_path = file_dialog.getExistingDirectory(self, "Select Model Directory")
        if model_path:
            self.model_input.setText(model_path)

    def start_process(self):
        print("GUI: Start process button clicked")
        url = self.url_input.text()
        if not url:
            print("GUI: No URL provided")
            self.log("Please enter a valid YouTube URL.")
            return

        model_path = self.model_input.text()
        if not model_path:
            print("GUI: No model path provided")
            self.log("Please select a local model directory.")
            return

        api_key = self.api_key_input.text()
        if not api_key:
            print("GUI: No API key provided")
            self.log("Please enter a valid Claude API Key.")
            return

        self.progress_bar.setValue(0)
        self.log_text.clear()

        print("GUI: Creating and starting worker")
        worker = Worker(url, model_path, self.device_combo.currentText(), api_key)
        worker.signals.log.connect(self.log)
        worker.signals.progress_update.connect(self.update_progress)
        worker.signals.finished.connect(self.process_finished)
        worker.signals.output.connect(self.on_output)
        worker.signals.error.connect(self.on_error)
        self.threadpool.start(worker)

    def update_progress(self, value):
        print(f"GUI: Updating progress to {value}")
        self.progress_bar.setValue(value)

    def process_finished(self):
        print("GUI: Process finished")
        self.log("Process finished.")

    def on_output(self, output_msg):
        print(f"GUI: Received output: {output_msg}")
        self.log(output_msg)

    def on_error(self, error_msg):
        print(f"GUI: Received error: {error_msg}")
        self.log(f"Error: {error_msg}")

    def log(self, message):
        print(f"GUI: Logging message: {message}")
        self.log_text.append(message)
        # Ensure the log is scrolled to the bottom
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
        logging.info(message)