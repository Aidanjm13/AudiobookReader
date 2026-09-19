from collections import deque
from PySide6.QtCore import QIODevice, Signal

SAMPLE_RATE = 48000
BYTES_PER_SAMPLE = 2

class StreamingAudioBuffer(QIODevice):
    clip_started = Signal(str, object)    # clip_id, item_index
    clip_finished = Signal(str, object)   # clip_id, item_index
    page_finished = Signal(int)           # page_index
    buffer_low = Signal()

    def __init__(self, sample_rate: int = 48000, channels: int = 2):
        super().__init__()
        self._buffer = bytearray()
        self._clip_markers = deque()
        self._current_clip_id = None

        self._current_page = None
        self._last_item_index = None

        self.sample_rate = sample_rate
        self.channels = channels
        self.bytes_per_sample = 2
        self.low_water_seconds = 0.5

        self._update_thresholds()

    def set_audio_format(self, sample_rate: int, channels: int):
        self.sample_rate = sample_rate
        self.channels = channels
        self._update_thresholds()

    def _update_thresholds(self):
        self.low_water_bytes = int(
            self.sample_rate * self.channels * self.bytes_per_sample * self.low_water_seconds
        )

    def set_page_boundary(self, page: int, last_item_index: int):
        """Define the terminal index for this page to trigger page turn."""
        self._current_page = page
        self._last_item_index = last_item_index

    def feed(self, clip_id: str, pcm_bytes: bytes, item_index: int, page: int):
        """Feed a synthesized chunk with its item metadata."""
        if not pcm_bytes:
            return
        self._buffer.extend(pcm_bytes)
        # Store: [clip_id, remaining_bytes, item_index, page]
        self._clip_markers.append([clip_id, len(pcm_bytes), item_index, page])
        self.readyRead.emit()

    def clear(self):
        self._buffer.clear()
        self._clip_markers.clear()
        self._current_clip_id = None
        self._current_page = None
        self._last_item_index = None

    def readData(self, maxlen: int) -> bytes:
        if not self._buffer:
            self.buffer_low.emit()
            return b""

        frame_size = self.channels * self.bytes_per_sample
        bytes_to_read = min(len(self._buffer), maxlen)
        bytes_to_read -= (bytes_to_read % frame_size)

        if bytes_to_read <= 0:
            return b""

        chunk = bytes(self._buffer[:bytes_to_read])
        del self._buffer[:bytes_to_read]

        self._advance_markers(len(chunk))

        if len(self._buffer) < self.low_water_bytes:
            self.buffer_low.emit()

        return chunk

    def writeData(self, data):
        return -1

    def bytesAvailable(self) -> int:
        return len(self._buffer) + super().bytesAvailable()

    def isSequential(self) -> bool:
        return True

    def _advance_markers(self, n_bytes: int):
        while n_bytes > 0 and self._clip_markers:
            if self._current_clip_id != self._clip_markers[0][0]:
                self._current_clip_id = self._clip_markers[0][0]
                self.clip_started.emit(self._current_clip_id, self._clip_markers[0][2])

            clip_id, remaining, item_index, page = self._clip_markers[0]
            if n_bytes < remaining:
                self._clip_markers[0][1] -= n_bytes
                n_bytes = 0
            else:
                n_bytes -= remaining
                self._clip_markers.popleft()
                self._current_clip_id = None
                self.clip_finished.emit(clip_id, item_index)

                if page == self._current_page and item_index == self._last_item_index:
                    self.page_finished.emit(page)