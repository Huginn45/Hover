"""Global hotkey listener using native Windows API via ctypes and QAbstractNativeEventFilter."""

import ctypes
import sys
from typing import Any, Callable
from PyQt6.QtCore import QAbstractNativeEventFilter, QObject, pyqtSignal

# Windows-specific constants
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

# Virtual key codes
VK_S = 0x53
VK_X = 0x58
VK_G = 0x47
VK_F8 = 0x77
VK_F9 = 0x78

HOTKEY_UNGHOST_ID = 9200


class _Win32EventFilter(QAbstractNativeEventFilter):
    """Filters native Windows messages to detect WM_HOTKEY events."""

    def __init__(self, handler: Callable[[int], bool]) -> None:
        super().__init__()
        self.handler = handler

    def nativeEventFilter(self, event_type: Any, message: Any) -> tuple[bool, int]:
        if sys.platform == "win32" and message:
            try:
                import ctypes.wintypes

                msg = ctypes.wintypes.MSG.from_address(int(message))
                if msg.message == WM_HOTKEY:
                    if self.handler(msg.wParam):
                        return True, 0
            except Exception:
                pass
        return False, 0


class GlobalHotkeyManager(QObject):
    """Manages system-wide global hotkeys with automatic conflict detection and fallbacks."""

    activated = pyqtSignal()          # Trigger snip
    unghost_requested = pyqtSignal()  # Un-ghost click-through pins (Ctrl+Alt+G)

    DEFAULT_CANDIDATES = [
        ("Ctrl+Shift+S", MOD_CONTROL | MOD_SHIFT, VK_S),
        ("Ctrl+Alt+S", MOD_CONTROL | MOD_ALT, VK_S),
        ("Alt+Shift+S", MOD_ALT | MOD_SHIFT, VK_S),
        ("F8", 0, VK_F8),
        ("Ctrl+Shift+X", MOD_CONTROL | MOD_SHIFT, VK_X),
    ]

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._filter: _Win32EventFilter | None = None
        self._registered_snip_hotkeys: dict[int, str] = {}
        self._hwnd: int = 0
        self._base_id: int = 9100

    def register_all_available(self, hwnd: int = 0) -> list[str]:
        """Try to register candidate hotkeys and return list of successfully bound key names."""
        if sys.platform != "win32":
            return []

        self._hwnd = hwnd
        user32 = ctypes.windll.user32
        success_names: list[str] = []

        # 1. Register Snip Hotkeys
        for idx, (name, mod, vk) in enumerate(self.DEFAULT_CANDIDATES):
            hotkey_id = self._base_id + idx
            user32.UnregisterHotKey(self._hwnd, hotkey_id)

            res = user32.RegisterHotKey(self._hwnd, hotkey_id, mod | MOD_NOREPEAT, vk)
            if res != 0:
                self._registered_snip_hotkeys[hotkey_id] = name
                success_names.append(name)

        # 2. Register Global Un-Ghost Hotkey (Ctrl + Alt + G)
        user32.UnregisterHotKey(self._hwnd, HOTKEY_UNGHOST_ID)
        user32.RegisterHotKey(self._hwnd, HOTKEY_UNGHOST_ID, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_G)

        # Install Event Filter
        if self._registered_snip_hotkeys:
            from PyQt6.QtWidgets import QApplication

            app = QApplication.instance()
            if app and self._filter is None:
                self._filter = _Win32EventFilter(self._handle_native_hotkey)
                app.installNativeEventFilter(self._filter)

        return success_names

    def _handle_native_hotkey(self, hotkey_id: int) -> bool:
        if hotkey_id == HOTKEY_UNGHOST_ID:
            self.unghost_requested.emit()
            return True
        elif hotkey_id in self._registered_snip_hotkeys:
            self.activated.emit()
            return True
        return False

    def unregister_all(self) -> None:
        """Unregister all hotkeys and clean up."""
        if sys.platform == "win32":
            from PyQt6.QtWidgets import QApplication

            app = QApplication.instance()
            if app and self._filter:
                app.removeNativeEventFilter(self._filter)
                self._filter = None

            user32 = ctypes.windll.user32
            for hotkey_id in list(self._registered_snip_hotkeys.keys()):
                user32.UnregisterHotKey(self._hwnd, hotkey_id)
            user32.UnregisterHotKey(self._hwnd, HOTKEY_UNGHOST_ID)

            self._registered_snip_hotkeys.clear()

    @property
    def registered_names(self) -> list[str]:
        return list(self._registered_snip_hotkeys.values())

    @property
    def primary_hotkey(self) -> str:
        names = self.registered_names
        return names[0] if names else "None"
