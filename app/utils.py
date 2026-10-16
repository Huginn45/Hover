"""Utility functions for Hover application."""

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QGuiApplication,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)


import sys
from pathlib import Path


def create_app_icon(size: int = 64) -> QIcon:
    """Return the application icon for Hover, loading assets if present or generating procedurally."""
    # Look for saved asset file (supports both script mode and PyInstaller bundle)
    if hasattr(sys, "_MEIPASS"):
        assets_dir = Path(sys._MEIPASS) / "assets"
    else:
        assets_dir = Path(__file__).resolve().parent.parent / "assets"

    ico_path = assets_dir / "icon.ico"
    png_path = assets_dir / "icon.png"

    if ico_path.exists():
        icon = QIcon(str(ico_path))
        if not icon.isNull():
            return icon

    if png_path.exists():
        icon = QIcon(str(png_path))
        if not icon.isNull():
            return icon

    # Fallback: Procedurally generate vector icon
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    margin = size * 0.08
    rect_box = QRect(int(margin), int(margin), int(size - 2 * margin), int(size - 2 * margin))

    # Background rounded rectangle with gradient
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0.0, QColor(37, 99, 235))   # Bright Royal Blue
    gradient.setColorAt(1.0, QColor(79, 70, 229))  # Indigo

    path = QPainterPath()
    corner_radius = size * 0.22
    path.addRoundedRect(
        float(rect_box.x()),
        float(rect_box.y()),
        float(rect_box.width()),
        float(rect_box.height()),
        corner_radius,
        corner_radius,
    )
    painter.fillPath(path, QBrush(gradient))

    # Inner "floating snip" window representation
    inner_margin = size * 0.22
    inner_rect = QRect(
        int(inner_margin),
        int(inner_margin),
        int(size - 2 * inner_margin),
        int(size - 2 * inner_margin),
    )

    inner_path = QPainterPath()
    inner_corner = size * 0.12
    inner_path.addRoundedRect(
        float(inner_rect.x()),
        float(inner_rect.y()),
        float(inner_rect.width()),
        float(inner_rect.height()),
        inner_corner,
        inner_corner,
    )
    painter.fillPath(inner_path, QBrush(QColor(255, 255, 255, 230)))

    # Accent pin/crosshair dot in the center of the inner window
    center_x = size / 2.0
    center_y = size / 2.0
    dot_radius = size * 0.09
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(239, 68, 68)))  # Accent Pin Red
    painter.drawEllipse(QPoint(int(center_x), int(center_y)), int(dot_radius), int(dot_radius))

    # Subtle pin needle line
    needle_pen = QPen(QColor(185, 28, 28), max(1.5, size * 0.04))
    painter.setPen(needle_pen)
    painter.drawLine(
        int(center_x),
        int(center_y + dot_radius * 0.8),
        int(center_x + size * 0.12),
        int(center_y + size * 0.18),
    )

    painter.end()
    return QIcon(pixmap)


def get_virtual_geometry() -> QRect:
    """Return the combined bounding rectangle covering all connected monitors."""
    screens = QGuiApplication.screens()
    if not screens:
        return QRect(0, 0, 1920, 1080)

    virtual_rect = screens[0].geometry()
    for screen in screens[1:]:
        virtual_rect = virtual_rect.united(screen.geometry())
    return virtual_rect


def copy_pixmap_to_clipboard(pixmap: QPixmap) -> None:
    """Copy a QPixmap to the system clipboard."""
    clipboard = QGuiApplication.clipboard()
    if clipboard:
        clipboard.setPixmap(pixmap)
