from fileHandling import getAppdataFolderPath
import ebooklib
from ebooklib import epub
from lxml import html
import tinycss2
from cssselect import GenericTranslator
import os
import copy
import posixpath
from urllib.parse import unquote
import pysbd
from PySide6.QtWidgets import QTextEdit
from PySide6.QtGui import QTextCursor, QTextBlockFormat, QTextDocument, QImage
from PySide6.QtCore import Qt, QUrl, QSize
from dataclasses import dataclass



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
#ebooklib represents a nested TOC entry as a (Section, [children]) tuple, and a
#leaf entry as a plain Link/Section object with .title/.href. This walks the
#tree recursively (depth-first), adding a Section's own title/href before
#descending into its children, so the result preserves reading order.
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
#the EPUB manifest lists every document item, but book.spine gives the actual
#playback order as a list of (item_id, linear_flag) pairs. This looks each id
#up in the manifest, drops the generated navigation document (EpubNav, e.g.
#the TOC page itself), and returns just the ordered chapter/document items.
def getSpineDocuments(book):
    idToItem = {item.get_id(): item for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT)}
    ordered = []
    for spineId, _linear in book.spine:
        item = idToItem.get(spineId)
        if item is not None and not isinstance(item, epub.EpubNav):
            ordered.append(item)
    return ordered

#internal helper: reduces an href (which may include a directory path and/or
#a '#fragment' anchor, and may be URL-encoded) down to just its plain,
#decoded filename. Used so TOC hrefs and spine-document names can be matched
#against each other even when they're written slightly differently.
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
        for title, href in _flattenToc(book.toc):
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
    """Returns a dict keyed by id(element) -> alignment string, resolved
    via real CSS selector matching (tag, class, descendant selectors --
    not just simple class-name lookup). Must be called once per chapter
    tree (the SAME tree object used later for extraction), since the
    id()-based keys only stay valid as long as those exact element
    objects remain alive -- see _keepAlive below."""
    import ebooklib
    translator = GenericTranslator()
    rules = []
    for item in book.get_items_of_type(ebooklib.ITEM_STYLE):
        css = item.get_content().decode('utf-8', errors='ignore')
        for rule in tinycss2.parse_stylesheet(css, skip_whitespace=True, skip_comments=True):
            if rule.type != 'qualified-rule':
                continue
            selector = tinycss2.serialize(rule.prelude).strip()
            align = None
            for decl in tinycss2.parse_declaration_list(rule.content):
                if decl.type == 'declaration' and decl.lower_name == 'text-align':
                    align = tinycss2.serialize(decl.value).strip()
            if align:
                rules.append((selector, align))
    return rules  # compiled selectors resolved per-chapter-tree, see below

def resolveAlignmentForTree(tree, rules):
    """Applies the parsed (selector, align) rules against ONE specific
    chapter's tree, returning {id(element): align}. Call this once per
    chapter, right after parsing that chapter's tree -- and keep the
    returned _keepAlive list alive alongside the dict for as long as
    you're using it, or id() collisions can silently corrupt results."""
    translator = GenericTranslator()
    elementAlign = {}
    keepAlive = []
    for selector, align in rules:
        try:
            xpath = translator.css_to_xpath(selector)
        except Exception:
            continue  # unsupported selector syntax -- skip rather than crash
        matched = tree.xpath(xpath)
        keepAlive.extend(matched)
        for el in matched:
            elementAlign[id(el)] = align
    return elementAlign, keepAlive

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

