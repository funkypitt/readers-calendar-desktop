import sys; import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import caldav_events as ce
from datetime import datetime, timedelta, date
L=ce.LOCAL
ICS="""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VTIMEZONE
TZID:Europe/Zurich
END:VTIMEZONE
BEGIN:VEVENT
UID:abc
DTSTART;TZID=Europe/Zurich:20260907T100000
DTEND;TZID=Europe/Zurich:20260907T110000
RRULE:FREQ=WEEKLY;UNTIL=20261231T225959Z
SUMMARY:Weekly
X-CUSTOM:kept
BEGIN:VALARM
ACTION:DISPLAY
DESCRIPTION:alarm text
TRIGGER:-PT10M
END:VALARM
END:VEVENT
BEGIN:VEVENT
UID:abc
RECURRENCE-ID;TZID=Europe/Zurich:20260914T100000
DTSTART;TZID=Europe/Zurich:20260914T150000
DTEND;TZID=Europe/Zurich:20260914T160000
SUMMARY:Weekly (moved by the phone)
END:VEVENT
END:VCALENDAR
""".replace("\n","\r\n")
ev=ce.Event("h","e",ICS)
ws=datetime(2026,9,1,tzinfo=L); we=datetime(2026,10,1,tzinfo=L)
occ=ev.occurrences(ws,we)
print("master occ:",[s.strftime("%d %H:%M") for s,e in occ])
assert [s.day for s,_ in occ]==[7,21,28], "UNTIL Z must expand; the 14th is overridden"
assert ev.summary=="Weekly" and ev.description=="" , ev.description
assert len(ev.overrides)==1 and ev.overrides[0].occurrences(ws,we)[0][0].hour==15
assert ev.overrides[0].series_rule and not ev.overrides[0].rrule
# this event: override the 21st
rid=datetime(2026,9,21,10,0,tzinfo=L)
out=ce.ics_with_override(ev,rid,summary="Only once",start=rid+timedelta(hours=2),end=rid+timedelta(hours=3),all_day=False)
e2=ce.Event("h","e",out)
assert "X-CUSTOM:kept" in out and "BEGIN:VTIMEZONE" in out
assert len(e2.overrides)==2 and [s.day for s,_ in e2.occurrences(ws,we)]==[7,28]
assert "RECURRENCE-ID;TZID=Europe/Zurich:20260921T100000" in out
# override again the same occurrence: replaced, not stacked
out3=ce.ics_with_override(e2,rid,summary="Again",start=rid,end=rid+timedelta(hours=1),all_day=False)
assert len(ce.Event("h","e",out3).overrides)==2
# delete only the 14th (which had an override)
out4=ce.ics_without_occurrence(ev,datetime(2026,9,14,10,0,tzinfo=L))
e4=ce.Event("h","e",out4); assert not e4.overrides and [s.day for s,_ in e4.occurrences(ws,we)]==[7,21,28]
assert "EXDATE;TZID=Europe/Zurich:20260914T100000" in out4
# this and following from the 21st
out5=ce.ics_until(ev,rid); e5=ce.Event("h","e",out5)
assert [s.day for s,_ in e5.occurrences(ws,datetime(2027,1,1,tzinfo=L))]==[7] and len(e5.overrides)==1, out5
assert "COUNT" not in e5.rrule and "UNTIL=20260921T075959Z" in e5.rrule, e5.rrule
# COUNT
evc=ce.Event("h","e",ICS.replace("RRULE:FREQ=WEEKLY;UNTIL=20261231T225959Z","RRULE:FREQ=WEEKLY;COUNT=10"))
assert ce.rule_for_the_rest(evc,rid)=="FREQ=WEEKLY;COUNT=8", ce.rule_for_the_rest(evc,rid)
# all-day
AD="BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:d\r\nDTSTART;VALUE=DATE:20260901\r\nDTEND;VALUE=DATE:20260902\r\nRRULE:FREQ=DAILY\r\nSUMMARY:D\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
ed=ce.Event("h","e",AD)
o=ce.ics_without_occurrence(ed,datetime(2026,9,3,tzinfo=L)); assert "EXDATE;VALUE=DATE:20260903" in o
assert 3 not in [s.day for s,_ in ce.Event("h","e",o).occurrences(ws,datetime(2026,9,6,tzinfo=L))]
o=ce.ics_until(ed,datetime(2026,9,4,tzinfo=L)); assert "UNTIL=20260903" in o
assert [s.day for s,_ in ce.Event("h","e",o).occurrences(ws,we)]==[1,2,3]
# full edit keeps overrides
full=ce.build_ics("abc",summary="W",start=ev.start,end=ev.end,all_day=False,rrule=ev.rrule,overrides=[x.lines for x in ev.overrides])
assert len(ce.Event("h","e",full).overrides)==1
print("all good")
