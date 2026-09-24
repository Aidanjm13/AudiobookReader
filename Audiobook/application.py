from PySide6.QtWidgets import QMainWindow, QApplication, QPushButton, QGridLayout, QSizePolicy, QFileDialog
from PySide6.QtGui import QIcon
from PySide6 import QtWidgets
from PySide6.QtCore import QSize, Qt, QTimer, QIODevice
from PySide6.QtMultimedia import QAudioSink, QAudioFormat, QMediaDevices, QAudio
from AudioBuffer import SAMPLE_RATE, StreamingAudioBuffer
from ui_Audiobook import Ui_MainWindow
from ui_BookWindow import Ui_BookWindow
from fileHandling import saveNewBook
from SQLHandler import init_db, add_book, get_books_by_accessed, get_book, update_book, add_settings, num_settings, get_active_setting, update_settings
from pathlib import Path
from epubReader import getBook, getLanguages, getCreators, getTitles, save_cover_image, renderItemsIntoTextEdit, getSectionTitles
import os
from bookPages import buildPages, getCurrentPageItems, goNextPage, goPrevPage, loadChapterStart, getCurrentPage, closeBook
from ttsWorker import get_tts_worker, tts_set_page
from textToSpeech import set_audio_format, get_available_voices, scan_downloaded_voices, get_downloaded_voices, reload_available_voices, parse_voice_string, get_voice_paths, download_voice, update_model

SUPPORTED_FILE_TYPES = {"epub"}

