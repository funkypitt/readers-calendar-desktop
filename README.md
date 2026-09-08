# Reader's Calendar (desktop)

A black-and-white, text-only desktop calendar for CalDAV servers: Infomaniak, Nextcloud,
Radicale, or any server that stores VEVENT. The desktop twin of
[Reader's Calendar for Android](https://github.com/funkypitt/readers-calendar), laid out
like its landscape mode.

One window. The month grid and the navigation on the left; on the right the agenda (a plain
list of the coming days), the week as a time grid, or one event in two columns. The
calendar an event belongs to is a quiet line of text, never a colour. White on black or
black on white. Nothing else.

## Install

Debian, Ubuntu, Pop!_OS:

```
sudo apt install ./readers-calendar_1.4.0_all.deb
```

Arch, Manjaro:

```
git clone https://github.com/funkypitt/readers-calendar-desktop
cd readers-calendar-desktop/packaging && makepkg -si
```

Anywhere else: `python3 readers_calendar.py` with PyQt5, requests and python-dateutil
installed.

## Account

The first run asks for the server, the username and a password. Infomaniak:
`https://sync.infomaniak.com`, the `AB12345` login of the Workspace, and an application
password if two-factor authentication is on. Nextcloud and Radicale take their usual
address. The password is stored in `~/.config/readers-calendar/config.json`, readable by
you only. Ctrl+, reopens the dialog.

## Google Calendar and other feeds

Google's CalDAV needs an OAuth client; the app takes the simpler road. In Google Calendar,
open the calendar's settings › *Integrate calendar* › *Secret address in iCal format*, and
paste that address in the account dialog under *feeds*, one per line as `name | address`.
Any `.ics` or `webcal://` address works the same way (holidays, a club's schedule). Feeds
are read-only: their events appear in the agenda, the week and the day like the others,
with "read-only" next to the calendar name on the event page. Google refreshes a secret
address every few hours. The app can run on feeds alone, with no CalDAV account.

The window opens on the week; the account dialog's *opens on* switches that to the day or the
agenda.

Click a calendar name at the bottom of the left column to hide or show it.

## Use

| Where | Effect |
|---|---|
| a day in the month grid | agenda from that day |
| ‹ › around the month, click the month name | previous, next, back to today |
| a day heading in the agenda, or "day" | that day as a time grid: solid blocks over the hours, overlaps side by side, the place next to the time |
| "week", or a day header in the week | the week as a time grid, one column per day; click a day header for that day |
| an empty slot in a grid | a new event at that hour |
| an event | its page: date, time, reminder, calendar, place and notes in two columns |
| edit | title, all day, dates (a month grid), times (typed), calendar, reminder, repeat, place, notes |
| + new event | the same page, asking for the title first |

| Key | Effect |
|---|---|
| Ctrl+N | new event |
| Ctrl+W | this week · Ctrl+J today as a grid · Ctrl+D today's agenda · Escape agenda |
| F5 | sync now (also every 5 minutes) |
| Ctrl+T | white on black / black on white |
| Ctrl+= / Ctrl+- | text size |
| Ctrl+, | account |

## Languages

English, French, German, Spanish, Portuguese and Russian, following the system language
(`LANG`). Dates follow the system locale too.

## What it does not do

Meeting invitations, attendees, time zones other than yours, and colours. Recurring events
are edited and deleted as a whole series.

## Licence

MIT.
