> The READMEs in this repository were written by an AI assistant from Antti's instructions — see [About these READMEs](../README.md#about-these-readmes).

# HIFF 2026 planner

A schedule planner for the Helsinki International Film Festival (Rakkautta & Anarkiaa) 2026, live at `https://akaukora.github.io/dashboards/hiff2026/`.

Pick films from the program, pick a screening time for each, and the page lays your picks out on a timetable grid by day and venue. Two screenings that overlap are marked as a clash; two that follow each other closely at different venues are marked as a tight transfer. A plan can be shared as a link (the picks are encoded in the URL after `#p=`), and screenings can be added to a calendar as an `.ics` file.

## Files

- `index.html` — the whole planner. The festival program (films, screenings, venues) is embedded in the file as `DATA`, taken from the timetable at hiff.fi; the page makes no network requests.

## How it keeps your plan

Your picks are kept in the browser's local storage, so they survive a reload but stay on your device. The share link carries the same picks, so opening it on another device or sending it to a friend reproduces the plan.

## Reusing it for another festival

The TIFF 2026 planner in `../tiff2026/` is this same page with a different program embedded. To build one for another festival, replace `DATA` with that festival's program in the same shape (one entry per screening with film, start, end and venue) and adjust the venue list.
