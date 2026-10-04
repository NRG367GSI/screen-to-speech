import sys
import os
import re
import io
import base64
import threading
import time
import requests

from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QComboBox,
    QListWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QScrollArea, QFrame, QInputDialog, QMessageBox
)
from PyQt6.QtCore import (
    Qt, QTimer, QRect, QPoint, QBuffer, QByteArray, QIODevice,
    pyqtSignal
)
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QPixmap, QImage, QGuiApplication
)

from PIL import Image
from silero_tts.silero_tts import SileroTTS

from preset_manager import PresetManager, Preset

try:
    import keyboard
    KEYBOARD_OK = True
except ImportError:
    KEYBOARD_OK = False
    print("[HOTKEYS] keyboard не установлен. Установите: pip install keyboard")


LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"
MODEL_NAME = "paddleocr-vl-1.6-q8_0"

SESSIONS_DIR = "sessions"
SAMPLE_RATE = 48000
MODEL_ID = "v4_ru"
DEVICE = "cpu"
MAX_LEN = 800

IMG_MAX_SIDE = 1024
IMG_JPEG_QUALITY = 80
MAX_TOKENS = 512

OCR_PROMPT = "Text Recognition:"

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

os.makedirs(SESSIONS_DIR, exist_ok=True)

preset_manager = PresetManager()

tts = None
tts_lock = threading.Lock()


def load_model(speaker: str, speed: float):
    global tts
    with tts_lock:
        try:
            tts = SileroTTS(
                model_id=MODEL_ID, language="ru",
                speaker=speaker, sample_rate=SAMPLE_RATE,
                device=DEVICE, speech_rate=speed,
            )
        except TypeError:
            tts = SileroTTS(
                model_id=MODEL_ID, language="ru",
                speaker=speaker, sample_rate=SAMPLE_RATE,
                device=DEVICE,
            )
        print(f"[TTS] Готов: {speaker}, скорость {speed}")


def split_text(text, max_len=MAX_LEN):
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


def prepare_image_for_sending(pil_image: Image.Image) -> bytes:
    w, h = pil_image.size
    if max(w, h) > IMG_MAX_SIDE:
        scale = IMG_MAX_SIDE / max(w, h)
        pil_image = pil_image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
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
        data, pil_image.width, pil_image.height,
        pil_image.width * 3, QImage.Format.Format_RGB888
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


