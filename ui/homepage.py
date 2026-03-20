from PySide6.QtWidgets import QWidget, QFrame, QLabel, QApplication
from PySide6.QtGui import QPixmap, QFont, QPainterPath, QRegion, QFontMetrics
from PySide6.QtCore import Qt, QRect, QPropertyAnimation, QEasingCurve, QEvent
from helpers.CustomWidgets import apply_widget_shadow
from helpers.json_manager import (
    get_current_user,
    get_user_graph_names,
    _num_pixels,
    get_theme,
    get_pixel_dict,
    get_current_graph,
)
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class HoverScaleFrame(QFrame):
    def __init__(self, parent=None, scale_factor=1.05, press_scale=1.03, duration=140):
        super().__init__(parent)
        self._hover_scale = scale_factor
        self._press_scale = press_scale
        self._duration = duration
        self._press_duration = 95
        self._release_duration = 140
        self._hovered = False
        self._pressed = False
        self._base_geometry = QRect()
        self._anchor_content = False
        self._anchor_base_geometry = QRect()
        self._child_base_positions = {}
        self._anim = QPropertyAnimation(self, b"geometry", self)
        self._anim.setDuration(duration)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    def setGeometry(self, *args):
        super().setGeometry(*args)
        if not self.underMouse() and not self._pressed:
            self._base_geometry = QRect(self.geometry())
            if self._anchor_content:
                self._anchor_base_geometry = QRect(self.geometry())
                self._capture_child_positions()
        self._update_child_anchor_positions()

    def enable_content_anchor(self):
        self._anchor_content = True
        self._anchor_base_geometry = QRect(self.geometry())
        self._capture_child_positions()
        self._update_child_anchor_positions()

    def _capture_child_positions(self):
        if not self._anchor_content:
            return
        self._child_base_positions = {}
        for child in self.findChildren(QWidget, options=Qt.FindDirectChildrenOnly):
            self._child_base_positions[child] = child.pos()

    def _update_child_anchor_positions(self):
        if not self._anchor_content or self._anchor_base_geometry.isNull():
            return
        dx = self._anchor_base_geometry.x() - self.geometry().x()
        dy = self._anchor_base_geometry.y() - self.geometry().y()
        for child, base_pos in list(self._child_base_positions.items()):
            if child is None or child.parent() is not self:
                self._child_base_positions.pop(child, None)
                continue
            child.move(base_pos.x() + dx, base_pos.y() + dy)

    def event(self, event):
        if event.type() == QEvent.Enter:
            self._hovered = True
            if self._base_geometry.isNull():
                self._base_geometry = QRect(self.geometry())
            if not self._pressed:
                self._animate_to(
                    self._scaled_rect(self._hover_scale),
                    duration=self._duration,
                    easing=QEasingCurve.OutCubic
                )
        elif event.type() == QEvent.Leave:
            self._hovered = False
            if not self._pressed and not self._base_geometry.isNull():
                self._animate_to(
                    self._base_geometry,
                    duration=self._duration,
                    easing=QEasingCurve.OutCubic
                )
        return super().event(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pressed = True
            if self._base_geometry.isNull():
                self._base_geometry = QRect(self.geometry())
            self._animate_to(
                self._scaled_rect(self._press_scale),
                duration=self._press_duration,
                easing=QEasingCurve.OutCubic
            )
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        was_pressed = self._pressed
        self._pressed = False
        if was_pressed and event.button() == Qt.LeftButton:
            if self._hovered:
                self._animate_to(
                    self._scaled_rect(self._hover_scale),
                    duration=self._release_duration,
                    easing=QEasingCurve.OutBack
                )
            elif not self._base_geometry.isNull():
                self._animate_to(
                    self._base_geometry,
                    duration=self._duration,
                    easing=QEasingCurve.OutCubic
                )
        super().mouseReleaseEvent(event)

    def _scaled_rect(self, scale):
        base = self._base_geometry if not self._base_geometry.isNull() else self.geometry()
        w = int(round(base.width() * scale))
        h = int(round(base.height() * scale))
        x = base.x() - (w - base.width()) // 2
        y = base.y() - (h - base.height()) // 2
        return QRect(x, y, w, h)

    def _animate_to(self, target, duration=None, easing=None):
        self._anim.stop()
        if duration is not None:
            self._anim.setDuration(int(duration))
        if easing is not None:
            self._anim.setEasingCurve(easing)
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(target)
        self._anim.start()

class HomePage(QWidget):
    def __init__(self):
        super().__init__()
        # keep construction lightweight; full UI setup happens in run()
        self._setup_done = False
    
    def _average_pixel(self, pixel_dict):
        if not pixel_dict:
            return 0

        values = []
        for v in pixel_dict.values():
            try:
                values.append(float(v))
            except (TypeError, ValueError):
                continue
        if not values:
            return 0
        return round(sum(values) / len(values), 2)

    def run(self):
        """Build the UI elements. Call this after creating the object when you
        actually want the visual elements initialized (e.g., before adding to a
        QStackedWidget or showing the widget).
        """
        if self._setup_done:
            return
        self._setup_done = True
        self.current_user = get_current_user()
        self.accent_color = get_theme().get("accent_color", "Error")
        self.graphs = get_user_graph_names(self.current_user)
        total_pixels = sum(_num_pixels(self.current_user, graph) for graph in self.graphs)
        self.num_graphs = len(self.graphs)
        self.max_username_length = 9
        # This widget is intended to be placed inside the central stacked area
        self.setFixedSize(640, 550)

        # MainFrame (fills widget with padding as requested)
        self.main_frame = QFrame(self)
        self.main_frame.setGeometry(0, 0, 640, 550)
        self.main_frame.setStyleSheet(
            "background-color: #2b2b2b; border-radius: 20px; border: 1px solid rgba(255,255,255,0.08);"
        )
        apply_widget_shadow(self.main_frame, radius=20)

        # HeatMap_frame inside MainFrame at 50,30 size 540x200
        self.heatmap_frame = HoverScaleFrame(self.main_frame, scale_factor=1.05, duration=140)
        self.heatmap_frame.setGeometry(50, 30, 540, 200)
        self.heatmap_frame.setStyleSheet(
            "background-color: #242424; border-radius: 20px; border: 1px solid rgba(255,255,255,0.08);"
        )
        self._heatmap_base_frame_w = 540
        self._heatmap_base_frame_h = 200
        self._heatmap_base_image_w = 520
        self._heatmap_base_image_h = 182

        # HeatMap image placeholder
        self.heatmap_image = QLabel(self.heatmap_frame)
        self.heatmap_image.setGeometry(10, 9, 520, 182)
        self.heatmap_image.setStyleSheet("background-color: #242424; border-radius: 20px;")
        self.heatmap_image.setAlignment(Qt.AlignCenter)
        self.heatmap_frame.installEventFilter(self)
        self._sync_heatmap_image_geometry()
        try:
            self.update_heatmap_image()
        
        except Exception:
            pass
        # LogoFrame2 in MainFrame at 50,257 size 250x250
        self.logo_frame2 = HoverScaleFrame(self.main_frame, scale_factor=1.05, duration=140)
        self.logo_frame2.setGeometry(50, 257, 250, 250)
        self.logo_frame2.setStyleSheet(
            "background-color: #242424; border-radius: 20px; border: 1px solid rgba(255,255,255,0.08);"
        )

        self.logo2_label = QLabel(self.logo_frame2)
        self.logo2_label.setGeometry(0, 0, 250, 250)
        self.logo2_label.setAlignment(Qt.AlignCenter)
        try:
            pix = QPixmap(os.path.join(BASE_DIR, "assets", "pixemln-logo-text_main.png"))
            if not pix.isNull():
                self.logo2_label.setPixmap(pix.scaled(225, 225, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.logo2_label.setStyleSheet("background-color: transparent; border: none;")
        except Exception:
            pass
        self.logo_frame2.enable_content_anchor()

        # DataBox in MainFrame at 320,257
        self.data_box = HoverScaleFrame(self.main_frame, scale_factor=1.05, duration=140)
        self.data_box.setGeometry(320, 257, 270, 250)
        self.data_box.setStyleSheet(
            "background-color: #242424; border-radius: 20px; border: 1px solid rgba(255,255,255,0.08);"
        )

        self.overview_labels = {}

        lines = [
            (f"Overview", 18),
            (f"User          {self.current_user}", 12),
            (f"Graphs        {self.num_graphs}", 12),
            (f"Total Pixels  {total_pixels}", 12),
            (f"Avg Pixel     {self._average_pixel(get_pixel_dict(self.current_user, self.graphs[0]) if self.graphs else {})}", 12)
        ]

        y = 0
        label_keys = ["overview", "user", "graphs", "total_pixels", "avg_pixel"]
        mono_family = "Roboto Mono"
        app = QApplication.instance()
        if app is not None:
            try:
                mono_family = app.property("pixemln_font_mono") or mono_family
            except Exception:
                pass

        for i, (text, size) in enumerate(lines):
            lbl = QLabel(text, self.data_box)
            lbl.setGeometry(0, y, 300, 40)
            f = QFont()
            if i > 0:
                f.setFamily(str(mono_family))
            f.setPointSize(size)
            lbl.setFont(f)
            if text.startswith("Overview"):
                lbl.setAlignment(Qt.AlignCenter)
            else:
                # Align left with some padding
                lbl.setAlignment(Qt.AlignLeft)
                lbl.setGeometry(15, y, 300, 40)
            lbl.setStyleSheet("color: #FFFFFF; background-color: transparent; border: none;")
            self._set_elided_text(lbl, text)
            self.overview_labels[label_keys[i]] = lbl
            y += 45
        self.data_box.enable_content_anchor()
        self.refresh_info()

    def _set_elided_text(self, label, text, width=240):
        metrics = QFontMetrics(label.font())
        elided = metrics.elidedText(text, Qt.ElideRight, width)
        label.setText(elided)

    def _current_graph_for_stats(self, graphs):
        if not graphs:
            return None
        try:
            current = get_current_graph()
            selected = current.get("graph")
            if selected in graphs:
                return selected
        except Exception:
            pass
        return graphs[0]

    def refresh_info(self):
        if not getattr(self, "_setup_done", False):
            return

        self.current_user = get_current_user()
        self.graphs = get_user_graph_names(self.current_user)
        self.num_graphs = len(self.graphs)
        total_pixels = sum(_num_pixels(self.current_user, graph) for graph in self.graphs)
        stats_graph = self._current_graph_for_stats(self.graphs)
        avg_pixel = self._average_pixel(get_pixel_dict(self.current_user, stats_graph) if stats_graph else {})

        lines = {
            "overview": "Overview",
            "user": f"User          {self.current_user}",
            "graphs": f"Graphs        {self.num_graphs}",
            "total_pixels": f"Total Pixels  {total_pixels}",
            "avg_pixel": f"Avg Pixel     {avg_pixel}",
        }
        for key, text in lines.items():
            lbl = self.overview_labels.get(key)
            if lbl is not None:
                self._set_elided_text(lbl, text)

        self.update_heatmap_image()

    def eventFilter(self, watched, event):
        if watched is getattr(self, "heatmap_frame", None) and event.type() == QEvent.Resize:
            self._sync_heatmap_image_geometry()
        return super().eventFilter(watched, event)

    def _sync_heatmap_image_geometry(self):
        if not hasattr(self, "heatmap_frame") or not hasattr(self, "heatmap_image"):
            return

        frame_w = self.heatmap_frame.width()
        frame_h = self.heatmap_frame.height()
        if frame_w <= 0 or frame_h <= 0:
            return

        scale = min(
            frame_w / float(self._heatmap_base_frame_w),
            frame_h / float(self._heatmap_base_frame_h)
        )
        img_w = max(1, int(round(self._heatmap_base_image_w * scale)))
        img_h = max(1, int(round(self._heatmap_base_image_h * scale)))
        img_x = (frame_w - img_w) // 2
        img_y = (frame_h - img_h) // 2
        self.heatmap_image.setGeometry(img_x, img_y, img_w, img_h)

        radius = max(1, min(int(round(20 * scale)), img_w // 2, img_h // 2))
        path = QPainterPath()
        path.addRoundedRect(self.heatmap_image.rect(), radius, radius)
        self.heatmap_image.setMask(QRegion(path.toFillPolygon().toPolygon()))
        self.update_heatmap_image()

    def update_heatmap_image(self):
        if not hasattr(self, "heatmap_image"):
            return
        if not getattr(self, "graphs", None):
            self.heatmap_image.clear()
            return
        # Reload on every refresh so file regenerations (heatmap/histogram) are visible immediately.
        pix = QPixmap(os.path.join(BASE_DIR, "assets", "heatmap.png"))
        if pix.isNull():
            self.heatmap_image.clear()
            return
        self.heatmap_image.setPixmap(
            pix.scaled(
                self.heatmap_image.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )
