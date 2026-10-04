import os
import json
import time
from dataclasses import dataclass, asdict, field
from typing import Optional


PRESETS_DIR = "presets"

DEFAULT_FRAME = {
    "x": 300,
    "y": 200,
    "width": 600,
    "height": 300,
    "visible": True,
}

DEFAULT_VOICES = {
    "primary": "baya",
    "secondary": "aidar",
    "current": "primary",
}

DEFAULT_SPEED = 1.0

DEFAULT_HOTKEYS = {
    "full_cycle": "ctrl+alt+space",
    "capture_only": "ctrl+alt+s",
    "recognize_only": "ctrl+alt+r",
    "toggle_frame": "ctrl+alt+up",
    "next_voice": "ctrl+alt+right",
    "prev_voice": "ctrl+alt+left",
    "new_session": "ctrl+alt+n",
    "open_settings": "ctrl+alt+o",
}

DEFAULT_WIDGET = {
    "x": 500,
    "y": 100,
    "width": 220,
    "height": 320,
}


@dataclass
class Preset:
    name: str = "default"
    created: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    updated: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))

    frame: dict = field(default_factory=lambda: dict(DEFAULT_FRAME))
    voices: dict = field(default_factory=lambda: dict(DEFAULT_VOICES))
    speed: float = DEFAULT_SPEED
    hotkeys: dict = field(default_factory=lambda: dict(DEFAULT_HOTKEYS))
    widget: dict = field(default_factory=lambda: dict(DEFAULT_WIDGET))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Preset":
        p = cls()
        p.name = data.get("name", "default")
        p.created = data.get("created", p.created)
        p.updated = data.get("updated", p.updated)
        p.frame = {**DEFAULT_FRAME, **data.get("frame", {})}
        p.voices = {**DEFAULT_VOICES, **data.get("voices", {})}
        p.speed = data.get("speed", DEFAULT_SPEED)
        p.hotkeys = {**DEFAULT_HOTKEYS, **data.get("hotkeys", {})}
        p.widget = {**DEFAULT_WIDGET, **data.get("widget", {})}
        return p


class PresetManager:
    def __init__(self, base_dir: str = PRESETS_DIR):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.current: Optional[Preset] = None
        self._load_or_create_default()

    def _preset_path(self, name: str) -> str:
        return os.path.join(self.base_dir, name, "preset.json")

    def _preset_dir(self, name: str) -> str:
        return os.path.join(self.base_dir, name)

    def _load_or_create_default(self):
        if not self.list_presets():
            print("[PRESETS] Нет пресетов — создаю 'default'")
            self.create("default", set_active=True)
        else:
            active_file = os.path.join(self.base_dir, "_active.txt")
            active_name = "default"
            if os.path.isfile(active_file):
                try:
                    with open(active_file, "r", encoding="utf-8") as f:
                        active_name = f.read().strip() or "default"
                except Exception:
                    pass
            if active_name not in self.list_presets():
                active_name = self.list_presets()[0]
            self.load(active_name)

    def list_presets(self) -> list[str]:
        if not os.path.isdir(self.base_dir):
            return []
        return sorted(
            d for d in os.listdir(self.base_dir)
            if os.path.isdir(os.path.join(self.base_dir, d))
            and os.path.isfile(self._preset_path(d))
        )

    def create(self, name: str, set_active: bool = True) -> Preset:
        if name in self.list_presets():
            raise ValueError(f"Пресет '{name}' уже существует")
        os.makedirs(self._preset_dir(name), exist_ok=True)
        preset = Preset(name=name)
        self._save(preset)
        if set_active:
            self.current = preset
            self._write_active(name)
        print(f"[PRESETS] Создан: {name}")
        return preset

    def load(self, name: str) -> Preset:
        path = self._preset_path(name)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Пресет '{name}' не найден")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        preset = Preset.from_dict(data)
        self.current = preset
        self._write_active(name)
        print(f"[PRESETS] Загружен: {name}")
        return preset

    def save_current(self):
        if self.current is None:
            return
        self.current.updated = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save(self.current)

    def delete(self, name: str) -> bool:
        if name == "default":
            print("[PRESETS] Нельзя удалить 'default'")
            return False
        if name not in self.list_presets():
            return False
        import shutil
        shutil.rmtree(self._preset_dir(name))
        print(f"[PRESETS] Удалён: {name}")
        if self.current and self.current.name == name:
            self.load("default")
        return True

    def rename(self, old: str, new: str) -> bool:
        if old == "default":
            print("[PRESETS] Нельзя переименовать 'default'")
            return False
        if old not in self.list_presets():
            return False
        if new in self.list_presets():
            print(f"[PRESETS] Имя '{new}' уже занято")
            return False
        os.rename(self._preset_dir(old), self._preset_dir(new))
        p = self.load(new)
        p.name = new
        self._save(p)
        print(f"[PRESETS] Переименован: {old} -> {new}")
        return True

    def _save(self, preset: Preset):
        os.makedirs(self._preset_dir(preset.name), exist_ok=True)
        path = self._preset_path(preset.name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(preset.to_dict(), f, ensure_ascii=False, indent=2)

    def _write_active(self, name: str):
        active_file = os.path.join(self.base_dir, "_active.txt")
        with open(active_file, "w", encoding="utf-8") as f:
            f.write(name)