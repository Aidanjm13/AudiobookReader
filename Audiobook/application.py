import sys
from PyQt6.QtWidgets import QApplication, QMainWindow

app = QApplication(sys.argv)
window = QMainWindow()
window.setWindowTitle("Audiobook Application")
window.show()
sys.exit(app.exec())