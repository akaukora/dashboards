#!/usr/bin/env python3
"""
Regenerate the static dashboard page from data/weekly_duolingo.json.

Run this after parse_duolingo.py adds new weeks (the GitHub Actions workflow
does this automatically). Writes to index.html right here in this folder, so
GitHub Pages can serve it straight from the repo root (each dashboard is its
own top-level folder, e.g. akaukora.github.io/dashboards/duolingo/).

dashboard_template.html is a bare content fragment (title/link/style, then
the page body, then a script) with no <!DOCTYPE>/<html>/<head>/<body> of its
own -- that's deliberate, since the same fragment is also pasted into an
Artifact-hosted preview that supplies its own document shell. GitHub Pages
serves this file standalone though, with nothing to wrap it, so this script
adds a real HTML5 document shell around it -- crucially including the
viewport meta tag, without which mobile browsers render it as a shrunk-down
desktop page instead of a responsive one.
"""
import json
import os
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "data", "weekly_duolingo.json")
LEAGUE_PATH = os.path.join(HERE, "data", "league_weekly.json")
TEMPLATE_PATH = os.path.join(HERE, "dashboard_template.html")
OUT_PATH = os.path.join(HERE, "index.html")

# A league week must overlap a report week by at least this many days before
# its score is used as a stand-in for that week.
MIN_OVERLAP_DAYS = 4

# How many nearby reported weeks to draw on when converting a stand-in week's
# XP into an estimate of minutes. A local window is used rather than a
# lifetime average because the XP-per-minute rate drifts a long way over time
# (roughly 7.9 in early 2025 to 13.8 by mid-2026, as Duolingo's scoring and
# his lesson mix changed). A lifetime figure would overstate minutes for the
# recent gaps by about a third.
RATIO_WINDOW_WEEKS = 12

DOC_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
"""
DOC_MID = "</head>\n<body>\n"
DOC_TAIL = "\n</body>\n</html>\n"


def _d(s):
    y, m, dd = (int(x) for x in s.split("-"))
    return date(y, m, dd)


def _overlap_days(a0, a1, b0, b1):
    lo, hi = max(a0, b0), min(a1, b1)
    return (hi - lo).days + 1 if hi >= lo else 0


def _local_xp_per_minute(target, reported):
    """Median XP-per-minute across the reported weeks nearest `target` in time.

    Deliberately local rather than lifetime: the rate climbs from roughly 7.9
    early in 2025 to 13.8 by mid-2026, so a single lifetime figure would
    overstate minutes for the recent gaps by about a third. The median (not the
    mean) keeps a single freak week from skewing the estimate -- individual
    weeks range from about 2.4 to 22.4 XP per minute.
    """
    usable = [r for r in reported
              if (r.get("minutes") or 0) > 0 and (r.get("xp") or 0) > 0 and not r.get("xp_missing")]
    if not usable:
        return None
    usable.sort(key=lambda r: abs((_d(r["week_start"]) - target).days))
    window = usable[:RATIO_WINDOW_WEEKS]
    ratios = sorted(r["xp"] / r["minutes"] for r in window)
    mid = len(ratios) // 2
    return ratios[mid] if len(ratios) % 2 else (ratios[mid - 1] + ratios[mid]) / 2


def merge_league_estimates(email_rows, league_rows):
    """Email-derived weeks are authoritative; league scores only stand in for
    weeks that have no report email at all.

    The two sources use different weekly grids -- Duolingo's league week ends
    ~3 days off from the report week -- so a league score is never mixed into
    a week that already has an email, and a stand-in week carries only XP
    (leagues say nothing about minutes or lessons). Because the fill is
    computed here at build time rather than written into the data file, a week
    reverts to real email figures the moment parse_duolingo.py picks that
    email up: nothing needs un-doing.
    """
    rows = sorted(email_rows, key=lambda r: r["week_start"])
    have = {r["week_start"] for r in rows}
    if not rows or not league_rows:
        return rows, 0

    league = [
        (_d(L["window_start"]), _d(L["window_end"]), L["xp"], L.get("competition", "leagues"))
        for L in league_rows
    ]
    last_league_end = max(w_end for _, w_end, _, _ in league)

    added = []
    week = _d(rows[0]["week_start"])
    while week <= last_league_end:
        key = week.isoformat()
        week_end = week + timedelta(days=6)
        if key not in have:
            best, best_ov = None, 0
            for l_start, l_end, xp, comp in league:
                ov = _overlap_days(week, week_end, l_start, l_end)
                if ov > best_ov:
                    best, best_ov = (l_start, l_end, xp, comp), ov
            if best and best_ov >= MIN_OVERLAP_DAYS:
                l_start, l_end, xp, comp = best
                ratio = _local_xp_per_minute(week, rows)
                row = {
                    "week_start": key,
                    "week_end": week_end.isoformat(),
                    "minutes": round(xp / ratio) if ratio else None,
                    "xp": xp,
                    "lessons": None,
                    "source": "league",
                    "estimated": True,
                    "league_window": f"{l_start.isoformat()} to {l_end.isoformat()}",
                    "competition": comp,
                }
                if ratio:
                    row["xp_per_min_used"] = round(ratio, 1)
                added.append(row)
        week += timedelta(days=7)

    merged = sorted(rows + added, key=lambda r: r["week_start"])
    return merged, len(added)


def main():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    league = []
    if os.path.exists(LEAGUE_PATH):
        with open(LEAGUE_PATH, encoding="utf-8") as f:
            league = json.load(f)

    data, n_est = merge_league_estimates(data, league)

    template = open(TEMPLATE_PATH, encoding="utf-8").read()
    filled = template.replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False))

    # Split the fragment right after the closing </style> tag: everything
    # before it (title/link/style) is genuine <head> content, everything
    # after (the page markup + the closing <script>) is <body> content.
    marker = "</style>"
    idx = filled.index(marker) + len(marker)
    head_content, body_content = filled[:idx], filled[idx:]

    out = DOC_HEAD + head_content + DOC_MID + body_content + DOC_TAIL
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"Wrote {OUT_PATH} with {len(data)} weeks "
          f"({len(data) - n_est} from emails, {n_est} XP-only from league scores).")


if __name__ == "__main__":
    main()