#internal helper: image `src`/`href` attributes in a chapter's HTML are
#relative to that chapter's own location inside the EPUB, not the EPUB root.
#This joins the relative path onto the chapter's directory and normalizes
#away any '..' segments, producing the absolute-within-the-EPUB path needed
#to look the image item up via book.get_item_with_href().
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
        tocFlat = _flattenToc(book.toc) if book.toc else []
        href = next((h for title, h in tocFlat if title == chapter), None)
        if href is None:
            return None
        item = book.get_item_with_href(href.split('#')[0])
        if item is None:
            return None

    # parse the chapter's raw (X)HTML into a walkable element tree
    tree = html.fromstring(item.get_content())
    blocks = []
    # walk every element in document order (tree.iter() is depth-first)
    for el in tree.iter():
        if el.tag in _IMAGE_TAGS:
            # handle <img>/<image> elements: resolve their src to an absolute
            # in-EPUB path and record an image block if that path really
            # exists in the manifest
            src = _getImageSrc(el)
            if not src:
                continue
            path = _resolveHref(item, src)
            if book.get_item_with_href(path) is not None:  # confirm it actually exists
                blocks.append({'type': 'image', 'path': path, 'alt': el.get('alt', '')})
            continue

        if el.tag not in _BLOCK_TAGS:
            # skip inline elements (span, a, em, etc.) -- their text is
            # picked up later via text_content() on their containing block
            continue
        if any(a.tag in _BLOCK_TAGS for a in el.iterancestors()):
            # skip block elements nested inside another block element (e.g. a
            # <p> inside a <div>) so we don't emit the same text twice --
            # only the outermost block in a nesting chain is processed
            continue

        # determine text alignment: an inline style="text-align:..." wins,
        # otherwise fall back to whatever the element's CSS class resolves to
        # via the alignMap built by getAlignmentMap()
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

        # split this block's text on real paragraph breaks (see
        # _blockToParagraphs) and emit one text block per resulting paragraph
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

_segmenter = pysbd.Segmenter(language='en', clean=False)

_ALIGN_MAP = {
    'left': Qt.AlignLeft,
    'center': Qt.AlignHCenter,
    'right': Qt.AlignRight,
    'justify': Qt.AlignJustify,
    None: Qt.AlignLeft,
}

#splits block of text into sentences using pysbd library
def split_sentences(text, language="en"):
    text = text.strip()
    if not text:
        return []
    segmenter = _segmenter if language == "en" else pysbd.Segmenter(language=language, clean=False)
    return [s.strip() for s in segmenter.segment(text) if s.strip()]

#goes through a chapters html tree and returns list of dictionaries as {'type': 'text', text, align} or {'type': 'image', path, alt}
#this is a generator ("lazy") twin of getChapterBlocks() above: identical
#parsing/alignment logic, but it yields each block as it's found instead of
#building a full list, so pagination (which may stop partway through a
#chapter) doesn't have to parse blocks it will never use.
def getChapterBlocksIter(book, chapter, alignMap=None):
    if alignMap is None:
        alignMap = getAlignmentMap(book)

    documents = getSpineDocuments(book)
    if isinstance(chapter, int): #gets chapter by number
        if chapter < 0 or chapter >= len(documents):
            return
        item = documents[chapter]
    else: #gets chapter by title
        tocFlat = _flattenToc(book.toc) if book.toc else []
        href = next((h for title, h in tocFlat if title == chapter), None)
        if href is None:
            return
        item = book.get_item_with_href(href.split('#')[0])
        if item is None:
            return

    tree = html.fromstring(item.get_content())
    for el in tree.iter():
        if el.tag in _IMAGE_TAGS:
            src = _getImageSrc(el)
            if not src:
                continue
            path = _resolveHref(item, src)
            if book.get_item_with_href(path) is not None:
                yield {'type': 'image', 'path': path, 'alt': el.get('alt', '')}
            continue

        #prevents duplicate text due to nested elements
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
            yield {'type': 'text', 'tag': el.tag, 'text': text, 'align': align}

#takes the blocks from chapterBlocks and turns it into sentences each
def blocksToItemsIter(blocksIter):
    for block in blocksIter:
        if block['type'] == 'image':
            yield {'type': 'image', 'path': block['path'], 'alt': block.get('alt', ''),
                   'align': block.get('align', 'center'), 'newParagraph': True}
            continue
        for i, s in enumerate(split_sentences(block['text'])):
            yield {'type': 'text', 'text': s, 'align': block['align'], 'newParagraph': (i == 0)}

