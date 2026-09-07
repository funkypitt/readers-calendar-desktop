#!/usr/bin/env python3
"""Reader's Calendar — a black-and-white, text-only desktop calendar on CalDAV
(Infomaniak, Nextcloud, Radicale…). The landscape design of the Android app: month grid and
navigation on the left, agenda / week grid / event page on the right. PyQt5 + requests +
python-dateutil, one file. MIT licence."""

import calendar
import json
import os
import sys
from datetime import date, datetime, timedelta

from PyQt5 import QtCore, QtGui, QtWidgets

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/usr/lib/readers-calendar")
import caldav_events as ce  # noqa: E402

APP = "readers-calendar"
VERSION = "1.1.0"
CONFIG_DIR = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), APP)
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
SYNC_MINUTES = 5
LOCAL = ce.LOCAL


def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    os.makedirs(CONFIG_DIR, mode=0o700, exist_ok=True)
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cfg, f, indent=2)
    os.chmod(tmp, 0o600)
    os.replace(tmp, CONFIG_FILE)


def day_label(d, today):
    base = d.strftime("%A %-d %B").lower()
    if d == today:
        return "today · " + base
    if d == today + timedelta(days=1):
        return "tomorrow · " + base
    return base if d.year == today.year else base + f" {d.year}"


def fmt_time(dt):
    return dt.strftime("%H:%M")


class Occ:
    """One occurrence shown in lists: event + its start/end datetimes."""
    def __init__(self, event, cal_name, start, end):
        self.event, self.cal_name, self.start, self.end = event, cal_name, start, end

    @property
    def date(self):
        return self.start.date()

    def when(self):
        if self.event.all_day:
            return "all day"
        if self.end.date() == self.start.date():
            return f"{fmt_time(self.start)} – {fmt_time(self.end)}"
        return f"{fmt_time(self.start)} – {self.end.strftime('%-d %b')} {fmt_time(self.end)}"


# ------------------------------------------------------------------------------------------
# Threads
# ------------------------------------------------------------------------------------------

class Worker(QtCore.QObject):
    done = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn())
        except Exception as e:
            self.failed.emit(str(e))


# ------------------------------------------------------------------------------------------
# Month grid (the left column, also the date picker)
# ------------------------------------------------------------------------------------------

class MonthGrid(QtWidgets.QWidget):
    day_clicked = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.month = date.today().replace(day=1)
        self.marked = set()
        self.selected = None
        self.fg = QtGui.QColor("#000"); self.bg = QtGui.QColor("#fff")
        self.week_monday = True
        self.setMinimumHeight(220)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self._cells = []

    def set_colors(self, fg, bg):
        self.fg, self.bg = QtGui.QColor(fg), QtGui.QColor(bg); self.update()

    def set_month(self, month):
        self.month = month.replace(day=1); self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cols, rows = 7, 7
        cw, ch = w / cols, h / rows
        dim = QtGui.QColor(self.fg); dim.setAlphaF(0.55)
        rule = QtGui.QColor(self.fg); rule.setAlphaF(0.25)
        small = QtGui.QFont(self.font()); small.setPointSizeF(self.font().pointSizeF() * 0.8)
        first = 0 if self.week_monday else 6
        # header
        p.setFont(small); p.setPen(dim)
        for i in range(7):
            name = calendar.day_abbr[(first + i) % 7][:1].lower()
            p.drawText(QtCore.QRectF(i * cw, 0, cw, ch), QtCore.Qt.AlignCenter, name)
        # days
        self._cells = []
        start = self.month - timedelta(days=(self.month.weekday() - first) % 7)
        today = date.today()
        d = start
        for r in range(1, rows):
            for c in range(cols):
                rect = QtCore.QRectF(c * cw, r * ch, cw, ch).adjusted(3, 3, -3, -3)
                self._cells.append((rect, d))
                in_month = d.month == self.month.month and d.year == self.month.year
                if d == today:
                    p.fillRect(rect, self.fg); p.setPen(self.bg)
                else:
                    if d == self.selected:
                        p.setPen(QtGui.QPen(self.fg, 1)); p.drawRect(rect)
                    p.setPen(self.fg if in_month else rule)
                p.setFont(self.font())
                p.drawText(rect.adjusted(0, 0, 0, -ch * 0.28), QtCore.Qt.AlignCenter, str(d.day))
                if d in self.marked:
                    p.setFont(small)
                    p.drawText(rect.adjusted(0, ch * 0.45, 0, 0), QtCore.Qt.AlignCenter, "•")
                d += timedelta(days=1)

    def mousePressEvent(self, e):
        for rect, d in self._cells:
            if rect.contains(e.pos()):
                self.day_clicked.emit(d); return


# ------------------------------------------------------------------------------------------
# Week grid (the time grid, painted)
# ------------------------------------------------------------------------------------------

def place_lanes(items):
    """Google-Calendar style lanes: overlapping events share the column side by side.
    items: [(start_min, end_min, occ)] -> [(start_min, end_min, occ, lane, lanes)]."""
    out = []; cluster = []; lane_ends = []; cluster_end = -1
    def flush():
        for row in cluster: row[4] = len(lane_ends)
        out.extend(cluster); cluster.clear(); lane_ends.clear()
    for s, e, o in sorted(items, key=lambda x: (x[0], -x[1])):
        if cluster and s >= cluster_end: flush()
        lane = next((i for i, le in enumerate(lane_ends) if le <= s), -1)
        if lane < 0: lane_ends.append(e); lane = len(lane_ends) - 1
        else: lane_ends[lane] = e
        cluster.append([s, e, o, lane, 1]); cluster_end = max(cluster_end, e)
    flush()
    return out


