"""PinnedCanvas: Frameless, borderless, always-on-top floating window for snips.

Features:
- High-DPI Crystal Clear 1:1 hardware pixel blitting
- Diff Slider Mode: Before & After comparison with interactive drag handle
- Opacity Control & Ghost Mode: Click-through transparency for background data entry
- Right-Click Context Menu: Instant access to all functions
- Highlighter Annotation: Realistic Multiply-blended highlighter pen with Undo
- Copy & Save: One-click export to clipboard and disk
"""

from PyQt6.QtCore import QPoint, QPointF, QRect, QRectF, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QColor,
    QCursor,
    QFont,
    QGuiApplication,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMenu,
    QWidget,
)


class PinnedCanvas(QWidget):
    """An undecorated, borderless floating window pinned permanently on top."""

    closed = pyqtSignal(object)
    ghost_state_changed = pyqtSignal()

    COLORS = [
        ("🟡 Yellow", QColor(255, 235, 59, 130)),
        ("🟢 Green", QColor(74, 222, 128, 130)),
        ("🌸 Pink", QColor(244, 114, 182, 130)),
        ("🔵 Cyan", QColor(56, 189, 248, 130)),
    ]

    def __init__(self, pixmap: QPixmap, initial_pos: QPoint | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.original_pixmap = pixmap
        self.zoom_factor = 1.0
        self.min_zoom = 0.25
        self.max_zoom = 5.0

        # Opacity & Ghost Mode
        self._canvas_opacity = 1.0
        self.is_ghost_mode = False

        # Diff Slider State
        self.is_diff_mode = False
        self.diff_pixmap: QPixmap | None = None
        self.diff_slider_pos = 0.5  # 0.0 to 1.0
        self.is_dragging_diff_slider = False
        self.diff_labels = ["Before", "After"]

        # Highlighting State
        self.is_highlighting = False
        self.highlight_color = self.COLORS[0][1]
        self.highlight_color_name = "Yellow"
        self.highlight_width = 18.0
        self.strokes: list[dict] = []
        self._current_stroke_points: list[QPointF] = []

        # Window Dragging State
        self._is_dragging = False
        self._drag_start_pos = QPoint()

        # Toast notification pill
        self._toast_message: str | None = None
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(self._clear_toast)

        # Border styling
        self.border_color = QColor(59, 130, 246, 180)
        self.border_width = 1

        self._setup_window_flags()
        self._setup_geometry(initial_pos)

    def _setup_window_flags(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setToolTip(
            "Hover Pin\n"
            "• Right-click for options (Diff, Opacity, Highlight, Copy, Save)\n"
            "• Left-drag to move | Wheel to zoom\n"
            "• Ctrl+Shift+Wheel to adjust opacity\n"
            "• 'D' to toggle Diff Slider | 'H' for Highlighter"
        )

    def _setup_geometry(self, initial_pos: QPoint | None) -> None:
        dpr = max(1.0, self.original_pixmap.devicePixelRatio())
        w = max(40, int(round(self.original_pixmap.width() / dpr)))
        h = max(40, int(round(self.original_pixmap.height() / dpr)))
        self.resize(w, h)
        if initial_pos is not None:
            self.move(initial_pos)

    # --------------------------------------------------------------------------
    # Opacity & Ghost Mode (Click-Through)
    # --------------------------------------------------------------------------
    def set_canvas_opacity(self, opacity: float) -> None:
        """Set window opacity between 0.15 and 1.0."""
        self._canvas_opacity = max(0.15, min(1.0, opacity))
        self.setWindowOpacity(self._canvas_opacity)
        self._show_toast(f"👻 Opacity: {int(round(self._canvas_opacity * 100))}%")

    def toggle_ghost_mode(self, enabled: bool | None = None) -> None:
        """Toggle click-through transparency mode."""
        self.is_ghost_mode = not self.is_ghost_mode if enabled is None else enabled
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, self.is_ghost_mode)

        if self.is_ghost_mode:
            # Set comfortable transparency if solid
            if self._canvas_opacity > 0.65:
                self.set_canvas_opacity(0.55)
            self._show_toast("👻 Ghost Mode Active: Click-through enabled. (Ctrl+Alt+G to un-ghost)")
        else:
            self._show_toast("✋ Ghost Mode Disabled: Window is interactive again")

        self.show()
        self.ghost_state_changed.emit()

    # --------------------------------------------------------------------------
    # Diff Slider Mechanics
    # --------------------------------------------------------------------------
    def start_diff_with_screen_underneath(self) -> None:
        """Capture the live screen content directly beneath the pinned window for comparison."""
        # Temporarily hide window to capture pristine underlying content
        self.hide()
        QApplication.processEvents()

        screen = QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
        dpr = screen.devicePixelRatio()
        screen_geo = screen.geometry()

        local_x = self.geometry().x() - screen_geo.x()
        local_y = self.geometry().y() - screen_geo.y()

        shot = screen.grabWindow(0, local_x, local_y, self.geometry().width(), self.geometry().height())
        shot.setDevicePixelRatio(dpr)

        self.diff_pixmap = shot
        self.is_diff_mode = True
        self.diff_slider_pos = 0.5
        self.diff_labels = ["Before", "Live Screen"]

        self.show()
        self._show_toast("🔀 Diff Mode: Drag slider handle ◀ ▶ to compare")
        self.update()

    def start_diff_with_file(self) -> None:
        """Prompt user for a comparison image file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image to Compare",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*)",
        )
        if filepath:
            img = QPixmap(filepath)
            if not img.isNull():
                self.diff_pixmap = img
                self.is_diff_mode = True
                self.diff_slider_pos = 0.5
                self.diff_labels = ["Before", "File Image"]
                self._show_toast("🔀 Diff Mode: Drag slider handle ◀ ▶ to compare")
                self.update()

    def swap_diff_images(self) -> None:
        """Swap the left and right comparison images."""
        if self.is_diff_mode and self.diff_pixmap:
            self.original_pixmap, self.diff_pixmap = self.diff_pixmap, self.original_pixmap
            self.diff_labels.reverse()
            self._show_toast(f"🔄 Swapped: Left is {self.diff_labels[0]}, Right is {self.diff_labels[1]}")
            self.update()

    def exit_diff_mode(self) -> None:
        """Exit Diff comparison mode."""
        self.is_diff_mode = False
        self.diff_pixmap = None
        self._show_toast("🔀 Diff Mode Exited")
        self.update()

    # --------------------------------------------------------------------------
    # Right-Click Context Menu
    # --------------------------------------------------------------------------
    def show_context_menu(self, global_pos: QPoint) -> None:
        """Display modern dark-themed context menu with all tools."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0f172a;
                color: #f1f5f9;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 5px;
                font-family: 'Segoe UI';
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 24px 6px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #2563eb;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #334155;
                margin: 4px 6px;
            }
        """)

        # 1. Diff Slider Submenu
        diff_menu = menu.addMenu("🔀  Diff Slider (Before / After)")
        diff_menu.setStyleSheet(menu.styleSheet())

        if not self.is_diff_mode:
            under_action = diff_menu.addAction("📸  Diff with Screen Underneath (D)")
            under_action.triggered.connect(self.start_diff_with_screen_underneath)

            file_action = diff_menu.addAction("📁  Diff with Image File...")
            file_action.triggered.connect(self.start_diff_with_file)
        else:
            swap_action = diff_menu.addAction(f"🔄  Swap ({self.diff_labels[0]} ⮀ {self.diff_labels[1]})")
            swap_action.triggered.connect(self.swap_diff_images)

            recapture_action = diff_menu.addAction("📸  Re-capture Screen Underneath")
            recapture_action.triggered.connect(self.start_diff_with_screen_underneath)

            exit_diff_action = diff_menu.addAction("✕  Exit Diff Mode (D)")
            exit_diff_action.triggered.connect(self.exit_diff_mode)

        # 2. Opacity & Ghost Mode Submenu
        opacity_pct = int(round(self._canvas_opacity * 100))
        op_menu = menu.addMenu(f"👻  Opacity & Ghost ({opacity_pct}%)")
        op_menu.setStyleSheet(menu.styleSheet())

        for pct in (100, 85, 70, 50, 30):
            action = op_menu.addAction(f"{pct}%" + (" (Solid)" if pct == 100 else ""))
            val = pct / 100.0
            action.triggered.connect(lambda checked=False, v=val: self.set_canvas_opacity(v))

        op_menu.addSeparator()
        ghost_action = op_menu.addAction("👻  Ghost Mode / Click-Through (Ctrl+G)")
        ghost_action.setCheckable(True)
        ghost_action.setChecked(self.is_ghost_mode)
        ghost_action.triggered.connect(lambda: self.toggle_ghost_mode())

        menu.addSeparator()

        # 3. Highlighter Tool
        hl_label = "🖍️  Highlight Mode (H)" if not self.is_highlighting else "✋  Exit Highlight Mode (H)"
        hl_action = menu.addAction(hl_label)
        hl_action.triggered.connect(lambda: self.set_highlighting(not self.is_highlighting))

        color_menu = menu.addMenu(f"🎨  Highlight Color ({self.highlight_color_name})")
        color_menu.setStyleSheet(menu.styleSheet())
        for name, color in self.COLORS:
            action = color_menu.addAction(name)
            color_name_clean = name.split()[1]
            action.triggered.connect(lambda checked=False, c=color, n=color_name_clean: self.set_highlight_color(c, n))

        if self.strokes:
            undo_action = menu.addAction("↩️  Undo Last Highlight (Ctrl+Z)")
            undo_action.triggered.connect(self.undo_highlight)

        menu.addSeparator()

        # 4. Copy & Save
        copy_action = menu.addAction("📋  Copy to Clipboard (Ctrl+C)")
        copy_action.triggered.connect(self.copy_to_clipboard)

        save_action = menu.addAction("💾  Save Image As... (Ctrl+S)")
        save_action.triggered.connect(self.save_image)

        menu.addSeparator()

        # 5. Zoom Submenu
        zoom_pct = int(round(self.zoom_factor * 100))
        zoom_menu = menu.addMenu(f"🔍  Zoom ({zoom_pct}%)")
        zoom_menu.setStyleSheet(menu.styleSheet())

        zoom_in_action = zoom_menu.addAction("Zoom In + (Wheel Up / Ctrl++)")
        zoom_in_action.triggered.connect(lambda: self._step_zoom(1.2))

        zoom_out_action = zoom_menu.addAction("Zoom Out - (Wheel Down / Ctrl+-)")
        zoom_out_action.triggered.connect(lambda: self._step_zoom(1 / 1.2))

        reset_zoom_action = zoom_menu.addAction("Reset to 100% (Ctrl+0)")
        reset_zoom_action.triggered.connect(lambda: setattr(self, "zoom_factor", 1.0) or self._apply_zoom())

        menu.addSeparator()

        # 6. Close
        close_action = menu.addAction("❌  Close / Dismiss (Esc)")
        close_action.triggered.connect(self.close)

        menu.exec(global_pos)

    def _step_zoom(self, factor: float) -> None:
        new_zoom = self.zoom_factor * factor
        if self.min_zoom <= new_zoom <= self.max_zoom:
            self.zoom_factor = new_zoom
            self._apply_zoom()

    # --------------------------------------------------------------------------
    # Highlight & Annotation Control
    # --------------------------------------------------------------------------
    def set_highlighting(self, enabled: bool) -> None:
        self.is_highlighting = enabled
        if enabled:
            self.setCursor(Qt.CursorShape.CrossCursor)
            self._show_toast("🖍️ Highlighter Active (Left-drag to highlight)")
        else:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self._show_toast("✋ Move Mode Active")
        self.update()

    def set_highlight_color(self, color: QColor, name: str) -> None:
        self.highlight_color = color
        self.highlight_color_name = name
        self.set_highlighting(True)
        self._show_toast(f"🎨 Color: {name}")

    def undo_highlight(self) -> None:
        if self.strokes:
            self.strokes.pop()
            self._show_toast("↩️ Stroke Undone")
            self.update()

    # --------------------------------------------------------------------------
    # Copy & Save Actions
    # --------------------------------------------------------------------------
    def get_composite_pixmap(self) -> QPixmap:
        """Render the original image merged with highlight strokes at full physical DPI."""
        result = self.original_pixmap.copy()
        if not self.strokes:
            return result

        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)

        for stroke in self.strokes:
            points = stroke["points"]
            if len(points) < 2:
                continue
            pen = QPen(stroke["color"], stroke["width"], Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            path = QPainterPath()
            path.moveTo(points[0])
            for pt in points[1:]:
                path.lineTo(pt)
            painter.strokePath(path, pen)

        painter.end()
        result.setDevicePixelRatio(self.original_pixmap.devicePixelRatio())
        return result

    def copy_to_clipboard(self) -> None:
        composite = self.get_composite_pixmap()
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setPixmap(composite)
        self._show_toast("📋 Copied to Clipboard!")

    def save_image(self) -> None:
        composite = self.get_composite_pixmap()
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Pinned Snip",
            "Hover_snip.png",
            "PNG Image (*.png);;JPEG Image (*.jpg);;All Files (*)",
        )
        if filepath:
            composite.save(filepath)
            self._show_toast("💾 Saved Successfully!")

    def _show_toast(self, message: str) -> None:
        self._toast_message = message
        self.update()
        self._toast_timer.start(2200)

    def _clear_toast(self) -> None:
        self._toast_message = None
        self.update()

    # --------------------------------------------------------------------------
    # Painting & Rendering
    # --------------------------------------------------------------------------
    def paintEvent(self, event) -> None:
        painter = QPainter(self)

        # 1:1 hardware pixel blit when unzoomed
        if abs(self.zoom_factor - 1.0) < 0.005:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        else:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        if self.is_diff_mode and self.diff_pixmap:
            # ------------------------------------------------------------------
            # Render Diff Mode (Before / After Split)
            # ------------------------------------------------------------------
            split_x = int(self.width() * self.diff_slider_pos)

            # Left side: Image A (Original)
            painter.save()
            painter.setClipRect(QRect(0, 0, split_x, self.height()))
            painter.drawPixmap(rect, self.original_pixmap)
            painter.restore()

            # Right side: Image B (Comparison)
            painter.save()
            painter.setClipRect(QRect(split_x, 0, self.width() - split_x, self.height()))
            painter.drawPixmap(rect, self.diff_pixmap)
            painter.restore()

            # Draw vertical divider line
            painter.setPen(QPen(QColor(0, 0, 0, 160), 3))
            painter.drawLine(split_x, 0, split_x, self.height())
            painter.setPen(QPen(QColor(56, 189, 248), 1.5))
            painter.drawLine(split_x, 0, split_x, self.height())

            # Draw circular draggable slider handle
            handle_y = self.height() // 2
            handle_radius = 15.0
            handle_rect = QRectF(split_x - handle_radius, handle_y - handle_radius, handle_radius * 2, handle_radius * 2)

            painter.setPen(QPen(QColor(56, 189, 248), 2))
            painter.setBrush(QColor(15, 23, 42, 240))
            painter.drawEllipse(handle_rect)

            # Draw handle arrows ◀ ▶
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(handle_rect, Qt.AlignmentFlag.AlignCenter, "◀ ▶")

            # Draw labels (Before / After)
            self._draw_diff_labels(painter, split_x)

        else:
            # ------------------------------------------------------------------
            # Standard Pinned Snip Rendering
            # ------------------------------------------------------------------
            painter.drawPixmap(rect, self.original_pixmap)

            # Draw highlight strokes
            scale_x = self.width() / max(1, self.original_pixmap.width())
            scale_y = self.height() / max(1, self.original_pixmap.height())

            painter.save()
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)

            all_strokes = list(self.strokes)
            if self._current_stroke_points:
                all_strokes.append({
                    "points": self._current_stroke_points,
                    "color": self.highlight_color,
                    "width": self.highlight_width,
                })

            for stroke in all_strokes:
                points = stroke["points"]
                if len(points) < 2:
                    continue
                stroke_width = stroke["width"] * scale_x
                pen = QPen(stroke["color"], stroke_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)

                path = QPainterPath()
                start = QPointF(points[0].x() * scale_x, points[0].y() * scale_y)
                path.moveTo(start)
                for pt in points[1:]:
                    scaled_pt = QPointF(pt.x() * scale_x, pt.y() * scale_y)
                    path.lineTo(scaled_pt)
                painter.strokePath(path, pen)

            painter.restore()

        # 1px Crisp Accent Border
        pen = QPen(self.border_color, self.border_width)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(0.5, 0.5, float(rect.width() - 1), float(rect.height() - 1)))

        # On-screen toast badge
        if self._toast_message:
            self._draw_toast_badge(painter)

        painter.end()

    def _draw_diff_labels(self, painter: QPainter, split_x: int) -> None:
        """Draw Before and After indicator badges at the top edges."""
        font = QFont("Segoe UI", 8, QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(15, 23, 42, 210))

        # Left label ("Before")
        lbl_left = self.diff_labels[0]
        rect_left = QRect(8, 8, 60, 20)
        painter.drawRoundedRect(QRectF(rect_left), 4.0, 4.0)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(rect_left, Qt.AlignmentFlag.AlignCenter, lbl_left)

        # Right label ("After")
        lbl_right = self.diff_labels[1]
        rect_right = QRect(self.width() - 80, 8, 72, 20)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(15, 23, 42, 210))
        painter.drawRoundedRect(QRectF(rect_right), 4.0, 4.0)
        painter.setPen(QColor(56, 189, 248))
        painter.drawText(rect_right, Qt.AlignmentFlag.AlignCenter, lbl_right)

    def _draw_toast_badge(self, painter: QPainter) -> None:
        font = QFont("Segoe UI", 9, QFont.Weight.DemiBold)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        text_w = metrics.horizontalAdvance(self._toast_message)
        text_h = metrics.height()

        badge_w = text_w + 24
        badge_h = text_h + 12
        badge_x = (self.width() - badge_w) // 2
        badge_y = self.height() - badge_h - 12

        badge_rect = QRect(badge_x, badge_y, badge_w, badge_h)
        path = QPainterPath()
        path.addRoundedRect(QRectF(badge_rect), 6.0, 6.0)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.fillPath(path, QColor(15, 23, 42, 230))
        painter.strokePath(path, QPen(QColor(59, 130, 246, 200), 1))

        painter.setPen(QColor(255, 255, 255))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, self._toast_message)

    # --------------------------------------------------------------------------
    # Mouse & Drag Interactions
    # --------------------------------------------------------------------------
    def _widget_to_original_coords(self, pt: QPointF) -> QPointF:
        scale_x = self.original_pixmap.width() / max(1, self.width())
        scale_y = self.original_pixmap.height() / max(1, self.height())
        return QPointF(pt.x() * scale_x, pt.y() * scale_y)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        # Right-Click immediately opens context menu
        if event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            # Check if user clicked near Diff Slider divider line
            if self.is_diff_mode:
                split_x = int(self.width() * self.diff_slider_pos)
                if abs(event.position().x() - split_x) <= 16:
                    self.is_dragging_diff_slider = True
                    event.accept()
                    return

            if self.is_highlighting:
                orig_pt = self._widget_to_original_coords(event.position())
                self._current_stroke_points = [orig_pt]
                self.update()
            else:
                self._is_dragging = True
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        # Handle dragging Diff Slider
        if self.is_dragging_diff_slider:
            new_pos = max(0.02, min(0.98, event.position().x() / max(1, self.width())))
            self.diff_slider_pos = new_pos
            self.update()
            event.accept()
            return

        # Update cursor when hovering near diff slider handle
        if self.is_diff_mode and not self._is_dragging and not self.is_highlighting:
            split_x = int(self.width() * self.diff_slider_pos)
            if abs(event.position().x() - split_x) <= 16:
                self.setCursor(Qt.CursorShape.SplitHCursor)
            else:
                self.setCursor(Qt.CursorShape.OpenHandCursor)

        if self.is_highlighting and (event.buttons() & Qt.MouseButton.LeftButton):
            orig_pt = self._widget_to_original_coords(event.position())
            self._current_stroke_points.append(orig_pt)
            self.update()
            event.accept()
        elif self._is_dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_start_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_dragging_diff_slider:
                self.is_dragging_diff_slider = False
                event.accept()
                return

            if self.is_highlighting:
                if len(self._current_stroke_points) >= 2:
                    self.strokes.append({
                        "points": list(self._current_stroke_points),
                        "color": self.highlight_color,
                        "width": self.highlight_width,
                    })
                self._current_stroke_points = []
                self.update()
            else:
                self._is_dragging = False
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self.is_highlighting:
            if self.is_diff_mode:
                self.diff_slider_pos = 0.5
                self.update()
            else:
                self.zoom_factor = 1.0
                self._apply_zoom()
            event.accept()

    def wheelEvent(self, event: QWheelEvent) -> None:
        angle_delta = event.angleDelta().y()
        if angle_delta == 0:
            return

        # Ctrl + Shift + Wheel: Adjust Opacity
        if (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            delta = 0.05 if angle_delta > 0 else -0.05
            self.set_canvas_opacity(self._canvas_opacity + delta)
            event.accept()
            return

        # Normal Wheel: Zoom
        factor = 1.1 if angle_delta > 0 else 0.9
        new_zoom = self.zoom_factor * factor

        if self.min_zoom <= new_zoom <= self.max_zoom:
            self.zoom_factor = new_zoom
            self._apply_zoom()

        event.accept()

    def _apply_zoom(self) -> None:
        dpr = max(1.0, self.original_pixmap.devicePixelRatio())
        base_w = self.original_pixmap.width() / dpr
        base_h = self.original_pixmap.height() / dpr
        new_w = max(40, int(round(base_w * self.zoom_factor)))
        new_h = max(40, int(round(base_h * self.zoom_factor)))
        self.resize(new_w, new_h)
        self.update()

    # --------------------------------------------------------------------------
    # Keyboard Shortcuts
    # --------------------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:
        # Escape: if highlighting or diffing, exit mode; else close window
        if event.key() == Qt.Key.Key_Escape:
            if self.is_highlighting:
                self.set_highlighting(False)
            elif self.is_diff_mode:
                self.exit_diff_mode()
            else:
                self.close()
            event.accept()
            return

        # D: Toggle Diff with Screen Underneath
        if event.key() == Qt.Key.Key_D:
            if self.is_diff_mode:
                self.exit_diff_mode()
            else:
                self.start_diff_with_screen_underneath()
            event.accept()
            return

        # H: Toggle Highlighter
        if event.key() == Qt.Key.Key_H:
            self.set_highlighting(not self.is_highlighting)
            event.accept()
            return

        # Ctrl Shortcuts
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_G:
                self.toggle_ghost_mode()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_C:
                self.copy_to_clipboard()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_S:
                self.save_image()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Z:
                self.undo_highlight()
                event.accept()
                return
            elif event.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                self._step_zoom(1.15)
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Minus:
                self._step_zoom(1 / 1.15)
                event.accept()
                return
            elif event.key() == Qt.Key.Key_0:
                self.zoom_factor = 1.0
                self._apply_zoom()
                event.accept()
                return

        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        self.closed.emit(self)
        super().closeEvent(event)
