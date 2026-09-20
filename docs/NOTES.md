# Reader's Calendar (desktop) — notes

Reference material moved out of the README.

## Windows and macOS: first opening

**Windows** — take the `.exe` from the
[latest release](https://github.com/funkypitt/readers-calendar-desktop/releases/latest) and open it: one file,
nothing to install, no Python needed. The app is not signed by a paid certificate, so Windows
shows a blue "Windows protected your PC" panel the first time: *More info* › *Run anyway*.

**macOS** — take the `.dmg` for your Mac (`apple-silicon` for an M1 and later, `intel` for an
older one), open it and drag the app onto *Applications*. It is not signed by a paid Apple
certificate either, so the first opening must be a **right click on the app › Open** › *Open*; a
double click at that point says the app "cannot be opened" and offers nothing but the bin. Once
opened that way it starts normally ever after. If macOS still refuses, in a Terminal:
`xattr -dr com.apple.quarantine "/Applications/Readers Calendar.app"`.

## Account

The first run asks for the server, the username and a password. Infomaniak:
`https://sync.infomaniak.com`, the `AB12345` login of the Workspace, and an application
password if two-factor authentication is on. Nextcloud and Radicale take their usual
address. The password is stored in `~/.config/readers-calendar/config.json`, readable by
you only. Ctrl+, reopens the dialog.

## Google Calendar

Two roads. The simple one: in Google Calendar, a calendar's settings › Integrate calendar ›
"Secret address in iCal format", pasted in the ⚙ dialog as a feed (`name | address`); Google
refreshes that address every few hours, and the calendar is read-only.

The direct one: your own Google account, through Google's Calendar API and OAuth, **read and
write since 1.9.0**. It takes an OAuth client of your own — Google issues none for a program like
this — made once in the [Google Cloud console](https://console.cloud.google.com): new project ›
APIs & Services › enable the *Google Calendar API* › OAuth consent screen (external, yourself as a
test user) › Credentials › OAuth client ID, type *Desktop app*. Then, on the consent screen,
**Publish app**: left "in testing", Google makes the connection expire every 7 days. Published but
unverified is fine for your own use; Google shows "Google hasn't verified this app" once, pass it
with Advanced › continue. Copy the client ID and the client secret into the ⚙ dialog and press
*connect the Google account*: the browser opens Google's consent page and comes back by itself to
a page this program serves on 127.0.0.1 for a moment. The refresh token is kept in the
configuration file (mode 0600) and can be forgotten from the same dialog. The permission asked is
*calendar* (read and write).

The account's calendars then work like the CalDAV ones: create, edit, drag to move, delete. The
calendars you may only read (shared with you, holidays…) stay read-only. For an occurrence of a
repeating event the program asks, as Google Calendar does, whether to change **only this event**
or **the whole series**. Every change follows Google's own recipe — read the event, change what
the form holds, write it back guarded by its etag — so guests, colours and meeting links stay
as they were, and an event changed meanwhile on the phone is not overwritten: the program says
so and shows Google's version. Guests are not e-mailed about changes. An account connected with
1.7 or 1.8 was granted read-only access: forget it and connect again to write.

Why the Calendar API and not Google's CalDAV endpoint: both need the same OAuth client, but
Google's CalDAV has no calendar list (each calendar is addressed by its ID) and no notion of
"only this occurrence" beyond raw iCalendar exceptions, while the API lists the calendars with
your rights on each, expands repeating events on Google's side and guards every write with etags.

Other `.ics` feeds work the same way as Google's secret address.

## A new computer

The account dialog, or the settings page › *export credentials…* writes the accounts (CalDAV server and login, the feeds, and the Google connection with its OAuth client) into a JSON file. Reader's
Calendar, Tasks and Notes can all write into the same file, each in its own section. On the new
computer, *import credentials…* at the same place brings them back — or, before the first
window, `readers-calendar --import-credentials readers-credentials.json` (and `--export-credentials FILE` the
other way). The look (colours, text size, font) stays out of it.

The file holds your passwords in clear and is written readable by you only: carry it on a USB key
or in your own cloud folder, not by e-mail, and delete it once imported.

## Use

| Where | Effect |
|---|---|
| a day in the small month on the left | agenda from that day |
| "month" | the month as a board, as on the phone: each day with its events (a dot of the calendar's colour, the time when there is room, the title), all-day events as solid bars, "+n" when a day is full; click an event to open it, a day for its time grid, double-click a day for a new event there, drag an event to another day to move it |
| a day heading in the agenda, or "day" | that day as a time grid: solid blocks over the hours, overlaps side by side, the place next to the time |
| "workdays" | Monday to Friday at full width; the weekend folded into a narrow strip at the right, a dot when a day holds something; click the strip for the whole week |
| "week", or a day header in the week | the week as a time grid, one column per day; click a day header for that day |
| an empty slot in a grid | a new event at that hour |
| drag a block in a grid | move the event (by quarter hours and whole days) |
| an event | its page: title, day and time, then its calendar, repeat, reminder, place and notes. The place and the notes are live text: a mail address or a web address opens where it belongs, the place opens the map, a phone number is copied (a computer has no dialer), and everything can be selected and copied. Dates, prices and room numbers stay plain text |
| edit, + new event | one quiet column: the title typed in place, the day, the times (start then end, typed), all day or another end day, then calendar, reminder, repeat, place and notes |
| ⌕ search | events whose title, place, notes or calendar hold the words, one year back and two ahead, accents and case ignored; a repeating event once |
| the calendars in the left column | show or hide one; the column scrolls when there are many; the dot is the calendar's colour (Google's own, a CalDAV calendar's `calendar-color`, otherwise a quiet colour of its own), repeated in a corner of every event block |
| ⚙ | settings: black on white or white on black, text size, font, the view it opens on, the first day of the week, the default reminder and calendar, the accounts |

| Key | Effect |
|---|---|
| ← / → | previous / next week, day or month |
| Ctrl+N | new event · Ctrl+S or Ctrl+Enter saves it |
| Ctrl+F | search |
| Ctrl+M | this month · Ctrl+W this week · Ctrl+Shift+W workdays · Ctrl+J today as a grid · Ctrl+D today's agenda |
| Escape | back (clears the search first) |
| F5 | sync now (also every 5 minutes) |
| Ctrl+T | white on black / black on white (also in the settings) |
| Ctrl+= / Ctrl+- | text size |
| Ctrl+, | settings |

The type follows the phone's scale — rows, titles at 0.8, secondary lines at 0.62 — in a light
face: Roboto Light when `fonts-roboto` is installed (the .deb recommends it), otherwise Noto Sans
Light or the closest light sans-serif.

## What it does not do

Meeting invitations and attendees, and time zones other than yours. Recurring CalDAV events
are edited and deleted as a whole series (Google ones offer "only this event" too).

## Windows and macOS builds

The Windows and macOS binaries are built by GitHub, since neither can be built here:
`.github/workflows/desktop-builds.yml` runs PyInstaller on a Windows runner and on two macOS
runners at every `v*` tag and attaches the `.exe` and the two `.dmg` to the release of that tag.
*Actions* › *Windows and macOS builds* › *Run workflow* builds them without a tag, kept as
artifacts. The icons come from `packaging/readers-calendar.png` (`.ico` beside it, `.icns` built on the
runner).
