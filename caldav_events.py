#!/usr/bin/env python3
"""CalDAV events for Reader's Calendar (desktop): discovery, VEVENT listing with recurrence
expansion, create, update, delete. Plain HTTP (requests) and python-dateutil for RRULE."""

import os
import re
import uuid
import zlib
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
from dateutil.rrule import rrulestr

NS = {"d": "DAV:", "c": "urn:ietf:params:xml:ns:caldav", "x": "http://apple.com/ns/ical/"}

# A calendar's colour as its server gives it (Google's backgroundColor, CalDAV calendar-color),
# filled while the calendars are listed; color_of() falls back on a quiet palette.
COLORS = {}
PALETTE = ["#7986cb", "#33b679", "#e67c73", "#f6bf26", "#8e24aa", "#039be5", "#f4511e", "#616161", "#0b8043", "#3f51b5"]


def color_of(url):
    c = COLORS.get(url)
    return c if c else PALETTE[zlib.crc32((url or "").encode()) % len(PALETTE)]


def _local_zone():
    """The system's time zone with its rules (Europe/Zurich), not today's fixed offset: with a fixed
    +02:00 a 09:00 event in December showed at 10:00, and times written in summer for winter
    dates were an hour off."""
    names = [os.environ.get("TZ", "").lstrip(":")]
    try:
        names.append(os.path.realpath("/etc/localtime").split("/zoneinfo/", 1)[1])
    except (IndexError, OSError):
        pass
    try:
        with open("/etc/timezone") as f:
            names.append(f.read().strip())
    except OSError:
        pass
    try:                    # Windows has neither file; Qt knows the name (Europe/Zurich) there too
        from PyQt5 import QtCore
        names.append(bytes(QtCore.QTimeZone.systemTimeZoneId()).decode())
    except Exception:
        pass
    for name in names:
        if name:
            try:
                return ZoneInfo(name)
            except Exception:
                continue
    return datetime.now().astimezone().tzinfo


LOCAL = _local_zone()


class CalDAVError(Exception):
    pass


# ------------------------------------------------------------------------------------------
# iCalendar (VEVENT)
# ------------------------------------------------------------------------------------------

def unfold(text):
    return re.sub(r"\r?\n[ \t]", "", text.replace("\r\n", "\n")).split("\n")


def fold(line):
    out, chunk = [], line.encode("utf-8")
    while len(chunk) > 72:
        cut = 72
        while cut > 0 and (chunk[cut] & 0xC0) == 0x80:
            cut -= 1
        out.append(chunk[:cut].decode("utf-8")); chunk = b" " + chunk[cut:]
    out.append(chunk.decode("utf-8"))
    return "\r\n".join(out)


