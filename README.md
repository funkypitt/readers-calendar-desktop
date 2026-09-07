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
sudo apt install ./readers-calendar_1.0.0_all.deb
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

Click a calendar name at the bottom of the left column to hide or show it.

## Use

| Where | Effect |
|---|---|
| a day in the month grid | agenda from that day |
| ‹ › around the month, click the month name | previous, next, back to today |
| a day heading in the agenda | that week as a time grid |
| an event | its page: date, time, reminder, calendar, place and notes in two columns |
| edit | title, all day, dates (a month grid), times (typed), calendar, reminder, repeat, place, notes |
| + new event | the same page, asking for the title first |

| Key | Effect |
|---|---|
| Ctrl+N | new event |
| Ctrl+W | this week · Ctrl+D today · Escape agenda |
| F5 | sync now (also every 5 minutes) |
| Ctrl+T | white on black / black on white |
| Ctrl+= / Ctrl+- | text size |
| Ctrl+, | account |

## What it does not do

Meeting invitations, attendees, time zones other than yours, and colours. Recurring events
are edited and deleted as a whole series.

## Licence

MIT.
