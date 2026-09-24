from dataclasses import dataclass, field
from typing import List
 
import pysbd
 
#takes the text and splits it into sentences using pysbd
_segmenter = pysbd.Segmenter(language="en", clean=False)
def split_sentences(text: str, language: str = "en") -> List[str]:
    text = text.strip()
    if not text:
        return []
 
    segmenter = _segmenter if language == "en" else pysbd.Segmenter(
        language=language, clean=False
    )
    sentences = [s.strip() for s in segmenter.segment(text)]
    return [s for s in sentences if s]