def unescape(v):
    return v.replace("\\n", "\n").replace("\\N", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def escape(v):
    return v.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def utcnow():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_dt(value, params):
    """DTSTART/DTEND value → (datetime or date, all_day)."""
    value = value.strip()
    if params.get("VALUE") == "DATE" or (len(value) == 8 and value.isdigit()):
        return date(int(value[:4]), int(value[4:6]), int(value[6:8])), True
    m = re.match(r"(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})?(Z?)", value)
    if not m:
        raise ValueError(value)
    y, mo, d, h, mi, s, z = m.groups()
    naive = datetime(int(y), int(mo), int(d), int(h), int(mi), int(s or 0))
    if z:
        return naive.replace(tzinfo=timezone.utc).astimezone(LOCAL), False
    tzid = params.get("TZID")
    if tzid:
        try:
            return naive.replace(tzinfo=ZoneInfo(tzid)).astimezone(LOCAL), False
        except Exception:
            pass
    return naive.replace(tzinfo=LOCAL), False


def props_of(lines):
    """VEVENT lines → {NAME: (value, params)} for the properties we read (first occurrence)."""
    out = {}
    for l in lines:
        if ":" not in l:
            continue
        head, value = l.split(":", 1)
        parts = head.split(";")
        name = parts[0].upper()
        params = {}
        for p in parts[1:]:
            if "=" in p:
                k, v = p.split("=", 1); params[k.upper()] = v.strip('"')
        out.setdefault(name, (value, params))
    return out


class Event:
    """One VEVENT (the master), plus the occurrences it expands to."""

    def __init__(self, href, etag, ics, lines=None):
        """lines: one VEVENT of the resource (an override); without it, the resource is read whole —
        the master, and the occurrences changed one by one (RECURRENCE-ID) as events of their own."""
        self.href, self.etag, self.ics = href, etag, ics
        self.writable = True
        self.master = None; self.overrides = []; self.override_blocks = []; self.tz_blocks = []; self.recurrence_id = None
        if lines is not None:
            self.lines = lines
        else:
            all_lines = unfold(ics)
            blocks = blocks_of(all_lines, "VEVENT")
            self.tz_blocks = blocks_of(all_lines, "VTIMEZONE")
            if not blocks:
                start = next((i for i, l in enumerate(all_lines) if l.upper().startswith("BEGIN:VEVENT")), 0)
                blocks = [all_lines[start:]]
            master = next((b for b in blocks if "RECURRENCE-ID" not in props_of(top_level(b))), blocks[0])
            self.lines = master
            self.override_blocks = [b for b in blocks if b is not master and "RECURRENCE-ID" in props_of(top_level(b))]
        p = props_of(top_level(self.lines))
        self.uid = p.get("UID", ("", {}))[0]
        self.summary = unescape(p.get("SUMMARY", ("", {}))[0]) or "(untitled)"
        self.location = unescape(p.get("LOCATION", ("", {}))[0])
        self.description = unescape(p.get("DESCRIPTION", ("", {}))[0])
        self.rrule = p.get("RRULE", ("", {}))[0]
        self.start, self.all_day = parse_dt(*p["DTSTART"]) if "DTSTART" in p else (datetime.now(LOCAL), False)
        if "DTEND" in p:
            self.end, _ = parse_dt(*p["DTEND"])
        elif "DURATION" in p:
            self.end = self.start + parse_duration(p["DURATION"][0])
        else:
            self.end = self.start + (timedelta(days=1) if self.all_day else timedelta(hours=1))
        self.exdates = set()
        for l in self.lines:
            if l.upper().startswith("EXDATE"):
                head, value = l.split(":", 1)
                params = {k.upper(): v for k, v in (x.split("=", 1) for x in head.split(";")[1:] if "=" in x)}
                for v in value.split(","):
                    try:
                        d, _ = parse_dt(v, params)
                        self.exdates.add(d if isinstance(d, date) and not isinstance(d, datetime) else d.date())
                    except ValueError:
                        pass
        if "RECURRENCE-ID" in p:
            try: self.recurrence_id, _ = parse_dt(*p["RECURRENCE-ID"])
            except ValueError: pass
        self.cancelled = p.get("STATUS", ("", {}))[0].upper() == "CANCELLED"
        for block in self.override_blocks:
            try:
                ov = Event(href, etag, ics, lines=block)
            except Exception:
                continue
            ov.master = self; ov.series_rule = self.rrule; ov.rrule = ""
            self.overrides.append(ov)
            if ov.recurrence_id is not None:
                r = ov.recurrence_id
                self.exdates.add(r if not isinstance(r, datetime) else r.date())
        self.reminder = None
        for i, l in enumerate(self.lines):
            if l.upper().startswith("BEGIN:VALARM"):
                block = props_of(self.lines[i:])
                trig = block.get("TRIGGER", ("", {}))[0]
                m = re.match(r"-?P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?", trig)
                if m:
                    dd, h, mi = m.groups()
                    self.reminder = (int(dd or 0) * 1440 + int(h or 0) * 60 + int(mi or 0))
                break

    def occurrences(self, window_start, window_end):
        """(start, end) pairs inside the window, as local datetimes (all-day: midnight to midnight)."""
        dur = self.end - self.start
        if not self.rrule:
            starts = [self.start]
        else:
            base = self.start if isinstance(self.start, datetime) else datetime(self.start.year, self.start.month, self.start.day, tzinfo=LOCAL)
            rule = local_until(self.rrule.replace("\\,", ","))
            # dateutil needs an aware/naive dtstart consistent with UNTIL; strip Z-UNTIL's tz issues by parsing naive
            try:
                r = rrulestr("RRULE:" + rule, dtstart=base.replace(tzinfo=None))
                lo = window_start.replace(tzinfo=None) - dur - timedelta(days=1)
                hi = window_end.replace(tzinfo=None) + timedelta(days=1)
                found = list(r.between(lo, hi, inc=True))[:500]
            except Exception:
                found = [base.replace(tzinfo=None)]
            starts = [dt.replace(tzinfo=LOCAL) if isinstance(self.start, datetime) else dt.date() for dt in found]
        out = []
        for s in starts:
            d = s if not isinstance(s, datetime) else s.date()
            if d in self.exdates:
                continue
            e = s + dur
            s_dt = s if isinstance(s, datetime) else datetime(s.year, s.month, s.day, tzinfo=LOCAL)
            e_dt = e if isinstance(e, datetime) else datetime(e.year, e.month, e.day, tzinfo=LOCAL)
            if e_dt > window_start and s_dt < window_end:
                out.append((s_dt, e_dt))   # always datetimes; all-day ones at local midnight
        return out


def parse_feed(text, source=""):
    """All VEVENTs of an iCalendar feed (Google's secret address, any .ics). Modified instances
    (RECURRENCE-ID) become standalone events and are excluded from their master. Read-only."""
    lines = unfold(text)
    blocks, cur = [], None
    for l in lines:
        u = l.upper()
        if u.startswith("BEGIN:VEVENT"):
            cur = [l]
        elif cur is not None:
            cur.append(l)
            if u.startswith("END:VEVENT"):
                blocks.append(cur); cur = None
    events, overrides = [], {}
    for i, b in enumerate(blocks):
        try:
            ev = Event(f"{source}#{i}", None, "\r\n".join(b))
        except Exception:
            continue
        ev.writable = False
        p = props_of(b)
        if "RECURRENCE-ID" in p:
            try:
                d, _ = parse_dt(*p["RECURRENCE-ID"])
                overrides.setdefault(ev.uid, set()).add(d if not isinstance(d, datetime) else d.date())
            except ValueError:
                pass
        events.append(ev)
    for ev in events:
        if ev.rrule and ev.uid in overrides:
            ev.exdates |= overrides[ev.uid]
    return events


def fetch_feed(url, timeout=30):
    """The text of an ICS feed over HTTP(S); Google's webcal:// links are plain https."""
    u = url.strip()
    if u.lower().startswith("webcal://"):
        u = "https://" + u[9:]
    r = requests.get(u, timeout=timeout, headers={"User-Agent": "readers-calendar"})
    if r.status_code >= 400:
        raise CalDAVError(f"feed: HTTP {r.status_code}")
    r.encoding = "utf-8"
    return r.text


def blocks_of(lines, name):
    """The BEGIN:name … END:name blocks of an unfolded iCalendar, each as its list of lines."""
    out, cur = [], None
    for l in lines:
        u = l.upper()
        if u.startswith("BEGIN:" + name):
            cur = [l]
        elif cur is not None:
            cur.append(l)
            if u.startswith("END:" + name):
                out.append(cur); cur = None
    return out


def top_level(vevent):
    """A VEVENT's own lines, without what its alarms hold (a VALARM has a DESCRIPTION too)."""
    out, depth = [], 0
    for l in vevent:
        u = l.upper()
        if u.startswith("BEGIN:VALARM"): depth += 1
        elif u.startswith("END:VALARM"): depth -= 1
        elif depth == 0: out.append(l)
    return out


def local_until(rule):
    """UNTIL=…Z rewritten as local wall time: the rule is expanded from a naive local start, and
    dateutil refuses a UTC UNTIL beside it — the series then showed its first occurrence only."""
    def fix(m):
        try:
            d, _ = parse_dt(m.group(1), {})
            return "UNTIL=" + d.strftime("%Y%m%dT%H%M%S")
        except ValueError:
            return m.group(0)
    return re.sub(r"UNTIL=(\d{8}T\d{6}Z)", fix, rule, flags=re.I)


def _form(master):
    """How the master writes its DTSTART — dates of the series (RECURRENCE-ID, EXDATE) must be
    written the same way to be recognised: ("DATE",) | ("UTC",) | ("TZID", name) | ("FLOAT",)."""
    value, params = props_of(top_level(master.lines)).get("DTSTART", ("", {}))
    if master.all_day: return ("DATE",)
    if value.strip().upper().endswith("Z"): return ("UTC",)
    if params.get("TZID"):
        try: ZoneInfo(params["TZID"]); return ("TZID", params["TZID"])
        except Exception: return ("UTC",)
    return ("FLOAT",)


def _stamp(name, dt, form):
    """One date property in the master's form. dt: aware datetime (or a date for all-day)."""
    if form[0] == "DATE":
        d = dt.date() if isinstance(dt, datetime) else dt
        return f"{name};VALUE=DATE:" + d.strftime("%Y%m%d")
    if form[0] == "UTC":
        return f"{name}:" + dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if form[0] == "TZID":
        return f"{name};TZID={form[1]}:" + dt.astimezone(ZoneInfo(form[1])).strftime("%Y%m%dT%H%M%S")
    return f"{name}:" + dt.astimezone(LOCAL).strftime("%Y%m%dT%H%M%S")


def _rid_key(ev_or_dt):
    d = ev_or_dt
    return d.astimezone(timezone.utc).strftime("%Y%m%dT%H%M") if isinstance(d, datetime) else d.strftime("%Y%m%d")


def compose(master, master_lines, override_blocks):
    """The resource again: the time zones it came with, the master, the changed occurrences."""
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//readers-calendar//EN"]
    for b in master.tz_blocks: lines += b
    lines += master_lines
    for b in override_blocks: lines += b
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(l) for l in lines) + "\r\n"


