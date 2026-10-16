"""TrayManager: System tray integration for Hover."""

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMenu, QMessageBox, QSystemTrayIcon


class TrayManager(QObject):
    """Manages the system tray icon, context menu, and system tray notifications."""

    snip_requested = pyqtSignal()
    show_quickbar_requested = pyqtSignal()
    unghost_requested = pyqtSignal()
    close_all_requested = pyqtSignal()
    exit_requested = pyqtSignal()

    def __init__(self, icon: QIcon, hotkey_str: str = "Ctrl+Alt+S", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.icon = icon
        self.hotkey_str = hotkey_str

        self.tray_icon = QSystemTrayIcon(self.icon, parent)
        self._snip_action: QAction | None = None
        self._setup_menu()
        self._update_tooltip()
        self.tray_icon.activated.connect(self._on_tray_activated)

    def set_hotkey_str(self, hotkey_str: str) -> None:
        self.hotkey_str = hotkey_str
        self._update_tooltip()
        if self._snip_action:
            self._snip_action.setText(f"✂️  New Snip ({self.hotkey_str})")

    def _update_tooltip(self) -> None:
        self.tray_icon.setToolTip(f"Hover - Pinned Screen Snipping Utility\nHotkey: {self.hotkey_str}")

    def _setup_menu(self) -> None:
        """Create the context menu for the tray icon."""
        menu = QMenu()

        self._snip_action = QAction(f"✂️  New Snip ({self.hotkey_str})", menu)
        self._snip_action.triggered.connect(self.snip_requested.emit)
        menu.addAction(self._snip_action)

        quickbar_action = QAction("📌  Show Quick Bar", menu)
        quickbar_action.triggered.connect(self.show_quickbar_requested.emit)
        menu.addAction(quickbar_action)

        unghost_action = QAction("👻  Un-Ghost All Pins (Ctrl+Alt+G)", menu)
        unghost_action.triggered.connect(self.unghost_requested.emit)
        menu.addAction(unghost_action)

        clear_action = QAction("🗑️  Close All Pinned Snips", menu)
        clear_action.triggered.connect(self.close_all_requested.emit)
        menu.addAction(clear_action)

        menu.addSeparator()

        about_action = QAction("ℹ️  About Hover", menu)
        about_action.triggered.connect(self._show_about)
        menu.addAction(about_action)

        menu.addSeparator()

        exit_action = QAction("❌  Exit", menu)
        exit_action.triggered.connect(self.exit_requested.emit)
        menu.addAction(exit_action)

        self.tray_icon.setContextMenu(menu)

    def show(self) -> None:
        """Display the system tray icon and show a brief introductory balloon notification."""
        self.tray_icon.show()
        self.tray_icon.showMessage(
            "Hover is Active",
            f"Press {self.hotkey_str} or click the Quick Bar to snip and pin.",
            self.icon,
            3500,
        )

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle clicks on the tray icon. Left-click or double-click starts a snip."""
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.snip_requested.emit()

    def _show_about(self) -> None:
        """Display information about Hover."""
        QMessageBox.information(
            None,
            "About Hover",
            "<h3>Hover v1.0</h3>"
            "<p>A lightweight, standalone desktop screenshot utility inspired by Grant Thornton's 'Picture This'.</p>"
            "<p><b>How to use:</b></p>"
            f"<ul>"
            f"<li><b>{self.hotkey_str}</b> or Tray/Quick Bar: Snip a screen region.</li>"
            f"<li><b>Left-Click & Drag:</b> Move pinned window anywhere.</li>"
            f"<li><b>Right-Click or Esc:</b> Close/dismiss pinned window.</li>"
            f"<li><b>Mouse Wheel:</b> Zoom in/out to inspect numbers.</li>"
            f"<li><b>Ctrl+C:</b> Copy pinned image to clipboard.</li>"
            f"</ul>",
        )
