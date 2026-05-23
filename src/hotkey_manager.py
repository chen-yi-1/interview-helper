"""Global hotkey manager for Windows.

Uses keyboard library first (simple API).
If admin rights are missing, falls back to RegisterHotKey + native event filter.
"""

import sys
from PySide6.QtCore import QTimer


class HotkeyManager:
    """Register global hotkeys that work when app is not focused."""

    def __init__(self, parent=None):
        self._parent = parent
        self._hotkeys = {}
        self._fallback = False

    def register(self, combo: str, callback):
        """Register a global hotkey.

        Args:
            combo: e.g. 'ctrl+shift+h'
            callback: callable (will be marshalled to GUI thread)
        """
        self._hotkeys[combo] = callback
        self._try_register_keyboard(combo, callback)

    def _try_register_keyboard(self, combo, callback):
        try:
            import keyboard
            def _wrapper():
                QTimer.singleShot(0, callback)
            keyboard.add_hotkey(combo, _wrapper, suppress=True)
            print(f"  热键 {combo.upper()} 已注册 (keyboard)")
        except Exception as e:
            print(f"  keyboard 热键失败 ({e}), 使用 WinAPI 备用")
            self._register_winapi(combo, callback)

    def _register_winapi(self, combo, callback):
        self._fallback = True
        from PySide6.QtCore import QAbstractNativeEventFilter
        import win32con, win32gui, ctypes, ctypes.wintypes

        # Map combo to modifier + vk
        parts = combo.lower().split('+')
        mod = 0
        vk = 0
        for p in parts:
            if p == 'ctrl':
                mod |= win32con.MOD_CONTROL
            elif p == 'shift':
                mod |= win32con.MOD_SHIFT
            elif p == 'alt':
                mod |= win32con.MOD_ALT
            elif p == 'win':
                mod |= win32con.MOD_WIN
            elif len(p) == 1:
                vk = ord(p.upper())
            elif p.startswith('f') and len(p) <= 3:
                vk = int(p[1:]) + 111  # VK_F1 = 112

        if vk == 0:
            print(f"  无法解析热键: {combo}")
            return

        class MSG(ctypes.Structure):
            _fields_ = [
                ("hwnd", ctypes.wintypes.HWND),
                ("message", ctypes.wintypes.UINT),
                ("wParam", ctypes.wintypes.WPARAM),
                ("lParam", ctypes.wintypes.LPARAM),
                ("time", ctypes.wintypes.DWORD),
                ("pt", ctypes.wintypes.POINT),
            ]

        key_id = hash(combo) & 0x7FFFFFFF
        win32gui.RegisterHotKey(None, key_id, mod, vk)

        class _Filter(QAbstractNativeEventFilter):
            def nativeEventFilter(_, eventType, message):
                if eventType == b"windows_generic_MSG":
                    try:
                        msg = MSG.from_address(message.__int__())
                        if msg.message == win32con.WM_HOTKEY and msg.wParam == key_id:
                            QTimer.singleShot(0, callback)
                            return True, 0
                    except Exception:
                        pass
                return False, 0

        self._filter = _Filter()
        from PySide6.QtWidgets import QApplication
        QApplication.instance().installNativeEventFilter(self._filter)
        print(f"  热键 {combo.upper()} 已注册 (WinAPI)")

    def unregister_all(self):
        if self._fallback:
            import win32gui
            for combo in self._hotkeys:
                key_id = hash(combo) & 0x7FFFFFFF
                try:
                    win32gui.UnregisterHotKey(None, key_id)
                except Exception:
                    pass
        else:
            try:
                import keyboard
                keyboard.unhook_all()
            except Exception:
                pass
        self._hotkeys.clear()
