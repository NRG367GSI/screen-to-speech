import io
import base64

from PIL import Image
from PyQt6.QtGui import QImage, QPixmap


IMG_MAX_SIDE = 1024
IMG_JPEG_QUALITY = 80


def prepare_image_for_sending(pil_image: Image.Image) -> bytes:
    w, h = pil_image.size
    if max(w, h) > IMG_MAX_SIDE:
        scale = IMG_MAX_SIDE / max(w, h)
        pil_image = pil_image.resize(
            (int(w * scale), int(h * scale)),
            Image.LANCZOS,
        )
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")
    buf = io.BytesIO()
    pil_image.save(buf, format="JPEG", quality=IMG_JPEG_QUALITY)
    return buf.getvalue()


def pil_to_qpixmap(pil_image: Image.Image) -> QPixmap:
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")
    data = pil_image.tobytes("raw", "RGB")
    qimg = QImage(
        data,
        pil_image.width,
        pil_image.height,
        pil_image.width * 3,
        QImage.Format.Format_RGB888,
    )
    return QPixmap.fromImage(qimg.copy())


def pil_to_base64_png(pil_image: Image.Image) -> str:
    buf = io.BytesIO()
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")
    pil_image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def base64_png_to_pil(b64: str) -> Image.Image:
    data = base64.b64decode(b64)
    return Image.open(io.BytesIO(data)).convert("RGB")