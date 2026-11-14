"""The macOS build's Info.plist completed after PyInstaller, before the signature: the version
(PyInstaller writes 0.0.0), and the oldest macOS the bundle runs on, read from its own binaries
— the highest "minos" among them — so an older Mac is told by the Finder instead of seeing the
app vanish at its first start. The app opens no documents: no document types.
usage: python packaging/macos-info.py "dist/Readers Calendar.app" 1.17.1"""
import os
import plistlib
import re
import subprocess
import sys

MACHO = {b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"}


def minos(app):
    """The highest macOS version any Mach-O file of the bundle asks for, as (major, minor)."""
    found = {}
    for root, _dirs, files in os.walk(app):
        for name in files:
            path = os.path.join(root, name)
            if os.path.islink(path):
                continue
            with open(path, "rb") as f:
                if f.read(4) not in MACHO:
                    continue
            out = subprocess.run(["otool", "-l", path], capture_output=True, text=True).stdout
            # LC_BUILD_VERSION says "minos 11.0", the older LC_VERSION_MIN_MACOSX "version 10.13"
            for cmd, value in re.findall(r"cmd (LC_BUILD_VERSION|LC_VERSION_MIN_MACOSX)\n(?:.*\n){0,3}?\s*(?:minos|version) (\d+(?:\.\d+)*)", out):
                v = tuple(int(x) for x in value.split(".")[:2])
                if v > found.get("v", (0, 0)):
                    found = {"v": v, "file": os.path.relpath(path, app)}
    return found


app, version = sys.argv[1], sys.argv[2]
path = app + "/Contents/Info.plist"
with open(path, "rb") as f:
    info = plistlib.load(f)
info["CFBundleShortVersionString"] = version
info["CFBundleVersion"] = version
low = minos(app)
if not low:
    sys.exit("no macOS version found in the bundle's binaries")
info["LSMinimumSystemVersion"] = "%d.%d" % low["v"]
with open(path, "wb") as f:
    plistlib.dump(info, f)
print("Info.plist:", version, "· macOS", info["LSMinimumSystemVersion"], "or later (asked by", low["file"] + ")")
