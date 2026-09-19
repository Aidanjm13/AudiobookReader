import threading
from collections import deque
from PySide6.QtCore import QObject, Signal
from textToSpeech import SynthesizeText

class MultiBookTTSWorker(QObject):
    # Emits (book_id, page_index, item_index, pcm_bytes, generation)
    item_synthesized = Signal(int, int, int, bytes, int)

    def __init__(self, synthesize_fn, page_source=None, behind=2, ahead=4):
        super().__init__()
        self.synthesize = synthesize_fn
        self.page_source = page_source
        self.behind = behind
        self.ahead = ahead

        self._queue = deque()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self.active_book = None
        self.current_page = {}
        self.book_version = {}

        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def queue_item(self, book_id: int, page_index: int, item_index: int, text: str, generation: int = 0):
        with self._lock:
            self._queue.append((book_id, page_index, item_index, text, generation))

    def clear_queue(self, book_id: int = None):
        with self._lock:
            if book_id is None:
                self._queue.clear()
            else:
                self._queue = deque(item for item in self._queue if item[0] != book_id)

    def set_active_book(self, book_id: int, page: int):
        with self._lock:
            self.active_book = book_id
            self.current_page[book_id] = page

    def _run(self):
        while not self._stop_event.is_set():
            task = None
            with self._lock:
                if self._queue:
                    task = self._queue.popleft()

            if task is None:
                self._stop_event.wait(timeout=0.03)
                continue

            book_id, page_index, item_index, text, generation = task
            if not text or not text.strip():
                continue

            try:
                pcm = self.synthesize(text)
                if pcm:
                    self.item_synthesized.emit(book_id, page_index, item_index, pcm, generation)
            except Exception as e:
                print(f"[TTSWorker] Error synthesizing item {item_index} on page {page_index}: {e}")

    def repaginate_book(self, book_id, new_current_page=0):
        with self._lock:
            self.book_version[book_id] = self.book_version.get(book_id, 0) + 1
            self.current_page[book_id] = new_current_page
            self._queue = deque(item for item in self._queue if item[0] != book_id)

    def stop(self):
        self._stop_event.set()


_worker = None
_worker_lock = threading.Lock()

def get_tts_worker():
    global _worker
    if _worker is None:
        with _worker_lock:
            if _worker is None:
                from bookPages import getPageItems
                _worker = MultiBookTTSWorker(
                    synthesize_fn=SynthesizeText,
                    page_source=getPageItems,
                )
    return _worker

def tts_set_page(book_id, page):
    worker = get_tts_worker()
    worker.set_active_book(book_id, page)

def repaginate_book(book_id, new_current_page=0):
    worker = get_tts_worker()
    worker.active_book = book_id
    worker.repaginate_book(book_id, new_current_page)

def tts_close_book(book_id):
    worker = get_tts_worker()
    with worker._lock:
        if book_id in worker.current_page:
            del worker.current_page[book_id]
        if book_id in worker.book_version:
            del worker.book_version[book_id]
        if worker.active_book == book_id:
            worker.active_book = None
        worker._queue = deque(item for item in worker._queue if item[0] != book_id)

def get_page_audio(book_id, page):
    return None