def _touched(vevent):
    now = utcnow()
    out = [l for l in vevent if l.split(":", 1)[0].upper() not in ("DTSTAMP", "LAST-MODIFIED")]
    return out[:1] + [f"DTSTAMP:{now}", f"LAST-MODIFIED:{now}"] + out[1:]


def _other_overrides(master, rid):
    key = _rid_key(rid)
    return [ov.lines for ov in master.overrides if ov.recurrence_id is None or _rid_key(ov.recurrence_id) != key]


def ics_with_override(master, rid, **kw):
    """One occurrence changed (rid: its original start): written beside the master as a VEVENT of
    the same UID with a RECURRENCE-ID, replacing an earlier change of the same occurrence."""
    kw = dict(kw); kw["rrule"] = ""
    block = vevent_lines(master.uid, extra=[_stamp("RECURRENCE-ID", rid, _form(master))], **kw)
    return compose(master, master.lines, _other_overrides(master, rid) + [block])


def ics_without_occurrence(master, rid):
    """One occurrence deleted: an EXDATE on the master, and its changed copy dropped if it had one."""
    lines = _touched(master.lines)
    lines = lines[:1] + [_stamp("EXDATE", rid, _form(master))] + lines[1:]
    return compose(master, lines, _other_overrides(master, rid))