class FrameWindow(QWidget):
    BORDER = 10
    MIN_W, MIN_H = 10, 10

    sig_geometry_changed = pyqtSignal()

    def __init__(self, preset: Preset):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setMinimumSize(self.MIN_W, self.MIN_H)

        self.apply_geometry_from_preset(preset)

        self._drag_pos = None
        self._edge = None
        self._resize_start = None
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(self._emit_geometry_changed)

    def apply_geometry_from_preset(self, preset: Preset):
        f = preset.frame
        self.setGeometry(f["x"], f["y"], f["width"], f["height"])

    def current_geometry_dict(self) -> dict:
        g = self.geometry()
        return {
            "x": g.x(),
            "y": g.y(),
            "width": g.width(),
            "height": g.height(),
        }

    def _emit_geometry_changed(self):
        self.sig_geometry_changed.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor(0, 220, 80, 220), 3))
        painter.drawRect(self.rect().adjusted(2, 2, -2, -2))

        handle = 8
        painter.setBrush(QColor(0, 220, 80, 220))
        for x, y in [
            (0, 0),
            (self.width() - handle, 0),
            (0, self.height() - handle),
            (self.width() - handle, self.height() - handle),
        ]:
            painter.drawRect(x, y, handle, handle)

    def _edge_at(self, pos: QPoint):
        w, h = self.width(), self.height()
        m = self.BORDER
        x, y = pos.x(), pos.y()
        left, right = x < m, x > w - m
        top, bottom = y < m, y > h - m
        if top and left: return "top-left"
        if top and right: return "top-right"
        if bottom and left: return "bottom-left"
        if bottom and right: return "bottom-right"
        if left: return "left"
        if right: return "right"
        if top: return "top"
        if bottom: return "bottom"
        return None

    def _cursor_for(self, edge):
        return {
            "top-left":     Qt.CursorShape.SizeFDiagCursor,
            "bottom-right": Qt.CursorShape.SizeFDiagCursor,
            "top-right":    Qt.CursorShape.SizeBDiagCursor,
            "bottom-left":  Qt.CursorShape.SizeBDiagCursor,
            "left":         Qt.CursorShape.SizeHorCursor,
            "right":        Qt.CursorShape.SizeHorCursor,
            "top":          Qt.CursorShape.SizeVerCursor,
            "bottom":       Qt.CursorShape.SizeVerCursor,
        }.get(edge, Qt.CursorShape.ArrowCursor)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            return
        if self._resize_start is not None:
            self._do_resize(event.globalPosition().toPoint())
            return
        edge = self._edge_at(event.position().toPoint())
        self.setCursor(self._cursor_for(edge))

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        edge = self._edge_at(event.position().toPoint())
        gp = event.globalPosition().toPoint()
        if edge is None:
            self._drag_pos = gp - self.frameGeometry().topLeft()
        else:
            self._edge = edge
            self._resize_start = (gp, self.geometry())

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        self._edge = None
        self._resize_start = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._save_timer.start()

    def _do_resize(self, gp: QPoint):
        start_gp, start_rect = self._resize_start
        dx = gp.x() - start_gp.x()
        dy = gp.y() - start_gp.y()
        r = QRect(start_rect)
        e = self._edge
        if "left" in e:
            r.setLeft(min(start_rect.left() + dx, start_rect.right() - self.MIN_W))
        if "right" in e:
            r.setRight(max(start_rect.right() + dx, start_rect.left() + self.MIN_W))
        if "top" in e:
            r.setTop(min(start_rect.top() + dy, start_rect.bottom() - self.MIN_H))
        if "bottom" in e:
            r.setBottom(max(start_rect.bottom() + dy, start_rect.top() + self.MIN_H))
        self.setGeometry(r)

    def capture(self) -> Image.Image:
        geo = self.geometry()
        self.hide()
        QApplication.processEvents()
        QTimer.singleShot(120, lambda: None)
        QApplication.processEvents()

        try:
            screen = QGuiApplication.primaryScreen()
            pixmap = screen.grabWindow(
                0, geo.x(), geo.y(), geo.width(), geo.height()
            )
            qimg = pixmap.toImage()

            ba = QByteArray()
            buffer = QBuffer(ba)
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            qimg.save(buffer, "PNG")
            buffer.close()

            pil = Image.open(io.BytesIO(bytes(ba))).convert("RGB")
        finally:
            self.show()
            QApplication.processEvents()
        return pil


