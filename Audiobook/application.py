from PySide6.QtWidgets import QMainWindow, QApplication, QPushButton, QGridLayout, QSizePolicy, QFileDialog
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize, Qt, QTimer
from ui_Audiobook import Ui_MainWindow
from ui_BookWindow import Ui_BookWindow
from fileHandling import saveNewBook
from SQLHandler import init_db, add_book, get_books_by_accessed, get_book, update_book
from pathlib import Path
from epubReader import getBook, getImageData, getLanguages, getCreators, getTitles, save_cover_image, buildPageIndex, ReadingPosition, findPageForPosition, renderPageFrom
import os
from ttsWorker import TTSWindowCache

SUPPORTED_FILE_TYPES = {"epub"} #currently supported file types
TTSWorker = TTSWindowCache()

class MainWindow(QMainWindow):
    def __init__(self):
        init_db()

        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.uploadFilesButton.clicked.connect(self.on_upload_clicked)

        self.books_rows = 2
        self.default_cover_size = QSize(120, 180)   # ideal/preferred size
        self.min_cover_size = QSize(60, 90)          # floor when shrinking
        self.cover_spacing = 10
        self.cover_paths = {}
        self._sized_once = False

        self.cover_size = self.default_cover_size
        self.setup_books_area()
        self.load_books()

        self.openBookWindows = []

    def on_upload_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select an audiobook file",
            "",  # starting directory ("" = default/last used)
            "Books (*.epub *.pdf *.txt);;All Files (*)"
        )
        if file_path:  # empty string if user cancelled
            ext = Path(file_path).suffix.lower().lstrip(".")
            if ext not in SUPPORTED_FILE_TYPES:
                raise ValueError(f"Unsupported file type: {ext}")
            newBookPath = saveNewBook(file_path)
            book = getBook(newBookPath)
            ##FIX ME: add protection in case of no titles, creators, etc..
            add_book(ext, newBookPath, save_cover_image(book,os.path.dirname(newBookPath)), getTitles(book)[0], getCreators(book)[0], getLanguages(book)[0], 0, 0)
            self.current_file = file_path
            self.load_books()

    #sets the scroll area up with proper margins and grid layout
    def setup_books_area(self):
        self.ui.booksScrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.ui.booksScrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.ui.booksScrollArea.setWidgetResizable(True)

        self.ui.scrollAreaWidgetContents.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        layout = self.ui.scrollAreaWidgetContents.layout()
        if layout is None:
            layout = QGridLayout(self.ui.scrollAreaWidgetContents)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(self.cover_spacing)
            layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.books_layout = layout

    def calculate_cover_size(self):
        """Use default size unless the scroll area is too short to fit books_rows at that size."""
        viewport = self.ui.booksScrollArea.viewport()
        margins = self.books_layout.contentsMargins()

        available_height = viewport.height() - margins.top() - margins.bottom()
        available_height -= self.cover_spacing * (self.books_rows - 1)

        needed_height = self.default_cover_size.height() * self.books_rows

        # uncomment if you want there to be a maximum size
        # if available_height >= needed_height:
        #     return self.default_cover_size

        # not enough room — shrink proportionally to fit
        scale = available_height / needed_height
        width = max(int(self.default_cover_size.width() * scale), self.min_cover_size.width())
        height = max(int(self.default_cover_size.height() * scale), self.min_cover_size.height())
        return QSize(width, height)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._sized_once:
            self._sized_once = True
            self.cover_size = self.calculate_cover_size()
            self.refresh_cover_sizes()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        new_size = self.calculate_cover_size()
        if new_size != self.cover_size:
            self.cover_size = new_size
            self.refresh_cover_sizes()

    def refresh_cover_sizes(self):
        for btn in self.cover_paths:
            btn.setFixedSize(self.cover_size)
            btn.setIconSize(self.cover_size)

    def load_books(self):
        books = get_books_by_accessed() #[{"id": book.id, "title": book.title, "path": book.file_path, "cover": book.image_path}]
        self.populate_books(books)

    def populate_books(self, books):
        self.clear_books()
        self.current_books = books
        for i, book in enumerate(books):
            col, row = divmod(i, self.books_rows)
            btn = self.create_book_button(book["id"], book["title"], book["path"], book["cover"])
            self.books_layout.addWidget(btn, row, col)

    def clear_books(self):
        while self.books_layout.count():
            item = self.books_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.cover_paths.clear()

    def create_book_button(self, id, title, path, cover_path):
        btn = QPushButton()
        btn.setFixedSize(self.cover_size)
        btn.setIconSize(self.cover_size)
        btn.setToolTip(title)
        btn.setFlat(True)

        icon = QIcon(cover_path)
        if icon.isNull():
            print(f"Warning: could not load cover image: {cover_path}")
            btn.setText(title)
        else:
            btn.setIcon(icon)

        btn.clicked.connect(lambda checked=False, i=id: self.open_book(id))
        self.cover_paths[btn] = cover_path
        return btn

    def open_book(self, id):
        print(f"Opening {id}")
        new_window = BookWindow(book_id = id)
        new_window.show()
        self.openBookWindows.append(new_window)