def ics_until(master, first_gone):
    """The series ended just before first_gone (the start of the first occurrence that goes):
    UNTIL replaces whatever ended it, and the changed occurrences from there on are dropped."""
    form = _form(master)
    if form[0] == "DATE":
        last = (first_gone.date() if isinstance(first_gone, datetime) else first_gone) - timedelta(days=1)
        until = last.strftime("%Y%m%d")
    elif form[0] == "FLOAT":
        until = (first_gone.astimezone(LOCAL) - timedelta(seconds=1)).strftime("%Y%m%dT%H%M%S")
    else:
        until = (first_gone.astimezone(timezone.utc) - timedelta(seconds=1)).strftime("%Y%m%dT%H%M%SZ")
    out = []
    for l in _touched(master.lines):
        if l.upper().startswith("RRULE"):
            head, value = l.split(":", 1)
            parts = [x for x in value.split(";") if x and x.split("=")[0].upper() not in ("UNTIL", "COUNT")]
            l = head + ":" + ";".join(parts + ["UNTIL=" + until])
        out.append(l)
    cut = _rid_key(first_gone)
    keep = [ov.lines for ov in master.overrides if ov.recurrence_id is not None and _rid_key(ov.recurrence_id) < cut]
    return compose(master, out, keep)


def shifted_exdates(master, delta):
    """The master's EXDATE lines for a series whose start moved by delta, in the form build_ics
    writes its DTSTART in — an EXDATE left at the old hour excludes nothing for a strict client."""
    tz = getattr(LOCAL, "key", None)
    form = ("DATE",) if master.all_day else (("TZID", tz) if tz else ("UTC",))
    out = []
    for l in top_level(master.lines):
        if not l.upper().startswith("EXDATE"): continue
        head, value = l.split(":", 1)
        params = {k.upper(): v for k, v in (x.split("=", 1) for x in head.split(";")[1:] if "=" in x)}
        for v in value.split(","):
            try:
                d, _ = parse_dt(v, params)
            except ValueError:
                continue
            out.append(_stamp("EXDATE", d + (timedelta(days=delta.days) if not isinstance(d, datetime) else delta), form))
    return out


