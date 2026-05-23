"""Global hotkey manager for Windows using RegisterHotKey + native event filter.

More reliable than keyboard library (no admin rights needed).
Uses pywin32 which is already installed.
"""

from PySide6.QtCore import QAbstractNativeEventFilter
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
import ctypes
from ctypes import wintypes


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


class _WinHotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self):
        super().__init__()
        self._callbacks = {}

    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            try:
                msg = _MSG.from_address(message.__int__())
                if msg.message == 0x0312:  # WM_HOTKEY
                    cb = self._callbacks.get(msg.wParam)
                    if cb:
                        cb()
                        return True, 0
            except Exception:
                pass
        return False, 0

    def add(self, key_id, callback):
        self._callbacks[key_id] = callback

    def remove(self, key_id):
        self._callbacks.pop(key_id, None)


_HOTKEY_MOD = {
    'ctrl': 0x0002,  # MOD_CONTROL
    'shift': 0x0004,  # MOD_SHIFT
    'alt': 0x0001,    # MOD_ALT
    'win': 0x0008,    # MOD_WIN
}

_VK = {chr(i): i for i in range(ord('A'), ord('Z') + 1)}
_VK.update({chr(i): i for i in range(ord('0'), ord('9') + 1)})
for i in range(1, 13):
    _VK[f'f{i}'] = i + 111  # VK_F1 = 112


class HotkeyManager:
    """Register global hotkeys using Windows RegisterHotKey API."""

    def __init__(self):
        import win32gui
        self._win32gui = win32gui
        self._filter = _WinHotkeyFilter()
        self._installed = False
        self._hotkeys = {}
        self._next_id = 1

    def register(self, combo: str, callback):
        """Register a global hotkey.

        Args:
            combo: e.g. 'ctrl+shift+q'
            callback: callable (marshalled to GUI thread automatically)
        """
        parts = combo.lower().split('+')
        mod = 0
        vk = 0
        for p in parts:
            if p in _HOTKEY_MOD:
                mod |= _HOTKEY_MOD[p]
            elif p.upper() in _VK:
                vk = _VK[p.upper()]

        if vk == 0:
            print(f"  无法解析热键: {combo}")
            return

        key_id = self._next_id
        self._next_id += 1

        try:
            self._win32gui.RegisterHotKey(None, key_id, mod, vk)
        except Exception as e:
            print(f"  热键注册失败 [{combo}]: {e}")
            return

        if not self._installed:
            QApplication.instance().installNativeEventFilter(self._filter)
            self._installed = True

        def _wrapper():
            QTimer.singleShot(0, callback)

        self._filter.add(key_id, _wrapper)
        self._hotkeys[combo] = key_id
        print(f"  热键 {combo.upper()} 已注册")

    def unregister_all(self):
        for combo, key_id in self._hotkeys.items():
            try:
                self._win32gui.UnregisterHotKey(None, key_id)
            except Exception:
                pass
        self._filter._callbacks.clear()
        self._hotkeys.clear()
