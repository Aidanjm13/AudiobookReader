from fileHandling import getAppdataFolderPath
import ebooklib
from ebooklib import epub
from lxml import html
import os

#returns the ebooklib book object with book path
def getBook(book_path):
    return epub.read_epub(book_path)

#returns a list of names of the creators, removes extra meta data about each individual creator, could include authors, illustrators, etc
def getCreators(book):
    creators = book.get_metadata('DC', 'creator')
    simpleList = []
    for creator in creators:
        simpleList.append(creator[0])
    return simpleList


#returns list of titles of the book, removes extra meta data about each individual title
def getTitles(book):
    titles = book.get_metadata('DC', 'title')
    simpleList = []
    for title in titles:
        simpleList.append(title[0])
    return simpleList

#gets book language
def getLanguages(book):
    languages = book.get_metadata('DC', 'language')
    simpleList = []
    for language in languages:
        simpleList.append(language[0])
    return simpleList

#internal helper: flattens book.toc (which can be nested via Section groups)
#into a flat list of (title, href) tuples, in reading order
def _flattenToc(tocEntries):
    flat = []
    for entry in tocEntries:
        if isinstance(entry, tuple):
            section, children = entry
            flat.append((section.title, getattr(section, 'href', None)))
            flat.extend(_flattenToc(children))
        else:
            flat.append((entry.title, entry.href))
    return flat

#internal helper: returns chapter document items in spine (reading) order, skipping nav pages
def _getSpineDocuments(book):
    idToItem = {item.get_id(): item for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT)}
    ordered = []
    for spineId, _linear in book.spine:
        item = idToItem.get(spineId)
        if item is not None and not isinstance(item, epub.EpubNav):
            ordered.append(item)
    return ordered

#gets the names of every chapter, returns list of chapter titles in reading order
def getChapterNames(book):
    if book.toc:
        return [title for title, href in _flattenToc(book.toc) if title]
    # no toc defined in this epub - fall back to numbering by spine position
    return [f"Chapter {i + 1}" for i in range(len(_getSpineDocuments(book)))]

#returns the plain-text content of a chapter, can enter either the chapter
#number (0-based int) or name (str, matching a value from getChapterNames)
def getChapterContent(book, chapter):
    documents = _getSpineDocuments(book)

    if isinstance(chapter, int):
        if chapter < 0 or chapter >= len(documents):
            return None
        item = documents[chapter]
    else:
        tocFlat = _flattenToc(book.toc) if book.toc else []
        href = next((h for title, h in tocFlat if title == chapter), None)
        if href is None:
            return None
        item = book.get_item_with_href(href.split('#')[0])  # strip in-page anchor
        if item is None:
            return None

    tree = html.fromstring(item.get_content())
    return tree.text_content().strip()

#gets the internal epub path to the cover/front-page image, for fast retrieval later
def getCoverImagePath(book):
    # EPUB3: manifest item marked properties="cover-image"
    cover_item = next(iter(book.get_items_of_type(ebooklib.ITEM_COVER)), None)
    if cover_item:
        return cover_item.get_name()

    # EPUB2: <meta name="cover" content="item-id"/> pointing at a manifest item
    for value, others in book.get_metadata('OPF', 'cover'):
        cover_id = others.get('content')
        if cover_id:
            item = book.get_item_with_id(cover_id)
            if item:
                return item.get_name()

    # fallback: any image whose id/filename hints "cover"
    for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
        if 'cover' in item.get_id().lower() or 'cover' in item.get_name().lower():
            return item.get_name()

    return None

#gets the cover image from the epub, and saves it as an actual usable image next to the book file
#outputs the path to that image
def save_cover_image(book, bookFolder):
    """Extract the cover image from an epub and save it to disk. Returns the saved path."""
    cover_href = getCoverImagePath(book)
    if cover_href is None:
        return None
    ext = os.path.splitext(cover_href)[1]
    output_path = os.path.join(bookFolder, f"cover{ext}")
    item = book.get_item_with_href(cover_href)
    if item is None:
        return None

    with open(output_path, "wb") as f:
        f.write(item.get_content())

    return output_path

#retrieves the actual image item given the path returned by getCoverImagePath
def getCoverImage(book, path):
    return book.get_item_with_href(path)