class ThumbnailWidget(QFrame):
    def __init__(self, pixmap: QPixmap, name: str, on_delete):
        super().__init__()
        self.setFrameShape(QFrame.Shape.Box)
        self.setFixedSize(180, 160)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        top = QHBoxLayout()
        self.lbl_name = QLabel(name)
        self.lbl_name.setStyleSheet("font-weight:bold;")
        top.addWidget(self.lbl_name)

        btn_del = QPushButton("✕")
        btn_del.setFixedSize(24, 24)
        btn_del.clicked.connect(lambda: on_delete(self))
        top.addWidget(btn_del)

        layout.addLayout(top)

        img_label = QLabel()
        img_label.setPixmap(pixmap.scaled(
            160, 110,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(img_label)


class ControlPanel(QWidget):
    sig_status = pyqtSignal(str)
    sig_text = pyqtSignal(str)
    sig_refresh_audio = pyqtSignal()
    sig_play_all = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("OCR + TTS")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setGeometry(50, 50, 1000, 820)

        self.current_session: list[dict] = []
        self.thumbnails: list[ThumbnailWidget] = []
        self.image_counter = 0

        self.session_dir = None
        self._new_session_dir()

        self.frame = FrameWindow(preset_manager.current)
        self.frame.sig_geometry_changed.connect(self._save_frame_geometry)
        if preset_manager.current.frame.get("visible", True):
            self.frame.show()

        top = QHBoxLayout()

        self.btn_toggle_frame = QPushButton("👁 Рамка")
        self.btn_toggle_frame.setStyleSheet(
            "background:#3F51B5;color:white;font-weight:bold;padding:6px;"
        )
        self.btn_toggle_frame.clicked.connect(self.toggle_frame)
        top.addWidget(self.btn_toggle_frame)

        self.btn_full_cycle = QPushButton("🎬 Полный цикл")
        self.btn_full_cycle.setStyleSheet(
            "background:#E91E63;color:white;font-weight:bold;padding:6px;"
        )
        self.btn_full_cycle.clicked.connect(self.full_cycle)
        top.addWidget(self.btn_full_cycle)

        self.btn_capture_only = QPushButton("📸 Только снять")
        self.btn_capture_only.clicked.connect(self.capture_only)
        top.addWidget(self.btn_capture_only)

        self.btn_recognize_only = QPushButton("🎙 Только распознать")
        self.btn_recognize_only.clicked.connect(self.process_session)
        top.addWidget(self.btn_recognize_only)

        top.addWidget(QLabel("Пресет:"))
        self.preset_box = QComboBox()
        self.preset_box.addItems(preset_manager.list_presets())
        self.preset_box.setCurrentText(preset_manager.current.name)
        self.preset_box.currentTextChanged.connect(self.on_preset_change)
        top.addWidget(self.preset_box)

        top.addWidget(QLabel("Голос:"))
        self.voice_box = QComboBox()
        self.voice_box.addItems(list(VOICES.keys()))
        primary_name = VOICE_IDS_TO_NAMES.get(
            preset_manager.current.voices["primary"], "Женский — Baya"
        )
        self.voice_box.setCurrentText(primary_name)
        self.voice_box.currentTextChanged.connect(self.on_voice_change)
        top.addWidget(self.voice_box)

        top.addWidget(QLabel("Скорость:"))
        self.speed_box = QComboBox()
        self.speed_box.addItems(list(SPEEDS.keys()))
        cur_speed = preset_manager.current.speed
        for name, val in SPEEDS.items():
            if abs(val - cur_speed) < 0.01:
                self.speed_box.setCurrentText(name)
                break
        self.speed_box.currentTextChanged.connect(self.on_speed_change)
        top.addWidget(self.speed_box)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.gallery_container = QWidget()
        self.gallery_layout = QHBoxLayout(self.gallery_container)
        self.gallery_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.scroll.setWidget(self.gallery_container)

        bottom = QHBoxLayout()

        self.btn_new_session = QPushButton("🆕 Новая сессия")
        self.btn_new_session.setStyleSheet(
            "background:#009688;color:white;font-weight:bold;padding:8px;"
        )
        self.btn_new_session.clicked.connect(self.new_session)
        bottom.addWidget(self.btn_new_session)

        self.btn_open_folder = QPushButton("📂 Открыть папку")
        self.btn_open_folder.clicked.connect(self.open_session_folder)
        bottom.addWidget(self.btn_open_folder)

        self.btn_play_all = QPushButton("▶ Воспроизвести все")
        self.btn_play_all.clicked.connect(self.play_all)
        bottom.addWidget(self.btn_play_all)

        self.btn_stop = QPushButton("⏹ Стоп")
        self.btn_stop.clicked.connect(self.stop_playback)
        bottom.addWidget(self.btn_stop)

        self.btn_save_preset = QPushButton("💾 Сохранить пресет")
        self.btn_save_preset.clicked.connect(self.save_preset)
        bottom.addWidget(self.btn_save_preset)

        self.btn_reset_preset = QPushButton("♻ Сбросить пресет")
        self.btn_reset_preset.clicked.connect(self.reset_preset)
        bottom.addWidget(self.btn_reset_preset)

        self.btn_quit = QPushButton("✕ Выход")
        self.btn_quit.setStyleSheet("background:#c0392b;color:white;font-weight:bold;")
        self.btn_quit.clicked.connect(self.quit_app)
        bottom.addWidget(self.btn_quit)

        self.audio_list = QListWidget()
        self.audio_list.setFixedHeight(90)
        self.audio_list.itemDoubleClicked.connect(self.play_selected)

        self.text_view = QTextEdit()
        self.text_view.setFixedHeight(90)
        self.text_view.setPlaceholderText("Распознанный текст появится здесь...")

        self.session_label = QLabel(f"Папка сессии: {self.session_dir}")
        self.session_label.setStyleSheet("color: gray;")

        hotkeys_label = QLabel(
            "Ctrl+Alt+Space — полный цикл  |  Ctrl+Alt+S — снять  |  "
            "Ctrl+Alt+R — распознать  |  Ctrl+Alt+Up — рамка  |  "
            "Ctrl+Alt+N — новая сессия"
        )
        hotkeys_label.setStyleSheet("color: #555; font-style: italic;")

        self.status = QLabel("Готов")

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(QLabel("Скриншоты текущей сессии:"))
        layout.addWidget(self.scroll, stretch=3)
        layout.addLayout(bottom)
        layout.addWidget(QLabel("Распознанный текст:"))
        layout.addWidget(self.text_view)
        layout.addWidget(QLabel("Готовые озвучки:"))
        layout.addWidget(self.audio_list)
        layout.addWidget(self.session_label)
        layout.addWidget(hotkeys_label)
        layout.addWidget(self.status)

        self.sig_status.connect(self.status.setText)
        self.sig_text.connect(self.text_view.setPlainText)
        self.sig_refresh_audio.connect(self.refresh_audio_list)
        self.sig_play_all.connect(self.play_all)

        self.refresh_audio_list()
        self.setup_hotkeys()

        primary = preset_manager.current.voices["primary"]
        speed = preset_manager.current.speed
        threading.Thread(target=load_model, args=(primary, speed), daemon=True).start()

    def setup_hotkeys(self):
        if not KEYBOARD_OK:
            print("[HOTKEYS] keyboard не установлен")
            return
        try:
            hk = preset_manager.current.hotkeys
            keyboard.add_hotkey(hk["full_cycle"], lambda: QTimer.singleShot(0, self.full_cycle))
            keyboard.add_hotkey(hk["capture_only"], lambda: QTimer.singleShot(0, self.capture_only))
            keyboard.add_hotkey(hk["recognize_only"], lambda: QTimer.singleShot(0, self.process_session))
            keyboard.add_hotkey(hk["toggle_frame"], lambda: QTimer.singleShot(0, self.toggle_frame))
            keyboard.add_hotkey(hk["new_session"], lambda: QTimer.singleShot(0, self.new_session))
            print("[HOTKEYS] Активированы")
        except Exception as e:
            print(f"[HOTKEYS] Ошибка: {e}")

    def toggle_frame(self):
        if self.frame.isVisible():
            self.frame.hide()
            preset_manager.current.frame["visible"] = False
        else:
            self.frame.show()
            preset_manager.current.frame["visible"] = True
        preset_manager.save_current()

    def _save_frame_geometry(self):
        geo = self.frame.current_geometry_dict()
        preset_manager.current.frame.update(geo)
        preset_manager.current.frame["visible"] = self.frame.isVisible()
        preset_manager.save_current()
        print(f"[PRESET] Сохранена геометрия рамки: {geo}")

    def _new_session_dir(self):
        stamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        path = os.path.join(SESSIONS_DIR, stamp)
        os.makedirs(path, exist_ok=True)
        os.makedirs(os.path.join(path, "screenshots"), exist_ok=True)
        os.makedirs(os.path.join(path, "audio"), exist_ok=True)
        self.session_dir = path
        if hasattr(self, "session_label"):
            self.session_label.setText(f"Папка сессии: {self.session_dir}")

    def new_session(self):
        if self.current_session or self.text_view.toPlainText():
            ans = QMessageBox.question(
                self, "Новая сессия",
                "Очистить текущую сессию и начать новую?\n"
                "Старые файлы на диске сохранятся.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if ans != QMessageBox.StandardButton.Yes:
                return
        self.clear_gallery()
        self.text_view.clear()
        self.audio_list.clear()
        self.image_counter = 0
        self._new_session_dir()
        self.status.setText(f"🆕 Новая сессия: {self.session_dir}")

    def open_session_folder(self):
        if self.session_dir and os.path.isdir(self.session_dir):
            os.startfile(os.path.abspath(self.session_dir))

    def on_preset_change(self, name):
        try:
            preset_manager.load(name)
            self.frame.apply_geometry_from_preset(preset_manager.current)
            if preset_manager.current.frame.get("visible", True):
                self.frame.show()
            else:
                self.frame.hide()
            primary = preset_manager.current.voices["primary"]
            self.voice_box.setCurrentText(VOICE_IDS_TO_NAMES.get(primary, "Женский — Baya"))
            cur_speed = preset_manager.current.speed
            for sname, sval in SPEEDS.items():
                if abs(sval - cur_speed) < 0.01:
                    self.speed_box.setCurrentText(sname)
                    break
            threading.Thread(target=load_model, args=(primary, cur_speed), daemon=True).start()
            self.status.setText(f"📁 Пресет: {name}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка пресета", str(e))

    def save_preset(self):
        name, ok = QInputDialog.getText(
            self, "Сохранить пресет", "Имя нового пресета:",
            text=f"preset_{len(preset_manager.list_presets()) + 1}"
        )
        if not ok or not name.strip():
            return
        try:
            preset_manager.create(name.strip(), set_active=True)
            self.preset_box.addItem(name.strip())
            self.preset_box.setCurrentText(name.strip())
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def reset_preset(self):
        ans = QMessageBox.question(
            self, "Сброс пресета",
            f"Сбросить пресет '{preset_manager.current.name}' к значениям по умолчанию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        preset_manager.current.frame = {
            "x": 300, "y": 200, "width": 600, "height": 300, "visible": True,
        }
        preset_manager.current.voices = {"primary": "baya", "secondary": "aidar", "current": "primary"}
        preset_manager.current.speed = 1.0
        preset_manager.save_current()
        self.frame.apply_geometry_from_preset(preset_manager.current)
        self.frame.show()
        self.voice_box.setCurrentText("Женский — Baya")
        self.speed_box.setCurrentText("1.0 — нормально")
        threading.Thread(target=load_model, args=("baya", 1.0), daemon=True).start()
        self.status.setText("♻ Пресет сброшен")

    def capture_only(self):
        if not self.frame.isVisible():
            self.frame.show()
            QApplication.processEvents()
        screenshot = self.frame.capture()
        self.add_screenshot(screenshot)
        self.status.setText(f"📸 Скриншотов: {len(self.current_session)}")

    def full_cycle(self):
        self.capture_only()
        self.process_session()

    def add_screenshot(self, pil_image: Image.Image):
        self.image_counter += 1
        name = str(self.image_counter)

        pixmap = pil_to_qpixmap(pil_image)
        thumb = ThumbnailWidget(pixmap, name, self.remove_thumbnail)
        self.gallery_layout.addWidget(thumb)
        self.thumbnails.append(thumb)

        try:
            shots_dir = os.path.join(self.session_dir, "screenshots")
            os.makedirs(shots_dir, exist_ok=True)
            filename = os.path.join(shots_dir, f"{self.image_counter:04d}.png")
            pil_image.save(filename, "PNG")
            print(f"[SCREENSHOT] Сохранён: {os.path.abspath(filename)}")
        except Exception as e:
            print(f"[SCREENSHOT] Ошибка сохранения: {e}")

        self.current_session.append({
            "name": name,
            "image_b64": pil_to_base64_png(pil_image),
            "text": ""
        })

    def remove_thumbnail(self, widget: ThumbnailWidget):
        idx = self.thumbnails.index(widget) if widget in self.thumbnails else -1
        if idx >= 0:
            self.thumbnails.pop(idx)
            if idx < len(self.current_session):
                self.current_session.pop(idx)
        widget.setParent(None)
        widget.deleteLater()
        self.status.setText(f"Скриншотов: {len(self.current_session)}")

    def clear_gallery(self):
        for w in list(self.thumbnails):
            w.setParent(None)
            w.deleteLater()
        self.thumbnails.clear()
        self.current_session.clear()

    def process_session(self):
        if not self.current_session:
            QMessageBox.information(self, "Нет скриншотов", "Сначала снимите скриншот.")
            return
        self.status.setText("🧠 Обработка...")
        threading.Thread(target=self._process_worker, daemon=True).start()

    def _process_worker(self):
        results = []
        for i, item in enumerate(self.current_session, 1):
            name = item["name"]
            pil_image = base64_png_to_pil(item["image_b64"])
            text = self._ocr_one(name, pil_image)
            item["text"] = text
            if text:
                results.append(text)
            del pil_image

        if not results:
            self.sig_status.emit("❌ Текст не распознан")
            return

        full_text = "\n\n".join(results)
        self.sig_text.emit(full_text)
        self.sig_status.emit(f"✅ Распознано {len(full_text)} символов. Озвучиваю...")

        try:
            md_path = os.path.join(self.session_dir, "text.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(f"# Сессия {os.path.basename(self.session_dir)}\n\n")
                f.write(f"Создано: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n")
                f.write(full_text)
            print(f"[TEXT] Сохранён: {os.path.abspath(md_path)}")
        except Exception as e:
            print(f"[TEXT] Ошибка сохранения: {e}")

        self.run_tts(full_text)

    def _ocr_one(self, name: str, pil_image: Image.Image) -> str:
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
            }

            self.sig_status.emit(f"🧠 OCR #{name}...")
            resp = requests.post(LM_STUDIO_URL, json=payload, timeout=180)
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"].strip()
            text = re.sub(r"^```.*?\n", "", text)
            text = re.sub(r"\n```$", "", text)
            text = re.sub(r"<\|LOC_\d+\|>", "", text)
            return text
        except Exception as e:
            print(f"Ошибка OCR ({name}):", e)
            return ""

    def run_tts(self, text):
        if tts is None:
            self.sig_status.emit("⏳ TTS ещё грузится...")
            return
        try:
            chunks = split_text(text, MAX_LEN)
            total = len(chunks)
            audio_dir = os.path.join(self.session_dir, "audio")
            os.makedirs(audio_dir, exist_ok=True)
            for i, chunk in enumerate(chunks, 1):
                filename = os.path.join(audio_dir, f"part_{i:03d}.wav")
                with tts_lock:
                    tts.tts(chunk, filename)
                self.sig_status.emit(f"🎙 {i}/{total}")
            self.sig_refresh_audio.emit()
            self.sig_status.emit(f"✅ Готово! Файлов: {total}")
            self.sig_play_all.emit()
        except Exception as e:
            self.sig_status.emit(f"❌ Ошибка TTS: {e}")
            print("Ошибка TTS:", e)

    def refresh_audio_list(self):
        self.audio_list.clear()
        if not self.session_dir:
            return
        audio_dir = os.path.join(self.session_dir, "audio")
        if not os.path.isdir(audio_dir):
            return
        for f in sorted(x for x in os.listdir(audio_dir) if x.endswith(".wav")):
            self.audio_list.addItem(f)

    def _audio_paths(self):
        if not self.session_dir:
            return []
        audio_dir = os.path.join(self.session_dir, "audio")
        return [
            os.path.join(audio_dir, self.audio_list.item(i).text())
            for i in range(self.audio_list.count())
        ]

    def play_selected(self):
        idx = self.audio_list.currentRow()
        if idx < 0:
            return
        path = self._audio_paths()[idx]
        threading.Thread(
            target=lambda: __import__("winsound").PlaySound(
                path,
                __import__("winsound").SND_FILENAME | __import__("winsound").SND_ASYNC
            ),
            daemon=True
        ).start()

    def play_all(self):
        paths = self._audio_paths()
        if not paths:
            return
        threading.Thread(target=self._play_sequence, args=(paths,), daemon=True).start()

    def _play_sequence(self, paths):
        import winsound
        for i, path in enumerate(paths, 1):
            self.sig_status.emit(f"▶ {i}/{len(paths)}")
            winsound.PlaySound(path, winsound.SND_FILENAME)
        self.sig_status.emit("✅ Воспроизведение завершено")

    def stop_playback(self):
        try:
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
            self.status.setText("⏹ Остановлено")
        except Exception:
            pass

    def on_voice_change(self, label):
        speaker = VOICES[label]
        speed = SPEEDS[self.speed_box.currentText()]
        preset_manager.current.voices["primary"] = speaker
        preset_manager.current.speed = speed
        preset_manager.save_current()
        threading.Thread(target=load_model, args=(speaker, speed), daemon=True).start()
        self.status.setText(f"⏳ Загружаю голос {label}...")

    def on_speed_change(self, label):
        speaker = VOICES[self.voice_box.currentText()]
        speed = SPEEDS[label]
        preset_manager.current.voices["primary"] = speaker
        preset_manager.current.speed = speed
        preset_manager.save_current()
        threading.Thread(target=load_model, args=(speaker, speed), daemon=True).start()
        self.status.setText(f"⏳ Загружаю скорость {label}...")

    def quit_app(self):
        try:
            if KEYBOARD_OK:
                keyboard.unhook_all()
        except Exception:
            pass
        try:
            preset_manager.save_current()
        except Exception:
            pass
        try:
            self.stop_playback()
        except Exception:
            pass
        self.frame.close()
        QApplication.quit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.quit_app()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        try:
            if KEYBOARD_OK:
                keyboard.unhook_all()
        except Exception:
            pass
        try:
            preset_manager.save_current()
        except Exception:
            pass
        self.frame.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    panel = ControlPanel()
    panel.show()
    sys.exit(app.exec())