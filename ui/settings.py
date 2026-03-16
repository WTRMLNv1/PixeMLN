from PySide6.QtWidgets import QWidget, QFrame, QLabel, QPushButton
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, QTimer, QVariantAnimation, QEasingCurve, QPropertyAnimation, QRect, QSequentialAnimationGroup
from helpers.CustomWidgets import CustomDropdown, CircleSlider, TickWidget, SpinnerWidget, apply_widget_shadow
from helpers.json_manager import get_current_user, get_all_graph_names, get_theme, set_theme, change_graph_type, change_display_graph, get_current_graph, get_user_graph_names
from helpers.colorUtils import hex_to_hsv, hsv_to_hex, darker, ideal_text_color
from functions.create_graph_images import create_histogram, create_heatmap
import threading
import time


class PresetAnimatedButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._base_geometry = QRect()
        self._hovered = False
        self._pressed = False

        self._anim = QPropertyAnimation(self, b"geometry", self)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        self._release_seq = None

        self._scale_idle = 1.00
        self._scale_hover = 1.04
        self._scale_press = 0.97
        self._scale_release_peak = 1.06

        self._dur_hover_ms = 100
        self._dur_press_ms = 50
        self._dur_release_up_ms = 75
        self._dur_release_settle_ms = 100

    def setGeometry(self, *args):
        super().setGeometry(*args)
        if not self._hovered and not self._pressed:
            self._base_geometry = QRect(self.geometry())

    def _scaled_rect(self, scale):
        base = self._base_geometry if not self._base_geometry.isNull() else self.geometry()
        w = int(round(base.width() * scale))
        h = int(round(base.height() * scale))
        x = base.x() - (w - base.width()) // 2
        y = base.y() - (h - base.height()) // 2
        return QRect(x, y, w, h)

    def _stop_release_seq(self):
        if self._release_seq is not None:
            self._release_seq.stop()
            self._release_seq.deleteLater()
            self._release_seq = None

    def _animate_to_scale(self, scale, duration_ms, curve):
        self._stop_release_seq()
        self._anim.stop()
        self._anim.setDuration(int(duration_ms))
        self._anim.setEasingCurve(curve)
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(self._scaled_rect(scale))
        self._anim.start()

    def _target_idle_or_hover(self):
        return self._scale_hover if self._hovered else self._scale_idle

    def _run_release_sequence(self):
        self._stop_release_seq()
        self._anim.stop()

        first = QPropertyAnimation(self, b"geometry", self)
        first.setDuration(self._dur_release_up_ms)
        first.setEasingCurve(QEasingCurve.OutCubic)
        first.setStartValue(self.geometry())
        first.setEndValue(self._scaled_rect(self._scale_release_peak))

        second = QPropertyAnimation(self, b"geometry", self)
        second.setDuration(self._dur_release_settle_ms)
        second.setEasingCurve(QEasingCurve.OutCubic)
        second.setStartValue(self._scaled_rect(self._scale_release_peak))
        second.setEndValue(self._scaled_rect(self._target_idle_or_hover()))

        seq = QSequentialAnimationGroup(self)
        seq.addAnimation(first)
        seq.addAnimation(second)
        self._release_seq = seq
        seq.finished.connect(self._clear_release_seq)
        seq.start()

    def _clear_release_seq(self):
        self._release_seq = None

    def enterEvent(self, event):
        self._hovered = True
        if not self._pressed:
            self._animate_to_scale(self._scale_hover, self._dur_hover_ms, QEasingCurve.OutCubic)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        if not self._pressed:
            self._animate_to_scale(self._scale_idle, self._dur_hover_ms, QEasingCurve.OutCubic)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pressed = True
            self._animate_to_scale(self._scale_press, self._dur_press_ms, QEasingCurve.InCubic)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        was_pressed = self._pressed
        self._pressed = False
        if was_pressed and event.button() == Qt.LeftButton:
            if self.rect().contains(event.position().toPoint()):
                self._run_release_sequence()
            else:
                self._animate_to_scale(self._target_idle_or_hover(), self._dur_hover_ms, QEasingCurve.OutCubic)
        super().mouseReleaseEvent(event)


