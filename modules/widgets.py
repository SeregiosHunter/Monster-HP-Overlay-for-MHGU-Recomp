import math

from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QLinearGradient, QPen
from PySide6.QtWidgets import QWidget

def _al(*flags):
    """Alignment flags as the plain int that QPainter.drawText wants."""
    value = 0
    for flag in flags:
        value |= getattr(flag, "value", flag)
    return int(value)


# Colour of each abnormal status bar.
STATUS_COLORS = {
    "Poison": "#b06ad8",
    "Sleep": "#5aa9e6",
    "Paralysis": "#f0d34a",
    "Dizzy": "#f29e4c",
    "Exhaust": "#4fc3c3",
    "Jump": "#9ad06a",
    "Blast": "#ff8a3d",
    "Rage": "#e5533d",
}
DEFAULT_STATUS_COLOR = "#c8c8c8"

CROWN_COLORS = {"Gold": "#f2c14e", "Silver": "#c0c7d1", "Mini": "#7ec8e3"}

HP_HIGH = ("#2f9e4f", "#7be07b")
HP_MID = ("#c9a227", "#f2d45c")
HP_LOW = ("#b3322a", "#ee6b5b")


class MonsterCard(QWidget):
    """One monster: name, HP bar and (optionally) abnormal status bars, painted by hand.

    It replaces the old QLabel, and keeps the parts of the QLabel API that overlay.py uses (clear, setParent).
    Everything is sized from ``font_size`` so the whole card scales with that config option.
    """

    def __init__(self, text_color: QColor, bg_color: QColor, font_families, font_size: int):
        super().__init__()
        self.text_color = QColor(text_color)
        self.bg_color = QColor(bg_color)
        self.families = list(font_families)
        fs = max(int(font_size), 1)
        self.fs = fs
        self.width_px = int(fs * 21)
        self._data = None
        self._rage_peak = 0
        self._rage_last = 0
        self._last_name = None

        def make_font(px, weight):
            font = QFont()
            font.setFamilies(self.families)
            font.setPixelSize(max(int(px), 8))
            font.setWeight(weight)
            return font

        self.name_font = make_font(fs * 0.85, QFont.Weight.DemiBold)
        self.small_name_font = make_font(fs * 0.7, QFont.Weight.DemiBold)
        self.pct_font = make_font(fs * 0.7, QFont.Weight.Medium)
        self.bar_font = make_font(fs * 0.62, QFont.Weight.DemiBold)
        self.small_bar_font = make_font(fs * 0.5, QFont.Weight.DemiBold)
        self.status_font = make_font(fs * 0.62, QFont.Weight.Medium)

    # ---- QLabel-like API -------------------------------------------------------------------------------------------
    def clear(self):
        self._data = None
        self.update()

    def set_data(self, name, hp, initial_hp, show_pct=True, show_initial=True, size_text="", crown_key="",
                 crown_text="", statuses=None, small=False):
        """statuses: list of (key, label, kind, cur, max) with kind 'bar', 'rage' or 'text'."""
        statuses = statuses or []
        if name != self._last_name:
            self._rage_peak = 0
            self._rage_last = 0
            self._last_name = name
        for key, _label, kind, cur, _max in statuses:
            if kind == "rage":
                if cur > self._rage_last:
                    self._rage_peak = cur
                self._rage_peak = max(self._rage_peak, cur)
                self._rage_last = cur
        initial_hp = max(initial_hp, 1)
        self._data = dict(
            name=name, hp=hp, initial_hp=initial_hp, show_pct=show_pct, show_initial=show_initial,
            size_text=size_text, crown_key=crown_key, crown_text=crown_text, statuses=statuses, small=small,
        )
        new_size = self.sizeHint()
        if new_size != self.size():
            self.setFixedSize(new_size)
        self.update()

    # ---- metrics ---------------------------------------------------------------------------------------------------
    def _metrics(self, small):
        fs = self.fs
        pad_x = round(fs * (0.5 if small else 0.65))
        pad_y = round(fs * (0.3 if small else 0.5))
        bar_h = round(fs * (0.62 if small else 0.95))
        gap = round(fs * (0.2 if small else 0.3))
        name_fm = QFontMetrics(self.small_name_font if small else self.name_font)
        status_fm = QFontMetrics(self.status_font)
        row_h = status_fm.height() + round(fs * 0.12)
        return pad_x, pad_y, bar_h, gap, name_fm, status_fm, row_h

    def sizeHint(self):
        if not self._data:
            return QSize(self.width_px, 1)
        small = self._data["small"]
        pad_x, pad_y, bar_h, gap, name_fm, _sfm, row_h = self._metrics(small)
        h = pad_y + name_fm.height() + gap + bar_h + pad_y
        if self._data["statuses"]:
            h += len(self._data["statuses"]) * (row_h + round(self.fs * 0.1)) + gap
        return QSize(self.width_px, h)

    def minimumSizeHint(self):
        return self.sizeHint()

    # ---- painting --------------------------------------------------------------------------------------------------
    def paintEvent(self, _event):
        d = self._data
        if not d:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        small = d["small"]
        pad_x, pad_y, bar_h, gap, name_fm, status_fm, row_h = self._metrics(small)
        w, h = self.width(), self.height()
        radius = self.fs * 0.4

        # background card
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.bg_color)
        p.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)

        inner_w = w - 2 * pad_x
        y = pad_y

        # header: name (+ size, crown) on the left, percentage on the right
        pct_text = ""
        if d["show_pct"]:
            pct_text = f"{max(0, min(100, math.ceil(d['hp'] / d['initial_hp'] * 100)))}%"
        p.setFont(self.pct_font)
        pct_w = QFontMetrics(self.pct_font).horizontalAdvance(pct_text) if pct_text else 0

        x = pad_x
        name_font = self.small_name_font if small else self.name_font
        p.setFont(name_font)
        p.setPen(self.text_color)
        extras_w = 0
        crown_w = 0
        if d["crown_text"]:
            crown_w = QFontMetrics(self.pct_font).horizontalAdvance(d["crown_text"]) + round(self.fs * 0.8)
            extras_w += crown_w + round(self.fs * 0.3)
        size_w = 0
        if d["size_text"]:
            size_w = QFontMetrics(self.pct_font).horizontalAdvance(d["size_text"])
            extras_w += size_w + round(self.fs * 0.3)
        name_room = max(inner_w - pct_w - extras_w - round(self.fs * 0.5), 20)
        name = name_fm.elidedText(d["name"], Qt.TextElideMode.ElideRight, name_room)
        p.drawText(QRectF(x, y, name_room + 2, name_fm.height()),
                   _al(Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignVCenter), name)
        x += name_fm.horizontalAdvance(name) + round(self.fs * 0.35)

        p.setFont(self.pct_font)
        pct_fm = QFontMetrics(self.pct_font)
        if d["crown_text"]:
            color = QColor(CROWN_COLORS.get(d["crown_key"], "#f2c14e"))
            badge = QRectF(x, y + (name_fm.height() - pct_fm.height()) / 2 + 1, crown_w, pct_fm.height() - 2)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(color.red(), color.green(), color.blue(), 60))
            p.drawRoundedRect(badge, 3, 3)
            p.setPen(color)
            p.drawText(badge, _al(Qt.AlignmentFlag.AlignCenter), d["crown_text"])
            x += crown_w + round(self.fs * 0.3)
        if d["size_text"]:
            faded = QColor(self.text_color)
            faded.setAlphaF(faded.alphaF() * 0.65)
            p.setPen(faded)
            p.drawText(QRectF(x, y, size_w + 2, name_fm.height()),
                       _al(Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignVCenter), d["size_text"])
        if pct_text:
            faded = QColor(self.text_color)
            faded.setAlphaF(faded.alphaF() * 0.8)
            p.setPen(faded)
            p.drawText(QRectF(w - pad_x - pct_w - 2, y, pct_w + 2, name_fm.height()),
                       _al(Qt.AlignmentFlag.AlignRight, Qt.AlignmentFlag.AlignVCenter), pct_text)

        # HP bar
        y += name_fm.height() + gap
        frac = max(0.0, min(1.0, d["hp"] / d["initial_hp"]))
        bar = QRectF(pad_x, y, inner_w, bar_h)
        bar_radius = bar_h * 0.3
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 30))
        p.drawRoundedRect(bar, bar_radius, bar_radius)
        if frac > 0:
            low, high = HP_HIGH if frac > 0.5 else HP_MID if frac > 0.25 else HP_LOW
            grad = QLinearGradient(bar.left(), 0, bar.right(), 0)
            grad.setColorAt(0, QColor(low))
            grad.setColorAt(1, QColor(high))
            p.setBrush(grad)
            p.drawRoundedRect(QRectF(bar.left(), bar.top(), max(bar.width() * frac, bar_radius * 2), bar.height()),
                              bar_radius, bar_radius)
        p.setFont(self.small_bar_font if small else self.bar_font)
        bar_fm = QFontMetrics(self.small_bar_font if small else self.bar_font)
        left_text = f"{d['hp']:,}"
        right_text = f"{d['initial_hp']:,}" if d["show_initial"] else ""
        inset = round(self.fs * 0.35)
        text_h = bar_fm.height()
        text_y = bar.top() + (bar.height() - text_h) / 2
        for text, align, ox in ((left_text, Qt.AlignmentFlag.AlignLeft, inset),
                                (right_text, Qt.AlignmentFlag.AlignRight, -inset)):
            if not text:
                continue
            rect = QRectF(bar.left() + inset, text_y, bar.width() - 2 * inset, text_h)
            p.setPen(QColor(0, 0, 0, 170))
            p.drawText(rect.translated(1, 1), int(align | Qt.AlignmentFlag.AlignVCenter), text)
            p.setPen(QColor(255, 255, 255, 240))
            p.drawText(rect, int(align | Qt.AlignmentFlag.AlignVCenter), text)

        # abnormal status rows
        if d["statuses"]:
            y += bar_h + gap
            p.setFont(self.status_font)
            label_w = max(status_fm.horizontalAdvance(s[1]) for s in d["statuses"]) + round(self.fs * 0.4)
            value_texts = []
            for key, _label, kind, cur, mx in d["statuses"]:
                if kind == "rage":
                    m, s = divmod(int(cur), 60)
                    value_texts.append(f"{m}:{s:02d}")
                elif kind == "text":
                    value_texts.append(f"{cur:,}" if isinstance(cur, int) else str(cur))
                else:
                    value_texts.append(f"{cur}/{mx}")
            value_w = max(status_fm.horizontalAdvance(t) for t in value_texts) + round(self.fs * 0.2)
            track_x = pad_x + label_w
            track_w = max(inner_w - label_w - value_w - round(self.fs * 0.3), 10)
            track_h = max(round(self.fs * 0.28), 4)
            for (key, label, kind, cur, mx), value_text in zip(d["statuses"], value_texts):
                p.setPen(self.text_color)
                p.drawText(QRectF(pad_x, y, label_w, row_h),
                           _al(Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignVCenter), label)
                if kind != "text":
                    if kind == "rage":
                        sfrac = cur / self._rage_peak if self._rage_peak else 0.0
                    else:
                        sfrac = cur / mx if mx else 0.0
                    sfrac = max(0.0, min(1.0, sfrac))
                    track = QRectF(track_x, y + (row_h - track_h) / 2, track_w, track_h)
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QColor(255, 255, 255, 30))
                    p.drawRoundedRect(track, track_h / 2, track_h / 2)
                    if sfrac > 0:
                        p.setBrush(QColor(STATUS_COLORS.get(key, DEFAULT_STATUS_COLOR)))
                        p.drawRoundedRect(QRectF(track.left(), track.top(), max(track.width() * sfrac, track_h),
                                                 track.height()), track_h / 2, track_h / 2)
                faded = QColor(self.text_color)
                faded.setAlphaF(faded.alphaF() * 0.85)
                p.setPen(faded)
                p.drawText(QRectF(w - pad_x - value_w, y, value_w, row_h),
                           _al(Qt.AlignmentFlag.AlignRight, Qt.AlignmentFlag.AlignVCenter), value_text)
                y += row_h + round(self.fs * 0.1)
        p.end()
