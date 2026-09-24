# Books — StoryGraph library

Dashboard of the reading history, live at `https://akaukora.github.io/dashboards/books-read/`.

## Files

- `index.html` — the dashboard. Reads `books.csv` (and `descriptions.json`, if present) from
  this folder on every visit and does everything in the browser.
- `fetch_descriptions.py`, `descriptions.json` — see *Descriptions* below.
- `books.csv` — StoryGraph's own library export, unchanged apart from the file name. The page reads
  its columns directly (*Title, Authors, ISBN/UID, Read Status, Last Date Read, Star Rating, Moods,
  Tags, Review, Read Count, Format*); the other export columns are carried but not used yet. (Before
  Sept 2026 this file was a hand-normalized version with short column names; the page still accepts
  that format, so nothing breaks if an old copy turns up.)

## Updating the data

StoryGraph has no API, so this one can't refresh itself like the film and music pages. The update
is three clicks and an upload, whenever you feel like it:

1. In StoryGraph: profile menu → **Manage account** → **Manage your data** → **Export StoryGraph
   library**. Wait for the email (or refresh the page) and download the CSV. Its name is long and
   includes your username and a timestamp.
2. Rename it to `books.csv`.
3. In GitHub, open `books-read/`, **Add file → Upload files**, drop it in (it replaces the old one),
   commit. Pages serves the new file within a minute, and the footer's *Latest finished* date
   confirms it.

Nothing else changes between updates. A book counts once, in the month of its *Last Date Read*;
books marked read without a date show in the table only; *currently-reading* gets its own strip.

## Descriptions (`descriptions.json`)

`fetch_descriptions.py` looks up a description for every book in `books.csv` — Google Books by
ISBN first, then Open Library, then Google Books by title and author for rows whose *ISBN/UID* is
an ASIN or empty — and writes them to `descriptions.json`. The workflow `update-books.yml` runs
it automatically whenever `books.csv` changes, so the update process above does not change; it
can also be started by hand from the Actions tab. Only books not yet in the file are fetched, so
a new export costs a handful of requests. No API key is needed. Books with nothing found are
listed under `"misses"` and retried on the next run.

On the page, *Recent reads* gets a **Review | Description** toggle (remembered in the browser) once
the file exists, and the table shows a small ⓘ after every title that has a description — click it
to open the blurb under the row. The footer credits Google Books and Open Library.

## The drop-in viewer

`storygraph-viewer/` is the same page for other people's data: it accepts a StoryGraph or Goodreads
export dropped on the page and keeps it in the browser. It is generated from this page by
`make_books_viewer.py`; regenerate after editing `index.html` here.