class MainWindow(QMainWindow):
    def __init__(self):
        init_db()
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.uploadFilesButton.clicked.connect(self.on_upload_clicked)

        self.books_rows = 2
        self.default_cover_size = QSize(120, 180)
        self.min_cover_size = QSize(60, 90)
        self.cover_spacing = 10
        self.cover_paths = {}
        self._sized_once = False

        self.cover_size = self.default_cover_size
        self.setup_books_area()
        self.load_books()
        self.openBookWindows = []
        if(num_settings() == 0):
            add_settings("Default", 1.0, 1.0, "piper", "en_US-lessac-medium", 16, "default", True)

        self.ui.RefreshVoiceButton.clicked.connect(self.handle_refresh_voices)
        self.ui.DownloadDeleteVoiceButton.clicked.connect(self.handle_action_button)
        self.ui.voicesComboBox.currentIndexChanged.connect(self.update_ui_state)

        # 2. Populate on launch
        self.populate_voices_dropdown()

    def on_upload_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select an audiobook file",
            "",
            "Books (*.epub *.pdf *.txt);;All Files (*)"
        )
        if file_path:
            ext = Path(file_path).suffix.lower().lstrip(".")
            if ext not in SUPPORTED_FILE_TYPES:
                raise ValueError(f"Unsupported file type: {ext}")
            newBookPath = saveNewBook(file_path)
            book = getBook(newBookPath)
            add_book(ext, newBookPath, save_cover_image(book, os.path.dirname(newBookPath)), 
                     getTitles(book)[0], getCreators(book)[0], getLanguages(book)[0], 0, 0)
            self.current_file = file_path
            self.load_books()

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
        viewport = self.ui.booksScrollArea.viewport()
        margins = self.books_layout.contentsMargins()
        available_height = viewport.height() - margins.top() - margins.bottom()
        available_height -= self.cover_spacing * (self.books_rows - 1)
        needed_height = self.default_cover_size.height() * self.books_rows

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
        books = get_books_by_accessed()
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
            btn.setText(title)
        else:
            btn.setIcon(icon)

        btn.clicked.connect(lambda checked=False, i=id: self.open_book(id))
        self.cover_paths[btn] = cover_path
        return btn

    def open_book(self, id):
        print(f"Opening {id}")
        new_window = BookWindow(book_id=id)
        new_window.show()
        self.openBookWindows.append(new_window)

    def populate_voices_dropdown(self):
        """Loads voices, sorts downloaded ones to the top with file sizes."""
        voices = get_available_voices()

        downloaded_voices = []
        available_voices = []

        # 1. Read the disk exactly ONCE
        local_inventory = scan_downloaded_voices()

        self.ui.voicesComboBox.blockSignals(True)
        self.ui.voicesComboBox.clear()

        # 1. Add Downloaded Voices First
        # Store as: userData=(raw_string, True)
        has_downloaded = False
        for voice_str in voices:
            if voice_str in local_inventory:
                size_mb = local_inventory[voice_str]
                display_text = f"{voice_str} ({size_mb:.1f} MB)"
                self.ui.voicesComboBox.addItem(display_text, userData=(voice_str, True))
                has_downloaded = True

        # Add Separator if needed
        if has_downloaded and len(local_inventory) < len(voices):
            self.ui.voicesComboBox.addItem("--- Available to Download ---", userData=None)

        # 2. Add Available Voices
        # Store as: userData=(raw_string, False)
        for voice_str in voices:
            if voice_str not in local_inventory:
                self.ui.voicesComboBox.addItem(voice_str, userData=(voice_str, False))

        self.ui.voicesComboBox.blockSignals(False)
        self.update_ui_state()

    def update_ui_state(self):
        """Instantly updates button based on the tuple stored in the dropdown."""
        item_data = self.ui.voicesComboBox.currentData()
        
        if not item_data: # Separator selected
            self.ui.DownloadDeleteVoiceButton.setEnabled(False)
            self.ui.DownloadDeleteVoiceButton.setText("Select a Voice")
            return
            
        self.ui.DownloadDeleteVoiceButton.setEnabled(True)
        
        # Unpack the tuple we stored during population
        raw_string, is_downloaded = item_data
        
        if is_downloaded:
            self.ui.DownloadDeleteVoiceButton.setText("Delete")
        else:
            self.ui.DownloadDeleteVoiceButton.setText("Download")

    def handle_action_button(self):
        item_data = self.ui.voicesComboBox.currentData()
        if not item_data:
            return
            
        raw_string, is_downloaded = item_data
        
        if is_downloaded:
            # DELETE LOGIC
            onnx_path, json_path = get_voice_paths(raw_string)
            
            if os.path.exists(onnx_path): os.remove(onnx_path)
            if os.path.exists(json_path): os.remove(json_path)
            
            self.populate_voices_dropdown() 
            
        else:
            # DOWNLOAD LOGIC

            lang, region, speaker, quality = parse_voice_string(raw_string)
            self.ui.DownloadDeleteVoiceButton.setEnabled(False)
            QtWidgets.QApplication.processEvents() 
            
            try:
                download_voice(raw_string)
                self.populate_voices_dropdown() 
            except Exception as e:
                print(f"Download failed: {e}")
            finally:
                self.ui.DownloadDeleteVoiceButton.setEnabled(True)

    def handle_refresh_voices(self):
        """Fetches fresh list from Hugging Face and updates combo box."""
        self.ui.RefreshVoiceButton.setEnabled(False)

        try:
            reload_available_voices()
            self.populate_voices_dropdown()
        except Exception as e:
            print(f"Failed to refresh: {e}")
        finally:
            self.ui.RefreshVoiceButton.setEnabled(True)