def rule_for_the_rest(master, first_kept):
    """The master's rule for a series that starts at first_kept: a COUNT loses what came before."""
    rule = master.rrule
    m = re.search(r"COUNT=(\d+)", rule, flags=re.I)
    if not m:
        return rule
    base = master.start if isinstance(master.start, datetime) else datetime(master.start.year, master.start.month, master.start.day, tzinfo=LOCAL)
    try:
        r = rrulestr("RRULE:" + local_until(rule.replace("\\,", ",")), dtstart=base.replace(tzinfo=None))
        before = len(r.between(base.replace(tzinfo=None), first_kept.astimezone(LOCAL).replace(tzinfo=None) - timedelta(seconds=1), inc=True))
    except Exception:
        return rule
    return re.sub(r"COUNT=\d+", "COUNT=%d" % max(1, int(m.group(1)) - before), rule, flags=re.I)


def parse_duration(d):
    m = re.match(r"-?P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", d or "")
    if not m:
        return timedelta(hours=1)
    w, dd, h, mi, s = (int(x or 0) for x in m.groups())
    return timedelta(weeks=w, days=dd, hours=h, minutes=mi, seconds=s)


def build_ics(uid, summary, start, end, all_day, location="", description="", rrule="", reminder=None, keep_lines=None, overrides=None):
    """A full VCALENDAR for one VEVENT. keep_lines: extra lines of the original VEVENT to preserve.
    overrides: the VEVENT blocks of occurrences changed one by one, written back beside it."""
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//readers-calendar//EN"]
    lines += vevent_lines(uid, summary, start, end, all_day, location, description, rrule, reminder, keep_lines)
    for b in overrides or []: lines += b
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(l) for l in lines) + "\r\n"


def vevent_lines(uid, summary, start, end, all_day, location="", description="", rrule="", reminder=None, keep_lines=None, extra=None):
    now = utcnow()
    lines = ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{now}", f"LAST-MODIFIED:{now}", f"SUMMARY:{escape(summary)}"]
    lines += extra or []
    if all_day:
        lines += ["DTSTART;VALUE=DATE:" + start.strftime("%Y%m%d"), "DTEND;VALUE=DATE:" + (end + timedelta(days=1)).strftime("%Y%m%d")]
    else:
        tz = getattr(LOCAL, "key", None)
        if tz:
            lines += [f"DTSTART;TZID={tz}:" + start.strftime("%Y%m%dT%H%M%S"), f"DTEND;TZID={tz}:" + end.strftime("%Y%m%dT%H%M%S")]
        else:
            lines += ["DTSTART:" + start.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ"), "DTEND:" + end.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")]
    if location:
        lines.append("LOCATION:" + escape(location))
    if description:
        lines.append("DESCRIPTION:" + escape(description))
    if rrule:
        lines.append("RRULE:" + rrule)
    for l in keep_lines or []:
        lines.append(l)
    if reminder is not None:
        lines += ["BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:" + escape(summary), f"TRIGGER:-PT{int(reminder)}M", "END:VALARM"]
    lines.append("END:VEVENT")
    return lines


# ------------------------------------------------------------------------------------------
# CalDAV
# ------------------------------------------------------------------------------------------

