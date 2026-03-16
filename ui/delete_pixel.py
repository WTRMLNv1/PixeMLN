from PySide6.QtWidgets import QWidget, QFrame, QLabel, QPushButton
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, QTimer
import os
from helpers.CustomWidgets import (
    RoundedFrame, CalendarPopup, CustomDropdown,
    HoverScaleButton, apply_widget_shadow,
)
from helpers.json_manager import (
    get_current_user,
    get_user_graphs,
    get_theme,
    get_pixel_dict,
    check_pixel_conflict,
)
from datetime import date


class DeletePixel(QWidget):
    def __init__(self, ui):
        super().__init__()
        self._setup_done = False
        self.ui = ui
        self.accent_buttons = []
        self.selected_date = None
        self.current_user = None
        self.current_graph = None

    def run(self):
        if self._setup_done:
            return
        self._setup_done = True

        self.setFixedSize(640, 550)

        self.main_frame = QFrame(self)
        self.main_frame.setGeometry(0, 0, 640, 550)
        self.main_frame.setStyleSheet("background-color: #2b2b2b; border-radius: 20px;")
        apply_widget_shadow(self.main_frame, radius=20)

        # Title
        title = QLabel("Delete Pixel", self.main_frame)
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
        divider.move((640 - 300) // 2, 70)

        # Context hint
        ctx = QFrame(self.main_frame)
        ctx.setGeometry(220, 100, 200, 100)
        ctx.setAttribute(Qt.WA_StyledBackground, True)
        ctx.setStyleSheet("""
        QFrame {
            background-color: #3a2e2e;
            border-radius: 20px;
            border: 1px solid rgba(82,59,59,217);
        }
        """)
        ctx_text = QLabel(
            "Remove a pixel entry\nfor a specific date\nfrom your chosen graph.",
            ctx,
        )
        ctx_text.setFont(QFont("", 10))
        ctx_text.setAlignment(Qt.AlignCenter)
        ctx_text.setStyleSheet("color: #FFFFFF; background: transparent;")
        ctx_text.setGeometry(0, 0, 200, 100)

        # Form
        form = QFrame(self.main_frame)
        form.setGeometry(44, 230, 552, 220)
        form.setStyleSheet(
            "background-color: #353535; border-radius: 20px;"
            " border: 1px solid rgba(96,96,96,0.9);"
        )

        gf = QFont()
        gf.setPointSize(15)

        graph_label = QLabel("Choose graph:", form)
        graph_label.setGeometry(12, 10, 300, 23)
        graph_label.setFont(gf)
        graph_label.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")

        # Graph dropdown
        current_user = None
        user_graphs = []
        try:
            current_user = get_current_user()
            user_graphs = get_user_graphs(current_user)
        except Exception:
            pass

        graph_names = [
            g["graph_id"] for g in user_graphs
            if isinstance(g, dict) and g.get("graph_id")
        ]
        self.current_user = current_user

        self.dropdown = CustomDropdown(
            form,
            items=graph_names,
            x=12,
            y=39,
            on_select=self._on_graph_selected,
        )

        date_label = QLabel("Choose Date", form)
        date_label.setGeometry(12, 80, 300, 23)
        date_label.setFont(gf)
        date_label.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")

        calendar_icon = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "assets", "calender.png",
        )
        self.date_dropdown = CustomDropdown(
            form,
            items=[],
            x=12,
            y=110,
            placeholder="Choose Date",
            icon_path=calendar_icon,
            rotate_icon=False,
        )
        self.date_dropdown.toggle_dropdown = self._toggle_calendar

        # Submit button
        self.submit_btn = HoverScaleButton("Delete", form, border_radius=15)
        self.submit_btn.setGeometry(12, 160, 100, 30)
        self.submit_btn.setCursor(Qt.PointingHandCursor)
        self.submit_btn.setFont(gf)
        self.accent_buttons.append(self.submit_btn)
        self._apply_delete_button_style()
        self.submit_btn.clicked.connect(self.submit)

        # Error label
        self.error_frame = QFrame(form)
        self.error_frame.setGeometry(12, 145, 361, 20)
        self.error_frame.setAttribute(Qt.WA_StyledBackground, True)
        self.error_frame.setStyleSheet(
            "QFrame { background-color: #7a1e1e; border-radius: 8px; }"
        )
        self.error_label = QLabel("", self.error_frame)
        self.error_label.setGeometry(6, 0, 349, 20)
        self.error_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.error_label.setStyleSheet(
            "color: #FFFFFF; background: transparent; border: none;"
        )
        self.error_frame.hide()

        # Confirm popup
        self.confirm_popup = QFrame(self.main_frame)
        self.confirm_popup.setFixedSize(460, 160)
        self.confirm_popup.setAttribute(Qt.WA_StyledBackground, True)
        self.confirm_popup.setStyleSheet("""
            QFrame {
                background-color: #5a2f2f;
                border-radius: 16px;
                border: 1px solid rgba(0,0,0,0.30);
            }
        """)
        cp_x = (640 - self.confirm_popup.width()) // 2
        cp_y = (550 - self.confirm_popup.height()) // 2
        self.confirm_popup.move(cp_x, cp_y)

        self.confirm_label = QLabel("", self.confirm_popup)
        self.confirm_label.setGeometry(12, 14, 436, 72)
        self.confirm_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.confirm_label.setWordWrap(True)
        self.confirm_label.setStyleSheet(
            "color: #FFFFFF; background: transparent; border: none;"
        )

        cancel_btn = QPushButton("Cancel", self.confirm_popup)
        cancel_btn.setGeometry(58, 110, 100, 32)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #dcdcdc; color: #222222;
                border-radius: 14px; font-size: 13px;
            }
            QPushButton:hover { background-color: #c9c9c9; }
        """)
        cancel_btn.clicked.connect(self.confirm_popup.hide)

        self.confirm_delete_btn = QPushButton("Delete", self.confirm_popup)
        self.confirm_delete_btn.setGeometry(298, 110, 100, 32)
        self.confirm_delete_btn.setCursor(Qt.PointingHandCursor)
        self.confirm_delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #c0392b; color: #FFFFFF;
                border-radius: 14px; font-size: 13px;
            }
            QPushButton:hover { background-color: #e74c3c; }
        """)
        self.confirm_delete_btn.clicked.connect(self._do_delete)
        self.confirm_popup.hide()

        # Success popup
        self.success_popup = QFrame(self.main_frame)
        self.success_popup.setFixedSize(420, 120)
        self.success_popup.setAttribute(Qt.WA_StyledBackground, True)
        self.success_popup.setStyleSheet("""
            QFrame {
                background-color: #2f8f5b;
                border-radius: 16px;
                border: 1px solid rgba(0,0,0,0.25);
            }
        """)
        sp_x = (640 - self.success_popup.width()) // 2
        sp_y = (550 - self.success_popup.height()) // 2
        self.success_popup.move(sp_x, sp_y)
        self.success_label = QLabel("", self.success_popup)
        self.success_label.setGeometry(12, 12, 396, 60)
        self.success_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.success_label.setWordWrap(True)
        self.success_label.setStyleSheet(
            "color: #FFFFFF; background: transparent; border: none;"
        )
        ok_btn = QPushButton("OK", self.success_popup)
        ok_btn.setGeometry(160, 80, 100, 28)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #e8f9ef; color: #1a5f3a;
                border-radius: 12px; font-size: 13px;
            }
            QPushButton:hover { background-color: #cfeedd; }
        """)
        ok_btn.clicked.connect(self.success_popup.hide)
        self.success_popup.hide()

        # Calendar popup
        from PySide6.QtCore import QPoint
        dd_pos = self.date_dropdown.mapTo(self.main_frame, QPoint(0, 0))
        cal_w = self.date_dropdown.width()
        cal_h = 200
        above_y = dd_pos.y() - cal_h - 6
        cal_y = above_y if above_y >= 0 else dd_pos.y() + 26
        self.calendar_popup = CalendarPopup(
            self.main_frame,
            x=dd_pos.x(),
            y=cal_y,
            width=cal_w,
            height=cal_h,
            on_date_selected=self._on_date_selected,
        )
        self.calendar_popup.hide()

        for w in (form, self.main_frame, self):
            try:
                w.installEventFilter(self)
            except Exception:
                pass

    # ── helpers ──────────────────────────────────────────

    def _apply_delete_button_style(self):
        self.submit_btn.setStyleSheet("""
            QPushButton {
                background-color: #c0392b;
                color: #FFFFFF;
                font-size: 15px;
                border-radius: 15px;
            }
            QPushButton:hover { background-color: #e74c3c; }
            QPushButton:pressed { background-color: #e74c3c; border-radius: 15px; }
        """)

    def _show_error(self, message):
        if not message:
            self.error_frame.hide()
            return
        self.error_label.setText(message)
        self.error_frame.show()

    def _on_graph_selected(self, graph_name):
        self.current_graph = graph_name
        self._show_error("")

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
        self.date_dropdown.label.setStyleSheet(
            "QLabel { color: #FFFFFF; background: transparent; border: none; }"
        )
        self.calendar_popup.hide()

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.MouseButtonPress and self.calendar_popup.isVisible():
            try:
                gpos = event.globalPos()
                local_main = self.main_frame.mapFromGlobal(gpos)
                if not self.calendar_popup.geometry().contains(local_main):
                    self.calendar_popup.hide()
            except Exception:
                pass
        return super().eventFilter(obj, event)

    # ── submit / delete logic ─────────────────────────────

    def submit(self):
        self.confirm_popup.hide()
        self.success_popup.hide()

        if not self.current_user:
            self._show_error("No current user found")
            return
        if not self.current_graph:
            self._show_error("Select a graph before deleting")
            return
        if not self.selected_date:
            self._show_error("Select a date before deleting")
            return

        date_str = self.selected_date.strftime("%d%m%Y")
        conflict = check_pixel_conflict(self.current_user, self.current_graph, date_str)
        if conflict.get("ok", True):
            # no entry exists for that date
            pretty = self.selected_date.strftime("%d %b %Y")
            self._show_error(f"No pixel found on {pretty} for '{self.current_graph}'")
            return

        self._show_error("")
        pretty = self.selected_date.strftime("%d %b %Y")
        existing = conflict.get("value", "?")
        self.confirm_label.setText(
            f"Delete the pixel on {pretty} for '{self.current_graph}'?\n"
            f"(value: {existing})"
        )
        self._pending_date_str = date_str
        self.confirm_popup.raise_()
        self.confirm_popup.show()

    def _do_delete(self):
        self.confirm_popup.hide()
        date_str = getattr(self, "_pending_date_str", None)
        if not date_str:
            return

        import json, os
        from helpers.json_manager import BASE_DIR
        file_path = os.path.join(BASE_DIR, "Data", "pixels.json")
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
        except Exception as e:
            self._show_error(f"Could not read data: {e}")
            return

        deleted = False
        for user_entry in data:
            if not (isinstance(user_entry, dict) and self.current_user in user_entry):
                continue
            for graph in user_entry[self.current_user]:
                if not (isinstance(graph, dict) and graph.get("graph_id") == self.current_graph):
                    continue
                pixels = graph.get("pixels", [])
                new_pixels = []
                for p in pixels:
                    if isinstance(p, dict) and date_str in p:
                        deleted = True
                        continue
                    if isinstance(p, str):
                        try:
                            d, _ = p.split("_", 1)
                            if d == date_str:
                                deleted = True
                                continue
                        except Exception:
                            pass
                    new_pixels.append(p)
                graph["pixels"] = new_pixels
                break
            break

        if not deleted:
            self._show_error("Pixel not found — it may have already been deleted.")
            return

        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            self._show_error(f"Could not save data: {e}")
            return

        pretty = self.selected_date.strftime("%d %b %Y")
        self.success_label.setText(
            f"Deleted pixel on {pretty} from '{self.current_graph}'."
        )
        self.success_popup.raise_()
        self.success_popup.show()

        # Reset date selection
        self.selected_date = None
        self.date_dropdown.label.setText("Choose Date")
        self.date_dropdown.label.setStyleSheet(
            "QLabel { color: #808080; background: transparent; border: none; }"
        )

        # Refresh homepage heatmap
        try:
            self.ui.home_screen.refresh_info()
        except Exception:
            pass

    # ── theme ──────────────────────────────────────────

    def update_accent_colors(self):
        try:
            self.calendar_popup.month_dd.update_accent_colors()
            self.calendar_popup.year_dd.update_accent_colors()
        except Exception:
            pass
        for dd in (self.dropdown, self.date_dropdown):
            try:
                dd.update_accent_colors()
            except Exception:
                pass

    def refresh_after_account_change(self):
        try:
            self.current_user = get_current_user()
        except Exception:
            self.current_user = None

        user_graphs = []
        try:
            from helpers.json_manager import get_user_graphs
            user_graphs = get_user_graphs(self.current_user) if self.current_user else []
        except Exception:
            pass

        graph_names = [
            g["graph_id"] for g in user_graphs
            if isinstance(g, dict) and g.get("graph_id")
        ]

        dd = getattr(self, "dropdown", None)
        if dd is not None:
            try:
                dd.items = graph_names
                dd.selected = None
                dd.label.setText("Choose graph name")
                dd.label.setStyleSheet(
                    "QLabel { color: #808080; background: transparent; border: none; }"
                )
            except Exception:
                pass

        self.current_graph = None
        self.selected_date = None
