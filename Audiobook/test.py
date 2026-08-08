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

from textSplitting import split_sentences


# testing epub reader when in system

fileName = "pg84-images-3 - copy"
bookPath = os.path.join(getBooksFolderPath(), fileName, f"{fileName}.epub")
book = getBook(bookPath)
print(getSectionTitles(book))
#print(getChapterBlocks(book,1))
#print(getCoverImagePath(book))
#print(getCoverImage(book,getCoverImagePath(book)))


# documents = getSpineDocuments(book)
# tocFlat = flattenToc(book.toc)

# print("First spine item name:", repr(documents[0].get_name()))
# print()
# print("TOC entries:")
# for title, href in tocFlat:
#     print(f"  {title!r} -> {href!r}")

