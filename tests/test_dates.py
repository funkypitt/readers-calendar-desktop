"""Day and month names follow the interface's language even where the C library has no locale
(a Mac opened from the Finder: no LANG, so strftime said "monday" under a French interface), and
a refused certificate is not taken for an unreachable server.
QT_QPA_PLATFORM=offscreen python3 tests/test_dates.py"""
import os, sys, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
TMP = tempfile.mkdtemp(prefix="readers-calendar-test-")      # never the real config
for var in ("HOME", "XDG_CONFIG_HOME", "APPDATA"):
    os.environ[var] = TMP
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from datetime import date
import requests
import readers_calendar as rc

D = date(2026, 11, 16)                                        # a Monday
rc._c_dates_match = lambda: False                             # as on a Mac without LANG
checks = []
for lang, label, short, month in (("fr", "lundi 16 novembre", "lun", "novembre 2026"),
                                  ("de", "montag 16 november", "mo", "November 2026"),
                                  ("en", "monday 16 november", "mon", "November 2026")):
    rc._LANG, rc._DATE_LOCALE = lang, None
    checks += [(lang + " day_label", rc.day_label(D, date(2026, 1, 1)), label),
               (lang + " short day", rc.fmt_date(D, "%a").lower()[:3].rstrip("."), short),
               (lang + " month_year", rc.month_year(D).lower(), month.lower()),
               (lang + " year kept", rc.fmt_date(D, "%-d %B %Y").split()[-1], "2026")]
rc._LANG = "fr"
checks += [("ssl", rc.err_text(requests.exceptions.SSLError("x")).split(" — ")[0], "le certificat du serveur n'est pas reconnu"),
           ("unreachable", rc.err_text(requests.exceptions.ConnectionError("x")), "serveur injoignable")]
failed = [c for c in checks if c[1] != c[2]]
for name, got, want in checks:
    print(("ok  " if got == want else "FAIL") + f" {name}: {got!r}" + ("" if got == want else f" (wanted {want!r})"))
sys.exit(1 if failed else 0)
