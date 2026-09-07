import threading

#this class is for storing the pagination of text for the currently opened books
#also has helper functions for getting and storing pages
class BookPages:
    """Thread-safe holder for the currently-loaded chapter's page text per book.
    The GUI thread writes here on pagination; the worker thread only reads."""
    def __init__(self):
        self._lock = threading.Lock()
        self._pages = {}  # book_id -> list[str], pages of the currently loaded chapter

    def set_pages(self, book_id, pages):
        """Call after (re)paginating a chapter, from the GUI thread."""
        with self._lock:
            self._pages[book_id] = pages

    def get_page(self, book_id, index):
        with self._lock:
            pages = self._pages.get(book_id)
            if pages is None or index < 0 or index >= len(pages):
                return None
            return pages[index]

    def close_book(self, book_id):
        with self._lock:
            self._pages.pop(book_id, None)


_book_pages = None
_book_pages_lock = threading.Lock()

#singleton function used to get the single shared BookPages store
def get_book_pages():
    global _book_pages
    if _book_pages is None:
        with _book_pages_lock:
            if _book_pages is None:  # double-checked locking
                _book_pages = BookPages()
    return _book_pages