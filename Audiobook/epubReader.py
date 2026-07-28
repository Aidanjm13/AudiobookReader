from fileHandling import getAppdataFolderPath
import ebooklib
from ebooklib import epub
from lxml import html

#gets the authors name
def getAuthor(book):
    return book.get_metadata('DC', 'creator')

#gets the book title
def getTitle(book):
    return book.get_metadata('DC', 'title')

#gets book language
def getLanguage(book):
    return book.get_metadata('DC', 'language')

#gets the names of every chapter returns list of chapters 
def getChapterNames(book):
    pass

#returns the content of a chapter, can enter either the chapter number or name
def getChapterContent(chapter):
    pass







# book = epub.read_epub("mybook.epub")

# # Metadata
# title = book.get_metadata('DC', 'title')
# author = book.get_metadata('DC', 'creator')
# language = book.get_metadata('DC', 'language')

# print(title, author)

# # Walk the spine (correct reading order)
# for item_id, _ in book.spine:
#     item = book.get_item_with_id(item_id)
#     tree = html.fromstring(item.get_content())
    
#     # Plain text
#     text = tree.text_content()
#     print(text)

# # Get all paragraphs
# paragraphs = tree.xpath('//p')
# for p in paragraphs:
#     print(p.text_content())

# # Get all headings
# headings = tree.xpath('//h1 | //h2 | //h3')

# # CSS-selector style (needs cssselect installed: pip install cssselect)
# paragraphs = tree.cssselect('p')

#  # --- Content, in correct reading order via spine ---
# chapters = []
# for item_id, _ in book.spine:
#     item = book.get_item_with_id(item_id)
#     if item.get_type() != ebooklib.ITEM_DOCUMENT:
#         continue  # skip non-content spine entries, if any

#     tree = html.fromstring(item.get_content())
#     text = tree.text_content().strip()
#     if text:
#         chapters.append(text)

# return chapters

