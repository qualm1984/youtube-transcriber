import sys
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox
from gui.main_window import MainWindow

def global_exception_handler(exctype, value, tb):
    error_msg = f"An uncaught exception occurred:\n{exctype}: {value}\n\nTraceback:\n"
    error_msg += ''.join(traceback.format_tb(tb))
    print(error_msg)
    QMessageBox.critical(None, "Uncaught Exception", error_msg)

if __name__ == '__main__':
    sys.excepthook = global_exception_handler
    
    app = QApplication(sys.argv)
    
    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        error_msg = f"An exception occurred in the main loop:\n{type(e).__name__}: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(error_msg)
        QMessageBox.critical(None, "Main Loop Exception", error_msg)
        sys.exit(1)