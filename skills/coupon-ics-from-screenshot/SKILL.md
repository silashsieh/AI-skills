---
name: coupon-ics-from-screenshot
description: Create Apple Calendar-compatible .ics files from coupon screenshots or coupon lists. Use when the user provides coupons, vouchers, tickets, rewards, or expiry screenshots and wants calendar events using due dates, all-day events, titles like <coupon>-<source>-<YYYY/MM/DD>, duplicate coupon handling, and no alerts unless explicitly requested.
---

# Coupon ICS from Screenshot

## Workflow

1. Extract each visible coupon from the screenshot or text.
2. For each coupon, capture:
   - coupon name exactly enough to identify the item
   - source app or source label, such as `國泰優惠`
   - due date, normalized to `YYYY/MM/DD`
3. Treat each visible coupon card as one event. If two cards have the same item and date, keep both unless the user asks to deduplicate.
4. Create an `.ics` file in the current workspace unless the user gives another path.
5. Make every coupon expiry an all-day event on the due date.
6. Do not add alerts, alarms, reminders, or `VALARM` blocks unless the user explicitly asks for them.
7. Verify the file before responding.

## Event Rules

Use this event title format:

```text
<coupon>-<source>-<YYYY/MM/DD>
```

Example:

```text
麥香紅茶-國泰優惠-2026/08/08
```

Use iCalendar all-day date fields only:

```ics
DTSTART;VALUE=DATE:20260930
DTEND;VALUE=DATE:20261001
```

`DTEND` must be the day after `DTSTART`, because iCalendar end dates are exclusive.

Do not use timed UTC fields for all-day coupon expiries:

```ics
DTSTART:20260930T010000Z
DTEND:20260930T020000Z
```

Timed UTC fields can appear in Apple Calendar as 9:00-10:00 in Taiwan and cause duplicate-looking timed events.

## ICS Template

Use this structure:

```ics
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Codex//Coupon Due Dates//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Coupon Due Dates
BEGIN:VEVENT
UID:<unique-stable-id>@local
DTSTAMP:<current-utc-timestamp>
DTSTART;VALUE=DATE:<YYYYMMDD>
DTEND;VALUE=DATE:<next-day-YYYYMMDD>
SUMMARY:<coupon>-<source>-<YYYY/MM/DD>
DESCRIPTION:來源:<source>\n到期日:<YYYY/MM/DD>
STATUS:CONFIRMED
TRANSP:TRANSPARENT
END:VEVENT
END:VCALENDAR
```

Generate a unique `UID` for every event, including duplicate coupons. Use stable, readable IDs such as:

```text
coupon-cathay-7eleven-wheat-black-tea-20260930-1@local
coupon-cathay-7eleven-wheat-black-tea-20260930-2@local
```

## Formatting

Follow iCalendar text rules enough for Apple Calendar, Google Calendar, and Outlook compatibility:

- Escape literal newlines in descriptions as `\n`.
- Escape commas and semicolons in text if they are present.
- Fold long lines at 75 octets where practical by starting continuation lines with one space.
- Keep Chinese text as UTF-8.

## Validation

Before final response, inspect the output file and verify:

```bash
rg -n "VALARM|TRIGGER|ACTION:DISPLAY|DTSTART:|DTEND:" <file>.ics
rg -n "^(BEGIN:VEVENT|UID:|DTSTART;VALUE=DATE|DTEND;VALUE=DATE|SUMMARY|END:VEVENT)" <file>.ics
LC_ALL=C awk '{ if (length($0) > 75) print NR ":" length($0) ":" $0 }' <file>.ics
```

Expected results:

- No `VALARM`, `TRIGGER`, or `ACTION:DISPLAY` unless explicitly requested.
- No timed `DTSTART:` or `DTEND:` lines for all-day coupon expiry events.
- Every event has one `DTSTART;VALUE=DATE`, one exclusive next-day `DTEND;VALUE=DATE`, one `SUMMARY`, and one unique `UID`.

If Apple Calendar shows both an all-day event and a 9:00-10:00 timed event, explain that the timed event likely came from an older import or another `.ics` file containing UTC timed fields. Tell the user to delete the old timed events and reimport the verified all-day-only `.ics` file.
