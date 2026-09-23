"""Google Calendar for Reader's Calendar, read and write, through Google's own API (Calendar API v3).

The user makes an OAuth client of their own in the Google Cloud console (a "Desktop app": its
secret is not a secret, Google says so) and connects once: the browser opens on Google's consent
page and comes back to a page this program serves on 127.0.0.1 for a moment. The refresh token is
kept in the configuration file, mode 0600, and access tokens are renewed from it. Events come
already expanded (singleEvents) and are turned into the same Event objects the CalDAV side uses,
writable where the account may write. Writes follow Google's own recipe: GET the event, change
what the form changed, PUT it back with If-Match on the etag the user saw (412 = changed elsewhere).
A recurring event's occurrence is its own instance id: changing or deleting it touches that
occurrence only; the series is its recurringEventId.
"""
import base64
import re
import hashlib
import http.server
import json
import os
import secrets
import threading
import time
import urllib.parse
import webbrowser
from datetime import date, datetime, timedelta, timezone

import requests

import caldav_events as ce

AUTH_URL = os.environ.get("READERS_GOOGLE_AUTH_URL", "https://accounts.google.com/o/oauth2/v2/auth")
TOKEN_URL = os.environ.get("READERS_GOOGLE_TOKEN_URL", "https://oauth2.googleapis.com/token")
API_URL = os.environ.get("READERS_GOOGLE_API_URL", "https://www.googleapis.com/calendar/v3")
SCOPE = "https://www.googleapis.com/auth/calendar"
WRITE_SCOPES = ("https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/calendar.events")
PREFIX = "google:"   # calendar "urls" in the program: google:<calendar id>


ACCOUNT = ""          # the connected account's address (its primary calendar's id), once read


class GoogleError(Exception):
    pass


class Conflict(GoogleError):
    """The event changed on Google since it was shown (HTTP 412)."""


def _done_page(ok):
    text = "Reader's Calendar is connected. You can close this tab." if ok else "Something went wrong. Close this tab and try again."
    return ("<!doctype html><meta charset=utf-8><title>reader's calendar</title>"
            "<body style='font-family:serif;background:#fff;color:#000;padding:2em;font-size:1.3em'>" + text + "</body>").encode()


class _Catch(http.server.BaseHTTPRequestHandler):
    """The one request Google's redirect makes to 127.0.0.1: it carries the code."""
    code = None; state = None; error = None

    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if q.get("state", [None])[0] != _Catch.state:
            _Catch.error = "state mismatch"
        elif "code" in q:
            _Catch.code = q["code"][0]
        else:
            _Catch.error = q.get("error", ["no code"])[0]
        body = _done_page(_Catch.code is not None)
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def connect(client_id, client_secret, open_browser=webbrowser.open, timeout=300):
    """Run the consent flow; return the token dict to keep (refresh_token, access_token, expires_at)."""
    if not client_id:
        raise GoogleError("no client id")
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    _Catch.code = _Catch.error = None; _Catch.state = secrets.token_urlsafe(16)
    srv = http.server.HTTPServer(("127.0.0.1", 0), _Catch)
    port = srv.server_address[1]
    redirect = f"http://127.0.0.1:{port}/"
    params = {"client_id": client_id, "redirect_uri": redirect, "response_type": "code", "scope": SCOPE, "access_type": "offline",
              "prompt": "consent", "state": _Catch.state, "code_challenge": challenge, "code_challenge_method": "S256"}
    url = AUTH_URL + "?" + urllib.parse.urlencode(params)
    t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
    try:
        open_browser(url)
        deadline = time.time() + timeout
        while _Catch.code is None and _Catch.error is None and time.time() < deadline:
            time.sleep(0.2)
    finally:
        srv.shutdown(); srv.server_close()
    if _Catch.code is None:
        raise GoogleError(_Catch.error or "the browser did not come back")
    data = {"code": _Catch.code, "client_id": client_id, "redirect_uri": redirect, "grant_type": "authorization_code", "code_verifier": verifier}
    if client_secret:
        data["client_secret"] = client_secret
    r = requests.post(TOKEN_URL, data=data, timeout=30)
    if r.status_code >= 400:
        raise GoogleError(f"token: HTTP {r.status_code} {r.text[:200]}")
    tok = r.json()
    if "refresh_token" not in tok:
        raise GoogleError("Google gave no refresh token — remove the app from your Google account's connections and connect again")
    return {"refresh_token": tok["refresh_token"], "access_token": tok.get("access_token", ""), "expires_at": time.time() + int(tok.get("expires_in", 0)) - 60,
            "scope": tok.get("scope", SCOPE)}


