#!/bin/bash
# Builds readers-calendar_<version>_all.deb next to this script. Needs dpkg-deb and fakeroot.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; SRC="$HERE/.."
VERSION=$(grep -oE '^VERSION = "[^"]+"' "$SRC/readers_calendar.py" | cut -d'"' -f2)
ROOT="$HERE/deb-root"; rm -rf "$ROOT"
install -Dm755 "$SRC/readers_calendar.py" "$ROOT/usr/lib/readers-calendar/readers_calendar.py"
install -Dm644 "$SRC/caldav_events.py" "$ROOT/usr/lib/readers-calendar/caldav_events.py"
install -Dm644 "$SRC/google_calendar.py" "$ROOT/usr/lib/readers-calendar/google_calendar.py"
install -Dm755 /dev/stdin "$ROOT/usr/bin/readers-calendar" <<'SH'
#!/bin/sh
exec python3 /usr/lib/readers-calendar/readers_calendar.py "$@"
SH
install -Dm644 "$HERE/readers-calendar.desktop" "$ROOT/usr/share/applications/readers-calendar.desktop"
install -Dm644 "$HERE/readers-calendar.svg" "$ROOT/usr/share/icons/hicolor/scalable/apps/readers-calendar.svg"
install -Dm644 "$SRC/LICENSE" "$ROOT/usr/share/doc/readers-calendar/copyright"
mkdir -p "$ROOT/DEBIAN"
cat > "$ROOT/DEBIAN/control" <<CTRL
Package: readers-calendar
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.8), python3-pyqt5, python3-requests, python3-dateutil
Recommends: fonts-roboto
Maintainer: funkypitt <pierregallaz@gmail.com>
Homepage: https://github.com/funkypitt/readers-calendar-desktop
Description: Black-and-white, text-only CalDAV calendar
 A single-window desktop calendar for CalDAV servers (Infomaniak, Nextcloud,
 Radicale...). Month grid on the left, agenda or week grid on the right, an
 event page in two columns. White on black or black on white.
CTRL
fakeroot dpkg-deb --build "$ROOT" "$HERE/readers-calendar_${VERSION}_all.deb"
rm -rf "$ROOT"
echo "built $HERE/readers-calendar_${VERSION}_all.deb"
