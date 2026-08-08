from fileHandling import getAppdataFolderPath
import ebooklib
from ebooklib import epub
from lxml import html
import tinycss2
import os
import copy
import posixpath
from urllib.parse import unquote

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
def flattenToc(tocEntries):
    flat = []
    for entry in tocEntries:
        if isinstance(entry, tuple):
            section, children = entry
            flat.append((section.title, getattr(section, 'href', None)))
            flat.extend(flattenToc(children))
        else:
            flat.append((entry.title, entry.href))
    return flat

#internal helper: returns chapter document items in spine (reading) order, skipping nav pages
def getSpineDocuments(book):
    idToItem = {item.get_id(): item for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT)}
    ordered = []
    for spineId, _linear in book.spine:
        item = idToItem.get(spineId)
        if item is not None and not isinstance(item, epub.EpubNav):
            ordered.append(item)
    return ordered

def _normalizeHref(href):
    return unquote(posixpath.basename(href.split('#')[0]))

# Returns a list the same length as getSpineDocuments(book) -- one entry
# per spine document, in reading order. Entry is the chapter title if the
# TOC names that document, else None. Use this to build your clickable
# chapter list (filter out the Nones); use plain spine index for playback
# order regardless of title.
def getSectionTitles(book):
    documents = getSpineDocuments(book)
    titleByHref = {}
    if book.toc:
        for title, href in flattenToc(book.toc):
            if not title:
                continue
            key = _normalizeHref(href)
            titleByHref.setdefault(key, title)
    return [titleByHref.get(_normalizeHref(item.get_name())) for item in documents]

# Parses every CSS stylesheet in the EPUB into a {class_name: alignment}
# map. Best-effort: only looks at simple class selectors (".foo", "p.foo")
# and the text-align property -- not a full CSS cascade, but covers how
# alignment is set in the vast majority of real EPUBs.
def getAlignmentMap(book):
    import ebooklib
    alignMap = {}
    for item in book.get_items_of_type(ebooklib.ITEM_STYLE):
        css = item.get_content().decode('utf-8', errors='ignore')
        rules = tinycss2.parse_stylesheet(css, skip_whitespace=True, skip_comments=True)
        for rule in rules:
            if rule.type != 'qualified-rule':
                continue
            prelude = tinycss2.serialize(rule.prelude)
            declarations = tinycss2.parse_declaration_list(rule.content)
            align = None
            for decl in declarations:
                if decl.type == 'declaration' and decl.lower_name == 'text-align':
                    align = tinycss2.serialize(decl.value).strip()
            if not align:
                continue
            for cls in prelude.split(','):
                cls = cls.strip()
                if '.' in cls:
                    className = cls.split('.')[-1].split(':')[0].strip()
                    if className:
                        alignMap[className] = align
    return alignMap

_BLOCK_TAGS = {'p', 'div', 'li', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
_IMAGE_TAGS = {'img', 'image'}

# Splits a single block element's text on <br/><br/> (a real paragraph
# break in poorly-structured EPUBs that skip <p> tags) vs. lone <br/>
# (a soft line break -- poetry, addresses -- which collapses to a space).
# lxml's text_content() silently drops <br/> entirely otherwise, gluing
# separate paragraphs into one run-on string.
def _blockToParagraphs(el):
    el = copy.deepcopy(el)
    for br in el.iter('br'):
        br.tail = '\n' + (br.tail or '')
    raw = el.text_content()
    chunks = [c.strip() for c in raw.split('\n\n')]
    paragraphs = []
    for chunk in chunks:
        text = ' '.join(chunk.split())
        if text:
            paragraphs.append(text)
    return paragraphs

# Plain <img src=...> uses `src`; SVG-wrapped covers use
# <image xlink:href=...> (sometimes just `href`) instead -- lxml's HTML
# parser reports these as literal attribute names, not namespaced.
def _getImageSrc(el):
    return el.get('src') or el.get('xlink:href') or el.get('href')

def _resolveHref(chapterItem, relSrc):
    chapterDir = posixpath.dirname(chapterItem.get_name())
    return posixpath.normpath(posixpath.join(chapterDir, relSrc))

# Fetches the actual image bytes for a path returned in an image block's
# 'path' field. Call this lazily, only when you're about to display
# that specific image, not up front for every block.
def getImageData(book, path):
    item = book.get_item_with_href(path)
    if item is None:
        return None
    return item.get_content(), item.media_type

# Same lookup semantics as getChapterContent (int index or TOC title).
# Returns ordered blocks: text ({'type':'text','tag':,'text':,'align':})
# and images ({'type':'image','data':bytes,'mime':str,'alt':str}),
# interleaved exactly as they appear in the source markup.
def getChapterBlocks(book, chapter, alignMap=None):
    if alignMap is None:
        alignMap = getAlignmentMap(book)

    documents = getSpineDocuments(book)
    if isinstance(chapter, int):
        if chapter < 0 or chapter >= len(documents):
            return None
        item = documents[chapter]
    else:
        tocFlat = flattenToc(book.toc) if book.toc else []
        href = next((h for title, h in tocFlat if title == chapter), None)
        if href is None:
            return None
        item = book.get_item_with_href(href.split('#')[0])
        if item is None:
            return None

    tree = html.fromstring(item.get_content())
    blocks = []
    for el in tree.iter():
        if el.tag in _IMAGE_TAGS:
            src = _getImageSrc(el)
            if not src:
                continue
            path = _resolveHref(item, src)
            if book.get_item_with_href(path) is not None:  # confirm it actually exists
                blocks.append({'type': 'image', 'path': path, 'alt': el.get('alt', '')})
            continue

        if el.tag not in _BLOCK_TAGS:
            continue
        if any(a.tag in _BLOCK_TAGS for a in el.iterancestors()):
            continue

        align = None
        style = el.get('style') or ''
        if 'text-align' in style:
            for part in style.split(';'):
                if 'text-align' in part:
                    align = part.split(':')[1].strip()
        if align is None:
            for cls in (el.get('class') or '').split():
                if cls in alignMap:
                    align = alignMap[cls]
                    break

        for text in _blockToParagraphs(el):
            blocks.append({'type': 'text', 'tag': el.tag, 'text': text, 'align': align})

    return blocks

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
