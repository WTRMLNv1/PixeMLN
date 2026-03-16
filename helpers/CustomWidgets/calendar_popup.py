from ._shared import *
from .rounded_frame import RoundedFrame
from .custom_dropdown import CustomDropdown

class CalendarPopup(RoundedFrame):
    """A themed popup calendar with month/year controls and animated month sliding.

    - Renders weekday labels and a 6x7 day grid.
    - Lets users navigate months via arrows or dropdowns.
    - Emits selection through the optional `on_date_selected` callback.

    Usage
    -----
        popup = CalendarPopup(
            parent=some_widget,
            x=20,
            y=50,
            on_date_selected=lambda d: print(d.isoformat()),
        )
        popup.refresh()
    """

    def __init__(self, parent, x, y, width=361, height=200, on_date_selected=None):
        super().__init__(parent, tl=12, tr=12, br=12, bl=12, make_border=True,
                         border_color="#8a8a8a", border_width=1, border_opacity=0.9)
        self.setGeometry(x, y, width, height)
        self.set_bg_color("#303030")
        apply_widget_shadow(self, radius=12)

        self.on_date_selected = on_date_selected
        self.current_date = date.today()
        self.current_month = self.current_date.month
        self.current_year = self.current_date.year
        self.selected_day = self.current_date.day
        self.selected_month = self.current_date.month
        self.selected_year = self.current_date.year
        self._is_animating = False
        self._month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        # header
        self._build_header()
        self._build_weekdays()
        self._build_grid()
        self.refresh()

    def _build_header(self):
        w = self.width()
        arrow_size = 15

        # left arrow
        self.left_btn = QPushButton(self)
        self.left_btn.setGeometry(8, 8, arrow_size, arrow_size)
        self.left_btn.setCursor(Qt.PointingHandCursor)
        self.left_btn.setStyleSheet("""
            QPushButton {
                background-color: #303030;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.08);
            }
        """)

        # right arrow
        self.right_btn = QPushButton(self)
        self.right_btn.setGeometry(w - 8 - arrow_size, 8, arrow_size, arrow_size)
        self.right_btn.setCursor(Qt.PointingHandCursor)
        self.right_btn.setStyleSheet("""
            QPushButton {
                background-color: #303030;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.08);
            }
        """)

        # arrow icons
        base_dir = os.path.dirname(os.path.dirname(__file__))
        arrow_path = os.path.join(base_dir, "assets", "side_arrow.png")
        fallback_path = os.path.join(base_dir, "assets", "dropdown_arrow.png")
        icon_pix = None
        for p in [arrow_path, fallback_path]:
            if os.path.exists(p):
                px = QPixmap(p)
                if not px.isNull():
                    icon_pix = px
                    break

        if icon_pix is not None:
            left_px = icon_pix
            right_px = icon_pix.transformed(QTransform().rotate(180), Qt.SmoothTransformation)
            self.right_btn.setIcon(QIcon(right_px))
            self.left_btn.setIcon(QIcon(left_px))
            self.right_btn.setIconSize(QSize(11, 11))
            self.left_btn.setIconSize(QSize(11, 11))
            self.left_btn.setStyleSheet("""
                QPushButton {
                    background-color: #303030;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,0.08);
                }
            """)

            self.right_btn.setStyleSheet("""
                QPushButton {
                    background-color: #303030;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,0.08);
                }
            """)
   

        self.left_btn.clicked.connect(self._prev_month)
        self.right_btn.clicked.connect(self._next_month)

        # month/year dropdowns
        years = [str(y) for y in range(2000, 2101)]

        total_w = 90 + 8 + 70
        start_x = max(32, (self.width() - total_w) // 2)
        self.month_dd = CustomDropdown(self, items=self._month_names, x=start_x, y=6, width=90, placeholder="Month", dropdown_color="#474747", arrow_button_color="#474747", arrow_color="#e6e6e6", box_color="#474747", arrow_type="small")
        self.year_dd = CustomDropdown(self, items=years, x=start_x + 98, y=6, width=100, placeholder="Year", dropdown_color="#474747", arrow_button_color="#474747", arrow_color="#e6e6e6", box_color="#474747", arrow_type="small")


        for i, btn in enumerate(self.month_dd.option_buttons):
            btn.clicked.connect(lambda checked=False, m=i + 1: self._set_month(m))
        for btn in self.year_dd.option_buttons:
            btn.clicked.connect(lambda checked=False, b=btn: self._set_year(int(b.text())))

        self.month_dd.set_value(self._month_names[self.current_month - 1])
        self.year_dd.set_value(str(self.current_year))

    def _build_weekdays(self):
        labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        pad = 10
        y = 36
        cell_w = int((self.width() - 2 * pad) / 7)
        for i, name in enumerate(labels):
            lab = QLabel(name, self)
            lab.setGeometry(pad + i * cell_w, y, cell_w, 16)
            f = QFont()
            f.setPointSize(9)
            f.setBold(True)
            lab.setFont(f)
            lab.setAlignment(Qt.AlignCenter)
            lab.setStyleSheet("color: #e6e6e6; background: transparent;")

    def _build_grid(self):
        pad = 10
        top = 58
        cell_w = int((self.width() - 2 * pad) / 7)
        cell_h = 22
        self._grid_rect = QRect(pad, top, cell_w * 7, cell_h * 6)
        self._cell_w = cell_w
        self._cell_h = cell_h

        self.grid_container = QWidget(self)
        self.grid_container.setGeometry(self._grid_rect)
        self.grid_container.setStyleSheet("background: transparent;")
        self.day_buttons = self._create_day_buttons(self.grid_container)

    def _create_day_buttons(self, parent):
        buttons = []
        for r in range(6):
            for c in range(7):
                btn = QPushButton("", parent)
                btn.setGeometry(c * self._cell_w, r * self._cell_h, self._cell_w, self._cell_h)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet("""
                    QPushButton {
                        color: #ffffff;
                        background: transparent;
                        border: none;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #2c2c2c;
                    }
                    QPushButton:disabled {
                        color: rgba(255,255,255,0.35);
                    }
                """)
                btn.clicked.connect(lambda checked=False, b=btn: self._pick_date(b))
                buttons.append(btn)
        return buttons

    def _populate_day_buttons(self, buttons, year, month):
        theme = get_theme() or {}
        accent = theme.get("accent_color", "#5BF69F")
        text_color = theme.get("text_color", "#FFFFFF")
        first = date(year, month, 1)
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        last_day = (next_month - timedelta(days=1)).day
        start_col = first.weekday()  # Mon=0

        for i, btn in enumerate(buttons):
            day_num = i - start_col + 1
            if 1 <= day_num <= last_day:
                btn.setText(str(day_num))
                btn.setEnabled(True)
                is_selected = (
                    day_num == self.selected_day
                    and month == self.selected_month
                    and year == self.selected_year
                )
                if is_selected:
                    btn.setStyleSheet("""
                        QPushButton {
                            color: %(text_color)s;
                            background-color: %(accent)s;
                            border: none;
                            border-radius: 4px;
                        }
                        QPushButton:hover {
                            background-color: %(accent)s;
                        }
                    """ % {"accent": accent, "text_color": text_color})
                else:
                    btn.setStyleSheet("""
                        QPushButton {
                            color: #ffffff;
                            background: transparent;
                            border: none;
                            border-radius: 4px;
                        }
                        QPushButton:hover {
                            background-color: #3f3f3f;
                        }
                        QPushButton:disabled {
                            color: rgba(255,255,255,0.35);
                        }
                    """)
            else:
                btn.setText("")
                btn.setEnabled(False)
                btn.setStyleSheet("""
                    QPushButton {
                        color: #ffffff;
                        background: transparent;
                        border: none;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #2c2c2c;
                    }
                    QPushButton:disabled {
                        color: rgba(255,255,255,0.35);
                    }
                """)

    def _update_month_year_dropdowns(self):
        self.month_dd.set_value(self._month_names[self.current_month - 1])
        self.year_dd.set_value(str(self.current_year))

    def _switch_month(self, new_year, new_month, direction=0, animate=True):
        if (new_year, new_month) == (self.current_year, self.current_month):
            return
        if self._is_animating:
            return

        old_container = self.grid_container
        self.current_year = int(new_year)
        self.current_month = int(new_month)
        self._update_month_year_dropdowns()

        if not animate or direction == 0:
            self._populate_day_buttons(self.day_buttons, self.current_year, self.current_month)
            return

        self._is_animating = True
        slide = self._grid_rect.width()
        base_x = self._grid_rect.x()
        base_y = self._grid_rect.y()
        start_x = base_x + slide if direction > 0 else base_x - slide
        end_x = base_x - slide if direction > 0 else base_x + slide

        new_container = QWidget(self)
        new_container.setGeometry(self._grid_rect)
        new_container.setStyleSheet("background: transparent;")
        new_container.move(start_x, base_y)
        new_buttons = self._create_day_buttons(new_container)
        self._populate_day_buttons(new_buttons, self.current_year, self.current_month)
        new_container.show()
        new_container.raise_()

        out_anim = QPropertyAnimation(old_container, b"pos", self)
        out_anim.setDuration(180)
        out_anim.setEasingCurve(QEasingCurve.OutCubic)
        out_anim.setStartValue(QPoint(base_x, base_y))
        out_anim.setEndValue(QPoint(end_x, base_y))

        in_anim = QPropertyAnimation(new_container, b"pos", self)
        in_anim.setDuration(180)
        in_anim.setEasingCurve(QEasingCurve.OutCubic)
        in_anim.setStartValue(QPoint(start_x, base_y))
        in_anim.setEndValue(QPoint(base_x, base_y))

        group = QParallelAnimationGroup(self)
        group.addAnimation(out_anim)
        group.addAnimation(in_anim)

        def _finish():
            old_container.deleteLater()
            self.grid_container = new_container
            self.day_buttons = new_buttons
            self._is_animating = False

        group.finished.connect(_finish)
        self._month_anim_group = group
        group.start()

    def refresh(self):
        self._populate_day_buttons(self.day_buttons, self.current_year, self.current_month)
        self._update_month_year_dropdowns()

    def _pick_date(self, btn):
        try:
            day = int(btn.text())
        except Exception:
            return
        self.selected_day = day
        self.selected_month = self.current_month
        self.selected_year = self.current_year
        self.refresh()
        d = date(self.current_year, self.current_month, day)
        if self.on_date_selected:
            self.on_date_selected(d)

    def _set_month(self, month):
        new_month = int(month)
        direction = 1 if new_month > self.current_month else -1
        self._switch_month(self.current_year, new_month, direction=direction, animate=True)

    def _set_year(self, year):
        new_year = int(year)
        direction = 1 if new_year > self.current_year else -1
        self._switch_month(new_year, self.current_month, direction=direction, animate=True)

    def _prev_month(self):
        if self.current_month == 1:
            new_month = 12
            new_year = self.current_year - 1
        else:
            new_month = self.current_month - 1
            new_year = self.current_year
        self._switch_month(new_year, new_month, direction=-1, animate=True)

    def _next_month(self):
        if self.current_month == 12:
            new_month = 1
            new_year = self.current_year + 1
        else:
            new_month = self.current_month + 1
            new_year = self.current_year
        self._switch_month(new_year, new_month, direction=1, animate=True)

