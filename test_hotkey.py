import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
VK_M = 0x4D

ok = user32.RegisterHotKey(None, 1, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, VK_M)
print(f"RegisterHotKey ok={ok} err={ctypes.get_last_error()}")

msg = wintypes.MSG()
print("Жми Ctrl+Shift+M, 5 раз (или Ctrl+C для выхода)...")
count = 0
while count < 5:
    ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
    if ret == 0:
        break
    if msg.message == WM_HOTKEY:
        print(f"✅ WM_HOTKEY id={msg.wParam}")
        count += 1

user32.UnregisterHotKey(None, 1)