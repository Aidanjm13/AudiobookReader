import threading
from SQLHandler import get_book, update_book_position
from epubReader import buildPageIndex, getBook

#this class is for storing the pagination of text for the currently opened books
#also has helper functions for getting and storing pages
class BookPages:
    def __init__(self):
        self._lock = threading.Lock()
        self._indexes = {}  # book_id : list[list[item]] - items for each page in chapter
        self._pages = {} # book_id : pageNum - the page that the book is currently on
        self._positions = {} # book_id : [chapter,position] - current chapter and position for a book
        self._fileType = {} # book_id : string - filetype of the book
        self._paths = {} # book_id : book_path = path to the bookFile

    def set_page(self, book_id, pages):
        """Call after (re)paginating a chapter, from the GUI thread."""
        with self._lock:
            self._pages[book_id] = pages

    def get_page(self, book_id):
        with self._lock:
            return self._pages[book_id]

    def set_position(self, book_id, chapter, position):
        with self._lock:
            self._positions[book_id] = [chapter,position]

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


    #sets book from database if it doesnt exist
    def open_book(self, book_id):
        if(book_id in self._fileType): return #if book already retrieved from database then return
        book = get_book(book_id)
        self.set_fileType(book_id, book.file_type)
        self.set_position(book_id, book.chapter, book.sentence)
        self.set_path(book_id, book.file_path)

    #clears book from object
    def close_book(self, book_id):
        with self._lock:
            self._pages.pop(book_id, None)
            self._positions.pop(book_id, None)
            self._fileType.pop(book_id, None)
            self._indexes.pop(book_id, None)
            self._paths.pop(book_id, None)


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

#takes the textArea from the book page and builds the index for the current chapter
#populates data from database if not already stored
#anchorTop gets item number from top of page to use as an anchor, mainly for font and text area size changes
def buildPages(book_id, textEdit, anchorTop = False):
    bookPages = get_book_pages()
    bookPages.open_book(book_id)
    position = bookPages.get_position(book_id)

    anchorItemIndex = None
    if anchorTop: #then setPosition as top of the page, and anchor pagination to it
        page = bookPages.get_page(book_id)
        if(page is not None):
            position[1] = setPositionTopPage(bookPages, book_id, page, position[0])
            anchorItemIndex = position[1]

    match bookPages.get_fileType(book_id):
        case "epub":
            items = buildPageIndex(getBook(bookPages.get_path(book_id)),textEdit,position[0],anchorItemIndex)
            bookPages.set_indexes(book_id, items)
            bookPages.set_page(book_id,getPageWithPosition(bookPages, book_id, position[1]))
        case _:
            return

#determines which page the book is on based on the item that number that it is on
#positions are 0 indexed
def getPageWithPosition(bookPages, book_id, position):
    pages = bookPages.get_indexes(book_id)
    itemCount = 0
    for i in range(len(pages)):
        page = pages[i]
        # a continuation fragment, if present, is always page[0] -- see
        # fillPageAndCapture: offset>0 only happens on the first item pulled
        itemCount += len(page) - (1 if page and page[0].get('continuation') else 0)
        if(itemCount > position): return i
    return -1 #position not found

#sets the current books position to the top of this page
def setPositionTopPage(bookPages, book_id, currentPageNum, chapter):
    pages = bookPages.get_indexes(book_id)
    itemCount = 0
    for i in range(currentPageNum):
        page = pages[i]
        itemCount += len(page) - (1 if page and page[0].get('continuation') else 0)
    bookPages.set_position(book_id, chapter, itemCount)
    return itemCount

#gets the items for the page that the book is currently on
#offset is if you want pages before or after the current page
def getCurrentPageItems(book_id, offset = 0):
    bookPages = get_book_pages()
    page = bookPages.get_page(book_id)+offset
    indexes = bookPages.get_indexes(book_id)
    if(page < 0 or page >= len(indexes)): return None
    return indexes[page]

#updates the book to the next page, moving it to the next chapter if needed
def goNextPage(book_id, textArea):
    bookPages = get_book_pages()
    currentPage = bookPages.get_page(book_id)
    indexes = bookPages.get_indexes(book_id)
    position = bookPages.get_position(book_id)
    if(currentPage+1 >= len(indexes)): #then we need to move to the next chapter
        bookPages.set_position(book_id,position[0]+1,0)
        bookPages.set_page(book_id,0)
        buildPages(book_id,textArea)
    else:
        bookPages.set_page(book_id, currentPage+1)
        setPositionTopPage(bookPages, book_id, currentPage+1, position[0])
    saveProgress(book_id)

def goPrevPage(book_id, textArea):
    bookPages = get_book_pages()
    currentPage = bookPages.get_page(book_id)
    indexes = bookPages.get_indexes(book_id)
    position = bookPages.get_position(book_id)
    if(currentPage-1 < 0): #then we need to move to the previous chapter
        if(position[0] > 0): #only if there is one
            bookPages.set_position(book_id,position[0]-1,0)
            buildPages(book_id,textArea)
            bookPages.set_page(book_id,len(bookPages.get_indexes(book_id))-1)
            setPositionTopPage(bookPages, book_id, len(bookPages.get_indexes(book_id))-1, position[0]-1)
    else:
        bookPages.set_page(book_id, currentPage-1)
        setPositionTopPage(bookPages, book_id, currentPage-1, position[0])
    saveProgress(book_id)

#saves new position to the database
def saveProgress(book_id):
    bookpages = get_book_pages()
    position = bookpages.get_position(book_id)
    update_book_position(book_id, position[0], position[1])