class BookWindow(QMainWindow):
    def __init__(self, book_id, parent=None):
        super().__init__(parent)
        self.ui = Ui_BookWindow()
        self.ui.setupUi(self)
        self.id = book_id
        self.databaseBook = get_book(book_id)
        self.settings = get_active_setting()
        self.book = getBook(self.databaseBook.file_path)
        self.fileType = self.databaseBook.file_type
        self.section = self.databaseBook.chapter
        self.sentence = self.databaseBook.sentence

        #updating font size before text is set
        font = self.ui.TextArea.font()
        font.setPointSizeF(self.settings.font_size)
        self.ui.TextArea.setFont(font)

        # Audio format configuration
        self.device = QMediaDevices.defaultAudioOutput()
        preferred = self.device.preferredFormat()
        
        self.audio_fmt = QAudioFormat()
        self.audio_fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        self.audio_fmt.setSampleRate(preferred.sampleRate() if preferred.sampleRate() > 0 else 48000)
        self.audio_fmt.setChannelCount(1)

        if not self.device.isFormatSupported(self.audio_fmt):
            self.audio_fmt.setChannelCount(preferred.channelCount() if preferred.channelCount() > 0 else 2)

        if not self.device.isFormatSupported(self.audio_fmt):
            self.audio_fmt = preferred

        self.active_sample_rate = self.audio_fmt.sampleRate()
        self.active_channels = self.audio_fmt.channelCount()
        set_audio_format(self.active_sample_rate, self.active_channels)

        # Lifecycle objects - created fresh on play, destroyed on stop
        self.audio_buffer = None
        self.sink = None
        self.audioState = -1  # -1 = Stopped, 0 = Paused, 1 = Playing

        # Worker initialization
        self.tts_worker = get_tts_worker()
        self.tts_worker.item_synthesized.connect(self._on_item_synthesized, Qt.QueuedConnection)

        # Granular streaming state
        self._current_page_items = []
        self._queue_cursor = 0
        self._pending_page = 0
        self._play_generation = 0

        QTimer.singleShot(0, self._loadInitialPage)
        QTimer.singleShot(0, self.loadChapterSelect)

        self.ui.nextPageButton.clicked.connect(lambda: self.goNext(True))
        self.ui.prevPageButton.clicked.connect(lambda: self.goPrevious(True))
        self.ui.AudioStart.clicked.connect(self.toggle_audio)

        # Font timer setup
        self.ui.FontEntry.setValue(self.settings.font_size)
        self.font_size_timer = QTimer()
        self.font_size_timer.setSingleShot(True)
        self.font_size_timer.timeout.connect(self.change_font_size)
        self.ui.FontEntry.valueChanged.connect(self.schedule_font_size_change)

        # speed timer setup
        self.speed_timer = QTimer()
        self.speed_timer.setSingleShot(True)
        self.speed_timer.timeout.connect(self.change_speed)
        self.ui.speedSlider.valueChanged.connect(self.speed_slider_change)
        self.ui.speedSpin.valueChanged.connect(self.speed_spin_change)

        # volume timer setup
        self.volume_timer = QTimer()
        self.volume_timer.setSingleShot(True)
        self.volume_timer.timeout.connect(self.change_volume)
        self.ui.volumeSlider.valueChanged.connect(self.volume_slider_change)
        self.ui.volumeSpin.valueChanged.connect(self.volume_spin_change)

        #update values with current settings
        self.ui.volumeSpin.setValue(self.settings.volume)
        self.ui.speedSpin.setValue(self.settings.speed)

        self.populate_voices_selection()
        self.ui.VoiceSelect.currentIndexChanged.connect(self.on_voice_change)

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.stop_audio()
        try:
            self.tts_worker.item_synthesized.disconnect(self._on_item_synthesized)
        except (RuntimeError, TypeError):
            pass
        closeBook(self.id)

    def loadChapterSelect(self):
        chapters = getSectionTitles(self.book)
        if(chapters[0] is None): chapters[0] = "Cover"
        for i in range(1,len(chapters)):
            if(chapters[i] is None): chapters[i] = f"Chapter {i}"
        
        self.ui.chapterList.clear()
        
        self.ui.chapterList.addItems(chapters)
        
        try:
            self.ui.chapterList.itemClicked.disconnect()
        except TypeError:
            pass 
            
        self.ui.chapterList.itemClicked.connect(self.handle_chapter_click)

    def handle_chapter_click(self, item):
        self.stop_audio()
        chapterNum = self.ui.chapterList.row(item) # Gets the index (0, 1, 2...)
        chapterTitle = item.text()                 # Gets the text
        
        print(f"Loading chapter {chapterNum}: {chapterTitle}")
        loadChapterStart(self.id, self.ui.TextArea, chapterNum)
        self.renderCurrentPage()

    def _loadInitialPage(self):
        buildPages(self.id, self.ui.TextArea)
        self.renderCurrentPage()

    def renderCurrentPage(self):
        match self.fileType:
            case "epub":
                items = getCurrentPageItems(self.id)
                renderItemsIntoTextEdit(self.book, self.ui.TextArea, items)

    def goNext(self, audioStop):
        if audioStop:
            self.stop_audio()
        goNextPage(self.id, self.ui.TextArea)
        self.renderCurrentPage()

    def goPrevious(self, audioStop):
        if audioStop:
            self.stop_audio()
        goPrevPage(self.id, self.ui.TextArea)
        self.renderCurrentPage()

    def speed_spin_change(self):
        self.speed_timer.start(1000)
        self.ui.speedSlider.blockSignals(True)
        self.ui.speedSlider.setValue(int(self.ui.speedSpin.value() * 100))
        self.ui.speedSlider.blockSignals(False)

    def speed_slider_change(self):
        self.speed_timer.start(1000)
        self.ui.speedSpin.blockSignals(True)
        self.ui.speedSpin.setValue(round((self.ui.speedSlider.value() / 100), 2))
        self.ui.speedSpin.blockSignals(False)

    def change_speed(self):
        speed_float = self.ui.speedSpin.value()
        update_settings(self.settings.id, speed=speed_float)
        from textToSpeech import _ENGINE_CONFIG
        _ENGINE_CONFIG["speed"] = speed_float

        # If audio is playing (or was paused mid-stream), restart it seamlessly from the current sentence
        if self.audioState in (0, 1):
            page_to_resume = self._pending_page
            item_to_resume = self._current_playing_item_index
            self._queue_page_audio(page_to_resume, start_item_index=item_to_resume)

    def volume_spin_change(self):
        self.volume_timer.start(100)
        self.ui.volumeSlider.blockSignals(True)
        self.ui.volumeSlider.setValue(int(self.ui.volumeSpin.value() * 100))
        self.ui.volumeSlider.blockSignals(False)
    
    def volume_slider_change(self):
        self.volume_timer.start(100)
        self.ui.volumeSpin.blockSignals(True)
        self.ui.volumeSpin.setValue(round((self.ui.volumeSlider.value() / 100), 2))
        self.ui.volumeSpin.blockSignals(False)

    def change_volume(self):
        volume_float = self.ui.volumeSpin.value()
        update_settings(self.settings.id, volume=volume_float)
        
        # Applies smoothly in real-time, no audio restart required
        if self.sink is not None:
            self.sink.setVolume(volume_float)

    def schedule_font_size_change(self):
        self.stop_audio()
        self.font_size_timer.start(1000)

    def change_font_size(self):
        self.stop_audio()
        fontSize = self.ui.FontEntry.value()
        update_settings(self.settings.id, font_size=fontSize)
        font = self.ui.TextArea.font()
        font.setPointSizeF(fontSize)
        self.ui.TextArea.setFont(font)
        buildPages(self.id, self.ui.TextArea, True)
        self.renderCurrentPage()

    def stop_audio(self):
        self._play_generation += 1  # Block upcoming pipeline deliveries
        self.audioState = -1
        
        # 1. Kill hardware stream securely
        if self.sink is not None:
            self.sink.stop()
            self.sink.deleteLater()
            self.sink = None

        # 2. Kill the device it was reading from
        if self.audio_buffer is not None:
            self.audio_buffer.close()
            self.audio_buffer.deleteLater()
            self.audio_buffer = None

        # 3. Clear pending syntheses
        self.tts_worker.clear_queue(self.id)

    # --- Item Streaming & Queue Handling ---
    def _queue_page_audio(self, page, start_item_index=0):
        self.stop_audio()
        self.audioState = 1
        self._pending_page = page
        tts_set_page(self.id, page)

        self.audio_buffer = StreamingAudioBuffer(sample_rate=self.active_sample_rate, channels=self.active_channels)
        self.audio_buffer.page_finished.connect(self.on_audio_page_finished)
        self.audio_buffer.clip_started.connect(self.on_clip_started)
        self.audio_buffer.clip_finished.connect(self.on_clip_finished)
        self.audio_buffer.buffer_low.connect(self._on_buffer_low)
        self.audio_buffer.open(QIODevice.ReadOnly)

        raw_items = getCurrentPageItems(self.id) or []
        self._current_page_items = [
            (idx, item['text'].strip())
            for idx, item in enumerate(raw_items)
            if item.get('type') != 'image' and item.get('text', '').strip()
        ]

        if not self._current_page_items:
            self.on_audio_page_finished(page)
            return

        last_index = self._current_page_items[-1][0]
        self.audio_buffer.set_page_boundary(page=page, last_item_index=last_index)

        # Fast-forward queue cursor to the requested start sentence (used by speed changes)
        self._queue_cursor = 0
        for i, (idx, text) in enumerate(self._current_page_items):
            if idx >= start_item_index:
                self._queue_cursor = i
                break

        self._queue_next_items(count=2)

    def _queue_next_items(self, count=1):
        for _ in range(count):
            if self._queue_cursor < len(self._current_page_items):
                idx, text = self._current_page_items[self._queue_cursor]
                
                # Add this print statement to see what enters the queue
                preview = text[:40].replace('\n', ' ') + ("..." if len(text) > 40 else "")
                print(f"[Pipeline] Queuing page {self._pending_page}, item {idx}: '{preview}'")
                
                self.tts_worker.queue_item(self.id, self._pending_page, idx, text, self._play_generation)
                self._queue_cursor += 1

    def _on_buffer_low(self):
        if self.audioState == 1 and self._queue_cursor < len(self._current_page_items):
            self._queue_next_items(count=1)

    def _on_item_synthesized(self, book_id: int, page_index: int, item_index: int, pcm_bytes: bytes, generation: int):
        if book_id != self.id or page_index != self._pending_page or generation != self._play_generation:
            return

        if not self.audio_buffer:
            return

        clip_id = f"{book_id}-{page_index}-{item_index}"
        self.audio_buffer.feed(clip_id, pcm_bytes, item_index, page_index)

        # Apply current volume when sink spins up
        if self.audioState == 1 and self.sink is None:
            self.sink = QAudioSink(self.device, self.audio_fmt)
            if hasattr(self.ui, 'VolumeSlider'):
                self.sink.setVolume(self.ui.VolumeSlider.value() / 100.0)
            else:
                self.sink.setVolume(1.0)
            self.sink.stateChanged.connect(self._on_audio_state_changed)
            self.sink.start(self.audio_buffer)

    def toggle_audio(self):
        if self.audioState == -1:
            cur_page = getCurrentPage(self.id)
            self._queue_page_audio(cur_page)
        elif self.audioState == 1:
            self.audioState = 0
            if self.sink:
                self.sink.suspend()
        elif self.audioState == 0:
            self.audioState = 1
            if self.sink:
                self.sink.resume()

    def on_audio_page_finished(self, page):
        # Defer the page transition to the main event loop!
        # This allows the C++ audio thread to safely finish its current 
        # callback BEFORE we destroy the sink and buffer.
        QTimer.singleShot(0, lambda: self._transition_to_next_page(page))

    def _transition_to_next_page(self, page):
        # We only want to advance if the user hasn't manually clicked away
        # or stopped the audio in the fraction of a second we waited.
        if self.audioState == 1 and self._pending_page == page:
            self.goNext(False)
            self._queue_page_audio(page + 1)

    def on_clip_started(self, clip_id, item_index):
        # Track exactly which sentence is currently outputting to the speakers
        self._current_playing_item_index = item_index

    def on_clip_finished(self, clip_id, item_index):
        pass

    def _on_audio_state_changed(self, state):
        state_names = {
            QAudio.ActiveState: "Active (Playing sound)",
            QAudio.SuspendedState: "Suspended (Paused)",
            QAudio.StoppedState: "Stopped",
            QAudio.IdleState: "Idle (Waiting for audio data / buffer empty)"
        }
        if self.sink:
            print(f"[QAudioSink] State: {state_names.get(state, state)} | Error: {self.sink.error()}")

    def populate_voices_selection(self):
        voices = get_downloaded_voices()
        self.ui.VoiceSelect.clear()
        for voice in voices:
            self.ui.VoiceSelect.addItem(voice)

    def on_voice_change(self):
        selected_voice = self.ui.VoiceSelect.currentText()
        update_settings(self.settings.id, voice_model=selected_voice)
        update_model("piper", selected_voice)
        self.stop_audio()
        

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()