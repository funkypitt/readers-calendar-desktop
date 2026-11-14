"""A block's lower edge, dragged in the week grid, changes the end alone: a single event, one
occurrence of a series, the whole series. The cursor says where the edge can be taken.

Runs the real window off screen against a stand-in server that keeps what is written:
QT_QPA_PLATFORM=offscreen python3 tests/test_resize.py [shot.png]"""
import os, sys, tempfile, time
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# never the real config: Linux reads XDG_CONFIG_HOME, macOS ~/Library under HOME, Windows APPDATA
TMP = tempfile.mkdtemp(prefix="readers-calendar-test-")
for var in ("HOME", "XDG_CONFIG_HOME", "APPDATA"):
    os.environ[var] = TMP
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from datetime import date, datetime, timedelta
from PyQt5 import QtCore, QtGui, QtWidgets
import caldav_events as ce
import readers_calendar as rc
rc.CONFIG_DIR = os.path.join(TMP, "readers-calendar"); rc.CONFIG_FILE = os.path.join(rc.CONFIG_DIR, "config.json")

L = ce.LOCAL
DAY = date.today() + timedelta(days=7 - date.today().weekday())     # next Monday: a whole week ahead
URL = "https://example.invalid/cal/"


def single():
    return ("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nUID:one\r\nDTSTART:%sT100000\r\nDTEND:%sT110000\r\n"
            "SUMMARY:One\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n" % (DAY.strftime("%Y%m%d"), DAY.strftime("%Y%m%d")))


def series():
    return ("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nUID:daily\r\nDTSTART:%sT140000\r\nDTEND:%sT150000\r\n"
            "RRULE:FREQ=DAILY;COUNT=5\r\nSUMMARY:Daily\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n" % (DAY.strftime("%Y%m%d"), DAY.strftime("%Y%m%d")))


class Server:
    store = {}
    written = []

    def __init__(self, *a): pass

    def calendars(self):
        return [("test", URL, True)]

    def events(self, url, ws, we):
        return [ce.Event(h, "e", text) for h, text in Server.store.items()]

    def put(self, href, ics, etag=None):
        Server.store[href] = ics; Server.written.append(("put", href, ics))

    def create(self, cal, **kw):
        Server.written.append(("create", cal, kw))


def reset():
    Server.store = {URL + "one.ics": single(), URL + "daily.ics": series()}; Server.written = []


reset()
rc.ce.CalDAV = Server
rc.save_config({"url": "https://example.invalid/", "username": "u", "password": "p", "default_view": "week"})
app = QtWidgets.QApplication(sys.argv)
w = rc.Main(); w.resize(1180, 760); w.show()


def settle(seconds=6):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents(); time.sleep(0.01)
        if not w.threads and getattr(w, "_sync_shown", 0) == getattr(w, "_sync_no", 0) and w.calendars:
            app.processEvents(); return
    raise SystemExit("the window never settled")


def check(what, ok):
    print(("ok   " if ok else "FAIL ") + what)
    if not ok: check.failed = True
check.failed = False


def mouse(kind, pos, buttons=QtCore.Qt.LeftButton):
    t = {"press": QtCore.QEvent.MouseButtonPress, "move": QtCore.QEvent.MouseMove, "release": QtCore.QEvent.MouseButtonRelease}[kind]
    b = QtCore.Qt.LeftButton if kind != "move" else QtCore.Qt.NoButton
    ev = QtGui.QMouseEvent(t, QtCore.QPointF(pos), b, buttons if kind != "release" else QtCore.Qt.NoButton, QtCore.Qt.NoModifier)
    QtWidgets.QApplication.sendEvent(w.week, ev); app.processEvents()


def box(summary, day):
    w.week.repaint(); w.week.grab()     # paint, so that the blocks' places are known
    for rect, o in w.week._boxes:
        if o.event.summary == summary and o.start.date() == day:
            return rect
    raise SystemExit("no block %s on %s" % (summary, day))


def stretch(summary, day, dy):
    r = box(summary, day)
    at = QtCore.QPointF(r.center().x(), r.bottom() - 2)
    mouse("press", at)
    for k in range(1, 5):
        mouse("move", at + QtCore.QPointF(0, dy * k / 4), QtCore.Qt.LeftButton)
    mouse("release", at + QtCore.QPointF(0, dy))


def all_occurrences(e):
    """The series' occurrences and those changed one by one, in order."""
    ws = datetime.combine(DAY, datetime.min.time(), tzinfo=L); we = ws + timedelta(days=7)
    return sorted(e.occurrences(ws, we) + [x for o in e.overrides for x in o.occurrences(ws, we)])


