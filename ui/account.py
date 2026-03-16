from PySide6.QtWidgets import QWidget, QFrame, QLabel, QPushButton, QLineEdit
from PySide6.QtGui import QFont, QPixmap, QColor, QPainter, QTransform
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QPoint, QRect, QSequentialAnimationGroup, QParallelAnimationGroup, QAbstractAnimation, QTimer, QVariantAnimation, Property
from helpers.CustomWidgets import HoverScaleButton, HorizontalButtonStrip, SpinnerWidget, TickWidget, CustomDropdown, apply_widget_shadow
import os
import re
from helpers.json_manager import (
    get_current_user,
    get_all_users,
    change_current_user,
    create_account,
    rename_account,
    delete_account,
    get_theme,
)


class MorphWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._radius = 14.0
        self._color = QColor("#5BF69F")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_StyledBackground, True)

    def _set_radius(self, value):
        try:
            self._radius = float(value)
        except Exception:
            return
        self.update()

    def _get_radius(self):
        return float(self._radius)

    def _set_color(self, value):
        c = value if isinstance(value, QColor) else QColor(value)
        if not c.isValid():
            return
        self._color = c
        self.update()

    def _get_color(self):
        return QColor(self._color)

    radius = Property(float, _get_radius, _set_radius)
    color = Property(QColor, _get_color, _set_color)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._color)
        painter.drawRoundedRect(self.rect(), self._radius, self._radius)
        painter.end()


