import pysbd
from PySide6.QtWidgets import QTextEdit
from PySide6.QtGui import QTextCursor, QTextBlockFormat, QTextDocument, QImage
from PySide6.QtCore import Qt, QUrl, QSize

_segmenter = pysbd.Segmenter(language='en', clean=False)

_ALIGN_MAP = {
    'left': Qt.AlignLeft,
    'center': Qt.AlignHCenter,
    'right': Qt.AlignRight,
    'justify': Qt.AlignJustify,
    None: Qt.AlignLeft,
}

def split_sentences(text, language="en"):
    text = text.strip()
    if not text:
        return []
    segmenter = _segmenter if language == "en" else pysbd.Segmenter(language=language, clean=False)
    return [s.strip() for s in segmenter.segment(text) if s.strip()]

# Flattens blocks (from getChapterBlocks) into a flat list of items ready
# for fillTextEdit. Text blocks get split into sentences (so overflow can
# stop mid-paragraph); image blocks pass through as a single item.
def blocksToItems(blocks):
    items = []
    for block in blocks:
        if block['type'] == 'image':
            items.append({
                'type': 'image', 'path': block['path'], 'alt': block.get('alt', ''),
                'align': block.get('align', 'center'), 'newParagraph': True,
            })
            continue
        for i, s in enumerate(split_sentences(block['text'])):
            items.append({
                'type': 'text', 'text': s, 'align': block['align'], 'newParagraph': (i == 0),
            })
    return items


def _fitWordBoundary(doc, cursor, pageHeight, text):
    words = text.split(' ')
    fitCount = 0
    acc = ''
    for n in range(1, len(words) + 1):
        trial = ' '.join(words[:n])
        cursor.insertText(trial[len(acc):])
        acc = trial
        if doc.size().height() > pageHeight:
            cursor.movePosition(QTextCursor.End)
            for _ in range(len(trial) - len(' '.join(words[:n-1]))):
                cursor.deletePreviousChar()
            fitCount = n - 1
            break
        fitCount = n
    else:
        fitCount = len(words)
    return fitCount, ' '.join(words[:fitCount])

# Fills `textEdit` with as many `items` as fit without overflowing its
# viewport, inserting images inline. `getImageData(book, path)` is called
# lazily -- only right when an image is actually about to be inserted.
# Returns the index of the first item that didn't fit (None = last page).
def fillTextEdit(book, textEdit, items, startIndex=0, startCharOffset=0, getImageData=None):
    doc = textEdit.document()
    doc.clear()
    doc.setTextWidth(textEdit.viewport().width())
    pageHeight = textEdit.viewport().height()

    cursor = QTextCursor(doc)
    cursor.movePosition(QTextCursor.Start)

    for i in range(startIndex, len(items)):
        item = items[i]
        offset = startCharOffset if i == startIndex else 0
        posBefore = cursor.position()
        firstInsert = (i == startIndex)

        blockFmt = QTextBlockFormat()
        blockFmt.setAlignment(_ALIGN_MAP.get(item.get('align'), Qt.AlignLeft))

        if item['newParagraph'] and not firstInsert:
            cursor.insertBlock(blockFmt)
        elif firstInsert:
            cursor.setBlockFormat(blockFmt)

        if item['type'] == 'image':
            data, mime = getImageData(book, item['path'])
            image = QImage.fromData(data)
            if image.isNull():
                continue
            maxWidth = textEdit.viewport().width()
            margin = doc.documentMargin() * 2
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
            cursor.setPosition(posBefore)
            cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()

            if item['type'] == 'text' and firstInsert:
                remaining = item['text'][offset:]
                fitCount, fittedText = _fitWordBoundary(doc, cursor, pageHeight, remaining)
                if fitCount == 0:
                    firstWord = remaining.split(' ', 1)[0]
                    cursor.insertText(firstWord)
                    fittedText = firstWord
                nextOffset = offset + len(fittedText)
                while nextOffset < len(item['text']) and item['text'][nextOffset] == ' ':
                    nextOffset += 1
                return i, nextOffset

            return i, 0

    return None, 0

def rebuildPageStarts(book, textEdit, items, getImageData, fromIndex=0, fromOffset=0):
    pageStarts = [(fromIndex, fromOffset)]
    idx, offset = fromIndex, fromOffset
    while True:
        idx, offset = fillTextEdit(book, textEdit, items, startIndex=idx, startCharOffset=offset, getImageData=getImageData)
        if idx is None:
            break
        pageStarts.append((idx, offset))
    return pageStarts