#if a single sentence cant fit on a page this handles the case and splits it mid sentence
#Called only when a whole sentence overflowed the page on its own. Adds the
#sentence's words back into the document one at a time (word-by-word, so
#the split lands on a word boundary rather than mid-word), stopping as soon
#as the accumulated text overflows pageHeight again. When that happens, the
#last (overflowing) word is deleted back out of the document via
#deletePreviousChar(), leaving only the words that actually fit.
#Returns (fitCount, fittedText): how many words fit, and the joined text
#of just those words -- the remainder is left for the next page.
def _fitWordBoundary(doc, cursor, pageHeight, text):
    words = text.split(' ')
    fitCount = 0
    acc = ''  # text inserted into the document so far
    for n in range(1, len(words) + 1):
        trial = ' '.join(words[:n])
        cursor.insertText(trial[len(acc):])  # only insert the newly-added word(s)
        acc = trial
        if doc.size().height() > pageHeight:
            # this word pushed us over the page height -- remove just it
            cursor.movePosition(QTextCursor.End)
            for _ in range(len(trial) - len(' '.join(words[:n - 1]))):
                cursor.deletePreviousChar()
            fitCount = n - 1
            break
        fitCount = n
    else:
        # loop completed without breaking -- every word fit
        fitCount = len(words)
    return fitCount, ' '.join(words[:fitCount])

