import threading
import time

class TTSWindowCache:
    def __init__(self, synthesize_fn, page_source, behind=2, ahead=4):
        self.synthesize = synthesize_fn
        self.page_source = page_source  # function(index) -> text or None
        self.behind = behind
        self.ahead = ahead

        self.cache = {}       # index -> audio
        self.pending = set()  # indices currently being synthesized
        self.current_page = 0

        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        self._stop_event = threading.Event()

        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _window_range(self):
        lo = max(0, self.current_page - self.behind)
        hi = self.current_page + self.ahead
        return lo, hi

    def _run(self):
        while not self._stop_event.is_set():
            with self.cond:
                lo, hi = self._window_range()
                missing = [
                    i for i in range(lo, hi + 1)
                    if i not in self.cache and i not in self.pending
                    and self.page_source(i) is not None
                ]
                if not missing:
                    self.cond.wait(timeout=0.5)
                    continue
                missing.sort(key=lambda i: abs(i - self.current_page))
                target = missing[0]
                self.pending.add(target)

            text = self.page_source(target)
            audio = self.synthesize(text)  # the slow part, done outside the lock

            with self.lock:
                lo, hi = self._window_range()
                if lo <= target <= hi:      # window may have moved while we worked
                    self.cache[target] = audio
                self.pending.discard(target)
                self._evict_outside_window()
                self.cond.notify_all()

    def _evict_outside_window(self):
        lo, hi = self._window_range()
        for idx in list(self.cache.keys()):
            if idx < lo or idx > hi:
                del self.cache[idx]

    def goto_page(self, index):
        with self.cond:
            self.current_page = index
            self._evict_outside_window()
            self.cond.notify_all()  # wake worker to reprioritize

    def get_page(self, index, block=True, timeout=None):
        with self.cond:
            deadline = None if timeout is None else time.time() + timeout
            while index not in self.cache:
                if not block:
                    return None
                remaining = None if deadline is None else deadline - time.time()
                if remaining is not None and remaining <= 0:
                    return None
                self.cond.wait(timeout=remaining)
            return self.cache[index]

    def next_page(self):
        self.goto_page(self.current_page + 1)
        return self.get_page(self.current_page)

    def prev_page(self):
        self.goto_page(max(0, self.current_page - 1))
        return self.get_page(self.current_page)

    def stop(self):
        self._stop_event.set()
        with self.cond:
            self.cond.notify_all()
        self.thread.join()