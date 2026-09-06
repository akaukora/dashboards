# Reading diary viewer (StoryGraph and Goodreads)

A drop-in version of the reading dashboard for anyone with a StoryGraph or Goodreads account.
One self-contained `index.html`: the visitor drops their library export on the page and gets
the dashboard for their own reading history. Nothing is uploaded — the file is parsed in the
browser and kept only in that browser's local storage.

Live at `https://akaukora.github.io/dashboards/storygraph-viewer/` once this folder is in the
`dashboards` repository as `storygraph-viewer/`. The relative links (`../books-read/`,
`../letterboxd-viewer/`) assume it sits next to the other dashboards.

## What a visitor does

1. StoryGraph: profile menu → **Manage account** → **Manage your data** → **Export
   StoryGraph library**; the CSV is ready after a moment. Goodreads: **My Books → Import and
   Export → Export Library**, which gives `goodreads_library_export.csv`.
2. Drop the file on the page (or use **Choose a file…**).
3. The data stays in the browser until **Forget my data** is pressed. **Load another file…**
   replaces it.

The page also accepts a `books.csv` in the personal dashboard's format, and a hosted CSV via
`?src=<raw URL>` (not kept in local storage).

## How the exports are read

The file is recognised by its headers (`Read Status` + `Last Date Read` = StoryGraph,
`Exclusive Shelf` + `Date Read` = Goodreads, `status` + `completed_date` = books.csv) and its
columns are mapped onto the `books.csv` names the page already reads:

| StoryGraph column | books.csv column |
|---|---|
| Title | title |
| Authors | authors |
| ISBN/UID | isbn |
| Read Status | status (`read`, `currently-reading`, `to-read`) |
| Last Date Read | completed_date (`YYYY/MM/DD` accepted as well as `YYYY-MM-DD`) |
| Star Rating | rating |
| Moods, Tags, Review, Read Count, Format | moods, tags, review, read_count, format |

| Goodreads column | books.csv column |
|---|---|
| Title, Author, ISBN13 | title, authors, isbn (the `="…"` wrapper is removed) |
| Exclusive Shelf | status (`read`, `currently-reading`, `to-read`) |
| Date Read | completed_date |
| My Rating | rating (Goodreads writes 0 for unrated → treated as no rating) |
| Bookshelves | moods — the user's shelves stand in for moods, minus the three exclusive shelves; every label switches to "Shelves" / "Ratings by shelf" |
| My Review, Read Count, Binding | review, read_count, format |

Everything else in either export (Contributors, Pace, the character questions, Content Warnings,
Date Added, Average Rating, Number of Pages, …) is ignored. Reviews are HTML fragments in both
exports; tags and `&nbsp;` are stripped for display.

The Goodreads mapping follows Goodreads' documented export layout and was tested against a
file built in that layout, not yet against a real export — the first real file should be checked
against the shelf page.

Because the page uses *Last Date Read* / *Date Read*, a book counts once, in the month it was last finished
(a reread of *Dune Messiah* shows on its latest date). Read books without a date — common for
libraries imported from Goodreads — appear in the table but not in the charts; the footer
reports how many. `Dates Read`, which holds every reading with start–end ranges, is not
analysed, so this viewer's numbers match the personal dashboard exactly for the same file.

## Differences from the personal dashboard

Only the shell: title, an empty state with the export steps, the drop zone and file picker,
local-storage persistence, the *Forget my data* button, a Films link to the Letterboxd viewer,
the Goodreads mapping with its label switch, HTML stripping in reviews, and the footer. Charts, filters, moods, the currently-reading strip and the table are the same
code. The page is generated from `books-read/index.html` by `make_books_viewer.py` (kept
outside the repository), so changes there carry over by re-running the script.

## Privacy

Local storage is per browser and per site. The page makes no network requests apart from
Chart.js from cdnjs (and the optional `?src=` CSV).
