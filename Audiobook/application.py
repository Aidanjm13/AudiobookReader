from PySide6.QtWidgets import QMainWindow, QApplication, QPushButton, QGridLayout, QSizePolicy, QFileDialog
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize, Qt, QTimer, QIODevice
from PySide6.QtMultimedia import QAudioSink, QAudioFormat, QMediaDevices, QAudio
from AudioBuffer import SAMPLE_RATE, StreamingAudioBuffer
from ui_Audiobook import Ui_MainWindow
from ui_BookWindow import Ui_BookWindow
from fileHandling import saveNewBook
from SQLHandler import init_db, add_book, get_books_by_accessed, get_book, update_book
from pathlib import Path
from epubReader import getBook, getLanguages, getCreators, getTitles, save_cover_image, renderItemsIntoTextEdit
import os
from bookPages import buildPages, getCurrentPageItems, goNextPage, goPrevPage, getCurrentPage, closeBook
from ttsWorker import get_page_audio
from textToSpeech import set_audio_format

SUPPORTED_FILE_TYPES = {"epub"} #currently supported file types

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
        self.fileType = self.databaseBook.file_type
        self.section = self.databaseBook.chapter
        self.sentence = self.databaseBook.sentence

        # audio setup and connections
        device = QMediaDevices.defaultAudioOutput()
        preferred = device.preferredFormat()
        
        fmt = QAudioFormat()
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        fmt.setSampleRate(preferred.sampleRate() if preferred.sampleRate() > 0 else 48000)
        fmt.setChannelCount(1)

        if not device.isFormatSupported(fmt):
            fmt.setChannelCount(preferred.channelCount() if preferred.channelCount() > 0 else 2)

        if not device.isFormatSupported(fmt):
            fmt = preferred

        active_sample_rate = fmt.sampleRate()
        active_channels = fmt.channelCount()

        set_audio_format(active_sample_rate, active_channels)

        self.audio_buffer = StreamingAudioBuffer(sample_rate=active_sample_rate, channels=active_channels)
        self.audio_buffer.open(QIODevice.ReadOnly)
        self.audio_buffer.page_finished.connect(self.on_audio_page_finished)
        self.audio_buffer.clip_started.connect(self.on_clip_started)
        self.audio_buffer.clip_finished.connect(self.on_clip_finished)

        self.sink = QAudioSink(device, fmt)
        self.sink.setVolume(1.0)
        self.audioState = -1
        self.sink.stateChanged.connect(self._on_audio_state_changed)

        self._pending_page = 0
        self._feed_timer = QTimer(self)
        self._feed_timer.setInterval(200)  # check every 200ms
        self._feed_timer.timeout.connect(self._try_feed_pending_page)

        # defer pagination until the widget has real, laid-out dimensions
        QTimer.singleShot(0, self._loadInitialPage)

        self.ui.nextPageButton.clicked.connect(lambda: self.goNext(True))
        self.ui.prevPageButton.clicked.connect(lambda: self.goPrevious(True))
        self.ui.AudioStart.clicked.connect(self.toggle_audio)

        #connecting single shot for Font Change
        self.font_size_timer = QTimer()
        self.font_size_timer.setSingleShot(True)
        self.font_size_timer.timeout.connect(self.change_font_size)
        self.ui.FontEntry.valueChanged.connect(self.schedule_font_size_change)

    #FIX ME: do we want to reload page index if this happens, wait a few seconds then do it
    #should have some system that if the text area is too small or minimized it is treated as a certain size so that tts can still work well
    def resizeEvent(self, event):
        super().resizeEvent(event)

    #close this book for bookPages and ttsWorker
    def closeEvent(self, event):
        super().closeEvent(event)
        closeBook(self.id)

    #is called when the book first opens, builds the index and renders the currentpage
    def _loadInitialPage(self):
        buildPages(self.id,self.ui.TextArea)
        self.renderCurrentPage()

    #renders the 
    def renderCurrentPage(self):
        match self.fileType:
            case "epub":
                items = getCurrentPageItems(self.id)
                renderItemsIntoTextEdit(self.book,self.ui.TextArea,items)

    #goes to the next page in the audiobook
    #audioStop causes the audio to stop when called, used if user changes page themself
    def goNext(self, audioStop):
        if(audioStop): self.stop_audio()
        goNextPage(self.id, self.ui.TextArea)
        self.renderCurrentPage()

    #goes to the prev page in the audiobook
    #audioStop causes the audio to stop when called, used if user changes page themself
    def goPrevious(self, audioStop):
        if(audioStop): self.stop_audio()
        goPrevPage(self.id, self.ui.TextArea)
        self.renderCurrentPage()


    def schedule_font_size_change(self):
        self.font_size_timer.start(500)  # restart the 500ms countdown

    def change_font_size(self):
        self.stop_audio()
        #change font size
        fontSize = self.ui.FontEntry.value()
        font = self.ui.TextArea.font()
        font.setPointSizeF(fontSize)
        self.ui.TextArea.setFont(font)

        #rebuild page index with anchor
        buildPages(self.id,self.ui.TextArea,True)
        self.renderCurrentPage()

    # --- audio feeding ---
    def _queue_page_audio(self, page):
        self._pending_page = page
        self._feed_timer.start()

    def _try_feed_pending_page(self):
        audio_list = get_page_audio(self.id, self._pending_page)
        if audio_list is None:
            return  # not synthesized yet, keep polling

        if not audio_list:
            print(f"[TTS] Warning: Page {self._pending_page} has no audio chunks.")
            self._feed_timer.stop()
            return

        self._feed_timer.stop()
        print(f"[TTS] Feeding {len(audio_list)} audio clips for page {self._pending_page}.")
        total_fed = 0
        for i, audio_bytes in enumerate(audio_list):
            if not audio_bytes:
                continue
            total_fed += len(audio_bytes)
            is_last = (i == len(audio_list) - 1)
            clip_id = f"{self.id}-{self._pending_page}-{i}"
            self.audio_buffer.feed(clip_id, audio_bytes, sentence_id=i,
                                    page=self._pending_page, is_last_of_page=is_last)
        print(f"[TTS] Total raw bytes loaded into buffer: {total_fed}")

        if self.audioState == 1:
            if self.sink.state() in (QAudio.StoppedState, QAudio.IdleState):
                self.sink.stop()
                self.sink.start(self.audio_buffer)

    #toggles audio starts it if not started, toggles it between resume and suspend otherwise
    def toggle_audio(self):
        if self.audioState == -1:
            self.audioState = 1
            cur_page = getCurrentPage(self.id)
            self._queue_page_audio(cur_page)
            if len(self.audio_buffer._buffer) > 0:
                self.sink.start(self.audio_buffer)
        elif self.audioState == 1:
            self.sink.suspend()
            self.audioState = 0
        elif self.audioState == 0:
            self.sink.resume()
            self.audioState = 1

    #fully stops and clears current audio buffer
    def stop_audio(self):
        self.sink.stop()
        self.audio_buffer.clear()
        self.audioState = -1

    # --- reacting to playback ---
    def on_audio_page_finished(self, page):
        self.goNext(False)   # auto-advance without stopping/resetting audio
        self._queue_page_audio(page + 1)

    def on_clip_started(self, clip_id, sentence_id):
        pass  # hook for highlighting — see note below

    def on_clip_finished(self, clip_id, sentence_id):
        pass

    def _on_audio_state_changed(self, state):
        state_names = {
            QAudio.ActiveState: "Active (Playing sound)",
            QAudio.SuspendedState: "Suspended (Paused)",
            QAudio.StoppedState: "Stopped",
            QAudio.IdleState: "Idle (Waiting for audio data / buffer empty)"
        }
        print(f"[QAudioSink] State: {state_names.get(state, state)} | Error: {self.sink.error()}")
    



if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()