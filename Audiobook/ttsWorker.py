import threading
import time
from textToSpeech import SynthesizeText

#tts worker for managing text to audio files for multiple audiobooks at the same time, prioritizes active book
#synthesize_fn is function for turning text to audio
#page_source is function for getting text with book id and index
#behing and ahead is how many indexes behind and ahead it should load as well
class MultiBookTTSWorker:
    def __init__(self, synthesize_fn, page_source, behind=2, ahead=4):
        self.synthesize = synthesize_fn
        self.page_source = page_source
        self.behind = behind
        self.ahead = ahead

        self.cache = {}              # (book_id, page_index) -> audio
        self.pending = set()         # (book_id, page_index, version)
        self.current_page = {}       # book_id -> current page index
        self.book_version = {}       # book_id -> int, bumped on repagination
        self.active_book = None

        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        self._stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    # ... _window_for, _in_window unchanged ...
    #what loops in the thread
    def _run(self):
        while not self._stop_event.is_set(): #while not stopped
            with self.cond:
                target = self._pick_next_target()
                if target is None:
                    self.cond.wait(timeout=0.5)
                    continue
                book_id, index = target
                version = self.book_version.get(book_id, 0)
                self.pending.add((book_id, index, version))

            text = self.page_source(book_id, index)
            audio = self.synthesize(text)

            with self.lock:
                current_version = self.book_version.get(book_id, 0)
                # only store if this book hasn't been repaginated/closed since we started
                if version == current_version and self._in_window(book_id, index):
                    self.cache[(book_id, index)] = audio
                self.pending.discard((book_id, index, version))
                self._evict_stale()
                self.cond.notify_all()

    #picks the book in which audio should be generated for starting with the current active book
    def _pick_next_target(self):
        book_order = [self.active_book] + [
            b for b in self.current_page if b != self.active_book
        ]
        for book_id in book_order:
            if book_id is None:
                continue
            lo, hi = self._window_for(book_id)
            cur = self.current_page[book_id]
            version = self.book_version.get(book_id, 0)
            missing = [
                (book_id, i) for i in range(lo, hi + 1)
                if (book_id, i) not in self.cache
                and (book_id, i, version) not in self.pending
                and self.page_source(book_id, i) is not None
            ]
            if missing:
                missing.sort(key=lambda t: abs(t[1] - cur))
                return missing[0]
        return None

    def _evict_stale(self):
        for key in list(self.cache.keys()):
            book_id, index = key
            if book_id not in self.current_page or not self._in_window(book_id, index):
                del self.cache[key]

    def repaginate_book(self, book_id, new_current_page=0):
        """Call this when page boundaries change (e.g. font size, page size)."""
        with self.cond:
            self.book_version[book_id] = self.book_version.get(book_id, 0) + 1
            self.current_page[book_id] = new_current_page
            # drop every cached page for this book — old boundaries are invalid
            for key in list(self.cache.keys()):
                if key[0] == book_id:
                    del self.cache[key]
            self.cond.notify_all()  # wake worker to start fresh under new version


_worker = None
_worker_lock = threading.Lock()

#singleton function used to get the single tts worker
def get_tts_worker():
    global _worker
    if _worker is None:
        with _worker_lock:
            if _worker is None:  # double-checked locking
                _worker = MultiBookTTSWorker(
                    synthesize_fn=SynthesizeText,
                    page_source=getPageTextUnified,
                    behind=2,
                    ahead=4,
                )
    return _worker

# per-book dispatch table, filled in when a book is opened
book_loaders = {}   # book_id -> loader function

#the index of the books so that it can be used to reconstruct text with the current positions
book_indexes = {}

#called when book is opened to set file type for loader and set it for the worker
def open_book(book_id, file_type, start_page, book_index = None):
    book_loaders[book_id] = LOADERS[file_type]
    if(book_index): book_indexes[book_id] = book_index
    _worker.open_book(book_id, start_page)

#TO DO:
#used to get the text for a specific page with a book id
#this will handle intersection of different file type page processing
#book_id is the database id of the book, page_index is the page number / current position of the book
def getPageTextUnified(book_id, page_index):
    return book_loaders[book_id](book_id, page_index)

#takes id and position for an epub file and returns the text for that page
def getPageTextEpub(book_id, page_index):

    return

# a registry mapping file_type -> loader function
LOADERS = {
    "epub": getPageTextEpub
}