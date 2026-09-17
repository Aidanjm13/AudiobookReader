
from collections import deque
 
from PySide6.QtCore import QIODevice, Signal

SAMPLE_RATE = 48000          # match your real TTS engine's output
BYTES_PER_SAMPLE = 2          # 16-bit PCM
LOW_WATER_SECONDS = 0.4       # start fetching more when < this much audio remains

class StreamingAudioBuffer(QIODevice):
    clip_started = Signal(str, object)    # clip_id, sentence_id
    clip_finished = Signal(str, object)   # clip_id, sentence_id
    page_finished = Signal(int)           # page_index
    buffer_low = Signal()
 
    def __init__(self, sample_rate: int = 48000, channels: int = 2):
        super().__init__()
        self._buffer = bytearray()
        self._clip_markers = deque()
        self._current_clip_id = None
        
        self.sample_rate = sample_rate
        self.channels = channels
        self.bytes_per_sample = 2  # 16-bit PCM = 2 bytes
        self.low_water_seconds = 0.4
        
        self._update_thresholds()

    def set_audio_format(self, sample_rate: int, channels: int):
        self.sample_rate = sample_rate
        self.channels = channels
        self._update_thresholds()

    def _update_thresholds(self):
        self.low_water_bytes = int(
            self.sample_rate * self.channels * self.bytes_per_sample * self.low_water_seconds
        )
 
    def feed(self, clip_id: str, pcm_bytes: bytes, sentence_id, page: int,
              is_last_of_page: bool = False):
        """Call this whenever a new chunk of TTS audio is ready."""
        self._buffer.extend(pcm_bytes)
        self._clip_markers.append([clip_id, len(pcm_bytes), sentence_id, page, is_last_of_page])
        self.readyRead.emit()
 
    def clear(self):
        self._buffer.clear()
        self._clip_markers.clear()
        self._current_clip_id = None
 
    # --- QIODevice overrides ---
    def readData(self, maxlen: int) -> bytes:
        if not self._buffer:
            self.buffer_low.emit()
            return b""
 
        chunk = bytes(self._buffer[:maxlen])
        del self._buffer[:maxlen]

        # Log read activity
        print(f"[Buffer] Sink requested {maxlen} bytes, returning {len(chunk)} bytes. Remaining: {len(self._buffer)}")
 
        # Announce the clip we just started sounding, if we haven't yet.
        if self._current_clip_id is None and self._clip_markers:
            clip_id, _, sentence_id, _page, _last = self._clip_markers[0]
            self._current_clip_id = clip_id
            self.clip_started.emit(clip_id, sentence_id)
 
        self._advance_markers(len(chunk))
 
        if len(self._buffer) < self.low_water_bytes:
            self.buffer_low.emit()
 
        return chunk
 
    def writeData(self, data):
        return -1  # read-only from Qt's perspective
 
    def bytesAvailable(self) -> int:
        return len(self._buffer) + super().bytesAvailable()
 
    def isSequential(self) -> bool:
        return True
 
    # --- internal bookkeeping ---
    def _advance_markers(self, n_bytes: int):
        while n_bytes > 0 and self._clip_markers:
            clip_id, remaining, sentence_id, page, is_last_of_page = self._clip_markers[0]
            if n_bytes < remaining:
                self._clip_markers[0][1] -= n_bytes
                n_bytes = 0
            else:
                n_bytes -= remaining
                self._clip_markers.popleft()
                self._current_clip_id = None  # next readData() announces the next clip
                self.clip_finished.emit(clip_id, sentence_id)
                if is_last_of_page:
                    self.page_finished.emit(page)