class Settings(QWidget):
    def __init__(self, ui):
        super().__init__()
        self.ui = ui
        self._setup_done = False
        self.preset_buttons = []
        self.display_type_buttons = {}
        self.display_type = None
        self._pending_color = None
        self.h_slider = None
        self.s_slider = None
        self.v_slider = None
        self._suppress_slider_sync = False
        self._spinner_anim = None
        self._tick_anim = None
        self._type_anim = None
        self._type_anim_duration_ms = 100
        self.graph_spinner = None
        self.type_spinner = None
        self.graph_tick = None
        self.type_tick = None
        self._load_seq = 0
        self.add_pixel_screen = self.ui.add_pixel_screen
        self.display_type_indicator = None
        self.display_type_track = None

    def run(self):
        if self._setup_done:
            return
        self._setup_done = True

        self.setFixedSize(640, 550)

        # Main frame
        self.main_frame = QFrame(self)
        self.main_frame.setGeometry(0, 0, 640, 550)
        self.main_frame.setStyleSheet("background-color: #2b2b2b; border-radius: 20px;")
        apply_widget_shadow(self.main_frame, radius=20)

        # Title
        title = QLabel("Settings", self.main_frame)
        f = QFont()
        f.setPointSize(35)
        f.setBold(True)
        title.setFont(f)
        title.setStyleSheet("color: #FFFFFF; border: none;")
        title.setGeometry(0, 16, 640, 55)
        title.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)

        # Divider
        divider = QFrame(self.main_frame)
        divider.setStyleSheet("background-color: #5a5a5a;")
        divider.setFixedSize(300, 1)
        divider.move(
            (self.main_frame.width() - divider.width()) // 2,
            70
        )

        # Accent frame
        self.accent_frame = QFrame(self.main_frame)
        self.accent_frame.setGeometry(45, 90, 551, 256)
        self.accent_frame.setStyleSheet(
            "background-color: #353535; border-radius: 20px; border: 1px solid rgba(96,96,96,0.9);"
        )

        accent_label = QLabel("Accent color", self.accent_frame)
        accent_label.setGeometry(17, 11, 200, 24)
        lf = QFont()
        lf.setPointSize(14)
        lf.setBold(True)
        accent_label.setFont(lf)
        accent_label.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")

        presets_label = QLabel("Presets", self.accent_frame)
        presets_label.setGeometry(392, 13, 200, 24)
        presets_label.setFont(lf)
        presets_label.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")

        # Accent preview
        theme = get_theme()
        self.accent_preview = QFrame(self.accent_frame)
        self.accent_preview.setGeometry(20, 45, 100, 100)
        self.accent_preview.setStyleSheet(
            f"background-color: {theme.get('accent_color', '#5BF69F')}; border-radius: 18px; border: none;"
        )

        # HSV sliders (visual only)
        self.h_slider = self._build_slider("Hue", 20, 160, 260, 14, 0, 360)
        self.s_slider = self._build_slider("Saturation", 20, 182, 260, 14, 0, 100)
        self.v_slider = self._build_slider("Value", 20, 204, 260, 14, 0, 100)
        self._sync_sliders_from_theme()

        # Preset buttons
        preset_colors = ["#5BF69F", "#8B5CF6", "#38BDF8", "#F43F5E", "#F97316", "#F740A8"]
        grid_x = 380
        grid_y = 50
        btn_size = 52
        gap = 14
        for i, color in enumerate(preset_colors):
            row = i // 2
            col = i % 2
            btn = PresetAnimatedButton("", self.accent_frame)
            btn.setGeometry(grid_x + col * (btn_size + gap), grid_y + row * (btn_size + gap), btn_size, btn_size)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._preset_style(color, active=(color == theme.get("accent_color"))))
            btn.clicked.connect(lambda checked=False, c=color: self._apply_preset(c))
            self.preset_buttons.append((btn, color))

        # Display frame
        self.display_frame = QFrame(self.main_frame)
        self.display_frame.setGeometry(45, 355, 551, 169)
        self.display_frame.setStyleSheet(
            "background-color: #353535; border-radius: 20px; border: 1px solid rgba(96,96,96,0.9);"
        )

        display_graph_label = QLabel("Display graph", self.display_frame)
        display_graph_label.setGeometry(16, 12, 200, 24)
        display_graph_label.setFont(lf)
        display_graph_label.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")
        accent = get_theme().get("accent_color", "#5BF69F")
        self.graph_spinner = SpinnerWidget(size=14, thickness=2, color=accent, parent=self.display_frame)
        self.graph_tick = TickWidget(size=14, thickness=2, color=accent, parent=self.display_frame)
        # self._position_status_widgets(display_graph_label, self.graph_spinner, self.graph_tick) added below

        graphs = []
        try:
            graphs = get_all_graph_names()
        except Exception:
            graphs = []

        self.display_dropdown = CustomDropdown(
            self.display_frame,
            box_color="#3f3f3f",
            items=graphs,
            x=16,
            y=40,
            width=350,
            placeholder="Choose graph name",
            rotate_icon=True,
            on_select=self._on_display_graph_selected,
            arrow_color="#6f6f6f"
        )

        self._position_status_widgets(self.display_dropdown, self.graph_spinner, self.graph_tick)

        display_type_label = QLabel("Display type", self.display_frame)
        display_type_label.setGeometry(16, 86, 200, 24)
        display_type_label.setFont(lf)
        display_type_label.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")
        self.type_spinner = SpinnerWidget(size=14, thickness=2, color=accent, parent=self.display_frame)
        self.type_tick = TickWidget(size=14, thickness=2, color=accent, parent=self.display_frame)
        # self._position_status_widgets(self.display_type_buttons["heatmap"], self.type_spinner, self.type_tick) - added below

        self.display_type = "histogram"
        try:
            current = get_current_graph()
            current_type = (current.get("type") or "").strip().lower()
            if current_type in ("histogram", "heatmap"):
                self.display_type = current_type
        except Exception:
            pass
        self.display_type_buttons["histogram"] = self._make_display_type_button(
            "histogram", 16, 116, "left"
        )
        self.display_type_buttons["heatmap"] = self._make_display_type_button(
            "heatmap", 102, 116, "right"
        )
        self._apply_display_type_styles()
        self._init_display_type_indicator()
        self._position_status_widgets(self.display_type_buttons["heatmap"], self.type_spinner, self.type_tick)
        self._sync_display_graph_selection(graphs)
        self._set_status_state("idle")

    def _build_slider(self, label, x, y, width, height, min_val, max_val):
        lab = QLabel(label, self.accent_frame)
        lab.setGeometry(x + width - 6, y - 2, 100, 18)
        lf = QFont()
        lf.setPointSize(11)
        lab.setFont(lf)
        lab.setStyleSheet("color: #bdbdbd; background: transparent; border: none;")

        slider = CircleSlider(self.accent_frame, min_val=min_val, max_val=max_val, value=min_val, snap_step=1, label=False)
        slider.setGeometry(x, y, width, max(18, height))
        slider.valueChanged.connect(self._on_slider_changed)
        return slider

    def _preset_style(self, color, active=False):
        border = "#d7d7d7" if active else "#5a5a5a"
        return f"""
            QPushButton {{
                background-color: {color};
                border-radius: 12px;
                border: 2px solid {border};
            }}
            QPushButton:pressed {{
                background-color: {color};
                border-radius: 12px;
                border: 2px solid {border};
            }}
        """

    def _apply_preset(self, color):
        hover = darker(color, 0.8)
        text = "#1e1e1e" if ideal_text_color(color) == "black" else "#FFFFFF"
        set_theme(accent_color=color, hover_color=hover, text_color=text)
        self.accent_preview.setStyleSheet(
            f"background-color: {color}; border-radius: 18px; border: none;"
        )
        self._sync_sliders_from_color(color)

        for btn, btn_color in self.preset_buttons:
            btn.setStyleSheet(self._preset_style(btn_color, active=(btn_color == color)))

        if hasattr(self.ui, "apply_theme"):
            self.ui.apply_theme()

    def _sync_sliders_from_theme(self):
        theme = get_theme()
        self._sync_sliders_from_color(theme.get("accent_color", "#5BF69F"))

    def _sync_sliders_from_color(self, hex_color):
        try:
            h, s, v = hex_to_hsv(hex_color)
            if self.h_slider:
                self.h_slider.blockSignals(True)
                self.h_slider.setValue(int(h))
                self.h_slider.blockSignals(False)
            if self.s_slider:
                self.s_slider.blockSignals(True)
                self.s_slider.setValue(int(s))
                self.s_slider.blockSignals(False)
            if self.v_slider:
                self.v_slider.blockSignals(True)
                self.v_slider.setValue(int(v))
                self.v_slider.blockSignals(False)
        except Exception:
            pass

    def _on_slider_changed(self):
        if not (self.h_slider and self.s_slider and self.v_slider):
            return
        h = self.h_slider.value()
        s = self.s_slider.value()
        v = self.v_slider.value()
        hex_color = hsv_to_hex(h, s, v)
        self._pending_color = hex_color
        self.accent_preview.setStyleSheet(
            f"background-color: {hex_color}; border-radius: 18px; border: none;"
        )
        for btn, btn_color in self.preset_buttons:
            btn.setStyleSheet(self._preset_style(btn_color, active=False))
        self._apply_slider_color()

    def _apply_slider_color(self):
        if not self._pending_color:
            return
        hover = darker(self._pending_color, 0.8)
        text = "#1e1e1e" if ideal_text_color(self._pending_color) == "black" else "#FFFFFF"
        set_theme(accent_color=self._pending_color, hover_color=hover, text_color=text)
        if hasattr(self.ui, "apply_theme"):
            self._suppress_slider_sync = True
            try:
                self.ui.apply_theme()
            finally:
                self._suppress_slider_sync = False

    def _make_display_type_button(self, text, x, y, side):
        btn = QPushButton(text, self.display_frame)
        btn.setGeometry(x, y, 86, 26)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda checked=False, t=text: self._set_display_type(t))
        btn.setProperty("side", side)
        return btn

    def _set_display_type(self, display_type):
        if display_type == self.display_type:
            return
        self.display_type = display_type
        try:
            change_graph_type(display_type)
        except Exception:
            pass
        self._load_seq += 1
        seq_id = self._load_seq
        self._apply_display_type_styles()
        self._animate_display_type_indicator()
        self._set_status_state("loading")

        def _worker():
            try:
                current_user = get_current_user()
                current_graph = get_current_graph()["graph"]
                # DEBUG: worker thread starting graph recreation for display_type=%s
                # The thread regenerates the cached display image when the user switches types.
                if display_type == "histogram":
                    # DEBUG: calling create_histogram for user=%s graph=%s
                    create_histogram(current_user, current_graph)
                else:
                    # DEBUG: calling create_heatmap for user=%s graph=%s
                    create_heatmap(current_user, current_graph)
            finally:
                def _ui_finish():
                    try:
                        self.add_pixel_screen._refresh_homepage_heatmap()
                    finally:
                        self._maybe_finish_load(seq_id)
                QTimer.singleShot(0, self, _ui_finish)

        threading.Thread(target=lambda: _worker(), daemon=True).start()
    def _apply_display_type_styles(self):
        theme = get_theme()
        text = theme.get("text_color", "#FFFFFF")
        for name, btn in self.display_type_buttons.items():
            color = text if name == self.display_type else "#a0a0a0"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {color};
                    font-size: 12px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: transparent;
                }}
            """)


    def update_accent_colors(self):
        theme = get_theme()
        self.accent_preview.setStyleSheet(
            f"background-color: {theme.get('accent_color', '#5BF69F')}; border-radius: 18px; border: none;"
        )
        if not self._suppress_slider_sync:
            self._sync_sliders_from_theme()
        self._apply_display_type_styles()
        try:
            accent = theme.get("accent_color", "#5BF69F")
            if self.graph_spinner is not None:
                self.graph_spinner.update_color(accent)
            if self.type_spinner is not None:
                self.type_spinner.update_color(accent)
            if self.graph_tick is not None:
                self.graph_tick.update_color(accent)
            if self.type_tick is not None:
                self.type_tick.update_color(accent)
        except Exception:
            pass
        try:
            self.display_dropdown.update_accent_colors()
        except Exception:
            pass
        self._update_display_type_indicator_style()

    def _sync_display_graph_selection(self, graphs):
        if not graphs:
            return
        selected = None
        try:
            current = get_current_graph()
            current_graph = current.get("graph")
            if current_graph in graphs:
                selected = current_graph
        except Exception:
            selected = None
        if not selected:
            selected = graphs[0]
        if selected:
            self.display_dropdown.set_value(selected)

    def _rebuild_display_dropdown_items(self, graphs):
        dd = getattr(self, "display_dropdown", None)
        if dd is None:
            return

        items = list(graphs or [])
        dd.items = items

        try:
            dd._close_dropdown()
        except Exception:
            try:
                dd.dropdown.hide()
            except Exception:
                pass
            dd.arrow_open = False
            try:
                dd._set_arrow_angle(0)
            except Exception:
                pass

        try:
            for child in dd.scroll_content.findChildren(QWidget, options=Qt.FindDirectChildrenOnly):
                child.deleteLater()
        except Exception:
            pass
        dd.option_buttons = []

        width = dd.width()
        for i, text in enumerate(items):
            btn = QPushButton(text, dd.scroll_content)
            btn.setGeometry(10, i * dd.row_h, width - 22, dd.row_h)

            bf = QFont()
            bf.setPointSize(12)
            btn.setFont(bf)
            btn.setStyleSheet("""
                QPushButton {
                    color: white;
                    background: transparent;
                    border: none;
                    text-align: left;
                    padding-left: 5px;
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                }
            """)
            btn.clicked.connect(lambda checked=False, b=btn, t=text: dd.select(b, t))
            dd.option_buttons.append(btn)

            if i < len(items) - 1:
                div = QFrame(dd.scroll_content)
                div.setGeometry(16, (i + 1) * dd.row_h - 1, width - 32, 1)
                div.setStyleSheet("background-color: rgba(144,144,144,128);")

        if not items:
            empty = QLabel("No graphs found", dd.scroll_content)
            empty.setGeometry(0, 0, width, dd.row_h)
            ef = QFont()
            ef.setPointSize(11)
            empty.setFont(ef)
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: #9a9a9a; background: transparent;")

        visible_rows = min(3, len(items)) if items else 1
        drop_h = dd.row_h * visible_rows + 2
        dd._dropdown_full_h = int(drop_h)
        dd.dropdown.setGeometry(dd.x(), dd.y() + 26, width, drop_h)
        dd.inner_frame.setGeometry(1, 1, width - 2, drop_h - 2)
        dd.scroll.setGeometry(0, 0, width - 2, drop_h - 2)
        dd.scroll_content.setMinimumHeight(dd.row_h * len(items) if items else dd.row_h)
        dd.scroll_content.setMinimumWidth(width)

    def _on_display_graph_selected(self, graph_name):
        if not graph_name:
            return
        try:
            current = get_current_graph()
            if current and current.get("graph") == graph_name:
                return
        except Exception:
            pass
        try:
            change_display_graph(graph_name)
        except Exception:
            pass
        self._load_seq += 1
        seq_id = self._load_seq
        self._set_status_state("loading")

        def _worker():
            try:
                current = get_current_graph()
                display_type = (current.get("type") or "").strip().lower()
                if display_type == "heatmap":
                    create_heatmap(get_current_user(), graph_name)
                else:
                    create_histogram(get_current_user(), graph_name)
            finally:
                def _ui_finish():
                    try:
                        self.add_pixel_screen._refresh_homepage_heatmap()
                    finally:
                        self._maybe_finish_load(seq_id)
                QTimer.singleShot(0, self, _ui_finish)

        threading.Thread(target=_worker, daemon=True).start()

    def refresh_after_account_change(self, min_loading_ms=2000):
        try:
            current_user = get_current_user()
        except Exception:
            current_user = None

        try:
            graphs = get_user_graph_names(current_user) if current_user else []
        except Exception:
            graphs = []
        self._rebuild_display_dropdown_items(graphs)

        try:
            current = get_current_graph() or {}
        except Exception:
            current = {}

        selected_graph = current.get("graph")
        display_type = (current.get("type") or "").strip().lower()
        if display_type not in ("histogram", "heatmap"):
            display_type = "histogram"

        if selected_graph not in graphs:
            selected_graph = graphs[0] if graphs else None
            if selected_graph:
                try:
                    change_display_graph(selected_graph)
                except Exception:
                    pass

        try:
            if selected_graph:
                self.display_dropdown._apply_selection(selected_graph, active_button=None)
                self.display_dropdown.selected = selected_graph
            else:
                self.display_dropdown.selected = None
                self.display_dropdown.label.setText("No graphs found")
                self.display_dropdown.label.setStyleSheet("""
                    QLabel {
                        color: #808080;
                        background: transparent;
                        border: none;
                    }
                """)
        except Exception:
            pass

        self._load_seq += 1
        seq_id = self._load_seq
        self._set_status_state("loading")
        started_at = time.monotonic()

        def _finish_ui():
            try:
                self.add_pixel_screen._refresh_homepage_heatmap()
            finally:
                elapsed_ms = int((time.monotonic() - started_at) * 1000)
                remaining_ms = max(0, int(min_loading_ms) - elapsed_ms)
                QTimer.singleShot(remaining_ms, self, lambda: self._maybe_finish_load(seq_id))

        if not selected_graph:
            QTimer.singleShot(0, self, _finish_ui)
            return

        def _worker():
            try:
                if display_type == "heatmap":
                    create_heatmap(current_user, selected_graph)
                else:
                    create_histogram(current_user, selected_graph)
            finally:
                QTimer.singleShot(0, self, _finish_ui)

        threading.Thread(target=_worker, daemon=True).start()

    def _maybe_finish_load(self, seq_id):
        if seq_id != self._load_seq:
            return
        self._set_status_state("done")

    def _set_status_state(self, state):
        if state not in ("idle", "loading", "done"):
            return
        if state == "idle":
            self._stop_spinner()
            for w in (self.graph_spinner, self.type_spinner, self.graph_tick, self.type_tick):
                if w is not None:
                    w.hide()
            return
        if state == "loading":
            self._start_spinner()
            return
        if state == "done":
            self._stop_spinner_with_tick()

    def _ensure_spinner(self):
        if self._spinner_anim is not None:
            return
        self._spinner_anim = QVariantAnimation(self)
        self._spinner_anim.setStartValue(0)
        self._spinner_anim.setEndValue(360)
        self._spinner_anim.setDuration(900)
        self._spinner_anim.setLoopCount(-1)
        self._spinner_anim.setEasingCurve(QEasingCurve.InOutSine)
        self._spinner_anim.valueChanged.connect(self._set_spinner_angle)

    def _set_spinner_angle(self, angle):
        if self.graph_spinner is not None:
            self.graph_spinner.setAngle(angle)
        if self.type_spinner is not None:
            self.type_spinner.setAngle(angle)

    def _start_spinner(self):
        self._ensure_spinner()
        if self._spinner_anim is None:
            return
        self._spinner_anim.setDuration(900)
        for w in (self.graph_spinner, self.type_spinner):
            if w is not None:
                w.show()
        for w in (self.graph_tick, self.type_tick):
            if w is not None:
                w.hide()
        if self._spinner_anim.state() != QVariantAnimation.Running:
            self._spinner_anim.start()

    def _stop_spinner(self):
        if self._spinner_anim is not None:
            self._spinner_anim.stop()

    def _stop_spinner_with_tick(self):
        self._ensure_spinner()
        self._ensure_tick_anim()
        if self._spinner_anim is not None:
            self._spinner_anim.setDuration(1500)
            QTimer.singleShot(200, self._spinner_anim.stop)

        def _show_ticks():
            for w in (self.graph_spinner, self.type_spinner):
                if w is not None:
                    w.hide()
            for w in (self.graph_tick, self.type_tick):
                if w is not None:
                    w.show()
            if self._tick_anim is not None:
                self._tick_anim.stop()
                self._set_tick_progress(0.0)
                self._tick_anim.start()

        QTimer.singleShot(220, _show_ticks)
        QTimer.singleShot(2220, self._hide_ticks)

    def _ensure_tick_anim(self):
        if self._tick_anim is not None:
            return
        self._tick_anim = QVariantAnimation(self)
        self._tick_anim.setStartValue(0.0)
        self._tick_anim.setEndValue(1.0)
        self._tick_anim.setDuration(220)
        self._tick_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._tick_anim.valueChanged.connect(self._set_tick_progress)

    def _set_tick_progress(self, value):
        if self.graph_tick is not None:
            self.graph_tick.setProgress(value)
        if self.type_tick is not None:
            self.type_tick.setProgress(value)

    def _hide_ticks(self):
        for w in (self.graph_tick, self.type_tick):
            if w is not None:
                w.hide()

    def _position_status_widgets(self, obj, spinner, tick):
        if obj is None or spinner is None or tick is None:
            return
        geom = obj.geometry()
        x = geom.x() + geom.width() + 10
        y = int(geom.y() + (geom.height() / 2) - (spinner.height() / 2))
        spinner.move(x, y)
        tick.move(x, y)

    def _display_type_indicator_radius(self):
        return """
            border-radius: 12px;
        """

    def _init_display_type_indicator(self):
        btn = self.display_type_buttons.get(self.display_type)
        if btn is None:
            return
        if self.display_type_track is None:
            left_btn = self.display_type_buttons.get("histogram")
            right_btn = self.display_type_buttons.get("heatmap")
            if left_btn is not None and right_btn is not None:
                x = left_btn.x()
                y = left_btn.y()
                w = (right_btn.x() + right_btn.width()) - left_btn.x()
                h = left_btn.height()
                self.display_type_track = QFrame(self.display_frame)
                self.display_type_track.setGeometry(x, y, w, h)
                self.display_type_track.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                self.display_type_track.setAttribute(Qt.WA_StyledBackground, True)
                self.display_type_track.setStyleSheet("""
                    QFrame {
                        background-color: #5a5a5a;
                        border-radius: 12px;
                    }
                """)
        self.display_type_indicator = QFrame(self.display_frame)
        self.display_type_indicator.setFixedSize(btn.size())
        self.display_type_indicator.move(btn.pos())
        self.display_type_indicator.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.display_type_indicator.setAttribute(Qt.WA_StyledBackground, True)
        self._update_display_type_indicator_style()
        if self.display_type_track is not None:
            self.display_type_track.lower()
        self.display_type_indicator.raise_()
        for b in self.display_type_buttons.values():
            b.raise_()

    def _update_display_type_indicator_style(self):
        if self.display_type_indicator is None:
            return
        btn = self.display_type_buttons.get(self.display_type)
        if btn is None:
            return
        theme = get_theme()
        accent = theme.get("accent_color", "#5BF69F")
        radius = self._display_type_indicator_radius()
        self.display_type_indicator.setStyleSheet(f"""
            QFrame {{
                background-color: {accent};
                {radius}
            }}
        """)

    def _animate_display_type_indicator(self):
        if self.display_type_indicator is None:
            self._init_display_type_indicator()
            return
        btn = self.display_type_buttons.get(self.display_type)
        if btn is None:
            return
        start_pos = self.display_type_indicator.pos()
        end_pos = btn.pos()
        if start_pos == end_pos:
            self._update_display_type_indicator_style()
            return
        if self._type_anim is None:
            self._type_anim = QPropertyAnimation(self.display_type_indicator, b"pos", self)
        self._type_anim.stop()
        self._type_anim.setDuration(self._type_anim_duration_ms)
        self._type_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._type_anim.setStartValue(start_pos)
        self._type_anim.setEndValue(end_pos)
        self._type_anim.start()
        self._update_display_type_indicator_style()

    def set_display_type_animation_speed(self, duration_ms):
        try:
            self._type_anim_duration_ms = max(40, int(duration_ms))
        except Exception:
            self._type_anim_duration_ms = 140
