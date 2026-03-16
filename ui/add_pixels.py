from PySide6.QtWidgets import QWidget, QFrame, QLabel, QPushButton, QLineEdit, QApplication
import os
from PySide6.QtGui import QPixmap, QFont, QIcon, QTransform
from PySide6.QtCore import Qt, QPoint, QSize, QTimer, QPropertyAnimation, QEasingCurve
from datetime import date, timedelta, datetime
import re
import threading
from functions.create_graph_images import create_heatmap, create_histogram
from helpers.CustomWidgets import RoundedFrame, CalendarPopup, CustomDropdown, HoverScaleButton, CircleScrollBar, apply_widget_shadow
from helpers.json_manager import (
    get_current_user,
    get_user_graphs,
    get_graph_type,
    add_pixel_entry,
    get_current_graph,
    get_theme,
    check_pixel_conflict,
    resolve_pixel_conflict,
)


class AddPixels(QWidget):
    def __init__(self, ui):
        super().__init__()
        self._setup_done = False
        self.selected_date = None
        self.ui = ui
        self.accent_buttons = []
        self._pending_conflict = None

    def run(self):
        if self._setup_done:
            return
        self._setup_done = True

        self.setFixedSize(640, 550)

        # MainFrame similar to homepage
        self.main_frame = QFrame(self)
        self.main_frame.setGeometry(0, 0, 640, 550)
        self.main_frame.setStyleSheet("background-color: #2b2b2b; border-radius: 20px;")
        apply_widget_shadow(self.main_frame, radius=20)

        # Title
        title = QLabel("Add Pixels", self.main_frame)
        f = QFont()
        f.setPointSize(35)
        f.setBold(True)
        title.setFont(f)
        title.setStyleSheet("color: #FFFFFF;")
        title.setGeometry(0, 16, 640, 40)
        title.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)


        # Divider
        divider = QFrame(self.main_frame)
        divider.setStyleSheet("background-color: #5a5a5a;")
        divider.setFixedSize(300, 1)
        divider.move(
            (self.main_frame.width() - divider.width()) // 2,
            70
        )


        # context_frame
        ctx = QFrame(self.main_frame)
        ctx.setGeometry(220, 100, 200, 100)
        ctx.setAttribute(Qt.WA_StyledBackground, True)
        ctx.setContentsMargins(10, 10, 10, 10)
        ctx.setStyleSheet("""
        QFrame {
            background-color: #2e3a34;
            border-radius: 20px;
            border: 1px solid rgba(59,82,71,217);
        }
        """)

        ctx_text = QLabel(
            "Add pixels to track\ndaily progress on your\nchosen graph.",
            ctx
        )
        tf = QFont()
        tf.setPointSize(10)
        ctx_text.setFont(tf)
        ctx_text.setAlignment(Qt.AlignCenter)
        ctx_text.setStyleSheet("color: #FFFFFF; background: transparent;")
        ctx_text.setGeometry(0, 0, 200, 100)

        # form_frame
        form = QFrame(self.main_frame)
        form.setGeometry(44, 230, 552, 280)
        form.setStyleSheet(
            "background-color: #353535; border-radius: 20px; border: 1px solid rgba(96,96,96,0.9);"
        )

        # graph_label
        graph_label = QLabel("Choose graph:", form)
        graph_label.setGeometry(12, 10, 300, 23)

        gf = QFont()
        gf.setPointSize(15)
        graph_label.setFont(gf)

        graph_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        graph_label.setFrameStyle(QFrame.NoFrame)
        graph_label.setLineWidth(0)

        graph_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                background: transparent;
                border: none;
            }
        """)


        current_user = None
        user_graphs = []
        try:
            current_user = get_current_user()
            user_graphs = get_user_graphs(current_user)
        except Exception:
            current_user = None
            user_graphs = []

        graph_names = []
        for g in user_graphs:
            if isinstance(g, dict) and g.get("graph_id"):
                graph_names.append(g.get("graph_id"))

        self.current_user = current_user
        self.current_graph = None
        self.current_graph_type = None

        self.dropdown = CustomDropdown(
            form,
            items=graph_names,
            x=12,
            y=39,
            on_select=self._on_graph_selected)

        date_label = QLabel("Choose Date", form)
        date_label.setGeometry(12, 80, 300, 23)
        date_label.setFont(gf)
        date_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        date_label.setFrameStyle(QFrame.NoFrame)
        date_label.setLineWidth(0)
        date_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                background: transparent;
                border: none;
            }
        """)

        calendar_icon = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "assets",
            "calender.png"
        )
        self.date_dropdown = CustomDropdown(
            form,
            items=[],
            x=12,
            y=110,
            placeholder="Choose Date",
            icon_path=calendar_icon,
            rotate_icon=False
        )
        self.date_dropdown.toggle_dropdown = self._toggle_calendar

        qty_label = QLabel("Enter quantity:", form)
        qty_label.setGeometry(12, 150, 300, 23)
        qty_label.setFont(gf)
        qty_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        qty_label.setFrameStyle(QFrame.NoFrame)
        qty_label.setLineWidth(0)
        qty_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                background: transparent;
                border: none;
            }
        """)

        self.qty_box = RoundedFrame(form, tl=20, tr=20, br=20, bl=20, make_border=False)
        self.qty_box.setGeometry(12, 180, 361, 22)
        self.qty_box.setStyleSheet("""
            QFrame {
                background-color: #3e3e3e;
            }
        """)
        self.qty_box.set_bg_color("#3e3e3e")

        self.qty_input = QLineEdit(self.qty_box)
        self.qty_input.setGeometry(10, 0, 341, 22)
        self.qty_input.setPlaceholderText("Enter quantity")
        mono_family = self.ui.fonts.get("mono") or "Roboto Mono"
        self.qty_input.setFont(QFont(mono_family, 11))
        self.qty_input.setReadOnly(True)
        self._set_qty_interaction_state(enabled=False)
        self.qty_input.textChanged.connect(self._on_qty_changed)
        self.qty_input.installEventFilter(self)

        self.qty_error = QFrame(form)
        self.qty_error.setGeometry(12, 206, 361, 20)
        self.qty_error.setAttribute(Qt.WA_StyledBackground, True)
        self.qty_error.setStyleSheet("""
            QFrame {
                background-color: #7a1e1e;
                border-radius: 8px;
            }
        """)
        self.qty_error_label = QLabel("", self.qty_error)
        self.qty_error_label.setGeometry(6, 0, 349, 20)
        self.qty_error_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.qty_error_label.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")
        self.qty_error.hide()

        self.submit_btn = HoverScaleButton("Submit", form, border_radius=15)
        self.submit_btn.setGeometry(12, 230, 100, 30)
        self.submit_btn.setCursor(Qt.PointingHandCursor)
        self.submit_btn.setFont(gf)
        self.accent_buttons.append(self.submit_btn)
        self._apply_accent_button_style(self.submit_btn)
        self.submit_btn.clicked.connect(self.submit)

        # delete hint label
        delete_hint = QLabel("to delete a pixel click ", form)
        delete_hint.setGeometry(122, 230, 136, 30)
        delete_hint.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        delete_hint.setStyleSheet("color: #8f8f8f; background: transparent; border: none; font-size: 13px;")

        self.delete_link = QPushButton("here", form)
        self.delete_link.setGeometry(255, 230, 32, 30)
        self.delete_link.setFlat(True)
        self.delete_link.setCursor(Qt.PointingHandCursor)
        self.delete_link.setStyleSheet("""
            QPushButton {
                color: #c0392b;
                background: transparent;
                border: none;
                font-size: 13px;
                text-decoration: underline;
                padding: 0;
                text-align: left;
            }
            QPushButton:hover { color: #e74c3c; }
        """)
        self.delete_link.clicked.connect(self._open_delete_modal)

        self.success_popup = QFrame(self.main_frame)
        self.success_popup.setFixedSize(420, 140)
        self.success_popup.setAttribute(Qt.WA_StyledBackground, True)
        self.success_popup.setStyleSheet("""
            QFrame {
                background-color: #2f8f5b;
                border-radius: 16px;
                border: 1px solid rgba(0,0,0,0.25);
            }
        """)
        sp_x = (self.main_frame.width() - self.success_popup.width()) // 2
        sp_y = (self.main_frame.height() - self.success_popup.height()) // 2
        self.success_popup.move(sp_x, sp_y)
        self.success_label = QLabel("", self.success_popup)
        self.success_label.setGeometry(12, 12, 396, 70)
        self.success_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.success_label.setWordWrap(True)
        self.success_label.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")
        self.success_ok_btn = QPushButton("OK", self.success_popup)
        self.success_ok_btn.setGeometry(160, 96, 100, 30)
        self.success_ok_btn.setCursor(Qt.PointingHandCursor)
        self.success_ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #e8f9ef;
                color: #1a5f3a;
                border-radius: 14px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #cfeedd;
            }
            QPushButton:pressed {
                background-color: #b9e4cc;
            }
        """)
        self.success_ok_btn.clicked.connect(self._hide_success_popup)
        self.success_popup.hide()

        self.conflict_popup = QFrame(self.main_frame)
        self.conflict_popup.setFixedSize(460, 165)
        self.conflict_popup.setAttribute(Qt.WA_StyledBackground, True)
        self.conflict_popup.setStyleSheet("""
            QFrame {
                background-color: #5a2f2f;
                border-radius: 16px;
                border: 1px solid rgba(0,0,0,0.30);
            }
        """)
        cp_x = (self.main_frame.width() - self.conflict_popup.width()) // 2
        cp_y = (self.main_frame.height() - self.conflict_popup.height()) // 2
        self.conflict_popup.move(cp_x, cp_y)

        self.conflict_label = QLabel("", self.conflict_popup)
        self.conflict_label.setGeometry(12, 14, 436, 82)
        self.conflict_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.conflict_label.setWordWrap(True)
        self.conflict_label.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")

        self.conflict_cancel_btn = QPushButton("Cancel", self.conflict_popup)
        self.conflict_cancel_btn.setGeometry(58, 112, 100, 32)
        self.conflict_cancel_btn.setCursor(Qt.PointingHandCursor)
        self.conflict_cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #dcdcdc;
                color: #222222;
                border-radius: 14px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #c9c9c9;
            }
        """)
        self.conflict_cancel_btn.clicked.connect(self._cancel_conflict_popup)

        self.conflict_combine_btn = QPushButton("Combine", self.conflict_popup)
        self.conflict_combine_btn.setGeometry(178, 112, 100, 32)
        self.conflict_combine_btn.setCursor(Qt.PointingHandCursor)
        self.conflict_combine_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0c15a;
                color: #1f1f1f;
                border-radius: 14px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #d9ad4f;
            }
        """)
        self.conflict_combine_btn.clicked.connect(lambda: self._resolve_conflict("combine"))

        self.conflict_replace_btn = QPushButton("Replace", self.conflict_popup)
        self.conflict_replace_btn.setGeometry(298, 112, 100, 32)
        self.conflict_replace_btn.setCursor(Qt.PointingHandCursor)
        self.conflict_replace_btn.setStyleSheet("""
            QPushButton {
                background-color: #8fd7a7;
                color: #103d1f;
                border-radius: 14px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #79c491;
            }
        """)
        self.conflict_replace_btn.clicked.connect(lambda: self._resolve_conflict("replace"))
        self.conflict_popup.hide()

        # ── delete pixel modal ──────────────────────────────────────────
        self.delete_modal_overlay = QFrame(self.main_frame)
        self.delete_modal_overlay.setGeometry(0, 0, 640, 550)
        self.delete_modal_overlay.setAttribute(Qt.WA_StyledBackground, True)
        self.delete_modal_overlay.setStyleSheet("QFrame { background-color: rgba(0,0,0,165); }")
        self.delete_modal_overlay.hide()

        delete_modal = QFrame(self.delete_modal_overlay)
        delete_modal.setGeometry(95, 150, 450, 250)
        delete_modal.setAttribute(Qt.WA_StyledBackground, True)
        delete_modal.setStyleSheet("""
            QFrame {
                background-color: #2f2f2f;
                border: 1px solid #555555;
                border-radius: 16px;
            }
        """)

        dm_title = QLabel("Delete a Pixel", delete_modal)
        dm_tf = QFont(); dm_tf.setPointSize(18); dm_tf.setBold(True)
        dm_title.setFont(dm_tf)
        dm_title.setGeometry(0, 14, 450, 28)
        dm_title.setAlignment(Qt.AlignCenter)
        dm_title.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")

        dm_lf = QFont(); dm_lf.setPointSize(11)

        dm_graph_lbl = QLabel("Graph", delete_modal)
        dm_graph_lbl.setFont(dm_lf)
        dm_graph_lbl.setGeometry(24, 52, 60, 18)
        dm_graph_lbl.setStyleSheet("color: #cfcfcf; background: transparent; border: none;")

        self.dm_graph_dropdown = CustomDropdown(
            delete_modal,
            items=[g for g in (graph_names or [])],
            x=24,
            y=74,
            width=402,
            placeholder="Choose graph",
            on_select=self._on_dm_graph_selected,
        )

        dm_date_lbl = QLabel("Date", delete_modal)
        dm_date_lbl.setFont(dm_lf)
        dm_date_lbl.setGeometry(24, 106, 60, 18)
        dm_date_lbl.setStyleSheet("color: #cfcfcf; background: transparent; border: none;")

        calendar_icon2 = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "assets", "calender.png"
        )
        self.dm_date_dropdown = CustomDropdown(
            delete_modal,
            items=[],
            x=24,
            y=128,
            width=402,
            placeholder="Choose Date",
            icon_path=calendar_icon2,
            rotate_icon=False,
        )
        self.dm_date_dropdown.toggle_dropdown = self._toggle_dm_calendar
        self.dm_selected_date = None

        self.dm_error = QLabel("", delete_modal)
        dm_ef = QFont(); dm_ef.setPointSize(10)
        self.dm_error.setFont(dm_ef)
        self.dm_error.setGeometry(24, 162, 402, 18)
        self.dm_error.setStyleSheet("color: #ff7e7e; background: transparent; border: none;")
        self.dm_error.hide()

        dm_cancel = QPushButton("Cancel", delete_modal)
        dm_cancel.setGeometry(24, 200, 130, 32)
        dm_cancel.setCursor(Qt.PointingHandCursor)
        dm_cancel.setStyleSheet("""
            QPushButton { background-color: #4b4b4b; color: #FFFFFF;
                border: 1px solid #616161; border-radius: 10px; font-size: 13px; }
            QPushButton:hover { background-color: #595959; }
        """)
        dm_cancel.clicked.connect(self._close_delete_modal)

        self.dm_delete_btn = QPushButton("Delete", delete_modal)
        self.dm_delete_btn.setGeometry(296, 200, 130, 32)
        self.dm_delete_btn.setCursor(Qt.PointingHandCursor)
        self.dm_delete_btn.setStyleSheet("""
            QPushButton { background-color: #c0392b; color: #FFFFFF;
                border-radius: 10px; font-size: 13px; border: none; }
            QPushButton:hover { background-color: #e74c3c; }
        """)
        self.dm_delete_btn.clicked.connect(self._submit_delete_pixel)
        self.dm_current_graph = None

        # calendar for the delete modal (parented to overlay so it floats above)
        self.dm_calendar_popup = CalendarPopup(
            self.delete_modal_overlay,
            x=119,
            y=108,
            width=402,
            height=200,
            on_date_selected=self._on_dm_date_selected,
        )
        self.dm_calendar_popup.hide()

        # calendar popup (custom)
        dd_pos = self.date_dropdown.mapTo(self.main_frame, QPoint(0, 0))
        cal_w = self.date_dropdown.width()
        cal_h = 200
        above_y = dd_pos.y() - cal_h - 6
        if above_y < 0:
            cal_y = dd_pos.y() + 26
        else:
            cal_y = above_y
        self.calendar_popup = CalendarPopup(
            self.main_frame,
            x=dd_pos.x(),
            y=cal_y,
            width=cal_w,
            height=cal_h,
            on_date_selected=self._on_date_selected
        )
        self.calendar_popup.hide()

        for w in (form, self.main_frame, self):
            try:
                w.installEventFilter(self)
            except Exception:
                pass

    # ── delete modal logic ──────────────────────────────────────────────

    def _open_delete_modal(self):
        self._hide_success_popup()
        self._hide_conflict_popup()
        # refresh graph list in case it changed
        user_graphs = []
        try:
            user_graphs = get_user_graphs(self.current_user) if self.current_user else []
        except Exception:
            pass
        graph_names = [g["graph_id"] for g in user_graphs if isinstance(g, dict) and g.get("graph_id")]
        try:
            self.dm_graph_dropdown.items = graph_names
        except Exception:
            pass
        self.dm_current_graph = None
        self.dm_selected_date = None
        self.dm_date_dropdown.label.setText("Choose Date")
        self.dm_date_dropdown.label.setStyleSheet("QLabel { color: #808080; background: transparent; border: none; }")
        self.dm_error.hide()
        self.delete_modal_overlay.raise_()
        self.delete_modal_overlay.show()

    def _close_delete_modal(self):
        self.dm_calendar_popup.hide()
        self.delete_modal_overlay.hide()

    def _on_dm_graph_selected(self, graph_name):
        self.dm_current_graph = graph_name
        self.dm_error.hide()

    def _toggle_dm_calendar(self):
        if self.dm_calendar_popup.isVisible():
            self.dm_calendar_popup.hide()
            return
        self.dm_calendar_popup.refresh()
        self.dm_calendar_popup.raise_()
        self.dm_calendar_popup.show()

    def _on_dm_date_selected(self, d):
        self.dm_selected_date = d
        self.dm_date_dropdown.label.setText(d.strftime("%d %b %Y"))
        self.dm_date_dropdown.label.setStyleSheet("QLabel { color: #FFFFFF; background: transparent; border: none; }")
        self.dm_calendar_popup.hide()

    def _submit_delete_pixel(self):
        self.dm_error.hide()
        if not self.current_user:
            self.dm_error.setText("No current user found"); self.dm_error.show(); return
        if not self.dm_current_graph:
            self.dm_error.setText("Select a graph"); self.dm_error.show(); return
        if not self.dm_selected_date:
            self.dm_error.setText("Select a date"); self.dm_error.show(); return

        date_str = self.dm_selected_date.strftime("%d%m%Y")
        conflict = check_pixel_conflict(self.current_user, self.dm_current_graph, date_str)
        if conflict.get("ok", True):
            pretty = self.dm_selected_date.strftime("%d %b %Y")
            self.dm_error.setText(f"No pixel on {pretty} for '{self.dm_current_graph}'")
            self.dm_error.show()
            return

        import json
        from helpers.json_manager import BASE_DIR
        file_path = os.path.join(BASE_DIR, "Data", "pixels.json")
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
        except Exception as e:
            self.dm_error.setText(f"Could not read data: {e}"); self.dm_error.show(); return

        deleted = False
        for user_entry in data:
            if not (isinstance(user_entry, dict) and self.current_user in user_entry):
                continue
            for graph in user_entry[self.current_user]:
                if not (isinstance(graph, dict) and graph.get("graph_id") == self.dm_current_graph):
                    continue
                pixels = graph.get("pixels", [])
                new_pixels = []
                for p in pixels:
                    if isinstance(p, dict) and date_str in p:
                        deleted = True; continue
                    if isinstance(p, str):
                        try:
                            d, _ = p.split("_", 1)
                            if d == date_str:
                                deleted = True; continue
                        except Exception:
                            pass
                    new_pixels.append(p)
                graph["pixels"] = new_pixels
                break
            break

        if not deleted:
            self.dm_error.setText("Pixel not found"); self.dm_error.show(); return

        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            self.dm_error.setText(f"Could not save: {e}"); self.dm_error.show(); return

        self._close_delete_modal()
        pretty = self.dm_selected_date.strftime("%d %b %Y")
        self.success_label.setText(f"Deleted pixel on {pretty} from '{self.dm_current_graph}'.")
        self.success_popup.raise_()
        self.success_popup.show()
        self._maybe_update_display_graph_for(self.dm_current_graph)

    def _maybe_update_display_graph_for(self, graph_id):
        """Like _maybe_update_display_graph but accepts an explicit graph_id."""
        try:
            current = get_current_graph()
        except Exception:
            return
        if not current or current.get("graph") != graph_id:
            return
        display_type = (current.get("type") or "").strip().lower()
        def _worker():
            try:
                if display_type == "histogram":
                    create_histogram(self.current_user, graph_id)
                else:
                    create_heatmap(self.current_user, graph_id)
            finally:
                QTimer.singleShot(0, self, self._refresh_homepage_heatmap)
        threading.Thread(target=_worker, daemon=True).start()

    def _apply_accent_button_style(self, btn):
        theme = get_theme()
        accent = theme.get("accent_color", "#5BF69F")
        hover = theme.get("hover_color", "#48C47F")
        text = theme.get("text_color", "#FFFFFF")
        try:
            btn.set_text_color(text)
        except Exception:
            pass
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: {text};
                font-size: 15px;
                border-radius: 15px;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:pressed {{
                background-color: {hover};
                border-radius: 15px;
            }}
        """)

    def _rebuild_graph_dropdown_items(self, graph_names):
        dd = getattr(self, "dropdown", None)
        if dd is None:
            return

        items = list(graph_names or [])
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

    def refresh_after_account_change(self):
        try:
            self.current_user = get_current_user()
        except Exception:
            self.current_user = None

        user_graphs = []
        try:
            user_graphs = get_user_graphs(self.current_user) if self.current_user else []
        except Exception:
            user_graphs = []

        graph_names = []
        for g in user_graphs:
            if isinstance(g, dict) and g.get("graph_id"):
                graph_names.append(g.get("graph_id"))

        self._rebuild_graph_dropdown_items(graph_names)

        self.current_graph = None
        self.current_graph_type = None
        self.dropdown.selected = None
        self.dropdown.label.setText("Choose graph name")
        self.dropdown.label.setStyleSheet("""
            QLabel {
                color: #808080;
                background: transparent;
                border: none;
            }
        """)

        self.qty_input.clear()
        self.qty_input.setReadOnly(True)
        self._set_qty_interaction_state(enabled=False)
        self._show_qty_error("Select graph before entering quantity")

    def update_accent_colors(self):
        for btn in self.accent_buttons:
            self._apply_accent_button_style(btn)
        for dd in (self.dropdown, self.date_dropdown):
            try:
                dd.update_accent_colors()
            except Exception:
                pass
        try:
            self.calendar_popup.month_dd.update_accent_colors()
            self.calendar_popup.year_dd.update_accent_colors()
        except Exception:
            pass

    def _toggle_calendar(self):
        if self.calendar_popup.isVisible():
            self.calendar_popup.hide()
            return
        self.calendar_popup.refresh()
        self.calendar_popup.raise_()
        self.calendar_popup.show()

    def _on_date_selected(self, d: date):
        self.selected_date = d
        self.date_dropdown.label.setText(d.strftime("%d %b %Y"))
        self.date_dropdown.label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                background: transparent;
                border: none;
            }
        """)
        self.calendar_popup.hide()

    def _on_qty_changed(self, text: str):
        if self.qty_input.isReadOnly():
            return
        if text == "":
            self._show_qty_error("")
            return
        if not re.fullmatch(r"[0-9.]+", text):
            self._show_qty_error("Only digits and '.' are allowed")
            return
        if text.startswith("."):
            self._show_qty_error("Number cannot start with '.'")
            return
        # Allow numbers like '9.' (no digits after decimal) as valid input.
        m = re.fullmatch(r"(\d+)(?:\.(\d*))?", text)
        if not m:
            self._show_qty_error("Only digits and '.' are allowed")
            return
        # If graph expects integer, reject if fractional part contains non-zero digits.
        frac = m.group(2)
        if self.current_graph_type == "int" and frac is not None and frac != "" and set(frac) != {"0"}:
            self._show_qty_error(f"{self.current_graph} only allows integers, not decimal numbers")
            return
        self._show_qty_error("")

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self.qty_input and event.type() == QEvent.MouseButtonPress:
            if self.qty_input.isReadOnly():
                self._show_qty_error("Select graph before entering quantity")
                return True
        if event.type() == QEvent.MouseButtonPress and self.calendar_popup.isVisible():
            try:
                gpos = event.globalPos()
                local_main = self.main_frame.mapFromGlobal(gpos)
                if not self.calendar_popup.geometry().contains(local_main):
                    self.date_dropdown.set_icon_compact(False)
                    self.calendar_popup.hide()
            except Exception:
                pass
        return super().eventFilter(obj, event)

    def _on_graph_selected(self, graph_name: str):
        self.current_graph = graph_name
        if self.current_user and graph_name:
            try:
                self.current_graph_type = get_graph_type(self.current_user, graph_name)
            except Exception:
                self.current_graph_type = None
        else:
            self.current_graph_type = None

        if graph_name:
            self.qty_input.setReadOnly(False)
            self._set_qty_interaction_state(enabled=True)
            self._on_qty_changed(self.qty_input.text())
        else:
            self.qty_input.setReadOnly(True)
            self._set_qty_interaction_state(enabled=False)
            self._show_qty_error("Select graph before entering quantity")

    def _set_qty_interaction_state(self, enabled: bool):
        if enabled:
            self.qty_box.set_bg_color("#3e3e3e")
            self.qty_box.setStyleSheet("""
                QFrame {
                    background-color: #3e3e3e;
                    border: 1px solid rgba(255,255,255,0.06);
                    border-radius: 20px;
                }
            """)
            self.qty_input.setStyleSheet("""
                QLineEdit {
                    color: #FFFFFF;
                    background: transparent;
                    border: none;
                }
                QLineEdit::placeholder {
                    color: #808080;
                }
            """)
            return

        self.qty_box.set_bg_color("#2f2f2f")
        self.qty_box.setStyleSheet("""
            QFrame {
                background-color: #2f2f2f;
                border: 1px solid rgba(255,255,255,0.03);
                border-radius: 20px;
            }
        """)
        self.qty_input.setStyleSheet("""
            QLineEdit {
                color: #7a7a7a;
                background: transparent;
                border: none;
            }
            QLineEdit::placeholder {
                color: #5f5f5f;
            }
            QLineEdit:read-only {
                color: #7a7a7a;
            }
        """)

    def _show_qty_error(self, message: str):
        if not message:
            self.qty_error.hide()
            return
        self.qty_error_label.setText(message)
        self.qty_error.show()
    
    def submit(self):
        self._hide_success_popup()
        self._hide_conflict_popup()
        if not self.current_user:
            self._show_qty_error("No current user found")
            return
        if not self.current_graph:
            self._show_qty_error("Select graph before submitting")
            return
        if not self.selected_date:
            self._show_qty_error("Select date before submitting")
            return
        qty_text = self.qty_input.text().strip()
        if not qty_text:
            self._show_qty_error("Enter quantity before submitting")
            return
        self._on_qty_changed(qty_text)
        if self.qty_error.isVisible():
            return

        # Parse quantity allowing inputs like '9.' and treating them as integer 9.
        quantity = qty_text
        m = re.fullmatch(r"(\d+)(?:\.(\d*))?", qty_text)
        if m:
            whole = m.group(1)
            frac = m.group(2)
            if frac is None or frac == "" or set(frac) == {"0"}:
                # no fractional digits or all-zero fractional part -> use int
                try:
                    quantity = int(whole)
                except Exception:
                    quantity = qty_text
            else:
                try:
                    quantity = float(qty_text)
                except Exception:
                    quantity = qty_text
        else:
            # fallback: try numeric casts
            try:
                quantity = int(qty_text)
            except Exception:
                try:
                    quantity = float(qty_text)
                except Exception:
                    quantity = qty_text

        date_str = self.selected_date.strftime("%d%m%Y")
        conflict = check_pixel_conflict(self.current_user, self.current_graph, date_str)
        if not conflict.get("ok", True):
            self._pending_conflict = {
                "username": self.current_user,
                "graph_id": self.current_graph,
                "date_str": date_str,
                "quantity": quantity,
                "quantity_text": qty_text,
                "existing_value": conflict.get("value"),
            }
            self._show_conflict_popup(date_str, conflict.get("value"))
            return

        ok = add_pixel_entry(self.current_user, self.current_graph, date_str, quantity)
        if not ok:
            self._show_qty_error("Invalid date")
            return

        self._show_success_popup(self.selected_date, qty_text)
        self._maybe_update_display_graph()

    def _show_conflict_popup(self, date_str: str, existing_value):
        try:
            d = datetime.strptime(date_str, "%d%m%Y").date()
            pretty_date = f"{d.day} {d.strftime('%B %Y')}"
        except Exception:
            pretty_date = date_str
        self.conflict_label.setText(
            f"A pixel has already been added on {pretty_date} with value {existing_value}."
        )
        self.conflict_popup.raise_()
        self._fade_in_popup(self.conflict_popup)

    def _hide_conflict_popup(self):
        try:
            self.conflict_popup.hide()
            self.conflict_popup.setWindowOpacity(1.0)
        except Exception:
            pass

    def _cancel_conflict_popup(self):
        self._pending_conflict = None
        self._hide_conflict_popup()

    def _resolve_conflict(self, action: str):
        pending = self._pending_conflict or {}
        if not pending:
            self._hide_conflict_popup()
            return

        ok = resolve_pixel_conflict(
            pending.get("username"),
            pending.get("graph_id"),
            pending.get("date_str"),
            pending.get("quantity"),
            action,
        )
        if not ok:
            self._show_qty_error("Could not update existing pixel for this date")
            return

        self._hide_conflict_popup()
        self._pending_conflict = None
        verb = "Combined" if action == "combine" else "Replaced"
        try:
            d = datetime.strptime(pending.get("date_str"), "%d%m%Y").date()
            pretty_date = f"{d.day} {d.strftime('%b %Y')}"
        except Exception:
            pretty_date = pending.get("date_str")
        self.success_label.setText(
            f"{verb} pixel entry on {pretty_date}."
        )
        self.success_popup.raise_()
        self._fade_in_popup(self.success_popup)
        self._maybe_update_display_graph()

    def _show_success_popup(self, d: date, quantity_text: str):
        pretty_date = d.strftime("%d %b %Y")
        self.success_label.setText(
            f"Successful! added entry on {pretty_date} with quantity {quantity_text}."
        )
        self.success_popup.raise_()
        self._fade_in_popup(self.success_popup)

    def _hide_success_popup(self):
        try:
            self.success_popup.hide()
            self.success_popup.setWindowOpacity(1.0)
        except Exception:
            pass

    def _fade_in_popup(self, popup):
        popup.setWindowOpacity(0.0)
        popup.show()
        anim = QPropertyAnimation(popup, b"windowOpacity", popup)
        anim.setDuration(180)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def _maybe_update_display_graph(self):
        try:
            current = get_current_graph()
        except Exception:
            return
        if not current or current.get("graph") != self.current_graph:
            return

        display_type = (current.get("type") or "").strip().lower()
        def _worker():
            try:
                # DEBUG: update worker starting for display_type=%s
                # Trigger regeneration of the display image after adding a pixel.
                if display_type == "histogram":
                    # DEBUG: creating histogram due to new pixel for user=%s graph=%s
                    create_histogram(self.current_user, self.current_graph)
                else:
                    # DEBUG: creating heatmap due to new pixel for user=%s graph=%s
                    create_heatmap(self.current_user, self.current_graph)
            finally:
                QTimer.singleShot(0, self, self._refresh_homepage_heatmap)

        threading.Thread(target=_worker, daemon=True).start()

    def _refresh_homepage_heatmap(self):
        self.homepage = self.ui.home_screen
        self.homepage.refresh_info()
