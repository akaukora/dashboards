#!/usr/bin/env python3
"""
Fetch new Duolingo weekly-progress-report emails over IMAP and append the
extracted stats (minutes / XP / lessons) to data/weekly_duolingo.json.

Designed to run unattended (e.g. from a GitHub Actions cron job) against a
dedicated mailbox that only receives forwarded Duolingo mail. Nothing here
needs any third-party AI service -- it's stdlib Python + your own mailbox
credentials, kept as repo secrets.

Env vars required:
  IMAP_HOST      e.g. imap.gmail.com
  IMAP_USER      the mailbox address
  IMAP_PASSWORD  an app password (NOT your normal login password)

Optional:
  IMAP_FOLDER    default "INBOX"
  LOOKBACK_DAYS  how many days back to search each run (default 35 -- wide
                 enough to catch a week Actions failed to run, cheap because
                 already-seen message-ids are skipped)
"""
import email
import html as htmlmod
import imaplib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "data", "weekly_duolingo.json")
SEEN_PATH = os.path.join(HERE, "data", "seen_message_ids.json")

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
}

TD_XP_RE = re.compile(r">\s*(\d+)\s*XP\s*</td>")
LABEL_RE = re.compile(r">\s*(2 Weeks Ago|Last Week|This Week)\s*</td>")
H2_MIN_RE = re.compile(r">\s*(\d+)\s*minutes?\s*</h2>")
H2_LESS_RE = re.compile(r">\s*(\d+)\s*lessons?\s*</h2>")
FAMILY2_RE = re.compile(r"(\d[\d,]*)\s*XP.{0,40}?(\d[\d,]*)\s*minutes?.{0,40}?(\d[\d,]*)\s*lessons?", re.S)
LESSON_MIN_RE = re.compile(r"(\d[\d,]*)\s*lessons?.{0,120}?(\d[\d,]*)\s*minutes?", re.S)
DATE_RANGE_RE = re.compile(
    r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2})"
    r"\s*[-–—]\s*"
    r"((?:January|February|March|April|May|June|July|August|September|October|November|December)?\s*\d{1,2}),?\s*(\d{4})?"
)


def to_int(s):
    return int(s.replace(",", "")) if s else None


def strip_html(raw):
    plain = re.sub("<[^>]+>", " ", raw)
    plain = re.sub(r"\s+", " ", plain)
    return htmlmod.unescape(plain)


def extract_stats(raw_html):
    """Returns (xp, minutes, lessons, date_range) or (None, None, None, None)
    if this doesn't look like a weekly-report email."""
    lower = raw_html.lower()
    if "weekly report" not in lower and "weekly progress" not in lower:
        return None, None, None, None

    xp = minutes = lessons = None

    # Style A: 3-column "2 Weeks Ago / Last Week / This Week" comparison table
    xps = TD_XP_RE.findall(raw_html)
    labels = LABEL_RE.findall(raw_html)
    if xps and labels and len(xps) == len(labels) == 3 and labels[-1] == "This Week":
        xp = xps[-1]
    m = H2_MIN_RE.search(raw_html)
    if m:
        minutes = m.group(1)
    m = H2_LESS_RE.search(raw_html)
    if m:
        lessons = m.group(1)

    plain = strip_html(raw_html)

    # Style B: "<N> XP ... <N> minutes ... <N> lessons" inline (various nudge templates)
    if xp is None or minutes is None or lessons is None:
        m = FAMILY2_RE.search(plain)
        if m:
            xp2, min2, less2 = m.groups()
            xp = xp or xp2
            minutes = minutes or min2
            lessons = lessons or less2

    if minutes is None or lessons is None:
        m = LESSON_MIN_RE.search(plain)
        if m:
            less2, min2 = m.groups()
            lessons = lessons or less2
            minutes = minutes or min2

    dr = DATE_RANGE_RE.search(plain)
    date_range = f"{dr.group(1)} - {dr.group(2)} {dr.group(3) or ''}".strip() if dr else None

    return to_int(xp), to_int(minutes), to_int(lessons), date_range


