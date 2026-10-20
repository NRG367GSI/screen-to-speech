import sys

from PyQt6.QtWidgets import QApplication

from preset_manager import PresetManager
from ui.control_panel import ControlPanel


def main():
    app = QApplication(sys.argv)

    from core.lmstudio_control import LMStudioControl
    lms = LMStudioControl()
    if lms.start_server():
        lms.ensure_model()

    preset_manager = PresetManager()

    panel = ControlPanel(preset_manager)
    panel.show()

    try:
        sys.exit(app.exec())
    finally:
        lms.unload_model()
        lms.stop_server()


if __name__ == "__main__":
    main()
    