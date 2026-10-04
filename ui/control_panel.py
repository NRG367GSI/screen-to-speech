import os
import time
import threading

from PyQt6.QtWidgets import (
    QWidget, QPushButton, QLabel, QComboBox,
    QListWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QScrollArea, QFrame, QInputDialog, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from preset_manager import PresetManager
from core.image_utils import pil_to_qpixmap, pil_to_base64_png, base64_png_to_pil
from core.session import Session
from core.ocr import recognize
from core.tts import TTS, VOICES, VOICE_IDS_TO_NAMES, SPEEDS, split_text
from ui.thumbnail import ThumbnailWidget
from ui.frame_window import FrameWindow
from ui.widget import Widget

try:
    import keyboard
    KEYBOARD_OK = True
except ImportError:
    KEYBOARD_OK = False
    print("[HOTKEYS] keyboard не установлен. Установите: pip install keyboard")


class ControlPanel(QWidget):
    sig_status = pyqtSignal(str)
    sig_text = pyqtSignal(str)
    sig_refresh_audio = pyqtSignal()
    sig_play_all = pyqtSignal()

    def __init__(self, preset_manager: PresetManager):
        super().__init__()
        self.preset_manager = preset_manager
        self.setWindowTitle("OCR + TTS")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setGeometry(50, 50, 1000, 820)

        self.current_session: list[dict] = []
        self.thumbnails: list[ThumbnailWidget] = []
        self.image_counter = 0

        self.session = Session()
        self.session.create()

        self.tts = TTS(
            speaker=preset_manager.current.voices["primary"],
            speed=preset_manager.current.speed,
        )

        self.frame = FrameWindow(preset_manager.current)
        self.frame.sig_geometry_changed.connect(self._save_frame_geometry)
        self.frame.hide()
        preset_manager.current.frame["visible"] = False

        self.widget = Widget(self)

        top = QHBoxLayout()

        self.btn_toggle_frame = QPushButton("👁 Рамка")
        self.btn_toggle_frame.setStyleSheet(
            "background:#3F51B5;color:white;font-weight:bold;padding:6px;"
        )
        self.btn_toggle_frame.setToolTip("Показать/скрыть рамку (Ctrl+Alt+Up)")
        self.btn_toggle_frame.clicked.connect(self.toggle_frame)
        top.addWidget(self.btn_toggle_frame)

        self.btn_full_cycle = QPushButton("🎬 Полный цикл")
        self.btn_full_cycle.setStyleSheet(
            "background:#E91E63;color:white;font-weight:bold;padding:6px;"
        )
        self.btn_full_cycle.setToolTip("Снять + распознать + озвучить (Ctrl+Alt+Space)")
        self.btn_full_cycle.clicked.connect(self.full_cycle)
        top.addWidget(self.btn_full_cycle)

        self.btn_capture_only = QPushButton("📸 Только снять")
        self.btn_capture_only.setToolTip("Снять скриншот (Ctrl+Alt+S)")
        self.btn_capture_only.clicked.connect(self.capture_only)
        top.addWidget(self.btn_capture_only)

        self.btn_recognize_only = QPushButton("🎙 Только распознать")
        self.btn_recognize_only.setToolTip("Распознать + озвучить (Ctrl+Alt+R)")
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
        self.btn_new_session.setToolTip("Новая сессия (Ctrl+Alt+N)")
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

        self.btn_collapse = QPushButton("➖")
        self.btn_collapse.setFixedSize(28, 22)
        self.btn_collapse.setToolTip("Свернуть в виджет")
        self.btn_collapse.clicked.connect(self.collapse_to_widget)

        self.btn_quit = QPushButton("✕ Выход")
        self.btn_quit.setStyleSheet("background:#c0392b;color:white;font-weight:bold;")
        self.btn_quit.clicked.connect(self.quit_app)

        bottom.addWidget(self.btn_collapse)
        bottom.addWidget(self.btn_quit)

        self.audio_list = QListWidget()
        self.audio_list.setFixedHeight(90)
        self.audio_list.itemDoubleClicked.connect(self.play_selected)

        self.text_view = QTextEdit()
        self.text_view.setFixedHeight(90)
        self.text_view.setPlaceholderText("Распознанный текст появится здесь...")

        self.session_label = QLabel(f"Папка сессии: {self.session.path}")
        self.session_label.setStyleSheet("color: gray;")

        self.hotkeys_label = QLabel(
            "Ctrl+Alt+Space — полный цикл  |  Ctrl+Alt+S — снять  |  "
            "Ctrl+Alt+R — распознать  |  Ctrl+Alt+Up — рамка  |  "
            "Ctrl+Alt+N — новая сессия"
        )
        self.hotkeys_label.setStyleSheet("color: #555; font-style: italic;")

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
        layout.addWidget(self.hotkeys_label)
        layout.addWidget(self.status)

        self.sig_status.connect(self.status.setText)
        self.sig_status.connect(self._forward_status_to_widget)
        self.sig_text.connect(self.text_view.setPlainText)
        self.sig_refresh_audio.connect(self.refresh_audio_list)
        self.sig_play_all.connect(self.play_all)

        self.refresh_audio_list()
        self.setup_hotkeys()

        threading.Thread(
            target=self.tts.load,
            args=(preset_manager.current.voices["primary"], preset_manager.current.speed),
            daemon=True
        ).start()

    def _forward_status_to_widget(self, text: str):
        if hasattr(self, "widget") and self.widget is not None:
            self.widget.update_status(text)

    def collapse_to_widget(self):
        self.hide()
        self.widget.show()
        self.widget.raise_()
        self.widget.activateWindow()

    def expand_from_widget(self):
        self.widget.hide()
        self.show()
        self.raise_()
        self.activateWindow()

    def setup_hotkeys(self):
        if not KEYBOARD_OK:
            print("[HOTKEYS] keyboard не установлен")
            return
        try:
            hk = self.preset_manager.current.hotkeys
            keyboard.add_hotkey(hk["full_cycle"], lambda: QTimer.singleShot(0, self.full_cycle))
            keyboard.add_hotkey(hk["capture_only"], lambda: QTimer.singleShot(0, self.capture_only))
            keyboard.add_hotkey(hk["recognize_only"], lambda: QTimer.singleShot(0, self.process_session))
            keyboard.add_hotkey(hk["toggle_frame"], lambda: QTimer.singleShot(0, self.toggle_frame))
            keyboard.add_hotkey(hk["new_session"], lambda: QTimer.singleShot(0, self.new_session))
            print("[HOTKEYS] Активированы")
        except Exception as e:
            print(f"[HOTKEYS] Ошибка: {e}")

    def re_register_hotkeys(self):
        if not KEYBOARD_OK:
            return
        try:
            keyboard.unhook_all()
            self.setup_hotkeys()
        except Exception as e:
            print(f"[HOTKEYS] Ошибка перерегистрации: {e}")

    def toggle_frame(self):
        if self.frame.isVisible():
            self.frame.hide()
            self.preset_manager.current.frame["visible"] = False
        else:
            self.frame.show()
            self.frame.raise_()
            self.frame.activateWindow()
            self.preset_manager.current.frame["visible"] = True
        self.preset_manager.save_current()

    def _save_frame_geometry(self):
        geo = self.frame.current_geometry_dict()
        self.preset_manager.current.frame.update(geo)
        self.preset_manager.current.frame["visible"] = self.frame.isVisible()
        self.preset_manager.save_current()
        print(f"[PRESET] Сохранена геометрия рамки: {geo}")

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
        self.session.create()
        self.session_label.setText(f"Папка сессии: {self.session.path}")
        self.status.setText(f"🆕 Новая сессия: {self.session.path}")

    def open_session_folder(self):
        self.session.open_folder()

    def on_preset_change(self, name):
        try:
            self.preset_manager.load(name)
            self.frame.apply_geometry_from_preset(self.preset_manager.current)
            if self.preset_manager.current.frame.get("visible", True):
                self.frame.show()
            else:
                self.frame.hide()
            primary = self.preset_manager.current.voices["primary"]
            self.voice_box.setCurrentText(VOICE_IDS_TO_NAMES.get(primary, "Женский — Baya"))
            cur_speed = self.preset_manager.current.speed
            for sname, sval in SPEEDS.items():
                if abs(sval - cur_speed) < 0.01:
                    self.speed_box.setCurrentText(sname)
                    break
            threading.Thread(
                target=self.tts.load,
                args=(primary, cur_speed),
                daemon=True
            ).start()
            self.re_register_hotkeys()
            self.status.setText(f"📁 Пресет: {name}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка пресета", str(e))

    def save_preset(self):
        name, ok = QInputDialog.getText(
            self, "Сохранить пресет", "Имя нового пресета:",
            text=f"preset_{len(self.preset_manager.list_presets()) + 1}"
        )
        if not ok or not name.strip():
            return
        try:
            self.preset_manager.create(name.strip(), set_active=True)
            self.preset_box.addItem(name.strip())
            self.preset_box.setCurrentText(name.strip())
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def reset_preset(self):
        ans = QMessageBox.question(
            self, "Сброс пресета",
            f"Сбросить пресет '{self.preset_manager.current.name}' к значениям по умолчанию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        self.preset_manager.current.frame = {
            "x": 300, "y": 200, "width": 600, "height": 300, "visible": True,
        }
        self.preset_manager.current.voices = {"primary": "baya", "secondary": "aidar", "current": "primary"}
        self.preset_manager.current.speed = 1.0
        self.preset_manager.save_current()
        self.frame.apply_geometry_from_preset(self.preset_manager.current)
        self.frame.show()
        self.voice_box.setCurrentText("Женский — Baya")
        self.speed_box.setCurrentText("1.0 — нормально")
        threading.Thread(target=self.tts.load, args=("baya", 1.0), daemon=True).start()
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

    def add_screenshot(self, pil_image):
        self.image_counter += 1
        name = str(self.image_counter)

        pixmap = pil_to_qpixmap(pil_image)
        thumb = ThumbnailWidget(pixmap, name, self.remove_thumbnail)
        self.gallery_layout.addWidget(thumb)
        self.thumbnails.append(thumb)

        try:
            path = self.session.save_screenshot(pil_image, index=self.image_counter)
            print(f"[SCREENSHOT] Сохранён: {os.path.abspath(path)}")
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
            self.sig_status.emit(f"🧠 OCR #{name}...")
            text = recognize(pil_image)
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
            header = (
                f"# Сессия {self.session.name}\n\n"
                f"Создано: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n"
            )
            self.session.save_text(full_text, header=header)
        except Exception as e:
            print(f"[TEXT] Ошибка сохранения: {e}")

        self.run_tts(full_text)

    def run_tts(self, text):
        if not self.tts.ready:
            self.sig_status.emit("⏳ TTS ещё грузится...")
            return
        try:
            chunks = split_text(text)
            total = len(chunks)
            for i, chunk in enumerate(chunks, 1):
                filename = self.session.audio_path(i)
                self.tts.synthesize(chunk, filename)
                self.sig_status.emit(f"🎙 {i}/{total}")
            self.sig_refresh_audio.emit()
            self.sig_status.emit(f"✅ Готово! Файлов: {total}")
            self.sig_play_all.emit()
        except Exception as e:
            self.sig_status.emit(f"❌ Ошибка TTS: {e}")
            print("Ошибка TTS:", e)

    def refresh_audio_list(self):
        self.audio_list.clear()
        for f in self.session.list_audio():
            self.audio_list.addItem(f)

    def _audio_paths(self):
        if not self.session.audio_dir:
            return []
        return [
            os.path.join(self.session.audio_dir, self.audio_list.item(i).text())
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
        self.preset_manager.current.voices["primary"] = speaker
        self.preset_manager.current.speed = speed
        self.preset_manager.save_current()
        threading.Thread(target=self.tts.load, args=(speaker, speed), daemon=True).start()
        self.status.setText(f"⏳ Загружаю голос {label}...")

    def on_speed_change(self, label):
        speaker = VOICES[self.voice_box.currentText()]
        speed = SPEEDS[label]
        self.preset_manager.current.voices["primary"] = speaker
        self.preset_manager.current.speed = speed
        self.preset_manager.save_current()
        threading.Thread(target=self.tts.load, args=(speaker, speed), daemon=True).start()
        self.status.setText(f"⏳ Загружаю скорость {label}...")

    def quit_app(self):
        try:
            if KEYBOARD_OK:
                keyboard.unhook_all()
        except Exception:
            pass
        try:
            self.preset_manager.save_current()
        except Exception:
            pass
        try:
            self.stop_playback()
        except Exception:
            pass
        try:
            self.widget.close()
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
            self.preset_manager.save_current()
        except Exception:
            pass
        try:
            self.widget.close()
        except Exception:
            pass
        self.frame.close()
        event.accept()
        QApplication.quit()