class BookWindow(QMainWindow):
    def __init__(self, book_id, parent=None):
        super().__init__(parent)
        self.ui = Ui_BookWindow()
        self.ui.setupUi(self)
        self.id = book_id
        self.databaseBook = get_book(book_id)
        self.book = getBook(self.databaseBook.file_path)
        self.section = self.databaseBook.chapter
        self.sentence = self.databaseBook.sentence

        # defer pagination until the widget has real, laid-out dimensions
        QTimer.singleShot(0, self._loadInitialPage)

        self.ui.nextPageButton.clicked.connect(self.goNext)
        self.ui.prevPageButton.clicked.connect(self.goPrevious)

        #connecting single shot for Font Change
        self.font_size_timer = QTimer()
        self.font_size_timer.setSingleShot(True)
        self.font_size_timer.timeout.connect(self.change_font_size)
        self.ui.FontEntry.valueChanged.connect(self.schedule_font_size_change)

    def _loadInitialPage(self):
        self.pageIndex = buildPageIndex(self.book, self.ui.TextArea, self.section, getImageData)
        savedPosition = ReadingPosition(chapter=self.section, itemIndex=self.sentence, charOffset=0)
        self.currentPage = findPageForPosition(self.pageIndex, savedPosition)
        self.currentPosition = self.pageIndex[self.currentPage]
        renderPageFrom(self.book, self.ui.TextArea, self.currentPosition, getImageData)

    def goNext(self):
        if self.currentPage + 1 < len(self.pageIndex):
            self.currentPage += 1
            self.currentPosition = self.pageIndex[self.currentPage]
            renderPageFrom(self.book, self.ui.TextArea, self.currentPosition, getImageData)
        else:
            self._goToNextChapter()
        self._saveProgress()

    def goPrevious(self):
        if self.currentPage > 0:
            self.currentPage -= 1
            self.currentPosition = self.pageIndex[self.currentPage]
            renderPageFrom(self.book, self.ui.TextArea, self.currentPosition, getImageData)
        else:
            self._goToPreviousChapter()
        self._saveProgress()

    def _goToNextChapter(self):
        self.section += 1
        self.pageIndex = buildPageIndex(self.book, self.ui.TextArea, self.section, getImageData)
        if not self.pageIndex:
            self.section -= 1
            return
        self.currentPage = 0
        renderPageFrom(self.book, self.ui.TextArea, self.pageIndex[self.currentPage], getImageData)

    def _goToPreviousChapter(self):
        if self.section == 0:
            return
        self.section -= 1
        self.pageIndex = buildPageIndex(self.book, self.ui.TextArea, self.section, getImageData)
        self.currentPage = len(self.pageIndex) - 1
        renderPageFrom(self.book, self.ui.TextArea, self.pageIndex[self.currentPage], getImageData)

    def _saveProgress(self):
        position = self.pageIndex[self.currentPage]
        update_book(self.id, chapter=position.chapter, sentence = position.itemIndex)

    def schedule_font_size_change(self):
        self.font_size_timer.start(500)  # restart the 500ms countdown

    def change_font_size(self):
        savedPosition = self.currentPosition   # sentence currently at the top of the page

        fontSize = self.ui.FontEntry.value()
        font = self.ui.TextArea.font()
        font.setPointSizeF(fontSize)
        self.ui.TextArea.setFont(font)

        # Anchor repagination at savedPosition so that sentence stays pinned to the
        # top of a page in the new layout, instead of just searching for whichever
        # page happens to contain it.
        self.pageIndex = buildPageIndex(self.book, self.ui.TextArea, self.section, getImageData,
                                         anchor=savedPosition)

        # buildPageIndex guarantees a page starting exactly at savedPosition when an
        # anchor is passed, so this is an exact match, not a nearest-fit search.
        self.currentPage = next(
            i for i, pos in enumerate(self.pageIndex)
            if pos.itemIndex == savedPosition.itemIndex and pos.charOffset == savedPosition.charOffset
        )
        self.currentPosition = self.pageIndex[self.currentPage]
        renderPageFrom(self.book, self.ui.TextArea, self.currentPosition, getImageData)


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()