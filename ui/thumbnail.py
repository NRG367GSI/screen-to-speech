from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap


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

        self.image_label = QLabel()
        self.image_label.setPixmap(pixmap.scaled(
            160, 110,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label)

    def set_pixmap(self, pixmap: QPixmap):
        self.image_label.setPixmap(pixmap.scaled(
            160, 110,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))