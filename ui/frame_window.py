import io

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import (
    Qt, QTimer, QRect, QPoint, QBuffer, QByteArray, QIODevice,
    pyqtSignal
)
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QGuiApplication
)

from PIL import Image


class FrameWindow(QWidget):
    BORDER = 10
    HANDLE_SIZE = 22
    MIN_W, MIN_H = 10, 10

    sig_geometry_changed = pyqtSignal()

    def __init__(self, preset, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint
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

    def apply_geometry_from_preset(self, preset):
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

        hs = self.HANDLE_SIZE
        painter.setBrush(QColor(0, 180, 60, 240))
        painter.setPen(QPen(QColor(255, 255, 255, 220), 1))
        painter.drawRect(4, 4, hs, hs)
        painter.setPen(QPen(QColor(255, 255, 255, 240), 2))
        cx, cy = 4 + hs // 2, 4 + hs // 2
        painter.drawLine(cx - 5, cy, cx + 5, cy)
        painter.drawLine(cx, cy - 5, cx, cy + 5)

    def _edge_at(self, pos: QPoint):
        w, h = self.width(), self.height()
        m = self.BORDER
        x, y = pos.x(), pos.y()

        hs = self.HANDLE_SIZE
        if 4 <= x <= 4 + hs and 4 <= y <= 4 + hs:
            return "move"

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
            "move":         Qt.CursorShape.SizeAllCursor,
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
        if edge is None or edge == "move":
            self._drag_pos = gp - self.frameGeometry().topLeft()
            event.accept()
        else:
            self._edge = edge
            self._resize_start = (gp, self.geometry())
            event.accept()

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