import sys
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QTimer
from ui.hotkeys import HotkeyManager


def main():
    app = QApplication(sys.argv)

    w = QWidget()
    w.show()

    mgr = HotkeyManager()
    mgr.fired.connect(lambda name: print(f"✅ FIRED: {name}"))
    mgr.start()

    mgr.register("mono", "ctrl+shift+m")
    mgr.register("up",   "ctrl+shift+up")
    mgr.register("down", "ctrl+shift+down")

    print("Жми Ctrl+Shift+M / Ctrl+Shift+↑ / Ctrl+Shift+↓. Ctrl+C — выход.")

    def _heartbeat():
        print(".", end="", flush=True)

    t = QTimer()
    t.timeout.connect(_heartbeat)
    t.start(2000)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()