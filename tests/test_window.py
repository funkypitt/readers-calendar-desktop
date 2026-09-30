"""The range read from the servers follows the view: a week, a day or a month far from today
is asked for when it is shown — it used to stay empty beyond 60 days, except in the month board.

Runs the real window off screen against a stand-in server that, like a real one, only returns
the events of the range asked:  QT_QPA_PLATFORM=offscreen python3 tests/test_window.py [shot.png]"""
import os, sys, tempfile, time
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="readers-calendar-test-")   # never the real config
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from datetime import date, datetime, timedelta
from PyQt5 import QtWidgets
import caldav_events as ce
import readers_calendar as rc

L = ce.LOCAL
TODAY = date.today()
FAR = TODAY + timedelta(days=104)        # beyond the 60 days read at first
FARTHER = TODAY + timedelta(days=200)
PAST = TODAY - timedelta(days=150)       # before the 45 days read at first
DAYS = {"soon": TODAY + timedelta(days=3), "far": FAR, "farther": FARTHER, "past": PAST}


def ics(name, d):
    return ("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nUID:%s\r\nDTSTART:%sT100000\r\nDTEND:%sT110000\r\n"
            "SUMMARY:%s\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n" % (name, d.strftime("%Y%m%d"), d.strftime("%Y%m%d"), name))


class Server:
    """What the window takes for the CalDAV account."""
    asked = []         # every range asked, in order
    delays = []        # seconds each coming answer waits (the first, then the second…)

    def __init__(self, *a): pass

    def calendars(self):
        return [("test", "https://example.invalid/cal/", True)]

    def events(self, url, ws, we):
        Server.asked.append((ws.date(), we.date()))
        if Server.delays: time.sleep(Server.delays.pop(0))
        return [ce.Event(url + n + ".ics", "e", ics(n, d)) for n, d in DAYS.items() if ws.date() <= d < we.date()]


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


def shown():
    return {o.event.summary for o in w.week.occs}


def check(what, ok):
    print(("ok   " if ok else "FAIL ") + what)
    if not ok: check.failed = True
check.failed = False

settle()
check("at opening, the range stops 60 days ahead", Server.asked[-1][1] == TODAY + timedelta(days=60))
check("the far event is not read yet", "far" not in {o.event.summary for o in w.occs})

w.show_week(FAR); settle()
check("a week %d days ahead shows its event" % (FAR - TODAY).days, shown() == {"far"})
n = len(Server.asked)
w.step(1); w.step(1); settle()
check("the next weeks cost no request (margin)", len(Server.asked) == n)

w.show_day_grid(FARTHER); settle()
check("a day 200 days ahead shows its event", shown() == {"farther"})

w.show_week(PAST); settle()
check("a week 150 days back shows its event", shown() == {"past"})
check("and the future stays read", {"far", "farther", "soon"} <= {o.event.summary for o in w.occs})

# a fresh window, for the left month grid and the agenda
w.close(); w = rc.Main(); w.show(); settle()
w.show_agenda(); settle()
for _ in range(12):
    if (w.grid.month.year, w.grid.month.month) == (FAR.year, FAR.month): break
    w.move_month(1)
settle()
check("the small month grid marks a day of a far month", FAR in w.grid.marked)
w.show_day(FARTHER); settle()
check("the agenda opened on a far day lists its event", any(o.event.summary == "farther" for o in w.occs))

# a slow answer to a narrow request arrives after the answer to the wider one: it must not win
w.close(); w = rc.Main(); w.show(); settle()
Server.delays = [1.0, 0.0]
w.sync(); w.show_week(FAR); settle()
check("a late answer to an older request is dropped", shown() == {"far"})

w.show_month(FAR); settle()
check("the month board shows the far event", any(o.event.summary == "far" for o in w.occs))

if len(sys.argv) > 1:
    w.show_week(FAR); settle(); w.grab().save(sys.argv[1]); print("shot:", sys.argv[1])
print("FAILED" if check.failed else "all good")
sys.stdout.flush()
os._exit(1 if check.failed else 0)
