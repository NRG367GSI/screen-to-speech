import re
import threading

from silero_tts.silero_tts import SileroTTS


MODEL_ID = "v4_ru"
LANGUAGE = "ru"
SAMPLE_RATE = 24000
DEVICE = "cpu"
MAX_LEN = 800


VOICES = {
    "Мужской — Aidar":   "aidar",
    "Мужской — Eugene":  "eugene",
    "Женский — Baya":    "baya",
    "Женский — Kseniya": "kseniya",
    "Женский — Xenia":   "xenia",
    "Случайный":         "random",
}

VOICE_IDS_TO_NAMES = {v: k for k, v in VOICES.items()}

SPEEDS = {
    "0.8 — медленно":     0.8,
    "1.0 — нормально":    1.0,
    "1.2 — быстро":       1.2,
    "1.5 — очень быстро": 1.5,
}


class TTS:
    def __init__(self, speaker: str = "baya", speed: float = 1.0):
        self.speaker = speaker
        self.speed = speed
        self._tts = None
        self._lock = threading.Lock()

    def load(self, speaker: str = None, speed: float = None):
        if speaker is not None:
            self.speaker = speaker
        if speed is not None:
            self.speed = speed

        with self._lock:
            try:
                self._tts = SileroTTS(
                    model_id=MODEL_ID, language=LANGUAGE,
                    speaker=self.speaker, sample_rate=SAMPLE_RATE,
                    device=DEVICE, speech_rate=self.speed,
                )
            except TypeError:
                self._tts = SileroTTS(
                    model_id=MODEL_ID, language=LANGUAGE,
                    speaker=self.speaker, sample_rate=SAMPLE_RATE,
                    device=DEVICE,
                )
            print(f"[TTS] Готов: {self.speaker}, скорость {self.speed}")

    @property
    def ready(self) -> bool:
        return self._tts is not None

    def synthesize(self, text: str, filename: str):
        with self._lock:
            if self._tts is None:
                raise RuntimeError("TTS не загружен. Вызовите load().")
            self._tts.tts(text, filename)

import re

import re


def normalize_for_tts(text: str) -> str:
    lines = text.split("\n")

    joined = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if line.endswith("-") and i + 1 < len(lines):
            next_line = lines[i + 1].lstrip()
            if next_line and next_line[0].islower():
                lines[i + 1] = line[:-1] + next_line
                i += 1
                continue
        joined.append(line)
        i += 1

    cleaned = []
    buffer = ""
    for line in joined:
        stripped = line.strip()
        if not stripped:
            if buffer:
                cleaned.append(buffer)
                buffer = ""
            continue

        if len(stripped) < 3:
            if buffer:
                buffer = buffer + " " + stripped
            else:
                buffer = stripped
            continue

        if buffer:
            cleaned.append(buffer)
            buffer = ""
        cleaned.append(stripped)

    if buffer:
        cleaned.append(buffer)

    result = "\n".join(cleaned)

    result = re.sub(r"\.{2,}", "…", result)
    result = re.sub(r"[ \t]+", " ", result)

    words = result.split()
    result = " ".join(
        w for w in words
        if any(ch.isalpha() for ch in w) or w in {"…", "—", "–"}
    )

    return result.strip()

def split_text(text: str, max_len: int = MAX_LEN) -> list:
    text = normalize_for_tts(text)
    sentences = re.split(r'(?<=[.!?…])\s+', text)
    chunks, current = [], ""
    for sentence in sentences:
        while len(sentence) > max_len:
            cut = sentence.rfind(",", 0, max_len)
            if cut == -1:
                cut = sentence.rfind(" ", 0, max_len)
            if cut == -1:
                cut = max_len
            chunks.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if len(current) + len(sentence) + 1 <= max_len:
            current = (current + " " + sentence).strip()
        else:
            if current:
                chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks