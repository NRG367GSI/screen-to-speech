import sys

from PyQt6.QtWidgets import QApplication

from preset_manager import PresetManager
from ui.control_panel import ControlPanel


def main():
    app = QApplication(sys.argv)

    preset_manager = PresetManager()

    panel = ControlPanel(preset_manager)
    panel.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
    