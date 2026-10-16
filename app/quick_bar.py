"""QuickBar: Floating on-screen launcher toolbar for Hover."""

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QMouseEvent, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class QuickBar(QWidget):
    """A sleek floating toolbar that gives immediate on-screen access to Hover actions."""

    snip_requested = pyqtSignal()
    clear_pins_requested = pyqtSignal()
    unghost_requested = pyqtSignal()
    minimize_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, icon: QIcon, hotkey_label: str = "Ctrl+Alt+S", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.icon = icon
        self.hotkey_label = hotkey_label

        self._is_dragging = False
        self._drag_start_pos = QPoint()

        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)

        # Title Label
        title_label = QLabel("📌 Hover")
        title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #60a5fa; background: transparent;")
        layout.addWidget(title_label)

        # Snip Button
        self.snip_btn = QPushButton(f"✂️ Snip ({self.hotkey_label})")
        self.snip_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        self.snip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.snip_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
        """)
        self.snip_btn.clicked.connect(self.snip_requested.emit)
        layout.addWidget(self.snip_btn)

        # Clear Pins Button
        self.clear_btn = QPushButton("🗑️ Clear")
        self.clear_btn.setFont(QFont("Segoe UI", 9))
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 6px 10px;
            }
            QPushButton:hover {
                background-color: #475569;
                color: #ffffff;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_pins_requested.emit)
        layout.addWidget(self.clear_btn)

        # Un-Ghost Button (active when ghost pins exist)
        self.unghost_btn = QPushButton("👻 Un-Ghost")
        self.unghost_btn.setToolTip("Un-ghost click-through pins (Ctrl+Alt+G)")
        self.unghost_btn.setFont(QFont("Segoe UI", 9))
        self.unghost_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.unghost_btn.setStyleSheet("""
            QPushButton {
                background-color: #475569;
                color: #f8fafc;
                border: 1px solid #64748b;
                border-radius: 6px;
                padding: 6px 10px;
            }
            QPushButton:hover {
                background-color: #64748b;
            }
        """)
        self.unghost_btn.clicked.connect(self.unghost_requested.emit)
        self.unghost_btn.hide()
        layout.addWidget(self.unghost_btn)

        # Hide to tray button
        min_btn = QPushButton("—")
        min_btn.setToolTip("Minimize to System Tray")
        min_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        min_btn.setFixedSize(26, 26)
        min_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #ffffff;
            }
        """)
        min_btn.clicked.connect(self.minimize_requested.emit)
        layout.addWidget(min_btn)

        # Close/Exit button
        close_btn = QPushButton("✕")
        close_btn.setToolTip("Exit Hover")
        close_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self.quit_requested.emit)
        layout.addWidget(close_btn)

        self.adjustSize()

    def update_hotkey_label(self, label: str) -> None:
        """Update button text with active hotkey."""
        self.hotkey_label = label
        self.snip_btn.setText(f"✂️ Snip ({label})")
        self.adjustSize()

    def paintEvent(self, event) -> None:
        """Draw dark translucent rounded pill background with subtle glow border."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        rect = self.rect()
        path.addRoundedRect(1.0, 1.0, float(rect.width() - 2), float(rect.height() - 2), 12.0, 12.0)

        # Dark sleek background
        painter.fillPath(path, QColor(15, 23, 42, 235))  # Slate 900 translucent

        # Subtle blue accent border
        from PyQt6.QtGui import QPen
        painter.strokePath(path, QPen(QColor(59, 130, 246, 160), 1.5))
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Allow dragging the quick bar anywhere on screen."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_start_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            event.accept()
