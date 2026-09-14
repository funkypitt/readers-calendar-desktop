"""Google Calendar for Reader's Calendar, read-only, through Google's own API.

The user makes an OAuth client of their own in the Google Cloud console (a "Desktop app": its
secret is not a secret, Google says so) and connects once: the browser opens on Google's consent
page and comes back to a page this program serves on 127.0.0.1 for a moment. The refresh token is
kept in the configuration file, mode 0600, and access tokens are renewed from it. Events come
already expanded (singleEvents) and are turned into the same Event objects the CalDAV side uses,
read-only, so the rest of the program does not know where they came from.
"""
import base64
import hashlib
import http.server
import json
import os
import secrets
import threading
import time
import urllib.parse
import webbrowser
from datetime import datetime, timezone

import requests

import caldav_events as ce

AUTH_URL = os.environ.get("READERS_GOOGLE_AUTH_URL", "https://accounts.google.com/o/oauth2/v2/auth")
TOKEN_URL = os.environ.get("READERS_GOOGLE_TOKEN_URL", "https://oauth2.googleapis.com/token")
API_URL = os.environ.get("READERS_GOOGLE_API_URL", "https://www.googleapis.com/calendar/v3")
SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
PREFIX = "google:"   # calendar "urls" in the program: google:<calendar id>


class GoogleError(Exception):
    pass


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
    return {"refresh_token": tok["refresh_token"], "access_token": tok.get("access_token", ""), "expires_at": time.time() + int(tok.get("expires_in", 0)) - 60}


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

    def _get(self, path, **params):
        r = self.s.get(API_URL + path, params=params, headers={"Authorization": "Bearer " + self._token()}, timeout=30)
        if r.status_code >= 400:
            raise GoogleError(f"Google: HTTP {r.status_code} {r.text[:200]}")
        return r.json()

    def calendars(self):
        """[(name, "google:<id>", False)] — read-only, like the feeds."""
        out, token = [], None
        while True:
            page = self._get("/users/me/calendarList", pageToken=token) if token else self._get("/users/me/calendarList")
            for c in page.get("items", []):
                if c.get("selected", True) or c.get("primary"):
                    out.append((c.get("summaryOverride") or c.get("summary") or c["id"], PREFIX + c["id"], False))
            token = page.get("nextPageToken")
            if not token:
                break
        return out

    def events(self, cal_url, start, end):
        """Events between start and end, each occurrence its own Event (Google expands them)."""
        cal_id = cal_url[len(PREFIX):]
        out, token = [], None
        params = {"singleEvents": "true", "orderBy": "startTime", "maxResults": 2500,
                  "timeMin": start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "timeMax": end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        while True:
            page = self._get(f"/calendars/{urllib.parse.quote(cal_id, safe='')}/events", **({**params, "pageToken": token} if token else params))
            for item in page.get("items", []):
                if item.get("status") == "cancelled":
                    continue
                ev = _to_event(item, cal_url)
                if ev:
                    out.append(ev)
            token = page.get("nextPageToken")
            if not token:
                break
        return out


def _to_event(item, cal_url):
    """One Google event as the program's Event, through the ICS it would be."""
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
    ev = ce.Event(cal_url + "#" + item.get("id", ""), None, "\r\n".join(lines))
    ev.writable = False
    ev.cal_url = cal_url
    return ev