class Account(QWidget):
    def __init__(self, ui):
        super().__init__()
        self.ui = ui
        self._setup_done = False
        self.accent_buttons = []
        self.current_user = None
        self.users = []
        self._arrow_source_pix = None
        self._action_button_content = {}
        self._arrow_hover_shift_px = 4
        self.change_user_spinner = None
        self.change_user_tick = None
        self._change_user_spinner_anim = None
        self._change_user_tick_anim = None
        self._change_user_load_seq = 0
        self.create_user_modal = None
        self.create_user_overlay = None
        self.create_user_input = None
        self.create_user_error = None
        self.create_user_confirm_btn = None
        self._create_user_submit_enabled = False
        self._create_user_morph = None
        self._create_user_morph_group = None
        self.edit_user_modal = None
        self.edit_user_overlay = None
        self.edit_user_select = None
        self.edit_user_name_input = None
        self.edit_user_error = None
        self.edit_user_warning = None
        self.edit_user_ok_btn = None
        self.edit_user_delete_btn = None
        self._edit_user_delete_armed = False
        self._edit_user_delete_arm_seq = 0
        self._edit_user_morph = None
        self._edit_user_morph_group = None

    def run(self):
        if self._setup_done:
            return
        self._setup_done = True

        self.setFixedSize(640, 550)

        self.main_frame = QFrame(self)
        self.main_frame.setGeometry(0, 0, 640, 550)
        self.main_frame.setStyleSheet("background-color: #2b2b2b; border-radius: 20px;")
        apply_widget_shadow(self.main_frame, radius=20)

        title = QLabel("Accounts", self.main_frame)
        tf = QFont()
        tf.setPointSize(35)
        tf.setBold(True)
        title.setFont(tf)
        title.setStyleSheet("color: #FFFFFF; border: none;")
        title.setGeometry(0, 16, 640, 55)
        title.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)

        divider = QFrame(self.main_frame)
        divider.setStyleSheet("background-color: #5a5a5a;")
        divider.setFixedSize(300, 1)
        divider.move((self.main_frame.width() - divider.width()) // 2, 70)

        self.current_user_box = QFrame(self.main_frame)
        self.current_user_box.setGeometry(191, 98, 260, 86)
        self.current_user_box.setStyleSheet("""
            QFrame {
                background-color: #2e3a34;
                border: 1px solid #3b5247;
                border-radius: 20px;
            }
        """)

        current_user_title = QLabel("current user", self.current_user_box)
        ctf = QFont()
        ctf.setPointSize(15)
        current_user_title.setFont(ctf)
        current_user_title.setGeometry(0, 8, 260, 26)
        current_user_title.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        current_user_title.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")

        self.current_user_value = QLabel("", self.current_user_box)
        cvf = QFont()
        cvf.setPointSize(15)
        cvf.setBold(True)
        self.current_user_value.setFont(cvf)
        self.current_user_value.setGeometry(0, 33, 260, 44)
        self.current_user_value.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.current_user_value.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")

        self.form_frame = QFrame(self.main_frame)
        self.form_frame.setGeometry(45, 220, 551, 286)
        self.form_frame.setStyleSheet(
            "background-color: #353535; border-radius: 20px; border: 1px solid rgba(96,96,96,0.9);"
        )

        label_font = QFont()
        label_font.setPointSize(15)
        label_font.setBold(True)

        change_label = QLabel("Change user:", self.form_frame)
        change_label.setGeometry(16, 10, 250, 30)
        change_label.setFont(label_font)
        change_label.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")

        self._load_data()

        self.change_user_strip = HorizontalButtonStrip(
            parent=self.form_frame,
            border_radius=8,
            button_height=30,
            button_radius=14,
            button_font_size=14,
            button_min_width=80,
            button_padding=28,
            spacing=8,
            bar_height=8,
            bar_arrow_area=12,
            bar_min_handle=22,
        )
        self.change_user_strip.setGeometry(12, 40, 383, 52)
        self._build_user_buttons()

        accent = get_theme().get("accent_color", "#5BF69F")
        self.change_user_spinner = SpinnerWidget(size=14, thickness=2, color=accent, parent=self.form_frame)
        self.change_user_tick = TickWidget(size=14, thickness=2, color=accent, parent=self.form_frame)
        self._position_change_user_status()
        self._set_change_user_status("idle")

        create_label = QLabel("Create user:", self.form_frame)
        create_label.setGeometry(16, 86, 250, 30)
        create_label.setFont(label_font)
        create_label.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")

        self.create_user_btn = QPushButton("Create user", self.form_frame)
        self.create_user_btn.setGeometry(12, 121, 140, 28)
        self.create_user_btn.setCursor(Qt.PointingHandCursor)
        self.accent_buttons.append(self.create_user_btn)

        edit_label = QLabel("Edit users:", self.form_frame)
        edit_label.setGeometry(16, 154, 250, 30)
        edit_label.setFont(label_font)
        edit_label.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")

        self.edit_user_btn = QPushButton("Edit users", self.form_frame)
        self.edit_user_btn.setGeometry(12, 189, 140, 28)
        self.edit_user_btn.setCursor(Qt.PointingHandCursor)
        self.edit_users_btn = self.edit_user_btn
        self.accent_buttons.append(self.edit_user_btn)

        self._prepare_arrow_source()
        self._setup_action_button_arrow(self.create_user_btn)
        self._setup_action_button_arrow(self.edit_user_btn)

        self.update_accent_colors()
        self._refresh_current_user_label()
        self.create_user_btn.clicked.connect(self._open_create_user_modal)
        self.edit_user_btn.clicked.connect(self._open_edit_user_modal)
        self._build_create_user_modal()
        self._build_edit_user_modal()
    
    def _pop_label_text(self, label, new_text):
        if label.text() == new_text:
            return

        base = QRect(label.geometry())

        def scaled_rect(scale):
            w = int(base.width() * scale)
            h = int(base.height() * scale)
            x = base.x() - (w - base.width()) // 2
            y = base.y() - (h - base.height()) // 2
            return QRect(x, y, w, h)

        shrink = scaled_rect(0.95)
        overshoot = scaled_rect(1.03)

        # Change text before animation to avoid mid-animation twitch.
        label.setText(new_text)

        # Stop any previous pop animation to avoid stacking artifacts.
        if hasattr(label, "_pop_anim"):
            label._pop_anim.stop()

        group = QSequentialAnimationGroup()
        label._pop_anim = group

        a1 = QPropertyAnimation(label, b"geometry")
        a1.setDuration(140)
        a1.setStartValue(base)
        a1.setEndValue(shrink)
        a1.setEasingCurve(QEasingCurve.InOutCubic)

        a2 = QPropertyAnimation(label, b"geometry")
        a2.setDuration(170)
        a2.setStartValue(shrink)
        a2.setEndValue(overshoot)
        a2.setEasingCurve(QEasingCurve.OutBack)

        a3 = QPropertyAnimation(label, b"geometry")
        a3.setDuration(140)
        a3.setStartValue(overshoot)
        a3.setEndValue(base)
        a3.setEasingCurve(QEasingCurve.OutCubic)

        group.addAnimation(a1)
        group.addAnimation(a2)
        group.addAnimation(a3)

        group.start()

    def _load_data(self):
        try:
            self.current_user = get_current_user()
        except Exception:
            self.current_user = None
        try:
            self.users = get_all_users()
        except Exception:
            self.users = []

    def _refresh_current_user_label(self):
        self._pop_label_text(
            self.current_user_value,
            self.current_user or "unknown"
        )
    def _on_change_user_selected(self, username):
        if not username:
            return
        if username == self.current_user:
            return
        self._change_user_load_seq += 1
        seq_id = self._change_user_load_seq
        self._set_change_user_status("loading")
        self.current_user = username
        self._refresh_current_user_label()
        try:
            change_current_user(username)
        except Exception:
            pass
        self._refresh_user_button_styles()
        try:
            add_pixels = getattr(self.ui, "add_pixel_screen", None)
            if add_pixels is not None and hasattr(add_pixels, "refresh_after_account_change"):
                add_pixels.refresh_after_account_change()
        except Exception:
            pass
        try:
            graphs = getattr(self.ui, "graphs_screen", None)
            if graphs is not None and hasattr(graphs, "refresh_after_account_change"):
                graphs.refresh_after_account_change()
        except Exception:
            pass
        handled = False
        try:
            settings = getattr(self.ui, "settings_screen", None)
            if settings is not None and hasattr(settings, "refresh_after_account_change"):
                settings.refresh_after_account_change(min_loading_ms=2000)
                handled = True
        except Exception:
            handled = False
        if not handled:
            try:
                self.ui.home_screen.refresh_info()
            except Exception:
                pass
        QTimer.singleShot(2000, self, lambda: self._finish_change_user_load(seq_id))

    def _build_user_buttons(self):
        strip = getattr(self, "change_user_strip", None)
        if strip is None:
            return
        safe_users = [str(u).strip() for u in (self.users or []) if str(u).strip()]
        theme = get_theme()
        strip.set_items(
            items=safe_users,
            on_click=self._on_change_user_selected,
            selected=self.current_user,
            accent_color=theme.get("accent_color", "#5BF69F"),
            hover_color=theme.get("hover_color", "#48C47F"),
            text_color=theme.get("text_color", "#FFFFFF"),
        )
        self._refresh_user_button_styles()

    def _build_create_user_modal(self):
        self.create_user_overlay = QFrame(self.main_frame)
        self.create_user_overlay.setGeometry(0, 0, 640, 550)
        self.create_user_overlay.setAttribute(Qt.WA_StyledBackground, True)
        self.create_user_overlay.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 165);
            }
        """)
        self.create_user_overlay.hide()

        self.create_user_modal = QFrame(self.create_user_overlay)
        self.create_user_modal.setGeometry(145, 170, 350, 210)
        self.create_user_modal.setAttribute(Qt.WA_StyledBackground, True)
        self.create_user_modal.setStyleSheet("""
            QFrame {
                background-color: #2f2f2f;
                border: 1px solid #555555;
                border-radius: 16px;
            }
        """)

        title = QLabel("Create account", self.create_user_modal)
        tf = QFont()
        tf.setPointSize(18)
        tf.setBold(True)
        title.setFont(tf)
        title.setGeometry(0, 16, 350, 28)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")

        input_label = QLabel("Username", self.create_user_modal)
        lf = QFont()
        lf.setPointSize(11)
        input_label.setFont(lf)
        input_label.setGeometry(24, 58, 100, 18)
        input_label.setStyleSheet("color: #cfcfcf; background: transparent; border: none;")

        self.create_user_input = QLineEdit(self.create_user_modal)
        self.create_user_input.setGeometry(24, 82, 302, 30)
        self.create_user_input.setPlaceholderText("Enter new username")
        mono_family = self.ui.fonts.get("mono") or "Roboto Mono"
        self.create_user_input.setFont(QFont(mono_family, 11))
        self.create_user_input.setStyleSheet("""
            QLineEdit {
                color: #FFFFFF;
                background-color: #3c3c3c;
                border: 1px solid #5b5b5b;
                border-radius: 10px;
                padding-left: 10px;
            }
            QLineEdit:focus {
                border: 1px solid #7a7a7a;
            }
            QLineEdit::placeholder {
                color: #8b8b8b;
            }
        """)
        self.create_user_input.returnPressed.connect(self._submit_create_user)
        self.create_user_input.textChanged.connect(self._on_create_user_text_changed)

        self.create_user_error = QLabel("", self.create_user_modal)
        ef = QFont()
        ef.setPointSize(10)
        self.create_user_error.setFont(ef)
        self.create_user_error.setGeometry(24, 116, 302, 20)
        self.create_user_error.setStyleSheet("color: #ff7e7e; background: transparent; border: none;")
        self.create_user_error.hide()

        cancel_btn = QPushButton("Cancel", self.create_user_modal)
        cancel_btn.setGeometry(24, 155, 145, 34)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #4b4b4b;
                color: #FFFFFF;
                border: 1px solid #616161;
                border-radius: 10px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #595959;
            }
            QPushButton:pressed {
                background-color: #666666;
            }
        """)
        cancel_btn.clicked.connect(self._close_create_user_modal)

        self.create_user_confirm_btn = QPushButton("Create", self.create_user_modal)
        self.create_user_confirm_btn.setGeometry(181, 155, 145, 34)
        self._set_create_user_submit_enabled(False)
        self.create_user_confirm_btn.clicked.connect(self._submit_create_user)

    def _open_create_user_modal(self):
        if self.create_user_overlay is None:
            return
        if self._create_user_morph_group is not None and self._create_user_morph_group.state() == QAbstractAnimation.Running:
            return
        self.create_user_error.hide()
        self.create_user_error.setText("")
        self.create_user_input.setText("")
        self._set_create_user_submit_enabled(False)

        start_top_left = self.create_user_btn.mapTo(self.main_frame, QPoint(0, 0))
        start_rect = QRect(start_top_left, self.create_user_btn.size())
        end_rect = QRect(self.create_user_modal.geometry())

        if self._create_user_morph is not None:
            self._create_user_morph.deleteLater()
            self._create_user_morph = None

        theme = get_theme()
        start_color = QColor(theme.get("accent_color", "#5BF69F"))
        if not start_color.isValid():
            start_color = QColor("#5BF69F")
        end_color = QColor("#2f2f2f")

        morph = MorphWidget(self.main_frame)
        morph.setGeometry(start_rect)
        morph.radius = 14.0
        morph.color = start_color
        morph.show()
        morph.raise_()
        self._create_user_morph = morph

        self.create_user_overlay.hide()

        group = QParallelAnimationGroup(self)

        geo_anim = QPropertyAnimation(morph, b"geometry", self)
        geo_anim.setDuration(280)
        geo_anim.setStartValue(start_rect)
        geo_anim.setEndValue(end_rect)
        geo_anim.setEasingCurve(QEasingCurve.InOutCubic)

        radius_anim = QPropertyAnimation(morph, b"radius", self)
        radius_anim.setDuration(280)
        radius_anim.setStartValue(14.0)
        radius_anim.setEndValue(16.0)
        radius_anim.setEasingCurve(QEasingCurve.InOutCubic)

        color_anim = QPropertyAnimation(morph, b"color", self)
        color_anim.setDuration(280)
        color_anim.setStartValue(start_color)
        color_anim.setEndValue(end_color)
        color_anim.setEasingCurve(QEasingCurve.InOutCubic)

        group.addAnimation(geo_anim)
        group.addAnimation(radius_anim)
        group.addAnimation(color_anim)
        group.finished.connect(self._finish_open_create_user_modal)
        self._create_user_morph_group = group
        group.start()

    def _finish_open_create_user_modal(self):
        if self._create_user_morph is not None:
            self._create_user_morph.deleteLater()
            self._create_user_morph = None
        self._create_user_morph_group = None
        self.create_user_overlay.raise_()
        self.create_user_overlay.show()
        self.create_user_modal.raise_()
        self.create_user_input.setFocus()

    def _close_create_user_modal(self):
        if self._create_user_morph_group is not None:
            self._create_user_morph_group.stop()
            self._create_user_morph_group = None
        if self._create_user_morph is not None:
            self._create_user_morph.deleteLater()
            self._create_user_morph = None
        if self.create_user_overlay is None:
            return
        self.create_user_overlay.hide()

    def _submit_create_user(self):
        username = self.create_user_input.text().strip() if self.create_user_input is not None else ""
        if not self._create_user_submit_enabled:
            ok, msg = self._validate_new_username(username)
            self.create_user_error.setText(msg)
            self.create_user_error.show()
            return
        ok, message = create_account(username)
        if not ok:
            self.create_user_error.setText(message)
            self.create_user_error.show()
            self._set_create_user_submit_enabled(False)
            return

        self._load_data()
        self._build_user_buttons()
        self._close_create_user_modal()
        self._on_change_user_selected(username)

    def _validate_new_username(self, username):
        name = str(username or "").strip()
        if not name:
            return False, "Username cannot be empty"
        if not re.fullmatch(r"[A-Za-z.0-9_-]+", name):
            return False, "Only letters, numbers, '-', '_', '.'"
        if name in (self.users or []):
            return False, "Username already exists"
        return True, ""

    def _on_create_user_text_changed(self, text):
        ok, msg = self._validate_new_username(text)
        name = str(text or "").strip()
        if not name:
            self.create_user_error.hide()
            self._set_create_user_submit_enabled(False)
            return
        if ok:
            self.create_user_error.hide()
            self._set_create_user_submit_enabled(True)
            return
        self.create_user_error.setText(msg)
        self.create_user_error.show()
        self._set_create_user_submit_enabled(False)

    def _set_create_user_submit_enabled(self, enabled):
        self._create_user_submit_enabled = bool(enabled)
        btn = self.create_user_confirm_btn
        if btn is None:
            return
        if self._create_user_submit_enabled:
            self._apply_accent_button_style(btn)
            btn.setCursor(Qt.PointingHandCursor)
            return
        btn.setStyleSheet("""
            QPushButton {
                background-color: #5b5b5b;
                color: #989898;
                border-radius: 10px;
                border: 1px solid #6a6a6a;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #5b5b5b;
            }
            QPushButton:pressed {
                background-color: #5b5b5b;
            }
        """)
        btn.setCursor(Qt.ForbiddenCursor)

    def _build_edit_user_modal(self):
        self.edit_user_overlay = QFrame(self.main_frame)
        self.edit_user_overlay.setGeometry(0, 0, 640, 550)
        self.edit_user_overlay.setAttribute(Qt.WA_StyledBackground, True)
        self.edit_user_overlay.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 165);
            }
        """)
        self.edit_user_overlay.hide()

        self.edit_user_modal = QFrame(self.edit_user_overlay)
        self.edit_user_modal.setGeometry(130, 120, 380, 310)
        self.edit_user_modal.setAttribute(Qt.WA_StyledBackground, True)
        self.edit_user_modal.setStyleSheet("""
            QFrame {
                background-color: #2f2f2f;
                border: 1px solid #555555;
                border-radius: 16px;
            }
        """)

        title = QLabel("Edit account", self.edit_user_modal)
        tf = QFont()
        tf.setPointSize(18)
        tf.setBold(True)
        title.setFont(tf)
        title.setGeometry(0, 16, 380, 28)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")

        select_label = QLabel("Select account", self.edit_user_modal)
        lf = QFont()
        lf.setPointSize(11)
        select_label.setFont(lf)
        select_label.setGeometry(24, 58, 130, 18)
        select_label.setStyleSheet("color: #cfcfcf; background: transparent; border: none;")
        self._rebuild_edit_user_dropdown([])

        rename_label = QLabel("Change name", self.edit_user_modal)
        rename_label.setFont(lf)
        rename_label.setGeometry(24, 120, 130, 18)
        rename_label.setStyleSheet("color: #cfcfcf; background: transparent; border: none;")

        self.edit_user_name_input = QLineEdit(self.edit_user_modal)
        self.edit_user_name_input.setGeometry(24, 144, 332, 30)
        self.edit_user_name_input.setPlaceholderText("Enter new username")
        mono_family = self.ui.fonts.get("mono") or "Roboto Mono"
        self.edit_user_name_input.setFont(QFont(mono_family, 11))
        self.edit_user_name_input.setStyleSheet("""
            QLineEdit {
                color: #FFFFFF;
                background-color: #3c3c3c;
                border: 1px solid #5b5b5b;
                border-radius: 10px;
                padding-left: 10px;
            }
            QLineEdit:focus {
                border: 1px solid #7a7a7a;
            }
            QLineEdit::placeholder {
                color: #8b8b8b;
            }
        """)
        self.edit_user_name_input.returnPressed.connect(self._submit_edit_user)
        self.edit_user_name_input.textChanged.connect(self._on_edit_user_name_changed)

        self.edit_user_error = QLabel("", self.edit_user_modal)
        ef = QFont()
        ef.setPointSize(10)
        self.edit_user_error.setFont(ef)
        self.edit_user_error.setGeometry(24, 178, 332, 20)
        self.edit_user_error.setStyleSheet("color: #ff7e7e; background: transparent; border: none;")
        self.edit_user_error.hide()

        self.edit_user_warning = QLabel("", self.edit_user_modal)
        self.edit_user_warning.setFont(ef)
        self.edit_user_warning.setGeometry(24, 200, 332, 26)
        self.edit_user_warning.setWordWrap(True)
        self.edit_user_warning.setStyleSheet("color: #ff9d66; background: transparent; border: none;")
        self.edit_user_warning.hide()

        self.edit_user_delete_btn = QPushButton("Delete", self.edit_user_modal)
        self.edit_user_delete_btn.setGeometry(24, 232, 332, 30)
        self.edit_user_delete_btn.setCursor(Qt.PointingHandCursor)
        self.edit_user_delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #b63d3d;
                color: #ffffff;
                border-radius: 10px;
                border: 1px solid #c85656;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #c44a4a;
            }
            QPushButton:pressed {
                background-color: #a93434;
            }
        """)
        self.edit_user_delete_btn.clicked.connect(self._on_edit_user_delete_clicked)

        cancel_btn = QPushButton("Cancel", self.edit_user_modal)
        cancel_btn.setGeometry(24, 270, 160, 30)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #4b4b4b;
                color: #FFFFFF;
                border: 1px solid #616161;
                border-radius: 10px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #595959;
            }
            QPushButton:pressed {
                background-color: #666666;
            }
        """)
        cancel_btn.clicked.connect(self._close_edit_user_modal)

        self.edit_user_ok_btn = QPushButton("Ok", self.edit_user_modal)
        self.edit_user_ok_btn.setGeometry(196, 270, 160, 30)
        self.edit_user_ok_btn.setCursor(Qt.PointingHandCursor)
        self.accent_buttons.append(self.edit_user_ok_btn)
        self._apply_accent_button_style(self.edit_user_ok_btn)
        self.edit_user_ok_btn.clicked.connect(self._submit_edit_user)

    def _open_edit_user_modal(self):
        if self.edit_user_overlay is None:
            return
        if self._edit_user_morph_group is not None and self._edit_user_morph_group.state() == QAbstractAnimation.Running:
            return
        self._load_data()
        self._populate_edit_user_select()
        self._reset_edit_user_delete_arm()
        self.edit_user_error.hide()
        self.edit_user_error.setText("")

        start_top_left = self.edit_user_btn.mapTo(self.main_frame, QPoint(0, 0))
        start_rect = QRect(start_top_left, self.edit_user_btn.size())
        end_rect = QRect(self.edit_user_modal.geometry())

        if self._edit_user_morph is not None:
            self._edit_user_morph.deleteLater()
            self._edit_user_morph = None

        theme = get_theme()
        start_color = QColor(theme.get("accent_color", "#5BF69F"))
        if not start_color.isValid():
            start_color = QColor("#5BF69F")
        end_color = QColor("#2f2f2f")

        morph = MorphWidget(self.main_frame)
        morph.setGeometry(start_rect)
        morph.radius = 14.0
        morph.color = start_color
        morph.show()
        morph.raise_()
        self._edit_user_morph = morph

        self.edit_user_overlay.hide()

        group = QParallelAnimationGroup(self)

        geo_anim = QPropertyAnimation(morph, b"geometry", self)
        geo_anim.setDuration(360)
        geo_anim.setStartValue(start_rect)
        geo_anim.setEndValue(end_rect)
        geo_anim.setEasingCurve(QEasingCurve.InOutCubic)

        radius_anim = QPropertyAnimation(morph, b"radius", self)
        radius_anim.setDuration(360)
        radius_anim.setStartValue(14.0)
        radius_anim.setEndValue(16.0)
        radius_anim.setEasingCurve(QEasingCurve.InOutCubic)

        color_anim = QPropertyAnimation(morph, b"color", self)
        color_anim.setDuration(360)
        color_anim.setStartValue(start_color)
        color_anim.setEndValue(end_color)
        color_anim.setEasingCurve(QEasingCurve.InOutCubic)

        group.addAnimation(geo_anim)
        group.addAnimation(radius_anim)
        group.addAnimation(color_anim)
        group.finished.connect(self._finish_open_edit_user_modal)
        self._edit_user_morph_group = group
        group.start()

    def _finish_open_edit_user_modal(self):
        if self._edit_user_morph is not None:
            self._edit_user_morph.deleteLater()
            self._edit_user_morph = None
        self._edit_user_morph_group = None
        self.edit_user_overlay.raise_()
        self.edit_user_overlay.show()
        self.edit_user_modal.raise_()
        if self.edit_user_name_input is not None:
            self.edit_user_name_input.setFocus()

    def _close_edit_user_modal(self):
        if self.edit_user_overlay is None:
            return
        if self._edit_user_morph_group is not None:
            self._edit_user_morph_group.stop()
            self._edit_user_morph_group = None
        if self._edit_user_morph is not None:
            self._edit_user_morph.deleteLater()
            self._edit_user_morph = None
        self._reset_edit_user_delete_arm()
        try:
            if self.edit_user_select is not None and hasattr(self.edit_user_select, "dropdown"):
                self.edit_user_select.dropdown.hide()
        except Exception:
            pass
        self.edit_user_overlay.hide()

    def _populate_edit_user_select(self):
        selected = self.current_user if self.current_user in (self.users or []) else ""
        if not selected and self.users:
            selected = self.users[0]
        self._rebuild_edit_user_dropdown(self.users)
        if self.edit_user_select is None:
            return
        if selected:
            self.edit_user_select.set_value(selected)
        else:
            self._on_edit_user_selected("")
        selected = self._get_selected_edit_user()
        if self.edit_user_name_input is not None:
            self.edit_user_name_input.setText(selected)
        enabled = bool(selected)
        if self.edit_user_name_input is not None:
            self.edit_user_name_input.setEnabled(enabled)
        if self.edit_user_ok_btn is not None:
            self.edit_user_ok_btn.setEnabled(enabled)
        if self.edit_user_delete_btn is not None:
            self.edit_user_delete_btn.setEnabled(enabled)

    def _rebuild_edit_user_dropdown(self, items):
        old = self.edit_user_select
        if old is not None:
            try:
                if hasattr(old, "dropdown") and old.dropdown is not None:
                    old.dropdown.deleteLater()
            except Exception:
                pass
            old.deleteLater()

        safe_items = [str(x).strip() for x in (items or []) if str(x).strip()]
        placeholder = "Select account" if safe_items else "No accounts"
        self.edit_user_select = CustomDropdown(
            self.edit_user_modal,
            items=safe_items,
            x=24,
            y=82,
            width=332,
            placeholder=placeholder,
            rotate_icon=False,
            on_select=self._on_edit_user_selected,
            dropdown_color="#3c3c3c",
            arrow_button_color="#3c3c3c",
            arrow_color="#d0d0d0",
            box_color="#3c3c3c",
            arrow_type="small",
        )

    def _get_selected_edit_user(self):
        if self.edit_user_select is None:
            return ""
        try:
            return str(self.edit_user_select.value() or "").strip()
        except Exception:
            return ""

    def _on_edit_user_selected(self, username):
        self._reset_edit_user_delete_arm()
        if self.edit_user_error is not None:
            self.edit_user_error.hide()
            self.edit_user_error.setText("")
        if self.edit_user_name_input is None:
            return
        self.edit_user_name_input.setText(str(username or "").strip())

    def _on_edit_user_name_changed(self, _text):
        self._reset_edit_user_delete_arm()
        if self.edit_user_error is not None:
            self.edit_user_error.hide()

    def _validate_edited_username(self, selected_username, new_username):
        selected = str(selected_username or "").strip()
        name = str(new_username or "").strip()
        if not selected:
            return False, "Select an account first"
        if not name:
            return False, "Username cannot be empty"
        if not re.fullmatch(r"[A-Za-z.0-9_-]+", name):
            return False, "Only letters, numbers, '-', '_', '.'"
        if name != selected and name in (self.users or []):
            return False, "Username already exists"
        return True, ""

    def _submit_edit_user(self):
        selected = self._get_selected_edit_user()
        new_name = self.edit_user_name_input.text().strip() if self.edit_user_name_input is not None else ""
        ok, msg = self._validate_edited_username(selected, new_name)
        if not ok:
            if self.edit_user_error is not None:
                self.edit_user_error.setText(msg)
                self.edit_user_error.show()
            return
        success, message = rename_account(selected, new_name)
        if not success:
            if self.edit_user_error is not None:
                self.edit_user_error.setText(message)
                self.edit_user_error.show()
            return
        self._close_edit_user_modal()
        self._reload_accounts_and_refresh_ui()

    def _on_edit_user_delete_clicked(self):
        selected = self._get_selected_edit_user()
        if not selected:
            if self.edit_user_error is not None:
                self.edit_user_error.setText("Select an account first")
                self.edit_user_error.show()
            return

        if not self._edit_user_delete_armed:
            self._edit_user_delete_armed = True
            self._edit_user_delete_arm_seq += 1
            seq_id = self._edit_user_delete_arm_seq
            if self.edit_user_delete_btn is not None:
                self.edit_user_delete_btn.setText("Confirm delete")
            if self.edit_user_warning is not None:
                self.edit_user_warning.setText(f"Warning: press Delete again to permanently remove '{selected}'.")
                self.edit_user_warning.show()
            QTimer.singleShot(3500, self, lambda: self._expire_edit_user_delete_arm(seq_id))
            return

        success, message = delete_account(selected)
        if not success:
            if self.edit_user_error is not None:
                self.edit_user_error.setText(message)
                self.edit_user_error.show()
            self._reset_edit_user_delete_arm()
            return

        self._close_edit_user_modal()
        self._reload_accounts_and_refresh_ui()

    def _expire_edit_user_delete_arm(self, seq_id):
        if seq_id != self._edit_user_delete_arm_seq:
            return
        self._reset_edit_user_delete_arm()

    def _reset_edit_user_delete_arm(self):
        self._edit_user_delete_armed = False
        self._edit_user_delete_arm_seq += 1
        if self.edit_user_delete_btn is not None:
            self.edit_user_delete_btn.setText("Delete")
        if self.edit_user_warning is not None:
            self.edit_user_warning.hide()
            self.edit_user_warning.setText("")

    def _reload_accounts_and_refresh_ui(self):
        self._load_data()
        self._build_user_buttons()
        self._refresh_current_user_label()
        self._refresh_user_button_styles()
        try:
            add_pixels = getattr(self.ui, "add_pixel_screen", None)
            if add_pixels is not None and hasattr(add_pixels, "refresh_after_account_change"):
                add_pixels.refresh_after_account_change()
        except Exception:
            pass
        try:
            graphs = getattr(self.ui, "graphs_screen", None)
            if graphs is not None and hasattr(graphs, "refresh_after_account_change"):
                graphs.refresh_after_account_change()
        except Exception:
            pass
        handled = False
        try:
            settings = getattr(self.ui, "settings_screen", None)
            if settings is not None and hasattr(settings, "refresh_after_account_change"):
                settings.refresh_after_account_change()
                handled = True
        except Exception:
            handled = False
        if not handled:
            try:
                self.ui.home_screen.refresh_info()
            except Exception:
                pass

    def _refresh_user_button_styles(self):
        strip = getattr(self, "change_user_strip", None)
        if strip is None:
            return
        theme = get_theme()
        strip.update_theme(
            accent_color=theme.get("accent_color", "#5BF69F"),
            hover_color=theme.get("hover_color", "#48C47F"),
            text_color=theme.get("text_color", "#FFFFFF"),
        )
        strip.set_selected(self.current_user)

    def _prepare_arrow_source(self):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        candidates = [
            (os.path.join(base_dir, "assets", "arrow_right.png"), 0),
            (os.path.join(base_dir, "assets", "right_arrow.png"), 0),
            (os.path.join(base_dir, "assets", "side_arrow.png"), 180),
            (os.path.join(base_dir, "assets", "dropdown_arrow.png"), -90),
        ]
        self._arrow_source_pix = None
        for path, rotation in candidates:
            pix = QPixmap(path)
            if not pix.isNull():
                if rotation:
                    pix = pix.transformed(QTransform().rotate(rotation), Qt.SmoothTransformation)
                self._arrow_source_pix = pix
                break

    def _recolor_colored_pixels(self, pixmap, color_hex):
        if pixmap is None or pixmap.isNull():
            return QPixmap()
        qcolor = QColor(color_hex)
        if not qcolor.isValid():
            qcolor = QColor("#FFFFFF")
        tinted = QPixmap(pixmap.size())
        tinted.fill(Qt.transparent)
        painter = QPainter(tinted)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), qcolor)
        painter.end()
        return tinted

    def _setup_action_button_arrow(self, btn):
        if btn is None:
            return
        text_value = btn.text()
        btn.setText("")

        content = QWidget(btn)
        content.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        content.setStyleSheet("background: transparent; border: none;")

        text_label = QLabel(text_value, content)
        text_label.setFont(btn.font())
        text_label.setStyleSheet("background: transparent; border: none; font-size: 15px;")

        arrow_label = QLabel(content)
        arrow_label.setObjectName("arrow")
        arrow_label.setStyleSheet("background: transparent; border: none;")

        anim = QPropertyAnimation(arrow_label, b"pos")
        anim.setDuration(150)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        self._action_button_content[btn] = {
            "content": content,
            "text": text_label,
            "arrow": arrow_label,
            "anim": anim,
        }
        self._layout_action_button_content(btn)

        btn.enterEvent = lambda e, b=btn: self._arrow_hover_enter(b)
        btn.leaveEvent = lambda e, b=btn: self._arrow_hover_leave(b)

    def _layout_action_button_content(self, btn):
        data = self._action_button_content.get(btn)
        if not data:
            return

        spacing = 3
        content = data["content"]
        text_label = data["text"]
        arrow_label = data["arrow"]

        text_label.adjustSize()
        text_w = text_label.width()
        text_h = text_label.height()

        pix = arrow_label.pixmap()
        if pix is None or pix.isNull():
            icon_w = 10
            icon_h = 10
        else:
            icon_w = pix.width()
            icon_h = pix.height()

        group_w = text_w + spacing + icon_w
        group_h = max(text_h, icon_h)
        x = max(0, (btn.width() - group_w) // 2)
        y = max(0, (btn.height() - group_h) // 2)

        # Keep the visible content centered, but reserve extra room on the right
        # so hover-shifting the arrow does not get clipped by the inner container.
        content.setGeometry(x, y, group_w + self._arrow_hover_shift_px, group_h)
        text_label.move(0, max(0, (group_h - text_h) // 2))
        arrow_label.move(text_w + spacing, max(0, (group_h - icon_h) // 2))
        data["original_arrow_pos"] = QPoint(arrow_label.pos())

    def _arrow_hover_enter(self, btn):
        data = self._action_button_content.get(btn)
        if not data:
            return
        arrow = data["arrow"]
        anim = data["anim"]
        start_pos = arrow.pos()
        end_pos = QPoint(start_pos.x() + self._arrow_hover_shift_px, start_pos.y())
        anim.stop()
        anim.setStartValue(start_pos)
        anim.setEndValue(end_pos)
        anim.start()

    def _arrow_hover_leave(self, btn):
        data = self._action_button_content.get(btn)
        if not data:
            return
        arrow = data["arrow"]
        anim = data["anim"]
        current_pos = arrow.pos()
        end_pos = data.get("original_arrow_pos", QPoint(data["text"].width() + 3, current_pos.y()))
        anim.stop()
        anim.setStartValue(current_pos)
        anim.setEndValue(end_pos)
        anim.start()

    def _update_action_button_content_color(self, color_hex):
        for btn, data in self._action_button_content.items():
            text_label = data["text"]
            text_label.setStyleSheet(f"background: transparent; border: none; color: {color_hex}; font-size: 15px;")
            self._layout_action_button_content(btn)


    def _update_action_button_arrows(self, color_hex):
        if self._arrow_source_pix is None:
            return
        tinted = self._recolor_colored_pixels(self._arrow_source_pix, color_hex)
        if tinted.isNull():
            return
        arrow_pix = tinted.scaled(QSize(10, 10), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        for btn, data in self._action_button_content.items():
            arrow_label = data["arrow"]
            arrow_label.setPixmap(arrow_pix)
            arrow_label.resize(arrow_pix.size())
            self._layout_action_button_content(btn)

    def _apply_accent_button_style(self, btn):
        theme = get_theme()
        accent = theme.get("accent_color", "#5BF69F")
        hover = theme.get("hover_color", "#48C47F")
        text = theme.get("text_color", "#FFFFFF")
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                border-radius: 14px;
                color: {text};
                font-size: 14px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:pressed {{
                background-color: {hover};
            }}
        """)

    def _position_change_user_status(self):
        if self.change_user_strip is None or self.change_user_spinner is None or self.change_user_tick is None:
            return
        geom = self.change_user_strip.geometry()
        x = geom.x() + geom.width() + 12
        y = int(geom.y() + (geom.height() / 2) - (self.change_user_spinner.height() / 2))
        self.change_user_spinner.move(x, y)
        self.change_user_tick.move(x, y)

    def _set_change_user_status(self, state):
        if state not in ("idle", "loading", "done"):
            return
        if state == "idle":
            self._stop_change_user_spinner()
            if self.change_user_spinner is not None:
                self.change_user_spinner.hide()
            if self.change_user_tick is not None:
                self.change_user_tick.hide()
            return
        if state == "loading":
            self._start_change_user_spinner()
            return
        self._stop_change_user_spinner_with_tick()

    def _ensure_change_user_spinner_anim(self):
        if self._change_user_spinner_anim is not None:
            return
        self._change_user_spinner_anim = QVariantAnimation(self)
        self._change_user_spinner_anim.setStartValue(0)
        self._change_user_spinner_anim.setEndValue(360)
        self._change_user_spinner_anim.setDuration(900)
        self._change_user_spinner_anim.setLoopCount(-1)
        self._change_user_spinner_anim.setEasingCurve(QEasingCurve.InOutSine)
        self._change_user_spinner_anim.valueChanged.connect(self._set_change_user_spinner_angle)

    def _set_change_user_spinner_angle(self, angle):
        if self.change_user_spinner is not None:
            self.change_user_spinner.setAngle(angle)

    def _start_change_user_spinner(self):
        self._ensure_change_user_spinner_anim()
        if self._change_user_spinner_anim is None:
            return
        if self.change_user_spinner is not None:
            self.change_user_spinner.show()
        if self.change_user_tick is not None:
            self.change_user_tick.hide()
        if self._change_user_spinner_anim.state() != QVariantAnimation.Running:
            self._change_user_spinner_anim.start()

    def _stop_change_user_spinner(self):
        if self._change_user_spinner_anim is not None:
            self._change_user_spinner_anim.stop()

    def _ensure_change_user_tick_anim(self):
        if self._change_user_tick_anim is not None:
            return
        self._change_user_tick_anim = QVariantAnimation(self)
        self._change_user_tick_anim.setStartValue(0.0)
        self._change_user_tick_anim.setEndValue(1.0)
        self._change_user_tick_anim.setDuration(220)
        self._change_user_tick_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._change_user_tick_anim.valueChanged.connect(self._set_change_user_tick_progress)

    def _set_change_user_tick_progress(self, value):
        if self.change_user_tick is not None:
            self.change_user_tick.setProgress(value)

    def _stop_change_user_spinner_with_tick(self):
        self._stop_change_user_spinner()
        self._ensure_change_user_tick_anim()
        if self.change_user_spinner is not None:
            self.change_user_spinner.hide()
        if self.change_user_tick is not None:
            self.change_user_tick.show()
        if self._change_user_tick_anim is not None:
            self._change_user_tick_anim.stop()
            self._set_change_user_tick_progress(0.0)
            self._change_user_tick_anim.start()
        QTimer.singleShot(1600, self._hide_change_user_tick)

    def _hide_change_user_tick(self):
        if self.change_user_tick is not None:
            self.change_user_tick.hide()

    def _finish_change_user_load(self, seq_id):
        if seq_id != self._change_user_load_seq:
            return
        self._set_change_user_status("done")

    def update_accent_colors(self):
        theme = get_theme()
        for btn in self.accent_buttons:
            self._apply_accent_button_style(btn)
        if self.create_user_confirm_btn is not None:
            self._set_create_user_submit_enabled(self._create_user_submit_enabled)
        self._refresh_user_button_styles()
        text_color = theme.get("text_color", "#FFFFFF")
        accent = theme.get("accent_color", "#5BF69F")
        hover = theme.get("hover_color", "#48C47F")
        try:
            if self.change_user_spinner is not None:
                self.change_user_spinner.update_color(accent)
            if self.change_user_tick is not None:
                self.change_user_tick.update_color(accent)
            if self.edit_user_select is not None and hasattr(self.edit_user_select, "update_accent_colors"):
                self.edit_user_select.update_accent_colors()
        except Exception:
            pass
        self._update_action_button_arrows(text_color)
        self._update_action_button_content_color(text_color)
