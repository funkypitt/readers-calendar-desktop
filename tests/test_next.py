"""An event's page offers "next", top right: the event that follows it in the calendars shown,
read in the order of the lists — and → does the same.

Runs the real window off screen against a stand-in server:
  QT_QPA_PLATFORM=offscreen python3 tests/test_next.py [shot.png]"""
import os, sys, tempfile, time
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# never the real config: Linux reads XDG_CONFIG_HOME, macOS ~/Library under HOME, Windows APPDATA
TMP = tempfile.mkdtemp(prefix="readers-calendar-test-")
for var in ("HOME", "XDG_CONFIG_HOME", "APPDATA"):
    os.environ[var] = TMP
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from datetime import date, timedelta
from PyQt5 import QtWidgets
import caldav_events as ce
import readers_calendar as rc
rc.CONFIG_DIR = os.path.join(TMP, "readers-calendar"); rc.CONFIG_FILE = os.path.join(rc.CONFIG_DIR, "config.json")

TODAY = date.today()
D1, D2 = TODAY + timedelta(days=1), TODAY + timedelta(days=2)
FAR = TODAY + timedelta(days=75)        # beyond the 60 days read at first, within a month of the last one before
LAST = TODAY + timedelta(days=58)
A, B = "https://example.invalid/a/", "https://example.invalid/b/"


def ics(name, d, hours=None, rule=""):
    when = ("DTSTART;VALUE=DATE:%s\r\nDTEND;VALUE=DATE:%s\r\n" % (d.strftime("%Y%m%d"), (d + timedelta(days=1)).strftime("%Y%m%d")) if hours is None
            else "DTSTART:%sT%02d0000\r\nDTEND:%sT%02d0000\r\n" % (d.strftime("%Y%m%d"), hours, d.strftime("%Y%m%d"), hours + 1))
    return "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nUID:%s\r\n%s%sSUMMARY:%s\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n" % (name, when, rule, name)


EVENTS = {A: [("dentist", D1, 10, ""), ("wingo", D1, None, ""), ("lunch", D1, 12, ""), ("daily", D2, 9, "RRULE:FREQ=DAILY;COUNT=2\r\n"),
              ("last", LAST, 10, ""), ("far", FAR, 10, "")],
          B: [("other", D1, 11, "")]}


class Server:
    def __init__(self, *a): pass

    def calendars(self):
        return [("a", A, True), ("b", B, True)]

    def events(self, url, ws, we):
        out = []
        for n, d, h, r in EVENTS[url]:
            ev = ce.Event(url + n + ".ics", "e", ics(n, d, h, r))
            if ev.occurrences(ws, we): out.append(ev)
        return out


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


def occ(name, d=None):
    return next(o for o in w.occs if o.event.summary == name and (d is None or o.date == d))


def page():
    return [l.text() for l in w.pages.currentWidget().findChildren(QtWidgets.QLabel) if l.isVisibleTo(w)]


def walk(n):
    out = []
    for _ in range(n):
        out.append((w._event.event.summary, w._event.date)); w.next_event(); settle()
    return out

settle()
w.show_event(occ("wingo")); settle()
check("the page of an event offers « next »", rc._("next") in page())
check("read in the order of the lists: the whole day, then the hours, a series occurrence by occurrence",
      walk(7) == [("wingo", D1), ("dentist", D1), ("other", D1), ("lunch", D1), ("daily", D2), ("daily", D2 + timedelta(days=1)), ("last", LAST)])
check("the last event read at first leads on: the month after it was fetched", w._event.event.summary == "far")
check("after the very last one, no « next »", rc._("next") not in page())
w.next_event(); settle()
check("and → stays on it", w._event.event.summary == "far")

w.show_event(occ("dentist")); settle()
w.step(1); settle()
check("→ on an event's page goes to the next one", w._event.event.summary == "other")
w.step(-1); settle()
check("← leaves the page alone", w._event.event.summary == "other" and w.pages.currentIndex() == 2)

hidden = w._event
w.toggle_calendar(B); settle()
w.show_event(occ("dentist")); w.next_event(); settle()
check("the events of a hidden calendar are skipped", w._event.event.summary == "lunch")
w.show_event(hidden); settle(); w.next_event(); settle()
check("an event that is not in the lists stands at its own start", w._event.event.summary == "lunch")

w.show_event(occ("dentist")); settle()
w.escape(); settle()
check("back leaves the event's page for the view", w.pages.currentIndex() == 1)

if len(sys.argv) > 1:
    w.show_event(occ("dentist")); settle(); w.grab().save(sys.argv[1]); print("shot:", sys.argv[1])
print("FAILED" if check.failed else "all good")
sys.stdout.flush()
os._exit(1 if check.failed else 0)
