"""The calendar of an event is picked among the calendars shown in the views; the hidden ones
unfold under "show more calendars" — and the one the event is in is always there.

QT_QPA_PLATFORM=offscreen python3 tests/test_pick.py [shot.png]"""
import os, sys, tempfile, time
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="readers-calendar-test-")   # never the real config
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from PyQt5 import QtCore, QtTest, QtWidgets
import readers_calendar as rc

U = "https://example.invalid/%s/"


class Server:
    def __init__(self, *a): pass

    def calendars(self):
        return [("archive", U % "archive", True), ("family", U % "family", True), ("holidays", U % "holidays", False),
                ("old", U % "old", True), ("personal", U % "personal", True)]

    def events(self, url, ws, we): return []


rc.ce.CalDAV = Server
rc.save_config({"url": "https://example.invalid/", "username": "u", "password": "p", "default_view": "week",
                "hidden_calendars": [U % "archive", U % "old"]})
app = QtWidgets.QApplication(sys.argv)
w = rc.Main(); w.resize(1180, 760); w.show()
end = time.time() + 6
while time.time() < end and not (w.calendars and not w.threads):
    app.processEvents(); time.sleep(0.01)


def check(what, ok):
    print(("ok   " if ok else "FAIL ") + what, flush=True)
    if not ok: check.failed = True
check.failed = False


def menu(current=None, clicks=()):
    """The lines of pick_calendar()'s menu, read again after each click of `clicks` (the menu is
    closed after the last). The offscreen platform sometimes closes a menu opened shortly after
    another one closed, before anything was done in it: such a try is done again."""
    for _try in range(8):
        for _i in range(20): app.processEvents(); time.sleep(0.01)
        got, seen, finished = menu_once(current, clicks)
        if finished: return got, seen
    raise SystemExit("the menu never stayed open")


def menu_once(current, clicks):
    seen, todo, state = [], list(clicks), {"over": False, "finished": False}

    def text(a):
        x = a.defaultWidget()
        return x.text() if isinstance(x, QtWidgets.QLabel) else x.findChildren(QtWidgets.QLabel)[0].text()

    def lines(m):
        return ["—" if a.isSeparator() else text(a) for a in m.actions() if a.isVisible()]

    def look():
        if state["over"]: return
        m = app.activePopupWidget()
        if m is None: QtCore.QTimer.singleShot(20, look); return
        seen.append(lines(m))
        if len(sys.argv) > 1 and current is None:
            shot = sys.argv[1].replace(".png", "-%d.png" % len(seen))
            if not os.path.exists(shot): app.processEvents(); m.grab().save(shot)
        if not todo: state["finished"] = True; m.close(); return
        go = todo.pop(0)
        a = next(a for a in m.actions() if a.isVisible() and not a.isSeparator() and text(a) == go)
        x = a.defaultWidget()
        if isinstance(x, rc.MoreLine):
            QtTest.QTest.mouseClick(x, QtCore.Qt.LeftButton); QtCore.QTimer.singleShot(20, look)
        else: state["finished"] = not todo; a.trigger(); m.close()

    QtCore.QTimer.singleShot(20, look)
    got = w.pick_calendar(current)
    state["over"] = True
    return got, seen, state["finished"]


more = rc._("show more calendars")
got, seen = menu()
check("the menu lists the calendars shown, then « show more calendars »", seen == [["family", "personal", "—", more]])
check("closed without a choice: nothing", got is None)
got, seen = menu(clicks=["personal"])
check("a shown calendar is picked in one click", got == U % "personal" and len(seen) == 1)
got, seen = menu(clicks=[more, "old"])
check("« show more calendars » unfolds the hidden ones under the shown, in the same menu", len(seen) == 2 and seen[1] == ["family", "personal", "archive", "old"])
check("a hidden calendar is picked there", got == U % "old")
got, seen = menu(current=U % "old")
check("the calendar the event is in is listed although hidden", seen == [["family", "personal", "old", "—", more]])
w.cfg["hidden_calendars"] = []
got, seen = menu()
check("nothing hidden: no « show more calendars »", seen == [["archive", "family", "old", "personal"]])
w.cfg["hidden_calendars"] = [U % n for n in ("archive", "family", "old", "personal")]
got, seen = menu()
check("everything hidden: all the calendars at once", seen == [["archive", "family", "old", "personal"]])
w.cfg["hidden_calendars"] = [U % "archive", U % "old"]
w.cfg.pop("default_calendar", None); w.edit_event(None)
check("a new event goes to the first calendar shown", w._edit_state["cal"] == U % "family")
sys.exit(1 if check.failed else 0)