class WeekHead(QtWidgets.QWidget):
    """Day headers and the all-day strip: stays put while the time grid scrolls."""
    event_clicked = QtCore.pyqtSignal(object)
    GUTTER = 48

    def __init__(self, parent=None):
        super().__init__(parent)
        self.start = date.today(); self.ndays = 7
        self.occs = []
        self.fg = QtGui.QColor("#000"); self.bg = QtGui.QColor("#fff")
        self._boxes = []
        self.setFixedHeight(64)

    def set_colors(self, fg, bg):
        self.fg, self.bg = QtGui.QColor(fg), QtGui.QColor(bg); self.update()

    def set_data(self, start, ndays, occs):
        self.start = start; self.ndays = ndays
        self.occs = [o for o in occs if o.event.all_day]
        rows = max((sum(1 for o in self.occs if o.start.date() <= start + timedelta(days=i) < o.end.date()) for i in range(ndays)), default=0)
        self.setFixedHeight((56 if ndays > 1 else 4) + rows * 22 + 4)
        self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        w = self.width(); gutter, header = self.GUTTER, (56 if self.ndays > 1 else 4)
        colw = (w - gutter - 8) / self.ndays
        dim = QtGui.QColor(self.fg); dim.setAlphaF(0.55)
        small = QtGui.QFont(self.font()); small.setPointSizeF(self.font().pointSizeF() * 0.78)
        today = date.today()
        self._boxes = []; self._heads = []
        for i in range(self.ndays if self.ndays > 1 else 0):
            d = self.start + timedelta(days=i)
            rect = QtCore.QRectF(gutter + i * colw, 0, colw, header).adjusted(2, 4, -2, -4)
            if self.ndays > 1:
                rect = QtCore.QRectF(rect.center().x() - 30, rect.top(), 60, rect.height())
            self._heads.append((rect, d))
            if d == today:
                p.fillRect(rect, self.fg); p.setPen(self.bg)
            else:
                p.setPen(dim)
            label = d.strftime("%a").lower() if self.ndays > 1 else d.strftime("%A %-d %B").lower()
            p.setFont(small); p.drawText(rect.adjusted(0, 4, 0, -rect.height() / 2), QtCore.Qt.AlignCenter, label)
            p.setPen(self.bg if d == today else self.fg); p.setFont(self.font())
            p.drawText(rect.adjusted(0, rect.height() / 2 - 4, 0, 0), QtCore.Qt.AlignCenter, str(d.day))
        for i in range(self.ndays):
            d = self.start + timedelta(days=i)
            y = header
            for o in self.occs:
                if o.start.date() <= d < o.end.date():
                    rect = QtCore.QRectF(gutter + i * colw, y, colw, 20).adjusted(2, 0, -2, 0)
                    p.fillRect(rect, self.fg); p.setPen(self.bg); p.setFont(small)
                    p.drawText(rect.adjusted(4, 0, -4, 0), QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, p.fontMetrics().elidedText(o.event.summary, QtCore.Qt.ElideRight, int(rect.width()) - 8))
                    self._boxes.append((rect, o)); y += 22

    day_clicked = QtCore.pyqtSignal(object)

    def mousePressEvent(self, e):
        for rect, o in self._boxes:
            if rect.contains(e.pos()):
                self.event_clicked.emit(o); return
        if self.ndays > 1:
            for rect, d in self._heads:
                if rect.contains(e.pos()):
                    self.day_clicked.emit(d); return