#takes items from the getChapterBlocks generators and attempts to fit them on the page to determine where the page boundaries are
#
#This is the core pagination primitive: it renders sentence/image items one
#at a time into textEdit's QTextDocument, checking the rendered height after
#each insertion, until adding the next item would overflow the page
#(pageHeight, the viewport's current height). It both PRODUCES the visible
#page (as a side effect of inserting into doc/cursor) and RETURNS bookkeeping
#about where the page ended, so callers can figure out where the next page
#should start.
#
#Params:
#  itemsIter    - iterator of remaining sentence/image dicts (from
#                 blocksToItemsIter) for this chapter
#  pendingItem  - if not None, a single item that should be inserted first
#                 (used when resuming a chapter mid-sentence -- see
#                 pendingOffset below), before pulling anything from itemsIter
#  pendingOffset- character offset into pendingItem['text'] to start from
#                 (lets a sentence that was split across two pages resume
#                 partway through, instead of being duplicated in full)
#
#Returns a 3-tuple:
#  (overflowItem, nextOffset, placed)
#    overflowItem - the item that didn't fit and starts the NEXT page, or
#                    None if every remaining item fit on this page (i.e. this
#                    was the chapter's last page)
#    nextOffset   - 0 normally; if overflowItem is a sentence that was split
#                    mid-sentence (see _fitWordBoundary), the character
#                    offset within it where the next page should resume
#    placed       - list of the items that were fully placed on this page,
#                    in order (used by callers to count how far pagination
#                    advanced)
def fillPageAndCapture(book, textEdit, itemsIter, pendingItem, pendingOffset, getImageDataFn):
    doc = textEdit.document()
    doc.clear()
    doc.setTextWidth(textEdit.viewport().width())
    pageHeight = textEdit.viewport().height()
    cursor = QTextCursor(doc)
    cursor.movePosition(QTextCursor.Start)

    firstInsert = True
    placed = []

    # yields pendingItem first (if any) on the very first call, then falls
    # through to pulling fresh items from itemsIter for everything after
    def nextItem():
        if pendingItem is not None and firstInsert:
            return pendingItem
        return next(itemsIter, None)

    item = nextItem()
    while item is not None:
        # only the very first item (which may be a resumed/split sentence)
        # uses pendingOffset; every later item starts at its own beginning
        offset = pendingOffset if firstInsert else 0
        posBefore = cursor.position()  # remember where to roll back to if this item overflows

        blockFmt = QTextBlockFormat()
        blockFmt.setAlignment(_ALIGN_MAP.get(item.get('align'), Qt.AlignLeft))

        #POTENTIAL FIX MAKE IT SCALE BASED ON FONT SIZE
        PARAGRAPH_SPACING = 12  # pixels — tune to taste

        if item['newParagraph'] and not firstInsert:
            # start a new paragraph/block for items marked as beginning one
            # (the first sentence of a source paragraph, or an image)
            blockFmt.setTopMargin(PARAGRAPH_SPACING)
            cursor.insertBlock(blockFmt)
        elif firstInsert:
            # apply alignment to the page's very first block without
            # inserting an extra empty block above it
            cursor.setBlockFormat(blockFmt)

        if item['type'] == 'image':
            # fetch and scale the image to fit within the remaining page
            # area (minus document margins), preserving aspect ratio, then
            # embed it into the QTextDocument as an inline resource
            data, mime = getImageDataFn(book, item['path'])
            image = QImage.fromData(data)
            if not image.isNull():
                margin = doc.documentMargin() * 2
                maxWidth = max(textEdit.viewport().width() - margin, 1)
                maxHeight = max(pageHeight - margin, 1)
                if image.width() > maxWidth or image.height() > maxHeight:
                    image = image.scaled(QSize(int(maxWidth), int(maxHeight)),
                                          Qt.KeepAspectRatio, Qt.SmoothTransformation)
                url = QUrl(item['path'])
                doc.addResource(QTextDocument.ImageResource, url, image)
                cursor.insertImage(url.toString())
        else:
            remaining = item['text'][offset:]
            cursor.insertText(remaining + ' ')

        if doc.size().height() > pageHeight:
            # this item pushed the page over its height limit -- undo it by
            # deleting everything from just before this item to the end
            cursor.setPosition(posBefore)
            cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()

            if item['type'] == 'text' and firstInsert:
                # special case: this is the very first item on an otherwise-
                # empty page and even it alone doesn't fit. Rather than
                # produce a blank page, force at least part of the sentence
                # onto it by splitting on a word boundary (or, failing that,
                # forcing in just the first word so progress is guaranteed).
                remaining = item['text'][offset:]
                fitCount, fittedText = _fitWordBoundary(doc, cursor, pageHeight, remaining)
                if fitCount == 0:
                    firstWord = remaining.split(' ', 1)[0]
                    cursor.insertText(firstWord)
                    fittedText = firstWord
                nextOffset = offset + len(fittedText)
                # skip past any space(s) so the next page doesn't start with
                # leading whitespace
                while nextOffset < len(item['text']) and item['text'][nextOffset] == ' ':
                    nextOffset += 1
                placed.append({**item, 'text': fittedText})
                return item, nextOffset, placed

            # normal case: this item didn't fit at all -- it becomes the
            # first item of the next page, starting from its own beginning
            return item, 0, placed

        # item fit fully -- keep it and move on to the next one
        placed.append(item)
        firstInsert = False
        item = nextItem()

    # ran out of items entirely -- everything fit, this is the chapter's last page
    return None, 0, placed

#a single, addressable location within the book: which chapter (spine
#index), which sentence/image item within that chapter's flattened item
#list (see blocksToItemsIter), and optionally a character offset into that
#item's text (used when a sentence is split across two pages). This is the
#unit used throughout the module to mark "the top of the current page",
#"where the user last left off", pagination boundaries, etc.
@dataclass
class ReadingPosition:
    chapter: int
    itemIndex: int
    charOffset: int = 0

#internal: paginates an already-extracted list of `items` forward starting at
#(startItemIndex, startCharOffset), returning page-start positions. The first
#entry is always (chapter, startItemIndex, startCharOffset). This is the core
#forward-fill loop shared by buildPageIndex, whether starting at the top of
#the chapter or at some arbitrary anchor sentence.
def _paginateFrom(book, textEdit, chapter, getImageDataFn, items, startItemIndex, startCharOffset):
    positions = [ReadingPosition(chapter, startItemIndex, startCharOffset)]

    if startCharOffset > 0:
        pendingItem = items[startItemIndex]
        pendingOffset = startCharOffset
        itemsIter = iter(items[startItemIndex + 1:])
    else:
        pendingItem = None
        pendingOffset = 0
        itemsIter = iter(items[startItemIndex:])

    itemsConsumedSoFar = startItemIndex
    pageItems = []

    while True:
        nextPendingItem, nextPendingOffset, placed = fillPageAndCapture(
            book, textEdit, itemsIter, pendingItem, pendingOffset, getImageDataFn)
        pageItems.append(placed)
        if nextPendingItem is not None:
            if nextPendingOffset > 0:
                nextItemIndex = itemsConsumedSoFar + len(placed) - 1
            else:
                nextItemIndex = itemsConsumedSoFar + len(placed)
            positions.append(ReadingPosition(chapter, nextItemIndex, nextPendingOffset))
            itemsConsumedSoFar = nextItemIndex
            pendingItem, pendingOffset = nextPendingItem, nextPendingOffset
        else:
            break

    return pageItems

