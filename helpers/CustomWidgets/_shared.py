# _shared.py
# This module provides shared utilities for custom widgets, such as applying shadows to widgets without affecting their children.
# Also contains the imports and constants used across multiple custom widget implementations.
import os
import re
from PySide6.QtWidgets import QFrame, QScrollBar, QPushButton, QLabel, QWidget, QScrollArea, QSizePolicy, QGraphicsDropShadowEffect
from PySide6.QtGui import QPainterPath, QPainter, QColor, QPixmap, QFont, QIcon, QTransform, QPen
from PySide6.QtCore import Qt, QRect, QRectF, QSize, QObject, Property, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, Signal, QTimer, QPoint, QPointF, QEvent
from datetime import date, timedelta
from helpers.json_manager import get_theme

# Shadow tuning (single place to edit)
SHADOW_THICKNESS_PX = 10
SHADOW_NEAR_ALPHA = 0x66
SHADOW_FAR_ALPHA = 16
SHADOW_BLUR_MULTIPLIER = 3.0
SHADOW_Y_OFFSET_RATIO = 0.4


class _ShadowSync(QObject):
    """Keep a dedicated shadow widget synced with the target widget."""
    def __init__(self, target, shadow):
        super().__init__(target)
        self._target = target
        self._shadow = shadow
        target.installEventFilter(self)
        self._sync()

    def _sync(self):
        try:
            if self._target is None or self._shadow is None:
                return
            self._shadow.setGeometry(self._target.geometry())
            self._shadow.setVisible(self._target.isVisible())
            self._shadow.lower()
            self._target.raise_()
        except Exception:
            pass

    def eventFilter(self, obj, event):
        if obj is self._target:
            et = event.type()
            if et in (
                QEvent.Move,
                QEvent.Resize,
                QEvent.Show,
                QEvent.Hide,
                QEvent.ParentChange,
                QEvent.ZOrderChange,
            ):
                self._sync()
        return super().eventFilter(obj, event)


def apply_widget_shadow(target, radius=20, blur=None, x_offset=0, y_offset=None, color=None, thickness=None):
    """Apply shadow via sibling layer so children are not shadow-rendered."""
    if target is None:
        return None
    parent = target.parentWidget()
    if parent is None:
        return None
    t = SHADOW_THICKNESS_PX if thickness is None else max(1, int(thickness))
    if blur is None:
        blur = float(t) * SHADOW_BLUR_MULTIPLIER
    if y_offset is None:
        y_offset = max(1, int(round(float(t) * SHADOW_Y_OFFSET_RATIO)))
    if color is None:
        color = f"#000000{int(SHADOW_NEAR_ALPHA):02X}"

    shadow = QFrame(parent)
    shadow.setObjectName(f"{target.objectName() or target.__class__.__name__}_shadow")
    shadow.setAttribute(Qt.WA_TransparentForMouseEvents, True)
    # Keep the source layer itself very faint; primary darkness comes from blur effect.
    shadow.setStyleSheet(
        f"background-color: rgba(0,0,0,{int(SHADOW_FAR_ALPHA)}); border: none; border-radius: {int(radius)}px;"
    )

    effect = QGraphicsDropShadowEffect(shadow)
    effect.setBlurRadius(float(blur))
    effect.setOffset(float(x_offset), float(y_offset))
    effect.setColor(QColor(color))
    shadow.setGraphicsEffect(effect)
    # effect.setColor(QColor("#FFFFFF")) |
    # effect.setBlurRadius(30)           | <- Testing
    # effect.setOffset(0, 10)            |

    sync = _ShadowSync(target, shadow)
    # Keep strong refs on target so helper objects stay alive.
    target._shadow_layer = shadow
    target._shadow_sync = sync
    target._shadow_effect = effect
    return shadow

