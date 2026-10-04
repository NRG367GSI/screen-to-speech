from PyQt6.QtWidgets import (
    QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal


WIDGET_W = 260
WIDGET_H = 56


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
        self.btn_frame.setToolTip("Рамка захвата")
        self.btn_frame.clicked.connect(self.parent_panel.toggle_frame)
        row.addWidget(self.btn_frame)

        self.btn_cycle = QPushButton("▶")
        self.btn_cycle.setToolTip("Полный цикл: снять + распознать + озвучить")
        self.btn_cycle.clicked.connect(self.parent_panel.full_cycle)
        row.addWidget(self.btn_cycle)

        self.btn_repeat = QPushButton("🔁")
        self.btn_repeat.setToolTip("Повторить озвучку текущей сессии")
        self.btn_repeat.clicked.connect(self.parent_panel.play_all)
        row.addWidget(self.btn_repeat)

        self.btn_new = QPushButton("🆕")
        self.btn_new.setToolTip("Новая сессия")
        self.btn_new.clicked.connect(self.parent_panel.new_session)
        row.addWidget(self.btn_new)

        self.btn_expand = QPushButton("⚙")
        self.btn_expand.setToolTip("Развернуть настройки")
        self.btn_expand.clicked.connect(self.parent_panel.expand_from_widget)
        row.addWidget(self.btn_expand)

        layout.addLayout(row)

        self.status = QLabel("Готов")
        self.status.setStyleSheet("color:#333; font-size:10px;")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)

        self.setToolTip(
            "Ctrl+Alt+Space — полный цикл\n"
            "Ctrl+Alt+Up — рамка\n"
            "Ctrl+Alt+←/→ — голос\n"
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

    def _on_status(self, text: str):
        self.status.setText(text)

    def update_status(self, text: str):
        self.status.setText(text)

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