def can_write(tokens):
    """Tokens from 1.7/1.8 were granted calendar.readonly: those calendars stay read-only until the
    account is connected again."""
    granted = (tokens or {}).get("scope", "https://www.googleapis.com/auth/calendar.readonly").split()
    return any(x in granted for x in WRITE_SCOPES)


class Google:
    """Calendars and events of one connected account. `tokens` is the dict returned by connect();
    it is updated in place when the access token is renewed, so the caller saves it."""

    def __init__(self, client_id, client_secret, tokens):
        self.client_id, self.client_secret, self.tokens = client_id, client_secret, tokens
        self.s = requests.Session()

    def _token(self):
        if self.tokens.get("access_token") and time.time() < self.tokens.get("expires_at", 0):
            return self.tokens["access_token"]
        data = {"refresh_token": self.tokens["refresh_token"], "client_id": self.client_id, "grant_type": "refresh_token"}
        if self.client_secret:
            data["client_secret"] = self.client_secret
        r = self.s.post(TOKEN_URL, data=data, timeout=30)
        if r.status_code >= 400:
            raise GoogleError(f"Google: HTTP {r.status_code} — connect the account again")
        tok = r.json()
        self.tokens["access_token"] = tok["access_token"]; self.tokens["expires_at"] = time.time() + int(tok.get("expires_in", 3600)) - 60
        return tok["access_token"]

    def _req(self, method, path, params=None, body=None, etag=None):
        h = {"Authorization": "Bearer " + self._token()}
        if etag:
            h["If-Match"] = etag
        r = self.s.request(method, API_URL + path, params=params, json=body, headers=h, timeout=30)
        if r.status_code == 412:
            raise Conflict("Google: the event changed elsewhere — shown again as it is now")
        if r.status_code >= 400:
            try:
                msg = r.json()["error"]["message"]
            except Exception:
                msg = r.text[:200]
            raise GoogleError(f"Google: HTTP {r.status_code} {msg}")
        return r.json() if r.content else {}

    def _get(self, path, **params):
        return self._req("GET", path, params=params)

    @staticmethod
    def _events_path(cal_url, event_id=""):
        path = f"/calendars/{urllib.parse.quote(cal_url[len(PREFIX):], safe='')}/events"
        return path + ("/" + urllib.parse.quote(event_id, safe="") if event_id else "")

    def calendars(self):
        """[(name, "google:<id>", writable)] — writable when the account owns or may edit the
        calendar and the connection was granted the write scope."""
        out, token = [], None
        write = can_write(self.tokens)
        while True:
            page = self._get("/users/me/calendarList", pageToken=token) if token else self._get("/users/me/calendarList")
            for c in page.get("items", []):
                if c.get("primary"):
                    global ACCOUNT
                    ACCOUNT = c["id"]
                if c.get("selected", True) or c.get("primary"):
                    if c.get("backgroundColor"):
                        ce.COLORS[PREFIX + c["id"]] = c["backgroundColor"]
                    out.append((c.get("summaryOverride") or c.get("summary") or c["id"], PREFIX + c["id"], write and c.get("accessRole") in ("owner", "writer")))
            token = page.get("nextPageToken")
            if not token:
                break
        return out

    def _defaults(self, cal_url):
        """The calendar's own reminder (minutes before, or None) — what useDefault means."""
        if cal_url not in _DEFAULTS:
            try:
                c = self._get("/users/me/calendarList/" + urllib.parse.quote(cal_url[len(PREFIX):], safe=""))
                pops = [x["minutes"] for x in c.get("defaultReminders", []) if x.get("method") == "popup"]
                _DEFAULTS[cal_url] = (min(pops) if pops else None, c.get("accessRole") in ("owner", "writer") and can_write(self.tokens))
            except GoogleError:
                _DEFAULTS[cal_url] = (None, False)
        return _DEFAULTS[cal_url]

    def events(self, cal_url, start, end):
        """Events between start and end, each occurrence its own Event (Google expands them). An
        occurrence of a series knows the series' rule, so the event page can say it repeats."""
        default_reminder, writable = self._defaults(cal_url)
        out, token, masters = [], None, {}
        params = {"singleEvents": "true", "orderBy": "startTime", "maxResults": 2500,
                  "timeMin": start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "timeMax": end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        while True:
            page = self._get(self._events_path(cal_url), **({**params, "pageToken": token} if token else params))
            for item in page.get("items", []):
                if item.get("status") == "cancelled":
                    continue
                rid = item.get("recurringEventId")
                if rid and rid not in masters:
                    try:
                        masters[rid] = self._get(self._events_path(cal_url, rid))
                    except GoogleError:
                        masters[rid] = {}
                ev = _to_event(item, cal_url, default_reminder, writable, masters.get(rid) if rid else None)
                if ev:
                    out.append(ev)
            token = page.get("nextPageToken")
            if not token:
                break
        return out

    # ---- writing -------------------------------------------------------------------------

    def create(self, cal_url, summary, start, end, all_day, location="", description="", rrule="", reminder=None, **_):
        body = {"summary": summary}
        _put_times(body, start, end, all_day)
        if location:
            body["location"] = location
        if description:
            body["description"] = description
        if rrule:
            body["recurrence"] = ["RRULE:" + rrule]
        _put_reminder(body, reminder)
        return self._req("POST", self._events_path(cal_url), body=body)

    def master(self, ev):
        """The series an occurrence belongs to, as an Event for the edit form."""
        g = ev.google
        item = self._get(self._events_path(g["cal"], g["recurring"]))
        default_reminder, writable = self._defaults(g["cal"])
        return _to_event(item, g["cal"], default_reminder, writable, None)

    def update(self, ev, summary, start, end, all_day, location="", description="", rrule="", reminder=None, **_):
        """ev: the Event the form was opened on — an occurrence, a single event, or a master from
        master(). Only what the form holds is replaced; guests, colours, meeting links… stay."""
        g = ev.google
        path = self._events_path(g["cal"], g["id"])
        body = self._get(path)
        body["summary"] = summary
        old_start = ev.start
        _put_times(body, start, end, all_day)
        for key, value in (("location", location), ("description", description)):
            if value:
                body[key] = value
            else:
                body.pop(key, None)
        if not body.get("recurringEventId"):        # an occurrence has no rule of its own
            rules = [x for x in body.get("recurrence", []) if not x.upper().startswith("RRULE:")]
            old_rule = next((x[6:] for x in body.get("recurrence", []) if x.upper().startswith("RRULE:")), "")
            if rrule and rrule != old_rule:
                body["recurrence"] = ["RRULE:" + rrule] + rules
            elif rrule:
                body["recurrence"] = [("RRULE:" + _retarget_byday(old_rule, old_start, start)) if x.upper().startswith("RRULE:") else x for x in body["recurrence"]]
            else:
                body.pop("recurrence", None)
        if reminder != ev.reminder:
            _put_reminder(body, reminder)
        return self._req("PUT", path, body=body, etag=ev.etag)

    def shift(self, ev, delta, series=False):
        """Move an occurrence (or its whole series) by delta, nothing else touched."""
        g = ev.google
        event_id = g["recurring"] if series and g.get("recurring") else g["id"]
        path = self._events_path(g["cal"], event_id)
        body = self._get(path)
        old = _read_time(body["start"])
        for key in ("start", "end"):
            t = body[key]
            if "date" in t:
                t["date"] = (date.fromisoformat(t["date"]) + timedelta(days=delta.days)).isoformat()
            else:
                t["dateTime"] = (datetime.fromisoformat(t["dateTime"].replace("Z", "+00:00")) + delta).isoformat()
        new = _read_time(body["start"])
        body["recurrence"] = [("RRULE:" + _retarget_byday(x[6:], old, new)) if x.upper().startswith("RRULE:") else x for x in body.get("recurrence", [])] or None
        if body["recurrence"] is None:
            body.pop("recurrence")
        # the etag the user saw guards the occurrence; a series is read fresh just above
        return self._req("PUT", path, body=body, etag=None if event_id != g["id"] else ev.etag)

    def move(self, ev, cal_url):
        """The event (a single one or a whole series) handed to another calendar of the account."""
        g = ev.google
        return self._req("POST", self._events_path(g["cal"], g["id"]) + "/move", params={"destination": cal_url[len(PREFIX):]})

    def delete(self, ev, series=False):
        g = ev.google
        event_id = g["recurring"] if series and g.get("recurring") else g["id"]
        return self._req("DELETE", self._events_path(g["cal"], event_id), etag=ev.etag if event_id == g["id"] else None)


_DEFAULTS = {}    # calendar url → (default reminder, writable), for the life of the program


def _put_times(body, start, end, all_day):
    """start/end as the form holds them: dates (end inclusive) or aware datetimes."""
    if all_day:
        body["start"] = {"date": start.isoformat()}
        body["end"] = {"date": (end + timedelta(days=1)).isoformat()}
    else:
        # a recurring event needs a zone name: the system's, or UTC with the times converted
        tz = getattr(ce.LOCAL, "key", None)
        if not tz:
            tz, start, end = "UTC", start.astimezone(timezone.utc), end.astimezone(timezone.utc)
        body["start"] = {"dateTime": start.isoformat(), "timeZone": tz}
        body["end"] = {"dateTime": end.isoformat(), "timeZone": tz}


def _put_reminder(body, minutes):
    body["reminders"] = {"useDefault": False, "overrides": [] if minutes is None else [{"method": "popup", "minutes": int(minutes)}]}


def _read_time(t):
    if "date" in t:
        return date.fromisoformat(t["date"])
    return datetime.fromisoformat(t["dateTime"].replace("Z", "+00:00"))


_DAYS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


def _retarget_byday(rule, old, new):
    """A weekly rule pinned to one weekday follows the event to its new weekday (Google's own UI
    does the same); anything richer is left as it is."""
    m = re.search(r"BYDAY=([A-Z]{2})(?=;|$)", rule or "")
    if not m or old is None or new is None or m.group(1) != _DAYS[old.weekday()] or old.weekday() == new.weekday():
        return rule
    return rule[:m.start(1)] + _DAYS[new.weekday()] + rule[m.end(1):]


def _to_event(item, cal_url, default_reminder=None, writable=False, master=None):
    """One Google event as the program's Event, through the ICS it would be. The rule of a series
    is kept aside (series_rule), never as RRULE: Google has already expanded the occurrences."""
    s, e = item.get("start", {}), item.get("end", {})
    if "date" in s:
        dtstart = "DTSTART;VALUE=DATE:" + s["date"].replace("-", "")
        dtend = "DTEND;VALUE=DATE:" + e.get("date", s["date"]).replace("-", "")
    elif "dateTime" in s:
        def z(v):
            d = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return d.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        dtstart = "DTSTART:" + z(s["dateTime"]); dtend = "DTEND:" + z(e.get("dateTime", s["dateTime"]))
    else:
        return None
    lines = ["BEGIN:VEVENT", "UID:" + item.get("id", ""), dtstart, dtend, "SUMMARY:" + ce.escape(item.get("summary", "") or "(untitled)")]
    if item.get("location"):
        lines.append("LOCATION:" + ce.escape(item["location"]))
    if item.get("description"):
        lines.append("DESCRIPTION:" + ce.escape(item["description"]))
    lines.append("END:VEVENT")
    ev = ce.Event(cal_url + "#" + item.get("id", ""), item.get("etag"), "\r\n".join(lines))
    ev.writable = writable
    ev.cal_url = cal_url
    rec = (master or item).get("recurrence", [])
    ev.series_rule = next((x[6:] for x in rec if x.upper().startswith("RRULE:")), "")
    ev.google = {"cal": cal_url, "id": item.get("id", ""), "recurring": item.get("recurringEventId")}
    rem = item.get("reminders", {})
    if rem.get("useDefault", True):
        ev.reminder = default_reminder
    else:
        pops = [x["minutes"] for x in rem.get("overrides", []) if x.get("method") == "popup"]
        ev.reminder = min(pops) if pops else None
    return ev