#internal: paginates items[:stopItemIndex] (plus a truncated copy of
#items[stopItemIndex] cut off at stopCharOffset, if the anchor lands
#mid-sentence) forward from the start of the chapter. Used to fill in the
#pages that come BEFORE a pinned anchor point without letting any of them
#run past it. The last page produced here may end up shorter than a full
#page -- it can't borrow content from the anchor's page, since the anchor
#must stay fixed at the top of its page.
def _paginateUpTo(book, textEdit, chapter, getImageDataFn, items, stopItemIndex, stopCharOffset):
    boundedItems = items[:stopItemIndex]
    if stopCharOffset > 0 and stopItemIndex < len(items) and items[stopItemIndex]['type'] == 'text':
        partial = dict(items[stopItemIndex])
        partial['text'] = partial['text'][:stopCharOffset]
        if partial['text'].strip():
            boundedItems = boundedItems + [partial]

    if not boundedItems:
        return []

    return _paginateFrom(book, textEdit, chapter, getImageDataFn, boundedItems, 0, 0)

#builds the full forward page index for a chapter.
#
#If `anchor` is given (a ReadingPosition within this chapter), pagination is
#pinned so that a page boundary lands exactly at the anchor -- this is what
#you want after a font-size change, so the sentence currently at the top of
#the page stays at the top of the page instead of drifting. Pages after the
#anchor are paginated forward starting at the anchor; pages before it are
#paginated forward from the start of the chapter but truncated so they never
#cross the anchor (see _paginateUpTo).
#
#Without an anchor, this just paginates the whole chapter from the start,
#same as before.
def buildPageIndex(book, textEdit, chapter, anchor=None):
    getImageDataFn=getImageData
    items = list(blocksToItemsIter(getChapterBlocksIter(book, chapter)))

    if not items:
        return [ReadingPosition(chapter, 0, 0)]

    if anchor is None or (anchor.itemIndex == 0 and anchor.charOffset == 0):
        return _paginateFrom(book, textEdit, chapter, getImageDataFn, items, 0, 0)

    beforePages = _paginateUpTo(book, textEdit, chapter, getImageDataFn, items,
                                 anchor.itemIndex, anchor.charOffset)
    afterPages = _paginateFrom(book, textEdit, chapter, getImageDataFn, items,
                                anchor.itemIndex, anchor.charOffset)
    return beforePages.extend(afterPages)

def findPageForPosition(pageIndex, savedPosition):
    """Given a rebuilt pageIndex (after a font/size change) and a saved
    ReadingPosition, finds which page NOW contains that sentence."""
    bestPage = 0
    # pageIndex entries are in order, each marking where a page STARTS.
    # keep advancing bestPage as long as a page's start is still at or
    # before the saved sentence; the first page whose start goes past it
    # means the previous bestPage is the one that contains it.
    for i, pos in enumerate(pageIndex):
        if pos.chapter != savedPosition.chapter:
            continue
        if pos.itemIndex <= savedPosition.itemIndex:
            bestPage = i
        else:
            break
    return bestPage


