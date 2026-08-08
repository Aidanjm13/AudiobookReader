from epubReader import *
from fileHandling import *
from SQLHandler import *
import os

#testing SQLAlchemy functions
firstRow = get_book(1)
#print(firstRow.title)
#print(firstRow.author)
#print(firstRow.language)
#print(firstRow.last_accessed)




# testing epub reader when in system

fileName = "pg84-images-3 - copy"
bookPath = os.path.join(getBooksFolderPath(), fileName, f"{fileName}.epub")
book = getBook(bookPath)
print(getChapterContent(book,3))
#print(getCoverImagePath(book))
#print(getCoverImage(book,getCoverImagePath(book)))

