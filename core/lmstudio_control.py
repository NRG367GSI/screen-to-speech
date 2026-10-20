import subprocess
import time


class LMStudioControl:
    def __init__(self, lms_path: str = "lms", model_key: str = "paddleocr-vl-1.6",
                 model_identifier: str = "paddleocr-vl-1.6-q8_0"):
        self.lms_path = lms_path
        self.model_key = model_key
        self.model_identifier = model_identifier
        self._started_by_us = False

    def _run(self, *args, timeout=60) -> tuple[bool, str]:
        try:
            r = subprocess.run(
                [self.lms_path, *args],
                capture_output=True, text=True, timeout=timeout,
                shell=False,
            )
            out = (r.stdout or "") + (r.stderr or "")
            return r.returncode == 0, out.strip()
        except Exception as e:
            return False, str(e)

    def is_server_running(self) -> bool:
        """Проверяет, запущен ли HTTP-сервер (по коду возврата lms server status)."""
        ok, _ = self._run("server", "status")
        return ok

    def is_model_loaded(self) -> bool:
        """Проверяет, загружена ли модель с нужным идентификатором."""
        ok, out = self._run("ps", "--json")
        if not ok:
            return False
        # Ищем identifier в JSON-выводе
        return self.model_identifier in out

    def _wait_for_server(self, timeout: int = 15) -> bool:
        """Ждёт, пока порт 1234 начнёт отвечать."""
        import socket
        for i in range(timeout):
            try:
                with socket.create_connection(("127.0.0.1", 1234), timeout=1):
                    return True
            except OSError:
                time.sleep(1)
        return False

    def start_server(self) -> bool:
        if self.is_server_running():
            print("[LMS] Сервер уже запущен")
            return True
        print("[LMS] Запускаю сервер...")
        ok, out = self._run("server", "start")
        if not ok:
            print(f"[LMS] Ошибка запуска: {out[:200]}")
            return False
        if self._wait_for_server(15):
            self._started_by_us = True
            print("[LMS] Сервер запущен и отвечает")
            return True
        print("[LMS] Сервер не поднялся за 15 секунд")
        return False

    def ensure_model(self) -> bool:
        """Гарантирует, что модель загружена с нужным идентификатором."""
        if self.is_model_loaded():
            print(f"[LMS] Модель уже загружена: {self.model_identifier}")
            return True

        print(f"[LMS] Загружаю модель {self.model_key} как {self.model_identifier}...")
        ok, out = self._run(
            "load", self.model_key,
            "--identifier", self.model_identifier,
            timeout=120,
        )
        if ok:
            print(f"[LMS] Модель загружена: {out[:150]}")
            return True
        print(f"[LMS] Ошибка загрузки модели: {out[:300]}")
        return False

    def stop_server(self):
        if not self._started_by_us:
            print("[LMS] Сервер запускали не мы — не останавливаю")
            return
        print("[LMS] Останавливаю сервер...")
        self._run("server", "stop")
        self._started_by_us = False

    def unload_model(self):
        print("[LMS] Выгружаю модель...")
        self._run("unload", self.model_identifier)