from PyQt6.QtWidgets import (
    QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

WIDGET_W = 120
WIDGET_H = 45


class Widget(QWidget):
    sig_status = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_panel = parent

        self.setWindowTitle("OCR + TTS")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setFixedSize(WIDGET_W, WIDGET_H)

        self._drag_pos = None
        self._shots_count = 0

        self._build_ui()
        self._restore_pos()

        self.sig_status.connect(self._on_status)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        row = QHBoxLayout()
        row.setSpacing(2)

        self.btn_frame = QPushButton("👁")
        self.btn_frame.setToolTip("Рамка захвата (Ctrl+Alt+Up)")
        self.btn_frame.setFixedSize(28, 24)
        self.btn_frame.setStyleSheet("font-size: 14px; padding: 0;")
        self.btn_frame.clicked.connect(self.parent_panel.toggle_frame)
        row.addWidget(self.btn_frame)

        self.btn_capture = QPushButton("📸")
        self.btn_capture.setToolTip("Снять в очередь (Ctrl+Alt+↓)")
        self.btn_capture.setFixedSize(28, 24)
        self.btn_capture.setStyleSheet("font-size: 14px; padding: 0;")
        self.btn_capture.clicked.connect(self.parent_panel.poly_capture)
        row.addWidget(self.btn_capture)

        self.btn_run = QPushButton("▶")
        self.btn_run.setToolTip("Запустить поликонвейер (Ctrl+Alt+→)")
        self.btn_run.setFixedSize(28, 24)
        self.btn_run.setStyleSheet("font-size: 14px; padding: 0;")
        self.btn_run.clicked.connect(self.parent_panel.poly_run)
        row.addWidget(self.btn_run)

        self.btn_expand = QPushButton("⚙")
        self.btn_expand.setToolTip("Развернуть настройки")
        self.btn_expand.setFixedSize(28, 24)
        self.btn_expand.setStyleSheet("font-size: 14px; padding: 0;")
        self.btn_expand.clicked.connect(self.parent_panel.expand_from_widget)
        row.addWidget(self.btn_expand)

        layout.addLayout(row)

        self.status = QLabel("📸 0 | Готов")
        self.status.setStyleSheet("color:#333; font-size:10px;")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)

        self.setToolTip(
            "Ctrl+Alt+Space — полный цикл\n"
            "Ctrl+Alt+↓ — снять в очередь\n"
            "Ctrl+Alt+→ — запустить поликонвейер\n"
            "Ctrl+Alt+Up — рамка\n"
            "Ctrl+Alt+N — новая сессия"
        )

    def _restore_pos(self):
        preset = self.parent_panel.preset_manager.current
        if not isinstance(preset.widget, dict):
            preset.widget = {}
        pos = preset.widget.setdefault("mini", {"x": None, "y": None})
        x = pos.get("x")
        y = pos.get("y")
        if x is None or y is None:
            x, y = 50, 50
        self.move(x, y)

    def _save_pos(self):
        g = self.geometry()
        preset = self.parent_panel.preset_manager.current
        if not isinstance(preset.widget, dict):
            preset.widget = {}
        preset.widget.setdefault("mini", {})
        preset.widget["mini"]["x"] = g.x()
        preset.widget["mini"]["y"] = g.y()
        self.parent_panel.preset_manager.save_current()

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, "parent_panel"):
            self._save_pos()

    def set_shots_count(self, count: int):
        self._shots_count = count
        self._update_status(self._last_status if hasattr(self, "_last_status") else "Готов")

    def _update_status(self, text: str):
        self.status.setText(f"📸 {self._shots_count} | {text}")

    def _on_status(self, text: str):
        self._last_status = text
        self._update_status(text)

    def update_status(self, text: str):
        self._last_status = text
        self._update_status(text)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        self._save_pos()
        event.accept()