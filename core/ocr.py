import re
import base64
import requests
import difflib
from PIL import Image

from core.image_utils import prepare_image_for_sending


LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"
MODEL_NAME = "paddleocr-vl-1.6-q8_0"
OCR_PROMPT = "Text Recognition:"
MAX_TOKENS = 1024


def _clean_text(text: str) -> str:
    text = re.sub(r"^```.*?\n", "", text)
    text = re.sub(r"\n```$", "", text)
    text = re.sub(r"<\|LOC_\d+\|>", "", text)
    return text.strip()


def recognize(pil_image: Image.Image, timeout: int = 180) -> str:
    try:
        img_bytes = prepare_image_for_sending(pil_image)
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")

        payload = {
            "model": MODEL_NAME,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": OCR_PROMPT},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{img_b64}"
                    }},
                ]
            }],
            "temperature": 0.0,
            "max_tokens": MAX_TOKENS,
            "store": False,
        }

        resp = requests.post(LM_STUDIO_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return _clean_text(text)

    except Exception as e:
        print(f"[OCR] Ошибка: {e}")
        return ""


def _split_lines(text: str) -> list:
    return [line.strip() for line in text.split("\n") if line.strip()]


def _normalize_line(line: str) -> str:
    line = line.lower().strip()
    line = re.sub(r"[^\w\s]", "", line)
    line = re.sub(r"\s+", " ", line)
    return line


def _line_is_duplicate(line: str, accepted_lines: set, threshold: float = 0.85) -> bool:
    line_clean = _normalize_line(line)
    if not line_clean:
        return True
    if line_clean in accepted_lines:
        return True
    for prev in accepted_lines:
        ratio = difflib.SequenceMatcher(None, line_clean, prev).ratio()
        if ratio >= threshold:
            return True
    return False


def recognize_all(images: list, on_progress=None, dedup_threshold: float = 0.85) -> list:
    results = []
    accepted_lines = set()
    total = len(images)

    for i, img in enumerate(images, 1):
        if on_progress:
            on_progress(i, total)

        text = recognize(img)
        if not text.strip():
            results.append("")
            continue

        lines = _split_lines(text)
        new_lines = []
        dup_count = 0

        for line in lines:
            if _line_is_duplicate(line, accepted_lines, threshold=dedup_threshold):
                dup_count += 1
                continue
            new_lines.append(line)
            accepted_lines.add(_normalize_line(line))

        if not new_lines:
            print(f"[OCR] Скрин {i}: все строки дубликаты ({dup_count})")
            results.append("")
            continue

        if dup_count > 0:
            print(f"[OCR] Скрин {i}: пропущено дубликатов {dup_count}, новых строк {len(new_lines)}")

        results.append("\n".join(new_lines))

    return results