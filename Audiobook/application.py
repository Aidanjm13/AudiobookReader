import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QPushButton, QLabel, QTextEdit, QFileDialog
)

class FileLoader(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Loader")
        self.setMinimumSize(500, 400)

        # Widgets
        self.btn = QPushButton("Upload File")
        self.label = QLabel("No file selected")
        self.label.setWordWrap(True)
        self.text_area = QTextEdit()
        self.text_area.setPlaceholderText("File contents will appear here...")
        self.text_area.setReadOnly(True)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.btn)
        layout.addWidget(self.label)
        layout.addWidget(self.text_area)
        self.setLayout(layout)

        # Signal
        self.btn.clicked.connect(self.open_file)

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select a File", "",
            "eBooks & PDFs (*.epub *.pdf);;All Files (*)"
        )
        if path:
            self.process_file(path)

    def process_file(self, path):
        ext = os.path.splitext(path)[1].lower()

        if ext == ".pdf":
            
        elif ext == ".epub":
            

app = QApplication(sys.argv)
window = FileLoader()
window.show()
sys.exit(app.exec())