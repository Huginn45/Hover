"""SnippingOverlay: Fullscreen dimmed overlay for rectangular region selection with native High-DPI preservation."""

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QGuiApplication,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QScreen,
)
from PyQt6.QtWidgets import QWidget

from app.utils import get_virtual_geometry


class SnippingOverlay(QWidget):
    """Fullscreen dimmed overlay covering all monitors to capture a screen region at 100% native resolution."""

    snippet_captured = pyqtSignal(QPixmap, QPoint)  # (cropped_pixmap, global_top_left)
    cancelled = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._virtual_rect = QRect()
        # Per-screen raw hardware framebuffers
        self._screen_shots: dict[QScreen, QPixmap] = {}

        self._origin_point = QPoint()
        self._current_point = QPoint()
        self._is_selecting = False

        self._dim_color = QColor(0, 0, 0, 110)
        self._border_pen = QPen(QColor(59, 130, 246), 2)

        self._setup_window()

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def start_capture(self) -> None:
        """Capture native GPU framebuffers for each monitor before showing the dimmed overlay."""
        # Grab pristine hardware framebuffer for each monitor at native DPI BEFORE window changes
        self._screen_shots.clear()
        for screen in QGuiApplication.screens():
            self._screen_shots[screen] = screen.grabWindow(0)

        self._virtual_rect = get_virtual_geometry()
        self.setGeometry(self._virtual_rect)

        self._origin_point = QPoint()
        self._current_point = QPoint()
        self._is_selecting = False

        self.show()
        self.raise_()
        self.activateWindow()

    # --------------------------------------------------------------------------
    # Paint Events
    # --------------------------------------------------------------------------
    def paintEvent(self, event) -> None:
        if not self._screen_shots:
            return

        painter = QPainter(self)
        # Disable bilinear smoothing for exact 1:1 hardware pixel blitting
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)

        # 1. Draw each monitor's native capture at exact screen position
        for screen, shot in self._screen_shots.items():
            screen_geo = screen.geometry()
            offset_pos = screen_geo.topLeft() - self._virtual_rect.topLeft()
            painter.drawPixmap(offset_pos, shot)

        # 2. Draw dimming layer across whole virtual desktop
        painter.fillRect(self.rect(), self._dim_color)

        # 3. If currently dragging a selection, reveal clear original content
        if self._is_selecting:
            selection_rect = QRect(self._origin_point, self._current_point).normalized()

            if selection_rect.width() > 1 and selection_rect.height() > 1:
                # Re-paint clear screenshot inside selection box from each intersecting monitor
                for screen, shot in self._screen_shots.items():
                    screen_geo = screen.geometry()
                    screen_rel_geo = screen_geo.translated(-self._virtual_rect.topLeft())
                    intersect = selection_rect.intersected(screen_rel_geo)
                    if not intersect.isEmpty():
                        # Map intersection to screen-local coordinates
                        target_rect = intersect
                        source_rect = intersect.translated(-screen_rel_geo.topLeft())
                        painter.drawPixmap(target_rect, shot, source_rect)

                # Draw bounding box outline
                painter.setPen(self._border_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(selection_rect)

                # Draw dimension badge
                self._draw_dimension_badge(painter, selection_rect)

        painter.end()

    def _draw_dimension_badge(self, painter: QPainter, rect: QRect) -> None:
        """Render a small HUD badge displaying the selection dimensions."""
        text = f"{rect.width()} × {rect.height()} px"
        font = QFont("Segoe UI", 9, QFont.Weight.DemiBold)
        painter.setFont(font)

        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()

        badge_padding_x = 8
        badge_padding_y = 4
        badge_w = text_width + (badge_padding_x * 2)
        badge_h = text_height + (badge_padding_y * 2)

        badge_x = rect.right() - badge_w
        badge_y = rect.bottom() + 6

        if badge_y + badge_h > self.height():
            badge_y = rect.bottom() - badge_h - 6
        if badge_x < 0:
            badge_x = rect.left()

        badge_rect = QRect(badge_x, badge_y, badge_w, badge_h)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(15, 23, 42, 220)))
        painter.drawRoundedRect(badge_rect, 4.0, 4.0)

        painter.setPen(QColor(255, 255, 255))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, text)

    # --------------------------------------------------------------------------
    # Mouse & Keyboard Events
    # --------------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin_point = event.position().toPoint()
            self._current_point = self._origin_point
            self._is_selecting = True
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            self.cancel_capture()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_selecting:
            self._current_point = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._is_selecting = False
            self.hide()

            selection_rect = QRect(self._origin_point, self._current_point).normalized()

            if selection_rect.width() > 4 and selection_rect.height() > 4:
                cropped = self._crop_native_region(selection_rect)
                global_pos = self._virtual_rect.topLeft() + selection_rect.topLeft()
                self.snippet_captured.emit(cropped, global_pos)
            else:
                self.cancelled.emit()

    def _crop_native_region(self, selection_rect: QRect) -> QPixmap:
        """Crop the exact physical screen pixels preserving 100% native clarity and DPI."""
        global_rect = selection_rect.translated(self._virtual_rect.topLeft())
        target_screen = QGuiApplication.screenAt(global_rect.center()) or QGuiApplication.primaryScreen()
        dpr = target_screen.devicePixelRatio()

        screen_geo = target_screen.geometry()
        local_x = global_rect.x() - screen_geo.x()
        local_y = global_rect.y() - screen_geo.y()

        shot = self._screen_shots.get(target_screen)
        if shot and not shot.isNull():
            # Physical pixel coordinates in the native buffer
            phys_x = int(round(local_x * dpr))
            phys_y = int(round(local_y * dpr))
            phys_w = int(round(global_rect.width() * dpr))
            phys_h = int(round(global_rect.height() * dpr))

            # Clamp safely within physical buffer bounds
            phys_x = max(0, min(phys_x, shot.width() - 1))
            phys_y = max(0, min(phys_y, shot.height() - 1))
            phys_w = max(1, min(phys_w, shot.width() - phys_x))
            phys_h = max(1, min(phys_h, shot.height() - phys_y))

            cropped = shot.copy(phys_x, phys_y, phys_w, phys_h)
            cropped.setDevicePixelRatio(dpr)
            return cropped

        # Fallback to direct grab
        return target_screen.grabWindow(0, local_x, local_y, global_rect.width(), global_rect.height())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_capture()
            event.accept()
        else:
            super().keyPressEvent(event)

    def cancel_capture(self) -> None:
        self._is_selecting = False
        self.hide()
        self.cancelled.emit()
