"""
Глобальные хоткеи через WinAPI RegisterHotKey (ctypes).

Всё в одном потоке: RegisterHotKey + GetMessageW.
Работает поверх игр. Не требует фокуса. Не требует pywin32.
"""

import ctypes
import threading
from ctypes import wintypes

from PyQt6.QtCore import QObject, pyqtSignal


MOD_ALT      = 0x0001
MOD_CONTROL  = 0x0002
MOD_SHIFT    = 0x0004
MOD_WIN      = 0x0008
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312
WM_APP    = 0x8000
WM_REGISTER   = WM_APP + 1
WM_UNREGISTER = WM_APP + 2
WM_STOP       = WM_APP + 3

VK = {
    "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
    "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
    "a": 0x41, "b": 0x42, "c": 0x43, "d": 0x44, "e": 0x45,
    "f": 0x46, "g": 0x47, "h": 0x48, "i": 0x49, "j": 0x4A,
    "k": 0x4B, "l": 0x4C, "m": 0x4D, "n": 0x4E, "o": 0x4F,
    "p": 0x50, "q": 0x51, "r": 0x52, "s": 0x53, "t": 0x54,
    "u": 0x55, "v": 0x56, "w": 0x57, "x": 0x58, "y": 0x59,
    "z": 0x5A,
    "space": 0x20,
    "down":  0x28,
    "up":    0x26,
    "left":  0x25,
    "right": 0x27,
    "enter": 0x0D,
    "esc":   0x1B,
    "tab":   0x09,
}

MOD_MAP = {
    "alt":   MOD_ALT,
    "ctrl":  MOD_CONTROL,
    "shift": MOD_SHIFT,
    "win":   MOD_WIN,
}


def parse_hotkey(s: str):
    parts = [p.strip().lower() for p in s.split("+") if p.strip()]
    if not parts:
        return None, None
    mods = 0
    vk = None
    for p in parts:
        if p in MOD_MAP:
            mods |= MOD_MAP[p]
        elif p in VK:
            vk = VK[p]
        else:
            return None, None
    if vk is None:
        return None, None
    return mods, vk


class HotkeyManager(QObject):
    fired = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32

        self._thread = None
        self._thread_id = 0
        self._ready = threading.Event()

        self._pending = []      # список (name, hotkey) для регистрации
        self._unregister_requested = False
        self._stop_requested = False

        self._map = {}          # id -> name
        self._next_id = 1
        self._lock = threading.Lock()

    def start(self):
        if self._thread is not None:
            return
        self._ready.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3.0)

    def _run(self):
        user32 = self._user32

        # Создаём очередь сообщений для этого потока
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)

        self._thread_id = self._kernel32.GetCurrentThreadId()
        print(f"[HOTKEY] Поток запущен, thread_id={self._thread_id}")
        self._ready.set()

        while not self._stop_requested:
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret == 0 or ret == -1:
                break

            m = msg.message

            if m == WM_REGISTER:
                with self._lock:
                    pending = list(self._pending)
                    self._pending.clear()
                for name, hotkey in pending:
                    self._do_register(name, hotkey)

            elif m == WM_UNREGISTER:
                self._do_unregister_all()

            elif m == WM_HOTKEY:
                hid = int(msg.wParam)
                name = self._map.get(hid)
                if name:
                    self.fired.emit(name)

            elif m == WM_STOP:
                break

            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        self._do_unregister_all()
        print("[HOTKEY] Поток завершён")

    def _do_register(self, name: str, hotkey: str) -> bool:
        mods, vk = parse_hotkey(hotkey)
        if mods is None:
            print(f"[HOTKEY] {name}: не удалось распарсить '{hotkey}'")
            return False

        mods |= MOD_NOREPEAT
        hid = self._next_id
        self._next_id += 1

        ok = self._user32.RegisterHotKey(
            None,
            ctypes.c_int(hid),
            ctypes.c_uint(mods),
            ctypes.c_uint(vk),
        )
        if not ok:
            err = ctypes.get_last_error() if hasattr(ctypes, "get_last_error") else 0
            print(f"[HOTKEY] {name} ({hotkey}): НЕ зарегистрирован (код {err})")
            return False

        self._map[hid] = name
        print(f"[HOTKEY] {name} ({hotkey}) → id={hid}")
        return True

    def _do_unregister_all(self):
        for hid in list(self._map.keys()):
            self._user32.UnregisterHotKey(None, ctypes.c_int(hid))
        self._map.clear()

    def register(self, name: str, hotkey: str):
        """Запрос на регистрацию — обрабатывается в потоке."""
        if self._thread_id == 0:
            print(f"[HOTKEY] {name}: поток не запущен")
            return
        with self._lock:
            self._pending.append((name, hotkey))
        self._user32.PostThreadMessageW(
            ctypes.c_uint(self._thread_id), WM_REGISTER, 0, 0
        )

    def unregister_all(self):
        if self._thread_id == 0:
            return
        self._user32.PostThreadMessageW(
            ctypes.c_uint(self._thread_id), WM_UNREGISTER, 0, 0
        )

    def stop(self):
        if self._thread_id == 0:
            return
        self._stop_requested = True
        self._user32.PostThreadMessageW(
            ctypes.c_uint(self._thread_id), WM_STOP, 0, 0
        )
        self._thread = None
        self._thread_id = 0