#renders the current page in the text edit
#Given a ReadingPosition marking the top of a page, re-derives that page's
#content and draws it into textEdit by walking the chapter's items from the
#start, skipping past everything before position.itemIndex, then filling the
#page from there with fillPageAndCapture(). Also computes and returns the
#ReadingPosition of the page that would come AFTER this one (or None if this
#is the chapter's last page) -- this is used by buildPageIndex to advance
#page-by-page through a chapter without keeping the whole item list in memory.
def renderPageFrom(book, textEdit, position, getImageDataFn):
    itemsIter = blocksToItemsIter(getChapterBlocksIter(book, position.chapter))
    # advance past all items before this page's starting item
    for _ in range(position.itemIndex):
        if next(itemsIter, None) is None:
            return None

    if position.charOffset > 0:
        # the page starts mid-sentence -- pull that sentence out as the
        # "pending" item so fillPageAndCapture resumes it at charOffset
        # instead of re-rendering it from the beginning
        pendingItem = next(itemsIter, None)
        pendingOffset = position.charOffset
    else:
        pendingItem = None
        pendingOffset = 0

    nextPendingItem, nextPendingOffset, placed = fillPageAndCapture(
        book, textEdit, itemsIter, pendingItem, pendingOffset, getImageDataFn)

    consumedThisPage = len(placed)

    if nextPendingItem is not None:
        # more content remains -- report where the following page would begin
        nextItemIndex = position.itemIndex + consumedThisPage - 1
        return ReadingPosition(position.chapter, nextItemIndex, nextPendingOffset)

    # nothing left in this chapter after this page
    return None

#renders a fixed list of items into textEdit, one after another, with the
#same paragraph/alignment/image handling as fillPageAndCapture -- but with
#no pagination bookkeeping: it doesn't check page height, doesn't split
#items that overflow, and doesn't report where a "next page" would start.
#Use this when you already know exactly which items belong in the text area
#(e.g. re-rendering a page whose contents were already determined) and just
#need them drawn in, rather than being figured out on the fly.
#
#Params:
#  items - a list (not iterator) of every sentence/image dict that should be
#          placed into textEdit, in order
#
#Returns nothing; all work happens as a side effect of inserting into
#doc/cursor, same as fillPageAndCapture.
def renderItemsIntoTextEdit(book, textEdit, items, getImageDataFn=getImageData):
    doc = textEdit.document()
    doc.clear()
    doc.setTextWidth(textEdit.viewport().width())
    pageHeight = textEdit.viewport().height()
    cursor = QTextCursor(doc)
    cursor.movePosition(QTextCursor.Start)

    firstInsert = True

    for item in items:
        blockFmt = QTextBlockFormat()
        blockFmt.setAlignment(_ALIGN_MAP.get(item.get('align'), Qt.AlignLeft))

        #POTENTIAL FIX MAKE IT SCALE BASED ON FONT SIZE
        PARAGRAPH_SPACING = 12  # pixels — tune to taste

        if item['newParagraph'] and not firstInsert:
            # start a new paragraph/block for items marked as beginning one
            # (the first sentence of a source paragraph, or an image)
            blockFmt.setTopMargin(PARAGRAPH_SPACING)
            cursor.insertBlock(blockFmt)
        elif firstInsert:
            # apply alignment to the very first block without inserting an
            # extra empty block above it
            cursor.setBlockFormat(blockFmt)

        if item['type'] == 'image':
            # fetch and scale the image to fit within the text area (minus
            # document margins), preserving aspect ratio, then embed it into
            # the QTextDocument as an inline resource
            data, mime = getImageDataFn(book, item['path'])
            image = QImage.fromData(data)
            if not image.isNull():
                margin = doc.documentMargin() * 2
                maxWidth = max(textEdit.viewport().width() - margin, 1)
                maxHeight = max(pageHeight - margin, 1)
                if image.width() > maxWidth or image.height() > maxHeight:
                    image = image.scaled(QSize(int(maxWidth), int(maxHeight)),
                                          Qt.KeepAspectRatio, Qt.SmoothTransformation)
                url = QUrl(item['path'])
                doc.addResource(QTextDocument.ImageResource, url, image)
                cursor.insertImage(url.toString())
        else:
            cursor.insertText(item['text'] + ' ')

        firstInsert = False