class WeekGrid(QtWidgets.QWidget):
    """The 24-hour time grid of one week (scrolls)."""
    event_clicked = QtCore.pyqtSignal(object)
    slot_clicked = QtCore.pyqtSignal(object, int)   # (date, hour)
    HOUR = 48
    TOP = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.start = date.today(); self.ndays = 7
        self.occs = []
        self.fg = QtGui.QColor("#000"); self.bg = QtGui.QColor("#fff")
        self.setMinimumHeight(24 * self.HOUR + 2 * self.TOP)
        self._boxes = []

    def set_colors(self, fg, bg):
        self.fg, self.bg = QtGui.QColor(fg), QtGui.QColor(bg); self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        w = self.width(); gutter, top = WeekHead.GUTTER, self.TOP
        colw = (w - gutter - 8) / self.ndays
        dim = QtGui.QColor(self.fg); dim.setAlphaF(0.55)
        rule = QtGui.QColor(self.fg); rule.setAlphaF(0.25)
        dimbg = QtGui.QColor(self.bg); dimbg.setAlphaF(0.7)
        small = QtGui.QFont(self.font()); small.setPointSizeF(self.font().pointSizeF() * 0.78)
        today = date.today()
        self._boxes = []
        p.setPen(rule)
        for hh in range(25):
            y = top + hh * self.HOUR
            p.drawLine(QtCore.QPointF(gutter, y), QtCore.QPointF(w - 8, y))
        for i in range(self.ndays + 1):
            x = gutter + i * colw
            p.drawLine(QtCore.QPointF(x, top), QtCore.QPointF(x, top + 24 * self.HOUR))
        p.setPen(dim); p.setFont(small)
        for hh in range(24):
            p.drawText(QtCore.QRectF(0, top + hh * self.HOUR - 8, gutter - 6, 16), QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter, f"{hh:02d}")
        fm_small = QtGui.QFontMetrics(small)
        for i in range(self.ndays):
            d = self.start + timedelta(days=i)
            items = []
            for o in self.occs:
                if o.event.all_day or o.start.date() != d:
                    continue
                s = o.start.hour * 60 + o.start.minute
                e_end = o.end if o.end.date() == d else datetime.combine(d, datetime.max.time(), tzinfo=o.start.tzinfo)
                e = max(e_end.hour * 60 + e_end.minute, s + 25)
                items.append((s, e, o))
            for s, e, o, lane, lanes in place_lanes(items):
                lane_w = (colw - 4) / lanes
                x0 = gutter + i * colw + 2 + lane * lane_w
                y0 = top + s / 60 * self.HOUR; y1 = top + e / 60 * self.HOUR
                # solid blocks: the white between them is the free time
                rect = QtCore.QRectF(x0, y0, lane_w - (1 if lane < lanes - 1 else 0), y1 - y0 - 1)
                p.fillRect(rect, self.fg)
                show_time = rect.height() >= fm_small.height() * 2 + 8
                inner = rect.adjusted(4, 2, -4, -(fm_small.height() + 3) if show_time else -2)
                whole = int(inner.height() // fm_small.lineSpacing()) * fm_small.lineSpacing()
                inner.setHeight(max(whole, fm_small.lineSpacing()))
                p.save(); p.setClipRect(rect.adjusted(2, 1, -2, -1))
                p.setFont(small); p.setPen(self.bg)
                flags = QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft | (QtCore.Qt.TextWordWrap if lane_w >= 44 else 0)
                p.drawText(inner, flags, o.event.summary)
                if show_time:
                    p.setPen(dimbg)
                    label = fmt_time(o.start) + (" · " + o.event.location if self.ndays == 1 and o.event.location else "")
                    p.drawText(rect.adjusted(4, 0, -4, -3), QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeft, label)
                p.restore()
                self._boxes.append((rect, o))
        if self.start <= today < self.start + timedelta(days=self.ndays):
            i = (today - self.start).days
            now = datetime.now()
            y = top + (now.hour + now.minute / 60) * self.HOUR
            p.setPen(QtGui.QPen(self.bg, 4)); p.drawLine(QtCore.QPointF(gutter + i * colw, y), QtCore.QPointF(gutter + (i + 1) * colw, y))
            p.setPen(QtGui.QPen(self.fg, 2)); p.drawLine(QtCore.QPointF(gutter + i * colw, y), QtCore.QPointF(gutter + (i + 1) * colw, y))
            p.setBrush(self.bg); p.setPen(QtCore.Qt.NoPen); p.drawEllipse(QtCore.QPointF(gutter + i * colw, y), 5, 5)
            p.setBrush(self.fg); p.drawEllipse(QtCore.QPointF(gutter + i * colw, y), 3, 3)

    def mousePressEvent(self, e):
        for rect, o in reversed(self._boxes):
            if rect.contains(e.pos()):
                self.event_clicked.emit(o); return
        gutter = WeekHead.GUTTER; colw = (self.width() - gutter - 8) / self.ndays
        if e.pos().x() >= gutter and self.TOP <= e.pos().y() < self.TOP + 24 * self.HOUR:
            i = int((e.pos().x() - gutter) / colw)
            if 0 <= i < self.ndays:
                self.slot_clicked.emit(self.start + timedelta(days=i), int((e.pos().y() - self.TOP) / self.HOUR))


# ------------------------------------------------------------------------------------------
# Small helpers: text rows, prompts
# ------------------------------------------------------------------------------------------

def row(text, secondary=None, size=None, dim_secondary=True, click=None, obj=None):
    w = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(w); lay.setContentsMargins(0, 6, 0, 6); lay.setSpacing(0)
    t = QtWidgets.QLabel(text); t.setWordWrap(True)
    if size:
        f = t.font(); f.setPointSize(size); t.setFont(f)
    if obj:
        t.setObjectName(obj)
    lay.addWidget(t)
    if secondary:
        s = QtWidgets.QLabel(secondary); s.setObjectName("dim"); s.setWordWrap(True); lay.addWidget(s)
    if click:
        w.setCursor(QtCore.Qt.PointingHandCursor); w.mousePressEvent = lambda e: click()
    return w


class TextPrompt(QtWidgets.QDialog):
    def __init__(self, title, initial="", multiline=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        lay = QtWidgets.QVBoxLayout(self)
        lab = QtWidgets.QLabel(title); lab.setObjectName("dim"); lay.addWidget(lab)
        if multiline:
            self.edit = QtWidgets.QPlainTextEdit(initial)
        else:
            self.edit = QtWidgets.QLineEdit(initial); self.edit.returnPressed.connect(self.accept)
        lay.addWidget(self.edit)
        btns = QtWidgets.QHBoxLayout(); btns.addStretch(1)
        c = QtWidgets.QPushButton("cancel"); c.clicked.connect(self.reject); btns.addWidget(c)
        ok = QtWidgets.QPushButton("ok"); ok.setDefault(True); ok.clicked.connect(self.accept); btns.addWidget(ok)
        lay.addLayout(btns)
        self.resize(520, 300 if multiline else 120)

    def value(self):
        return self.edit.toPlainText() if isinstance(self.edit, QtWidgets.QPlainTextEdit) else self.edit.text()


class DatePick(QtWidgets.QDialog):
    def __init__(self, initial, fg, bg, parent=None):
        super().__init__(parent)
        self.setWindowTitle("date")
        self.value = initial
        lay = QtWidgets.QVBoxLayout(self)
        nav = QtWidgets.QHBoxLayout()
        prev = QtWidgets.QLabel("‹"); nxt = QtWidgets.QLabel("›"); self.title = QtWidgets.QLabel(); self.title.setObjectName("dim")
        for l in (prev, nxt):
            l.setCursor(QtCore.Qt.PointingHandCursor)
        nav.addWidget(prev); nav.addWidget(self.title, 1, QtCore.Qt.AlignCenter); nav.addWidget(nxt)
        lay.addLayout(nav)
        self.grid = MonthGrid(); self.grid.set_colors(fg, bg); self.grid.set_month(initial); self.grid.selected = initial
        self.grid.setMinimumSize(320, 260)
        self.grid.day_clicked.connect(self._pick)
        lay.addWidget(self.grid)
        prev.mousePressEvent = lambda e: self._move(-1)
        nxt.mousePressEvent = lambda e: self._move(1)
        self._refresh()

    def _refresh(self):
        self.title.setText(self.grid.month.strftime("%B %Y").lower())

    def _move(self, delta):
        m = self.grid.month
        y, mo = m.year, m.month + delta
        if mo == 0: y, mo = y - 1, 12
        if mo == 13: y, mo = y + 1, 1
        self.grid.set_month(date(y, mo, 1)); self._refresh()

    def _pick(self, d):
        self.value = d; self.accept()


# ------------------------------------------------------------------------------------------
# Main window
# ------------------------------------------------------------------------------------------

REMINDERS = [None, 0, 10, 30, 60, 120, 1440]
REPEATS = [("", "does not repeat"), ("FREQ=DAILY", "every day"), ("FREQ=WEEKLY", "every week"), ("FREQ=MONTHLY", "every month"), ("FREQ=YEARLY", "every year")]


def reminder_label(m):
    if m is None: return "no reminder"
    if m == 0: return "at the time of the event"
    if m < 60: return f"{m} minutes before"
    if m < 1440: return f"{m // 60} hours before"
    return f"{m // 1440} days before"


class Main(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.client = None
        self.calendars = []          # [(name, url, writable)]
        self.events = []             # masters of the loaded window
        self.occs = []               # expanded occurrences of the loaded window
        self.threads = []
        self.font_size = int(self.cfg.get("font_size", 13))
        self.dark = bool(self.cfg.get("dark", False))
        self.window_days = 60
        self.setWindowTitle("reader's calendar")
        self.resize(1180, 760)

        central = QtWidgets.QWidget(); self.setCentralWidget(central)
        outer = QtWidgets.QHBoxLayout(central); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        # ---- left column: month grid + navigation
        left = QtWidgets.QWidget(); left.setObjectName("left"); left.setFixedWidth(330)
        ll = QtWidgets.QVBoxLayout(left); ll.setContentsMargins(20, 18, 20, 12); ll.setSpacing(6)
        mnav = QtWidgets.QHBoxLayout()
        self.m_prev = QtWidgets.QLabel("‹"); self.m_next = QtWidgets.QLabel("›"); self.m_title = QtWidgets.QLabel(); self.m_title.setObjectName("dim")
        for l in (self.m_prev, self.m_next, self.m_title): l.setCursor(QtCore.Qt.PointingHandCursor)
        mnav.addWidget(self.m_prev); mnav.addWidget(self.m_title, 1, QtCore.Qt.AlignCenter); mnav.addWidget(self.m_next)
        ll.addLayout(mnav)
        self.grid = MonthGrid(); self.grid.setFixedHeight(250); ll.addWidget(self.grid)
        ll.addSpacing(10)
        self.nav_agenda = row("agenda", click=lambda: self.show_agenda()); ll.addWidget(self.nav_agenda)
        self.nav_day = row("day", click=lambda: self.show_day_grid(date.today())); ll.addWidget(self.nav_day)
        self.nav_week = row("week", click=lambda: self.show_week(date.today())); ll.addWidget(self.nav_week)
        self.nav_new = row("+ new event", click=lambda: self.edit_event(None)); ll.addWidget(self.nav_new)
        ll.addStretch(1)
        self.cal_box = QtWidgets.QVBoxLayout(); ll.addLayout(self.cal_box)
        self.status = QtWidgets.QLabel(""); self.status.setObjectName("dim"); self.status.setWordWrap(True)
        bottom = QtWidgets.QHBoxLayout(); bottom.addWidget(self.status, 1)
        gear = QtWidgets.QLabel("⚙"); gear.setObjectName("dim"); gear.setCursor(QtCore.Qt.PointingHandCursor); gear.mousePressEvent = lambda e: self.setup(); bottom.addWidget(gear, 0)
        ll.addLayout(bottom)
        outer.addWidget(left)
        sep = QtWidgets.QFrame(); sep.setObjectName("sep"); sep.setFixedWidth(1); outer.addWidget(sep)

        # ---- right: stacked pages
        self.pages = QtWidgets.QStackedWidget(); outer.addWidget(self.pages, 1)
        self.page_agenda = self._page_scroll(); self.pages.addWidget(self.page_agenda[0])
        self.page_week = QtWidgets.QWidget(); wl = QtWidgets.QVBoxLayout(self.page_week); wl.setContentsMargins(24, 18, 24, 12)
        wnav = QtWidgets.QHBoxLayout()
        self.w_prev = QtWidgets.QLabel("‹"); self.w_next = QtWidgets.QLabel("›"); self.w_title = QtWidgets.QLabel(); self.w_title.setObjectName("dim"); self.w_today = QtWidgets.QLabel("today")
        for l in (self.w_prev, self.w_next, self.w_today): l.setCursor(QtCore.Qt.PointingHandCursor)
        wnav.addWidget(self.w_prev); wnav.addWidget(self.w_title, 1, QtCore.Qt.AlignLeft); wnav.addWidget(self.w_today); wnav.addWidget(self.w_next)
        wl.addLayout(wnav)
        self.week_head = WeekHead(); self.week_head.event_clicked.connect(self.show_event); self.week_head.day_clicked.connect(self.show_day_grid); wl.addWidget(self.week_head)
        self.week = WeekGrid(); self.week.event_clicked.connect(self.show_event); self.week.slot_clicked.connect(self.new_at)
        wscroll = QtWidgets.QScrollArea(); wscroll.setWidgetResizable(True); wscroll.setFrameShape(QtWidgets.QFrame.NoFrame); wscroll.setWidget(self.week)
        self.week_scroll = wscroll; wl.addWidget(wscroll, 1)
        self.pages.addWidget(self.page_week)
        self.page_event = self._page_scroll(); self.pages.addWidget(self.page_event[0])
        self.page_edit = self._page_scroll(); self.pages.addWidget(self.page_edit[0])

        self.m_prev.mousePressEvent = lambda e: self.move_month(-1)
        self.m_next.mousePressEvent = lambda e: self.move_month(1)
        self.m_title.mousePressEvent = lambda e: self.go_today()
        self.grid.day_clicked.connect(self.show_day)
        self.w_prev.mousePressEvent = lambda e: self.step_grid(-1)
        self.w_next.mousePressEvent = lambda e: self.step_grid(1)
        self.w_today.mousePressEvent = lambda e: (self.show_week if self.week.ndays > 1 else self.show_day_grid)(date.today())

        for seq, fn in (("Ctrl+T", self.toggle_theme), ("F5", self.sync), ("Ctrl+R", self.sync), ("Ctrl+N", lambda: self.edit_event(None)),
                        ("Ctrl+=", lambda: self.zoom(1)), ("Ctrl++", lambda: self.zoom(1)), ("Ctrl+-", lambda: self.zoom(-1)),
                        ("Ctrl+,", self.setup), ("Ctrl+Q", self.close), ("Escape", self.show_agenda), ("Ctrl+W", lambda: self.show_week(date.today())), ("Ctrl+D", self.go_today), ("Ctrl+J", lambda: self.show_day_grid(date.today()))):
            QtWidgets.QShortcut(QtGui.QKeySequence(seq), self, fn)
        self.timer = QtCore.QTimer(self); self.timer.timeout.connect(self.sync); self.timer.start(SYNC_MINUTES * 60 * 1000)
        self.apply_style()
        self.refresh_month_title()
        if self.cfg.get("url"):
            self.connect_client()
        else:
            QtCore.QTimer.singleShot(0, self.setup)

    def _page_scroll(self):
        scroll = QtWidgets.QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        host = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(host); lay.setContentsMargins(28, 18, 28, 18); lay.setSpacing(2); lay.addStretch(1)
        scroll.setWidget(host)
        return scroll, lay

    @staticmethod
    def _clear(lay):
        while lay.count() > 1:
            item = lay.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            elif item.layout():
                sub = item.layout()
                while sub.count():
                    x = sub.takeAt(0)
                    if x.widget(): x.widget().deleteLater()

    # ---- look ------------------------------------------------------------------------

    def apply_style(self):
        bg, fg = ("#000000", "#ffffff") if self.dark else ("#ffffff", "#000000")
        dim = "rgba(255,255,255,0.55)" if self.dark else "rgba(0,0,0,0.55)"
        rule = "rgba(255,255,255,0.25)" if self.dark else "rgba(0,0,0,0.25)"
        s = self.font_size
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background: {bg}; color: {fg}; font-size: {s}pt; font-weight: 300; }}
            QLabel#dim {{ color: {dim}; }}
            QLabel#big {{ font-size: {s + 9}pt; }}
            QFrame#sep {{ background: {rule}; }}
            QScrollArea, QScrollArea > QWidget > QWidget {{ background: {bg}; }}
            QScrollBar:vertical {{ background: {bg}; width: 6px; }} QScrollBar::handle:vertical {{ background: {rule}; min-height: 24px; }} QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
            QMenu {{ background: {bg}; color: {fg}; border: 1px solid {rule}; }} QMenu::item:selected {{ background: {fg}; color: {bg}; }}
            QLineEdit, QPlainTextEdit {{ background: {bg}; color: {fg}; border: 1px solid {rule}; padding: 6px; }}
            QPushButton {{ background: {bg}; color: {fg}; border: 1px solid {fg}; padding: 6px 18px; }} QPushButton:default {{ background: {fg}; color: {bg}; }}
            QDialog {{ background: {bg}; }} QToolTip {{ background: {bg}; color: {fg}; border: 1px solid {rule}; }}
        """)
        self.grid.set_colors(fg, bg); self.week.set_colors(fg, bg); self.week_head.set_colors(fg, bg)
        f = QtGui.QFont(); f.setPointSize(s); f.setWeight(QtGui.QFont.Light); self.grid.setFont(f); self.week.setFont(f); self.week_head.setFont(f)
        self.render_current()

    def toggle_theme(self):
        self.dark = not self.dark; self.cfg["dark"] = self.dark; save_config(self.cfg); self.apply_style()

    def zoom(self, delta):
        self.font_size = max(9, min(24, self.font_size + delta)); self.cfg["font_size"] = self.font_size; save_config(self.cfg); self.apply_style()

    # ---- network -----------------------------------------------------------------------

    def run(self, fn, on_done):
        thread = QtCore.QThread(self); worker = Worker(fn); worker.moveToThread(thread)
        thread.started.connect(worker.run); worker.done.connect(on_done); worker.failed.connect(self.show_error)
        worker.done.connect(thread.quit); worker.failed.connect(thread.quit)
        pair = (thread, worker); thread.finished.connect(lambda: self.threads.remove(pair) if pair in self.threads else None)
        self.threads.append(pair); thread.start()

    def show_error(self, text):
        self.status.setText(text)

    def setup(self):
        dlg = QtWidgets.QDialog(self); dlg.setWindowTitle("reader's calendar")
        form = QtWidgets.QFormLayout(dlg); form.setSpacing(12)
        intro = QtWidgets.QLabel("CalDAV calendars. Infomaniak: https://sync.infomaniak.com, username like AB12345,\nan application password if two-factor authentication is on. Nextcloud, Radicale… work too.")
        intro.setObjectName("dim"); form.addRow(intro)
        url = QtWidgets.QLineEdit(self.cfg.get("url", "")); user = QtWidgets.QLineEdit(self.cfg.get("username", "")); pw = QtWidgets.QLineEdit(self.cfg.get("password", "")); pw.setEchoMode(QtWidgets.QLineEdit.Password)
        form.addRow("server", url); form.addRow("username", user); form.addRow("app password", pw)
        btns = QtWidgets.QHBoxLayout(); btns.addStretch(1)
        c = QtWidgets.QPushButton("cancel"); c.clicked.connect(dlg.reject); btns.addWidget(c)
        ok = QtWidgets.QPushButton("connect"); ok.setDefault(True); ok.clicked.connect(dlg.accept); btns.addWidget(ok)
        form.addRow(btns); dlg.resize(560, 260)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            if not self.cfg.get("url"): self.status.setText("not connected — Ctrl+, to set up")
            return
        self.cfg.update({"url": url.text().strip(), "username": user.text().strip(), "password": pw.text()}); save_config(self.cfg)
        self.connect_client()

    def connect_client(self):
        self.client = ce.CalDAV(self.cfg["url"], self.cfg.get("username", ""), self.cfg.get("password", ""))
        self.status.setText("connecting…")
        self.run(self.client.calendars, self.got_calendars)

    def got_calendars(self, cals):
        self.calendars = cals
        self._clear_calbox()
        hidden = set(self.cfg.get("hidden_calendars", []))
        for name, url, writable in cals:
            lab = QtWidgets.QLabel(("" if url in hidden else "■ ") + name + ("" if writable else "  (read only)"))
            lab.setObjectName("dim" if url in hidden else ""); lab.setCursor(QtCore.Qt.PointingHandCursor)
            lab.mousePressEvent = lambda e, u=url: self.toggle_calendar(u)
            self.cal_box.addWidget(lab)
        self.sync()

    def _clear_calbox(self):
        while self.cal_box.count():
            item = self.cal_box.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def toggle_calendar(self, url):
        hidden = set(self.cfg.get("hidden_calendars", []))
        hidden ^= {url}
        if len(hidden) >= len(self.calendars):
            return
        self.cfg["hidden_calendars"] = sorted(hidden); save_config(self.cfg)
        self.got_calendars(self.calendars)

    def window(self):
        start = datetime.combine(date.today() - timedelta(days=45), datetime.min.time(), LOCAL)
        return start, start + timedelta(days=45 + self.window_days)

    def sync(self):
        if not self.client or not self.calendars:
            return
        self.status.setText("syncing…")
        hidden = set(self.cfg.get("hidden_calendars", []))
        ws, we = self.window()
        cals = [(n, u) for n, u, _ in self.calendars if u not in hidden]

        def fetch():
            out = []
            for name, url in cals:
                for ev in self.client.events(url, ws, we):
                    ev.cal_url = url
                    for s, e in ev.occurrences(ws, we):
                        out.append(Occ(ev, name, s, e))
            out.sort(key=lambda o: (o.start, not o.event.all_day))
            return out
        self.run(fetch, self.got_events)

    def got_events(self, occs):
        self.occs = occs
        self.grid.marked = {o.date for o in occs}; self.grid.update()
        self.status.setText(f"synced {datetime.now().strftime('%H:%M')}")
        self.render_current()

    # ---- pages -------------------------------------------------------------------------

    def render_current(self):
        idx = self.pages.currentIndex()
        if idx == 0: self.render_agenda()
        elif idx == 1: self.render_week()
        elif idx == 2 and getattr(self, "_event", None): self.show_event(self._event, refresh=True)

    def refresh_month_title(self):
        self.m_title.setText(self.grid.month.strftime("%B %Y").lower())

    def move_month(self, delta):
        m = self.grid.month; y, mo = m.year, m.month + delta
        if mo == 0: y, mo = y - 1, 12
        if mo == 13: y, mo = y + 1, 1
        self.grid.set_month(date(y, mo, 1)); self.refresh_month_title()

    def go_today(self):
        self.grid.set_month(date.today()); self.refresh_month_title(); self.show_agenda()

    def show_agenda(self, from_date=None):
        self.pages.setCurrentIndex(0); self._agenda_from = from_date or date.today(); self.render_agenda()

    def show_day(self, d):
        self.grid.selected = d; self.grid.update(); self.show_agenda(d)

    def render_agenda(self):
        scroll, lay = self.page_agenda
        self._clear(lay)
        today = date.today(); start = getattr(self, "_agenda_from", today)
        occs = [o for o in self.occs if o.end > datetime.combine(start, datetime.min.time(), LOCAL)]
        i = 0
        if not occs:
            lay.insertWidget(i, row("nothing planned", obj="dim")); i += 1
        cur = None
        for o in occs:
            d = o.date if o.date >= start else start
            if d != cur:
                cur = d
                h = QtWidgets.QLabel(day_label(d, today)); h.setObjectName("" if d == today else "dim")
                h.setContentsMargins(0, 14, 0, 0); h.setCursor(QtCore.Qt.PointingHandCursor); h.mousePressEvent = lambda e, dd=d: self.show_day_grid(dd)
                lay.insertWidget(i, h); i += 1
            sec = o.when() + (" · " + o.event.location if o.event.location else "")
            lay.insertWidget(i, row(o.event.summary, sec, size=self.font_size + 4, click=lambda oo=o: self.show_event(oo))); i += 1
        more = row("show more days", obj="dim", click=self.more_days); lay.insertWidget(i, more)

    def more_days(self):
        self.window_days += 60; self.sync()

    def show_week(self, d):
        first = 0 if self.cfg.get("week_monday", True) else 6
        start = d - timedelta(days=(d.weekday() - first) % 7)
        self.week.start = start; self.week.ndays = 7; self.week_head.ndays = 7
        self.w_title.setText(start.strftime("%-d %b") + " – " + (start + timedelta(days=6)).strftime("%-d %b %Y").lower())
        self._open_grid()

    def show_day_grid(self, d):
        """One day as a time grid: the same page, one column wide."""
        self.week.start = d; self.week.ndays = 1; self.week_head.ndays = 1
        self.w_title.setText(day_label(d, date.today()))
        self._open_grid()

    def step_grid(self, delta):
        n = self.week.ndays
        (self.show_week if n > 1 else self.show_day_grid)(self.week.start + timedelta(days=n * delta))

    def _open_grid(self):
        self.pages.setCurrentIndex(1); self.render_week()
        # open an hour before the first thing shown (or now, if today is shown); 08:00 when empty
        days = [self.week.start + timedelta(days=i) for i in range(self.week.ndays)]
        firsts = [o.start.hour for o in self.week.occs if not o.event.all_day and o.start.date() in days]
        if date.today() in days: firsts.append(datetime.now().hour)
        target = max(0, min(18, (min(firsts) if firsts else 8) - 1))
        QtCore.QTimer.singleShot(0, lambda: self.week_scroll.verticalScrollBar().setValue(int(WeekGrid.HOUR * target)))

    def new_at(self, d, hour):
        self.edit_event(None)
        st = self._edit_state
        st["start"] = datetime.combine(d, datetime.min.time(), LOCAL).replace(hour=hour); st["end"] = st["start"] + timedelta(hours=1)
        self.render_edit()

    def render_week(self):
        s = self.week.start; e = s + timedelta(days=self.week.ndays)
        self.week.occs = [o for o in self.occs if o.start.date() < e and o.end.date() >= s]
        self.week_head.set_data(s, self.week.ndays, self.week.occs)
        self.week.update()

    def show_event(self, o, refresh=False):
        self._event = o
        scroll, lay = self.page_event
        self._clear(lay)
        ev = o.event
        two = QtWidgets.QHBoxLayout(); left = QtWidgets.QVBoxLayout(); right = QtWidgets.QVBoxLayout()
        title = QtWidgets.QLabel(ev.summary); title.setObjectName("big"); title.setWordWrap(True); left.addWidget(title)
        if o.start.date() == (o.end - timedelta(seconds=1)).date():
            when = o.start.strftime("%A %-d %B %Y").lower()
        else:
            when = o.start.strftime("%-d %b").lower() + " – " + (o.end - timedelta(seconds=1)).strftime("%-d %b %Y").lower()
        left.addSpacing(10); left.addWidget(QtWidgets.QLabel(when)); left.addWidget(QtWidgets.QLabel(o.when()))
        if ev.rrule:
            r = QtWidgets.QLabel(dict(REPEATS).get(ev.rrule, "repeats")); r.setObjectName("dim"); left.addWidget(r)
        if ev.reminder is not None:
            r = QtWidgets.QLabel(reminder_label(ev.reminder)); r.setObjectName("dim"); left.addWidget(r)
        # the calendar it belongs to: a quiet line of text, never a colour
        c = QtWidgets.QLabel(o.cal_name); c.setObjectName("dim"); c.setContentsMargins(0, 12, 0, 0); left.addWidget(c)
        left.addStretch(1)
        if ev.location:
            l = QtWidgets.QLabel(ev.location); l.setWordWrap(True); right.addWidget(l)
            sep = QtWidgets.QFrame(); sep.setObjectName("sep"); sep.setFixedHeight(1); right.addWidget(sep)
        if ev.description:
            d = QtWidgets.QLabel(ev.description); d.setWordWrap(True); right.addWidget(d)
        if not ev.location and not ev.description:
            d = QtWidgets.QLabel("—"); d.setObjectName("dim"); right.addWidget(d)
        right.addStretch(1)
        two.addLayout(left, 45); two.addSpacing(24); two.addLayout(right, 55)
        lay.insertLayout(0, two)
        actions = QtWidgets.QHBoxLayout(); actions.setSpacing(28); actions.setContentsMargins(0, 18, 0, 0)
        for text, fn in (("← back", self.show_agenda), ("edit", lambda: self.edit_event(o)), ("delete", lambda: self.delete_event(o))):
            l = QtWidgets.QLabel(text); l.setCursor(QtCore.Qt.PointingHandCursor); l.mousePressEvent = lambda e, f=fn: f(); actions.addWidget(l)
        actions.addStretch(1)
        lay.insertLayout(1, actions)
        self.pages.setCurrentIndex(2)

    def delete_event(self, o):
        m = QtWidgets.QMenu(self)
        m.addAction("delete" + (" the whole series" if o.event.rrule else ""), lambda: self._do_delete(o))
        m.exec_(QtGui.QCursor.pos())

    def _do_delete(self, o):
        self.status.setText("deleting…")
        self.run(lambda: self.client.delete(o.event.href), lambda _: (self.show_agenda(), self.sync()))

    # ---- edit --------------------------------------------------------------------------

    def edit_event(self, o):
        writable = [(n, u) for n, u, w in self.calendars if w]
        if not writable:
            self.status.setText("no writable calendar"); return
        ev = o.event if o else None
        now = datetime.now(LOCAL).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        state = {
            "uid": ev.uid if ev else None, "href": ev.href if ev else None, "etag": ev.etag if ev else None,
            "summary": ev.summary if ev else "", "all_day": ev.all_day if ev else False,
            "start": (ev.start if isinstance(ev.start, datetime) else datetime.combine(ev.start, datetime.min.time(), LOCAL)) if ev else now,
            "end": (ev.end - (timedelta(days=1) if ev.all_day else timedelta(0)) if isinstance(ev.end, datetime) else datetime.combine(ev.end - timedelta(days=1), datetime.min.time(), LOCAL)) if ev else now + timedelta(hours=1),
            "location": ev.location if ev else "", "description": ev.description if ev else "",
            "reminder": ev.reminder if ev else self.cfg.get("default_reminder", 10), "rrule": ev.rrule if ev else "",
            "cal": getattr(ev, "cal_url", None) if ev else (self.cfg.get("default_calendar") or writable[0][1]),
        }
        if state["cal"] not in [u for _, u in writable]:
            state["cal"] = writable[0][1]
        self._edit_state = state
        self.render_edit()
        self.pages.setCurrentIndex(3)
        if not ev:
            QtCore.QTimer.singleShot(0, lambda: self._prompt("summary", "title"))

    def render_edit(self):
        st = self._edit_state
        scroll, lay = self.page_edit
        self._clear(lay)
        i = 0
        def add(w):
            nonlocal i
            lay.insertWidget(i, w); i += 1
        add(row(st["summary"] or "title", size=self.font_size + 6, click=lambda: self._prompt("summary", "title")))
        two = QtWidgets.QHBoxLayout(); left = QtWidgets.QVBoxLayout(); right = QtWidgets.QVBoxLayout()
        left.addWidget(row("all day: " + ("on" if st["all_day"] else "off"), click=lambda: self._set("all_day", not st["all_day"])))
        left.addWidget(row(st["start"].strftime("%A %-d %B %Y").lower(), "starts", click=lambda: self._pick_date("start")))
        if not st["all_day"]:
            left.addWidget(row(fmt_time(st["start"]), "start time", click=lambda: self._pick_time("start")))
        left.addWidget(row(st["end"].strftime("%A %-d %B %Y").lower(), "ends", click=lambda: self._pick_date("end")))
        if not st["all_day"]:
            left.addWidget(row(fmt_time(st["end"]), "end time", click=lambda: self._pick_time("end")))
        left.addStretch(1)
        cal_name = next((n for n, u, _ in self.calendars if u == st["cal"]), "…")
        right.addWidget(row(cal_name, "calendar", click=self._pick_calendar))
        right.addWidget(row(reminder_label(st["reminder"]), "reminder", click=self._pick_reminder))
        right.addWidget(row(dict(REPEATS).get(st["rrule"], "repeats (custom rule)"), "repeat", click=self._pick_repeat))
        right.addWidget(row(st["location"] or "location", "location" if st["location"] else None, click=lambda: self._prompt("location", "location")))
        right.addWidget(row((st["description"][:80] + "…") if len(st["description"]) > 80 else (st["description"] or "description"), "description" if st["description"] else None, click=lambda: self._prompt("description", "description", True)))
        right.addStretch(1)
        two.addLayout(left, 1); two.addSpacing(24); two.addLayout(right, 1)
        lay.insertLayout(i, two); i += 1
        actions = QtWidgets.QHBoxLayout(); actions.setSpacing(28); actions.setContentsMargins(0, 18, 0, 0)
        for text, fn in (("cancel", self.show_agenda), ("save", self.save_event)):
            l = QtWidgets.QLabel(text); l.setCursor(QtCore.Qt.PointingHandCursor); l.mousePressEvent = lambda e, f=fn: f(); actions.addWidget(l)
        actions.addStretch(1)
        lay.insertLayout(i, actions)

    def _set(self, key, value):
        self._edit_state[key] = value; self.render_edit()

    def _prompt(self, key, title, multiline=False):
        dlg = TextPrompt(title, self._edit_state[key], multiline, self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self._set(key, dlg.value().strip())

    def _pick_date(self, key):
        fg, bg = ("#ffffff", "#000000") if self.dark else ("#000000", "#ffffff")
        dlg = DatePick(self._edit_state[key].date(), fg, bg, self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            st = self._edit_state; old = st[key]; new = datetime.combine(dlg.value, old.time(), LOCAL)
            if key == "start":
                st["end"] = st["end"] + (new - old)
            st[key] = new; self.render_edit()

    def _pick_time(self, key):
        dlg = TextPrompt(("start" if key == "start" else "end") + " time (hh:mm)", fmt_time(self._edit_state[key]), False, self)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        import re
        m = re.match(r"^\s*(\d{1,2})\s*[:hH.]?\s*(\d{2})?\s*$", dlg.value())
        if not m:
            return
        h, mi = int(m.group(1)), int(m.group(2) or 0)
        if not (0 <= h <= 23 and 0 <= mi <= 59):
            return
        st = self._edit_state; old = st[key]; new = old.replace(hour=h, minute=mi)
        if key == "start":
            st["end"] = st["end"] + (new - old)
        st[key] = new; self.render_edit()

    def _menu_pick(self, options):
        m = QtWidgets.QMenu(self); chosen = []
        for label, value in options:
            m.addAction(label, lambda v=value: chosen.append(v))
        m.exec_(QtGui.QCursor.pos())
        return chosen[0] if chosen else None

    def _pick_calendar(self):
        v = self._menu_pick([(n, u) for n, u, w in self.calendars if w])
        if v is not None: self._set("cal", v)

    def _pick_reminder(self):
        v = self._menu_pick([(reminder_label(m), ("none" if m is None else m)) for m in REMINDERS])
        if v is not None: self._set("reminder", None if v == "none" else v)

    def _pick_repeat(self):
        v = self._menu_pick([(label, rule) for rule, label in REPEATS])
        if v is not None: self._set("rrule", v)

    def save_event(self):
        st = self._edit_state
        if not st["summary"]:
            self._prompt("summary", "title"); return
        if st["all_day"]:
            start, end = st["start"].date(), st["end"].date()
            if end < start: self.status.setText("the end is before the start"); return
        else:
            start, end = st["start"], st["end"]
            if end <= start: self.status.setText("the end is before the start"); return
        keep = []
        if st["href"]:
            src = next((o.event for o in self.occs if o.event.href == st["href"]), None)
            if src:
                keep = [l for l in src.lines if l.split(":", 1)[0].split(";", 1)[0].upper() in ("EXDATE", "CREATED", "SEQUENCE", "CLASS", "STATUS", "TRANSP", "CATEGORIES")]
        kw = dict(summary=st["summary"], start=start, end=end, all_day=st["all_day"], location=st["location"], description=st["description"], rrule=st["rrule"], reminder=st["reminder"], keep_lines=keep)
        self.status.setText("saving…")
        if st["href"]:
            fn = lambda: self.client.put(st["href"], ce.build_ics(st["uid"], **kw), etag=st["etag"])
        else:
            fn = lambda: self.client.create(st["cal"], **kw)
        self.run(fn, lambda _: (self.show_agenda(), self.sync()))


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("reader's calendar")
    app.setDesktopFileName(APP)
    w = Main(); w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