def week_start_from(date_range, sent_dt):
    if date_range:
        m = re.match(r"([A-Za-z]+)\s+(\d+)\s*-\s*(?:[A-Za-z]+\s+)?(\d+)\s*(\d{4})?", date_range)
        if m:
            mon, d1, d2, yr = m.groups()
            year = int(yr) if yr else sent_dt.year
            try:
                start = datetime(year, MONTHS[mon], int(d1))
                if start > sent_dt + timedelta(days=3):
                    start = datetime(year - 1, MONTHS[mon], int(d1))
                return start.strftime("%Y-%m-%d"), (start + timedelta(days=6)).strftime("%Y-%m-%d")
            except Exception:
                pass
    start = sent_dt - timedelta(days=7)
    return start.strftime("%Y-%m-%d"), (start + timedelta(days=6)).strftime("%Y-%m-%d")


def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    host = os.environ["IMAP_HOST"]
    user = os.environ["IMAP_USER"]
    password = os.environ["IMAP_PASSWORD"]
    folder = os.environ.get("IMAP_FOLDER", "INBOX")
    lookback_days = int(os.environ.get("LOOKBACK_DAYS", "35"))

    data = load_json(DATA_PATH, [])
    seen = set(load_json(SEEN_PATH, []))
    existing_weeks = {r["week_start"] for r in data}

    since_date = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%d-%b-%Y")

    imap = imaplib.IMAP4_SSL(host)
    imap.login(user, password)
    imap.select(folder)

    status, msg_ids = imap.search(None, f'(FROM "duolingo.com" SINCE {since_date})')
    if status != "OK":
        print("IMAP search failed:", status, file=sys.stderr)
        sys.exit(1)

    new_rows = 0
    for num in msg_ids[0].split():
        status, msg_data = imap.fetch(num, "(RFC822)")
        if status != "OK":
            continue
        raw_bytes = msg_data[0][1]
        msg = email.message_from_bytes(raw_bytes)
        message_id = msg.get("Message-ID", f"num-{num.decode()}")
        if message_id in seen:
            continue
        seen.add(message_id)

        # find the html (or plain) body
        body = None
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype in ("text/html", "text/plain"):
                    try:
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    except Exception:
                        continue
                    if ctype == "text/html":
                        break
        else:
            try:
                body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
            except Exception:
                body = None
        if not body:
            continue

        xp, minutes, lessons, date_range = extract_stats(body)
        if minutes is None:
            continue  # not a full weekly stats email (or a template we don't recognize yet)
        # A few templates (e.g. "Your progress report is ready") report minutes and
        # lessons but never state an XP figure. Record the week anyway rather than
        # silently dropping it -- the dashboard fades the XP bar for these via
        # xp_missing rather than treating the week as unreported.
        xp_missing = xp is None

        date_hdr = msg.get("Date")
        try:
            sent_dt = email.utils.parsedate_to_datetime(date_hdr)
            if sent_dt.tzinfo is None:
                sent_dt = sent_dt.replace(tzinfo=timezone.utc)
        except Exception:
            sent_dt = datetime.now(timezone.utc)

        week_start, week_end = week_start_from(date_range, sent_dt.replace(tzinfo=None))
        if week_start in existing_weeks:
            continue  # already have this week (e.g. from another template variant)

        subject = str(email.header.make_header(email.header.decode_header(msg.get("Subject", ""))))

        row = {
            "week_start": week_start,
            "week_end": week_end,
            "minutes": minutes,
            "xp": xp or 0,
            "lessons": lessons or 0,
            "sent_date": sent_dt.strftime("%Y-%m-%d"),
            "subject": subject,
        }
        if xp_missing:
            row["xp_missing"] = True
        data.append(row)
        existing_weeks.add(week_start)
        new_rows += 1
        xp_note = f"{xp} XP" if not xp_missing else "XP not reported"
        print(f"Added week {week_start}: {minutes} min, {xp_note}, {lessons} lessons")

    imap.logout()

    data.sort(key=lambda r: r["week_start"])
    save_json(DATA_PATH, data)
    save_json(SEEN_PATH, sorted(seen))

    print(f"Done. {new_rows} new week(s) added. {len(data)} total weeks tracked.")
    # Signal to the workflow whether anything changed, for the commit step.
    gha_out = os.environ.get("GITHUB_OUTPUT")
    if gha_out:
        with open(gha_out, "a") as f:
            f.write(f"changed={'true' if new_rows else 'false'}\n")


if __name__ == "__main__":
    main()
