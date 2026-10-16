"""Hover: Standalone Desktop Screenshot Utility.

Inspired by Grant Thornton's 'Picture This'.
Allows snipping any screen region and pinning it permanently on top of all applications.
"""

import sys
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QGuiApplication, QPixmap
from PyQt6.QtWidgets import QApplication, QWidget

from app.canvas import PinnedCanvas
from app.hotkey import GlobalHotkeyManager
from app.overlay import SnippingOverlay
from app.quick_bar import QuickBar
from app.tray import TrayManager
from app.utils import create_app_icon


class HoverApp:
    """Master controller managing tray, hotkeys, overlays, quick bar, and pinned canvases."""

    def __init__(self, qapp: QApplication) -> None:
        self.qapp = qapp
        self.app_icon = create_app_icon(size=64)
        self.qapp.setWindowIcon(self.app_icon)

        # Track all active pinned canvas instances
        self.pinned_canvases: list[PinnedCanvas] = []
        self._quickbar_was_visible = False

        # Persistent hidden window for Windows message routing
        self._listener_widget = QWidget()
        self._listener_widget.hide()

        # 1. Initialize Global Hotkeys
        self.hotkey_mgr = GlobalHotkeyManager()
        self.hotkey_mgr.activated.connect(self.trigger_snip)
        self.hotkey_mgr.unghost_requested.connect(self.unghost_all_pins)
        bound_hotkeys = self.hotkey_mgr.register_all_available(hwnd=int(self._listener_widget.winId()))
        if not bound_hotkeys:
            bound_hotkeys = self.hotkey_mgr.register_all_available(hwnd=0)

        primary_hotkey = bound_hotkeys[0] if bound_hotkeys else "Ctrl+Alt+S"
        hotkeys_display = " or ".join(bound_hotkeys) if bound_hotkeys else "Tray Only"

        # 2. Initialize Snipping Overlay
        self.overlay = SnippingOverlay()
        self.overlay.snippet_captured.connect(self.on_snippet_captured)
        self.overlay.cancelled.connect(self._on_snip_cancelled)

        # 3. Initialize Floating Quick Bar (immediate on-screen feedback)
        self.quick_bar = QuickBar(self.app_icon, hotkey_label=primary_hotkey)
        self.quick_bar.snip_requested.connect(self.trigger_snip)
        self.quick_bar.clear_pins_requested.connect(self.close_all_pins)
        self.quick_bar.unghost_requested.connect(self.unghost_all_pins)
        self.quick_bar.minimize_requested.connect(self.quick_bar.hide)
        self.quick_bar.quit_requested.connect(self.quit)
        self._position_quick_bar()
        self.quick_bar.show()

        # 4. Initialize System Tray
        self.tray = TrayManager(self.app_icon, hotkey_str=hotkeys_display)
        self.tray.snip_requested.connect(self.trigger_snip)
        self.tray.show_quickbar_requested.connect(self._restore_quick_bar)
        self.tray.unghost_requested.connect(self.unghost_all_pins)
        self.tray.close_all_requested.connect(self.close_all_pins)
        self.tray.exit_requested.connect(self.quit)
        self.tray.show()

        # 5. Output informative console banner
        self._print_startup_banner(bound_hotkeys)

    def _position_quick_bar(self) -> None:
        """Position the QuickBar horizontally centered near the top of the primary screen."""
        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.quick_bar.width()) // 2
            y = geo.y() + 30
            self.quick_bar.move(x, y)

    def _restore_quick_bar(self) -> None:
        """Show and bring QuickBar to foreground."""
        self.quick_bar.show()
        self.quick_bar.raise_()
        self.quick_bar.activateWindow()

    def _print_startup_banner(self, hotkeys: list[str]) -> None:
        """Print clear startup diagnostic information in the terminal."""
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

        keys_str = ", ".join(hotkeys) if hotkeys else "Tray Menu / Quick Bar"
        banner = f"""
===================================================================
  HOVER - Desktop Screenshot & Pinned Window Utility
===================================================================
  [+] Status: Active & Running
  [+] Active Hotkey(s): {keys_str}
  [+] On-Screen Quick Bar: Visible (near top of screen)
  [+] System Tray: Active in taskbar notification area

  HOW TO USE:
  * Press {keys_str} OR click [Snip] on the Quick Bar
  * Drag a box over any screen area to snip and pin
  * Left-click & drag the pinned window to move it
  * Right-click any pin for Diff Slider, Opacity/Ghost, Highlight, Copy, Save
  * Press 'D' on a pin to toggle Diff Slider (Before & After comparison)
  * 'Ctrl + Shift + Wheel' to adjust pin Opacity (or 'Ctrl + G' for Ghost Mode)
  * 'Ctrl + Alt + G' to Un-Ghost all pins anytime
  * Right-click or press 'Esc' on any pinned snip to dismiss it
  * Mouse wheel over a snip to zoom in/out | 'Ctrl + C' to copy
===================================================================
"""
        try:
            print(banner, flush=True)
        except Exception:
            pass

    def trigger_snip(self) -> None:
        """Start a new snipping operation, hiding the QuickBar temporarily from screenshot."""
        self._quickbar_was_visible = self.quick_bar.isVisible()
        if self._quickbar_was_visible:
            self.quick_bar.hide()
            QApplication.processEvents()

        self.overlay.start_capture()

    def on_snippet_captured(self, pixmap: QPixmap, global_pos: QPoint) -> None:
        """Spawn a new borderless, always-on-top PinnedCanvas at the captured coordinates."""
        if self._quickbar_was_visible:
            self.quick_bar.show()

        canvas = PinnedCanvas(pixmap=pixmap, initial_pos=global_pos)
        canvas.closed.connect(self._on_canvas_closed)
        canvas.ghost_state_changed.connect(self._sync_ghost_ui)
        self.pinned_canvases.append(canvas)
        canvas.show()
        canvas.raise_()
        canvas.activateWindow()

    def _on_snip_cancelled(self) -> None:
        """Restore QuickBar if capture was cancelled."""
        if self._quickbar_was_visible:
            self.quick_bar.show()

    def _on_canvas_closed(self, canvas: PinnedCanvas) -> None:
        """Remove canvas from active list when dismissed."""
        if canvas in self.pinned_canvases:
            self.pinned_canvases.remove(canvas)
        self._sync_ghost_ui()

    def _sync_ghost_ui(self) -> None:
        """Show un-ghost button on QuickBar if any pins are click-through."""
        has_ghost = any(c.is_ghost_mode for c in self.pinned_canvases)
        self.quick_bar.unghost_btn.setVisible(has_ghost)
        self.quick_bar.adjustSize()

    def unghost_all_pins(self) -> None:
        """Restore full input interactivity to all click-through pins."""
        for canvas in self.pinned_canvases:
            if canvas.is_ghost_mode:
                canvas.toggle_ghost_mode(False)
        self._sync_ghost_ui()

    def close_all_pins(self) -> None:
        """Dismiss and close all active pinned floating canvases."""
        for canvas in list(self.pinned_canvases):
            canvas.close()
        self.pinned_canvases.clear()
        self._sync_ghost_ui()

    def quit(self) -> None:
        """Clean shutdown."""
        self.hotkey_mgr.unregister_all()
        self.close_all_pins()
        self.quick_bar.close()
        self.qapp.quit()


def main() -> None:
    if sys.platform == "win32":
        try:
            import ctypes
            # Enable Per-Monitor DPI Awareness V2 (-4) before creating QApplication
            # Without this, Windows DWM forces bitmap stretching and blurs/zooms the snip overlay!
            try:
                ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
            except Exception:
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(2)
                except Exception:
                    pass

            # Explicit AppUserModelID ensures Windows taskbar displays the app icon
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("hover.screenshot.utility.1.0")
        except Exception:
            pass

    # High-DPI rounding policy for multi-monitor setups
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    app = QApplication(sys.argv)
    app.setApplicationName("Hover")
    app.setApplicationDisplayName("Hover")
    app.setQuitOnLastWindowClosed(False)  # Keep running in background

    hover_app = HoverApp(app)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
