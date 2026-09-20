# Reader's Calendar (desktop)

A black-and-white, text-only desktop calendar for CalDAV servers: Infomaniak, Nextcloud, Radicale,
or any server that stores VEVENT. One window: the month and the navigation on the left; on the
right the agenda, the month, the week or the day as a time grid, or one event. The calendar an
event belongs to is a line of text and a small dot, never a coloured block. The desktop twin of
[Reader's Calendar for Android](https://github.com/funkypitt/readers-calendar), laid out like its
landscape mode. No account with the app, only your own server.

## Key points

- Views: agenda, month, week, workdays, day. Click a day for its time grid, an event for its page, an empty slot for a new event at that hour.
- Drag an event to move it: to another day in the month, by quarter hours and whole days in the grids.
- Ctrl+N new event, Ctrl+S saves, Ctrl+F search (title, place, notes, calendar; one year back, two ahead), ← / → previous and next, Escape back.
- Syncs every 5 minutes and on F5. Ctrl+T flips white on black / black on white; ⚙ or Ctrl+, holds the settings and the accounts.
- Account: server, username and password, asked at first run and kept in `~/.config/readers-calendar/config.json`, readable by you only. Infomaniak: `https://sync.infomaniak.com` and the `AB12345` login.
- Google Calendar: a secret iCal address as a read-only feed, or your own account, read and write, with an OAuth client you create yourself (steps in the notes). Other `.ics` feeds work too.
- A new computer: *export credentials…* writes a JSON file that Reader's Calendar, Tasks and Notes share; *import credentials…* reads it back. It holds passwords in clear: delete it once imported.
- Limits: no invitations or attendees, no time zones other than yours; a repeating CalDAV event is edited or deleted as a whole series (Google ones also offer "only this event").
- English, French, German, Spanish, Portuguese and Russian, following the system language; dates follow the locale.

More detail: [docs/NOTES.md](docs/NOTES.md).

## Install

- Debian, Ubuntu, Pop!_OS: add the [apt repository](https://funkypitt.github.io/apt-repo/), then `sudo apt install readers-calendar`. Or take the `.deb` from the [latest release](https://github.com/funkypitt/readers-calendar-desktop/releases/latest): `sudo apt install ./readers-calendar_*_all.deb`.
- Arch, Manjaro: `git clone https://github.com/funkypitt/readers-calendar-desktop && cd readers-calendar-desktop/packaging && makepkg -si`.
- Windows (`.exe`) and macOS (`.dmg`, `apple-silicon` or `intel`): from the latest release. They are unsigned: on Windows *More info* › *Run anyway*, on macOS right click on the app › *Open* the first time.
- Anywhere else: `python3 readers_calendar.py` with PyQt5, requests and python-dateutil installed.

## Build

`packaging/build-deb.sh` builds the .deb. The Windows and macOS binaries are built by GitHub Actions
at every `v*` tag.

## Crédits / Credits

© 2026 Pierre Gallaz. Développé avec [Claude Code](https://claude.com/claude-code) (Anthropic).
Licence MIT, voir `LICENSE`.

© 2026 Pierre Gallaz. Developed with [Claude Code](https://claude.com/claude-code) (Anthropic).
MIT licence, see `LICENSE`.
