import os
import time
import shutil


SESSIONS_DIR = "sessions"


class Session:
    def __init__(self, base_dir: str = SESSIONS_DIR):
        self.base_dir = base_dir
        self.path = None
        self.screenshots_dir = None
        self.audio_dir = None
        self.text_path = None
        self.manifest_path = None
        self.short_id = None
        self._counter = 0
        os.makedirs(self.base_dir, exist_ok=True)

    def create(self) -> str:
        stamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        short_id = time.strftime("%H%M%S")
        path = os.path.join(self.base_dir, stamp)

        suffix = 1
        original = path
        while os.path.exists(path):
            path = f"{original}_{suffix}"
            suffix += 1

        os.makedirs(path, exist_ok=True)
        os.makedirs(os.path.join(path, "screenshots"), exist_ok=True)
        os.makedirs(os.path.join(path, "audio"), exist_ok=True)

        self.path = path
        self.screenshots_dir = os.path.join(path, "screenshots")
        self.audio_dir = os.path.join(path, "audio")
        self.text_path = os.path.join(path, "text.md")
        self.manifest_path = os.path.join(path, "manifest.json")
        self.short_id = short_id
        self._counter = 0

        print(f"[SESSION] Создана: {os.path.abspath(path)} (id={short_id})")
        return path

    def next_screenshot_path(self) -> str:
        if self.screenshots_dir is None:
            raise RuntimeError("Сессия не создана. Вызовите create().")
        self._counter += 1
        filename = f"{self._counter:04d}.png"
        return os.path.join(self.screenshots_dir, filename)

    def screenshot_path(self, index: int) -> str:
        if self.screenshots_dir is None:
            raise RuntimeError("Сессия не создана. Вызовите create().")
        return os.path.join(self.screenshots_dir, f"{index:04d}.png")

    def audio_path(self, index: int) -> str:
        if self.audio_dir is None:
            raise RuntimeError("Сессия не создана. Вызовите create().")
        return os.path.join(self.audio_dir, f"part_{index:03d}.wav")

    def list_audio(self) -> list:
        if self.audio_dir is None or not os.path.isdir(self.audio_dir):
            return []
        return sorted(
            f for f in os.listdir(self.audio_dir) if f.endswith(".wav")
        )

    def save_text(self, text: str, header: str = None):
        if self.text_path is None:
            raise RuntimeError("Сессия не создана. Вызовите create().")
        with open(self.text_path, "w", encoding="utf-8") as f:
            if header:
                f.write(header)
            f.write(text)
        print(f"[SESSION] Текст сохранён: {os.path.abspath(self.text_path)}")

    def save_screenshot(self, pil_image, index: int = None) -> str:
        if index is None:
            path = self.next_screenshot_path()
        else:
            path = self.screenshot_path(index)
        pil_image.save(path, "PNG")
        print(f"[SESSION] Скриншот сохранён: {os.path.abspath(path)}")
        return path

    def open_folder(self):
        if self.path and os.path.isdir(self.path):
            os.startfile(os.path.abspath(self.path))

    def clear(self):
        self.path = None
        self.screenshots_dir = None
        self.audio_dir = None
        self.text_path = None
        self.manifest_path = None
        self.short_id = None
        self._counter = 0

    def save_manifest(self, data: dict):
        if self.manifest_path is None:
            raise RuntimeError("Сессия не создана. Вызовите create().")
        import json
        payload = {
            "session": os.path.basename(self.path) if self.path else "",
            "short_id": self.short_id,
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        payload.update(data)
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"[SESSION] Манифест сохранён: {os.path.abspath(self.manifest_path)}")

    @property
    def name(self) -> str:
        return os.path.basename(self.path) if self.path else ""