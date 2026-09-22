import threading
from SQLHandler import get_book, update_book_position
from epubReader import buildPageIndex, getBook
from ttsWorker import tts_set_page, repaginate_book, tts_close_book

# This class stores the pagination of text for currently opened books
class BookPages:
    def __init__(self):
        self._lock = threading.Lock()
        self._indexes = {}   # book_id : list[list[item]] - items for each page in chapter
        self._pages = {}     # book_id : pageNum - current page
        self._positions = {} # book_id : [chapter, position]
        self._fileType = {}  # book_id : string - filetype of book
        self._paths = {}     # book_id : path to book file

    def set_page(self, book_id, pages):
        with self._lock:
            self._pages[book_id] = pages

    def get_page(self, book_id):
        with self._lock:
            return self._pages[book_id]

    def set_position(self, book_id, chapter, position):
        with self._lock:
            self._positions[book_id] = [chapter, position]

    def get_position(self, book_id):
        with self._lock:
            return self._positions[book_id]

    def set_fileType(self, book_id, fileType):
        with self._lock:
            self._fileType[book_id] = fileType

    def get_fileType(self, book_id):
        with self._lock:
            return self._fileType[book_id]

    def set_path(self, book_id, path):
        with self._lock:
            self._paths[book_id] = path

    def get_path(self, book_id):
        with self._lock:
            return self._paths[book_id]

    def set_indexes(self, book_id, indexes):
        with self._lock:
            self._indexes[book_id] = indexes

    def get_indexes(self, book_id):
        with self._lock:
            return self._indexes[book_id]

    def open_book(self, book_id):
        if book_id in self._fileType:
            return
        book = get_book(book_id)
        self.set_fileType(book_id, book.file_type)
        self.set_position(book_id, book.chapter, book.sentence)
        self.set_path(book_id, book.file_path)

    def close_book(self, book_id):
        with self._lock:
            self._pages.pop(book_id, None)
            self._positions.pop(book_id, None)
            self._fileType.pop(book_id, None)
            self._indexes.pop(book_id, None)
            self._paths.pop(book_id, None)
        tts_close_book(book_id)


_book_pages = None
_book_pages_lock = threading.Lock()

def get_book_pages():
    global _book_pages
    if _book_pages is None:
        with _book_pages_lock:
            if _book_pages is None:
                _book_pages = BookPages()
    return _book_pages


def buildPages(book_id, textEdit, anchorTop = False):
    bookPages = get_book_pages()
    bookPages.open_book(book_id)
    position = bookPages.get_position(book_id)
    anchorItemIndex = None
    if anchorTop:
        page = bookPages.get_page(book_id)
        if(page is not None):
            position[1] = setPositionTopPage(bookPages, book_id, page, position[0])
            anchorItemIndex = position[1]

    match bookPages.get_fileType(book_id):
        case "epub":
            items = buildPageIndex(getBook(bookPages.get_path(book_id)), textEdit, position[0], anchorItemIndex)
            bookPages.set_indexes(book_id, items)
            page = getPageWithPosition(bookPages, book_id, position[1])
            bookPages.set_page(book_id, page)
        case _:
            return
            
    page = bookPages.get_page(book_id)
    repaginate_book(book_id, page)


def getPageWithPosition(bookPages, book_id, position):
    pages = bookPages.get_indexes(book_id)
    itemCount = 0
    for i in range(len(pages)):
        page = pages[i]
        itemCount += len(page) - (1 if page and page[0].get('continuation') else 0)
        if itemCount > position:
            return i
    return -1


def setPositionTopPage(bookPages, book_id, currentPageNum, chapter):
    pages = bookPages.get_indexes(book_id)
    itemCount = 0
    for i in range(currentPageNum):
        page = pages[i]
        itemCount += len(page) - (1 if page and page[0].get('continuation') else 0)
    bookPages.set_position(book_id, chapter, itemCount)
    return itemCount


def getCurrentPageItems(book_id, offset=0):
    bookPages = get_book_pages()
    page = bookPages.get_page(book_id) + offset
    indexes = bookPages.get_indexes(book_id)
    if page < 0 or page >= len(indexes):
        return None
    return indexes[page]


def getPageItems(book_id, pageNum):
    bookPages = get_book_pages()
    indexes = bookPages.get_indexes(book_id)
    if pageNum < 0 or pageNum >= len(indexes):
        return None
    return indexes[pageNum]


def goNextPage(book_id, textArea):
    bookPages = get_book_pages()
    currentPage = bookPages.get_page(book_id)
    indexes = bookPages.get_indexes(book_id)
    position = bookPages.get_position(book_id)
    if currentPage + 1 >= len(indexes):
        bookPages.set_position(book_id, position[0] + 1, 0)
        bookPages.set_page(book_id, 0)
        buildPages(book_id, textArea)
    else:
        bookPages.set_page(book_id, currentPage + 1)
        setPositionTopPage(bookPages, book_id, currentPage + 1, position[0])
    saveProgress(book_id)
    setTTSWorkerPage(book_id)


def goPrevPage(book_id, textArea):
    bookPages = get_book_pages()
    currentPage = bookPages.get_page(book_id)
    indexes = bookPages.get_indexes(book_id)
    position = bookPages.get_position(book_id)
    if currentPage - 1 < 0:
        if position[0] > 0:
            bookPages.set_position(book_id, position[0] - 1, 0)
            buildPages(book_id, textArea)
            bookPages.set_page(book_id, len(bookPages.get_indexes(book_id)) - 1)
            setPositionTopPage(bookPages, book_id, len(bookPages.get_indexes(book_id)) - 1, position[0] - 1)
    else:
        bookPages.set_page(book_id, currentPage - 1)
        setPositionTopPage(bookPages, book_id, currentPage - 1, position[0])
    saveProgress(book_id)
    setTTSWorkerPage(book_id)

#moves to the start of the chapter
def loadChapterStart(book_id, textArea, chapterNum):
    bookPages = get_book_pages()
    bookPages.set_position(book_id, chapterNum, 0)
    buildPages(book_id, textArea)
    bookPages.set_page(book_id, 0)
    saveProgress(book_id)
    setTTSWorkerPage(book_id)


def saveProgress(book_id):
    bookpages = get_book_pages()
    position = bookpages.get_position(book_id)
    update_book_position(book_id, position[0], position[1])


def setTTSWorkerPage(book_id):
    bookPages = get_book_pages()
    page = bookPages.get_page(book_id)
    if page is None:
        return
    tts_set_page(book_id, page)


def getCurrentPage(book_id):
    bookPages = get_book_pages()
    return bookPages.get_page(book_id)


def closeBook(book_id):
    bookPages = get_book_pages()
    bookPages.close_book(book_id)