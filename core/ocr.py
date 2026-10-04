import re
import base64
import requests

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


import difflib


def _is_duplicate(new_text: str, previous_texts: list, threshold: float = 0.9) -> bool:
    if not new_text.strip():
        return True
    new_clean = new_text.strip().lower()
    for prev in previous_texts:
        if not prev.strip():
            continue
        prev_clean = prev.strip().lower()
        ratio = difflib.SequenceMatcher(None, new_clean, prev_clean).ratio()
        if ratio >= threshold:
            return True
    return False


def recognize_all(images: list, on_progress=None, dedup_threshold: float = 0.9) -> list:
    results = []
    accepted = []
    total = len(images)
    for i, img in enumerate(images, 1):
        if on_progress:
            on_progress(i, total)
        text = recognize(img)
        if not text.strip():
            results.append("")
            continue
        if _is_duplicate(text, accepted, threshold=dedup_threshold):
            print(f"[OCR] Дубликат пропущен: {text[:60]}...")
            results.append("")
            continue
        accepted.append(text)
        results.append(text)
    return results