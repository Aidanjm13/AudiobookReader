import threading
import time
from textToSpeech import SynthesizeText

#tts worker for managing text to audio files for multiple audiobooks at the same time, prioritizes active book
#synthesize_fn is function for turning text to audio
#page_source is function for getting text with book id and index (page)
#behing and ahead is how many indexes behind and ahead it should load as well
class MultiBookTTSWorker:
    def __init__(self, synthesize_fn, page_source, behind=2, ahead=4):
        self.synthesize = synthesize_fn
        self.page_source = page_source
        self.behind = behind
        self.ahead = ahead

        self.cache = {}              # (book_id, page_num) -> [audio]
        self.pending = set()         # (book_id, page_num, version)
        self.current_page = {}       # book_id -> current page index
        self.book_version = {}       # book_id -> int, bumped on repagination
        self.active_book = None

        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        self._stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    #returns the (lo, hi) page range this book should keep cached, based on
    #its current page and the worker's behind/ahead settings
    def _window_for(self, book_id):
        cur = self.current_page[book_id]
        lo = max(0, cur - self.behind)
        hi = cur + self.ahead
        return lo, hi

    #whether a given page index falls inside book_id's current cache window
    def _in_window(self, book_id, index):
        lo, hi = self._window_for(book_id)
        return lo <= index <= hi
    
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

            #once a page is decided, get audio for each text item on that page, and store to cache
            textItems = self.page_source(book_id, index)
            if not textItems:
                continue
            audio = []
            for item in textItems:
                if item.get('type') == 'image': 
                    continue
                text = item.get('text', '').strip()
                if not text:
                    continue
                pcm = self.synthesize(text)
                print(f"[TTS Worker] Synthesized: '{text[:30]}...' -> {len(pcm)} bytes")
                audio.append(pcm)

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
                from bookPages import getPageItems
                _worker = MultiBookTTSWorker(
                    synthesize_fn=SynthesizeText,
                    page_source=getPageItems,
                    behind=2,
                    ahead=4,
                )
    return _worker

#called when the book is opened
def tts_set_page(book_id, page):
    worker = get_tts_worker()
    with worker.cond:
        worker.current_page[book_id] = page
        worker.active_book = book_id
        worker.cond.notify_all()  # wake worker to start processing this book


#call when page boundaries change and book needs to be reloaded
def repaginate_book(book_id, new_current_page=0):
    worker = get_tts_worker()
    worker.active_book = book_id
    worker.repaginate_book(book_id, new_current_page)

#returns cached audio for a specific book page, or None if not synthesized yet
#safe to call from any thread
def get_page_audio(book_id, page):
    worker = get_tts_worker()
    with worker.lock:
        return worker.cache.get((book_id, page))

#closes book with this id
def tts_close_book(book_id):
    worker = get_tts_worker()
    with worker.cond:
        if book_id in worker.current_page:
            del worker.current_page[book_id]
        if book_id in worker.book_version:
            del worker.book_version[book_id]
        # drop every cached page for this book
        for key in list(worker.cache.keys()):
            if key[0] == book_id:
                del worker.cache[key]
        if worker.active_book == book_id:
            worker.active_book = None
        worker.cond.notify_all()  # wake worker to update its state