class CalDAV:
    def __init__(self, url, username, password):
        self.base = url.strip()
        self.s = requests.Session()
        self.s.auth = (username, password)
        self.s.headers["User-Agent"] = "readers-calendar"

    def _req(self, method, url, body=None, depth=None, headers=None, content_type="application/xml; charset=utf-8"):
        h = {}
        if depth is not None:
            h["Depth"] = str(depth)
        if body is not None:
            h["Content-Type"] = content_type
        if headers:
            h.update(headers)
        r = self.s.request(method, url, data=body.encode("utf-8") if isinstance(body, str) else body, headers=h, timeout=30)
        if r.status_code == 401:
            raise CalDAVError("wrong username or app password")
        if r.status_code >= 400:
            raise CalDAVError(f"{method} {url}: HTTP {r.status_code}")
        return r

    def _propfind(self, url, props, depth):
        body = ('<?xml version="1.0" encoding="utf-8"?><d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav" xmlns:x="http://apple.com/ns/ical/"><d:prop>'
                + "".join(f"<{p}/>" for p in props) + "</d:prop></d:propfind>")
        return ET.fromstring(self._req("PROPFIND", url, body, depth).content)

    def _href(self, root, path, against):
        el = root.find(path, NS)
        href = el.find("d:href", NS) if el is not None else None
        return urljoin(against, href.text.strip()) if href is not None and href.text else None

    def calendars(self):
        """[(name, url, writable)] for the VEVENT collections."""
        candidates = []
        try:
            root = self._propfind(self.base, ["d:current-user-principal", "c:calendar-home-set"], 0)
            home = self._href(root, ".//c:calendar-home-set", self.base)
            principal = self._href(root, ".//d:current-user-principal", self.base)
            if not home and principal:
                home = self._href(self._propfind(principal, ["c:calendar-home-set"], 0), ".//c:calendar-home-set", principal)
            if home:
                candidates.append(home)
        except CalDAVError:
            pass
        candidates.append(self.base)
        for home in candidates:
            root = self._propfind(home, ["d:displayname", "d:resourcetype", "c:supported-calendar-component-set", "d:current-user-privilege-set", "x:calendar-color"], 1)
            out = []
            for resp in root.findall("d:response", NS):
                href = resp.find("d:href", NS)
                rtype = resp.find(".//d:resourcetype", NS)
                if href is None or rtype is None or rtype.find("c:calendar", NS) is None:
                    continue
                comps = [c.get("name", "").upper() for c in resp.findall(".//c:supported-calendar-component-set/c:comp", NS)]
                if comps and "VEVENT" not in comps:
                    continue
                name_el = resp.find(".//d:displayname", NS)
                name = (name_el.text or "").strip() if name_el is not None else ""
                privs = resp.find(".//d:current-user-privilege-set", NS)
                writable = privs is None or privs.find(".//d:write", NS) is not None or privs.find(".//d:all", NS) is not None or privs.find(".//d:write-content", NS) is not None
                url = urljoin(self.base, href.text.strip())
                color = resp.find(".//x:calendar-color", NS)
                if color is not None and color.text and color.text.strip().startswith("#") and len(color.text.strip()) >= 7:
                    COLORS[url] = color.text.strip()[:7]      # #RRGGBBAA → #RRGGBB
                out.append((name or urlparse(url).path.rstrip("/").split("/")[-1], url, writable))
            if out:
                return out
        raise CalDAVError("no calendar found at this address")

    def events(self, cal_url, window_start, window_end):
        """Events overlapping the window (masters; expand client-side with Event.occurrences)."""
        fmt = lambda dt: dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        body = ('<?xml version="1.0" encoding="utf-8"?><c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">'
                '<d:prop><d:getetag/><c:calendar-data/></d:prop><c:filter><c:comp-filter name="VCALENDAR"><c:comp-filter name="VEVENT">'
                f'<c:time-range start="{fmt(window_start)}" end="{fmt(window_end)}"/></c:comp-filter></c:comp-filter></c:filter></c:calendar-query>')
        root = ET.fromstring(self._req("REPORT", cal_url, body, 1).content)
        out = []
        for resp in root.findall("d:response", NS):
            href = resp.find("d:href", NS); etag = resp.find(".//d:getetag", NS); data = resp.find(".//c:calendar-data", NS)
            if href is None or data is None or not data.text:
                continue
            try:
                out.append(Event(urljoin(cal_url, href.text.strip()), etag.text if etag is not None else None, data.text))
            except Exception:
                continue
        return out

    def put(self, url, ics, etag=None, create=False):
        h = {"If-None-Match": "*"} if create else ({"If-Match": etag} if etag else {})
        self._req("PUT", url, ics, headers=h, content_type="text/calendar; charset=utf-8")

    def create(self, cal_url, **kw):
        uid = str(uuid.uuid4())
        self.put(urljoin(cal_url.rstrip("/") + "/", uid + ".ics"), build_ics(uid, **kw), create=True)
        return uid

    def delete(self, url):
        self._req("DELETE", url)