choice = {"text": None}
def fake_exec(menu, *a):
    for act in menu.actions():
        if act.text() == choice["text"]:
            act.trigger(); return act
    return None
QtWidgets.QMenu.exec_ = fake_exec

settle(); w.show_week(DAY); settle()
H = rc.WeekGrid.HOUR

# the cursor
r = box("One", DAY)
mouse("move", QtCore.QPointF(r.center().x(), r.bottom() - 2), QtCore.Qt.NoButton)
check("over the lower edge the cursor is the vertical arrows", w.week.cursor().shape() == QtCore.Qt.SizeVerCursor)
mouse("move", QtCore.QPointF(r.center().x(), r.center().y()), QtCore.Qt.NoButton)
check("over the middle it is the usual one", w.week.cursor().shape() != QtCore.Qt.SizeVerCursor)

# a single event, one hour longer
stretch("One", DAY, H)
settle()
e = ce.Event("x", "e", Server.store[URL + "one.ics"])
check("a single event stretched by an hour ends at 12:00", e.end.hour == 12 and e.start.hour == 10)
# then shortened by 75 minutes: 10:00 – 10:45
stretch("One", DAY, -H * 1.25)
settle()
e = ce.Event("x", "e", Server.store[URL + "one.ics"])
check("shortened, it ends at 10:45, the start in place", (e.start.hour, e.end.hour, e.end.minute) == (10, 10, 45))
# never shorter than a quarter hour
stretch("One", DAY, -H * 3)
settle()
e = ce.Event("x", "e", Server.store[URL + "one.ics"])
check("never shorter than a quarter hour", (e.end - e.start) == timedelta(minutes=15))
# a click on the edge without moving opens the event
r = box("One", DAY); mouse("press", QtCore.QPointF(r.center().x(), r.bottom() - 2)); mouse("release", QtCore.QPointF(r.center().x(), r.bottom() - 2))
check("a click on the edge opens the event", w.pages.currentIndex() == 2)
w.show_week(DAY); settle()

# one occurrence of a series: Wednesday's, half an hour shorter
choice["text"] = rc._("change the length of only this event")
stretch("Daily", DAY + timedelta(days=2), -H / 2)
settle()
e = ce.Event("x", "e", Server.store[URL + "daily.ics"])
occ = all_occurrences(e)
lengths = [(s.day, int((en - s).total_seconds() // 60)) for s, en in occ]
check("only Wednesday's occurrence lasts 30 minutes: %s" % lengths, [m for _, m in lengths] == [60, 60, 30, 60, 60])

# the whole series, half an hour longer
choice["text"] = rc._("change the length of the whole series")
stretch("Daily", DAY + timedelta(days=3), H / 2)
settle()
e = ce.Event("x", "e", Server.store[URL + "daily.ics"])
occ = all_occurrences(e)
lengths = [int((en - s).total_seconds() // 60) for s, en in occ]
check("the whole series lasts 90 minutes, the changed one kept: %s" % lengths, lengths == [90, 90, 30, 90, 90])
check("the series still starts at 14:00", all(s.hour == 14 for s, _ in occ))

# no choice: nothing written, the block goes back
choice["text"] = None; n = len(Server.written)
stretch("Daily", DAY + timedelta(days=4), H)
settle()
check("a closed menu writes nothing", len(Server.written) == n)

# moving still moves
stretch_free = box("One", DAY)
at = QtCore.QPointF(stretch_free.center().x(), stretch_free.top() + 4)
mouse("press", at); mouse("move", at + QtCore.QPointF(0, H), QtCore.Qt.LeftButton); mouse("release", at + QtCore.QPointF(0, H)); settle()
e = ce.Event("x", "e", Server.store[URL + "one.ics"])
check("a block taken in the middle still moves (11:00 – 11:15)", (e.start.hour, e.end.hour, e.end.minute) == (11, 11, 15))

if len(sys.argv) > 1:
    r = box("One", DAY); at = QtCore.QPointF(r.center().x(), r.bottom() - 2)
    mouse("press", at); mouse("move", at + QtCore.QPointF(0, H * 1.5), QtCore.Qt.LeftButton)
    w.grab().save(sys.argv[1]); print("shot:", sys.argv[1])
print("FAILED" if check.failed else "all good")
sys.stdout.flush()
os._exit(1 if check.failed else 0)
