# Music viewer — your own listening history

A drop-in version of the [music dashboard](../music/): anyone can open the page, drop the export of
their streaming service on it and get the same analysis — forgotten favorites, when each artist was
last heard, new artists per year, how favorites were made, listening by year, month and hour. Live
at `https://akaukora.github.io/dashboards/music-viewer/` once this folder is in the `dashboards`
repository as `music-viewer/`.

Everything happens in the browser. Files are parsed by the page's own JavaScript, nothing is uploaded,
and the parsed plays are kept in the browser's IndexedDB so the dashboard is still there on the next
visit. *Forget my data* removes them.

## Files

- `index.html` — the viewer. Generated from `../music/index.html` by `make_music_viewer.py` (kept in
  the repository root next to the other generators); edit the personal page and regenerate rather
  than editing the viewer by hand.
- `README.md` — this file.

## Accepted exports

| Service | How to get it | What the page reads |
| --- | --- | --- |
| **Last.fm** | Last.fm has no export button. Community exporters: [Last.fm to CSV](https://benjaminbenben.com/lastfm-to-csv/) (headerless CSV: artist, album, track, `06 Sep 2026, 14:23`), [lastfmstats.com](https://lastfmstats.com) (semicolon-separated CSV `Artist;Album;AlbumId;Track;Date#user` with millisecond timestamps, or JSON `{ username, scrobbles: [...] }`), [mainstream.ghan.nl export](https://mainstream.ghan.nl/export.html) (CSV `uts, utc_time, artist, …, album, …, track, …` or the same as JSON). | All of them, plus this repository's own `scrobbles.csv`. Detection is by headers, or for the headerless file by finding the date column. |
| **Spotify** | Account → Privacy settings → *Download your data*, tick **Extended streaming history**; arrives by email in up to 30 days as a zip of `Streaming_History_Audio_<years>_<n>.json` files. The quicker one-year *Account data* export (`StreamingHistory0.json`, `endTime` / `artistName` / `trackName` / `msPlayed`) also works. | Drop all the JSON files at once — more files of the same kind add up. Rows for podcasts and audiobooks (no track name) are skipped; plays under 30 seconds are treated as skips and left out, the way Spotify itself counts a stream. |
| **Apple Music** | [privacy.apple.com](https://privacy.apple.com) → *Request a copy of your data* → Apple Media Services; in the zip look for `Apple Music Play Activity.csv`. | Uses *Artist Name*, *Song Name* (or *Content Name* in older exports), *Event Start Timestamp*, *Play Duration Milliseconds* and *Event Type*: only `PLAY_END` rows count (Apple writes several event rows per play), plays under 30 seconds are left out. There is no album column, so the album views stay empty. |
| **Tidal, Qobuz, Deezer…** | No play log to export. Connect the service to Last.fm and export from there. | — |

Any other CSV with recognizable headers (artist / track / album and a date, timestamp or `uts` column)
is read too. Files that don't parse are reported by name; the rest still load.

The Spotify and Apple parsers were written from the documented export formats and tested on synthetic
files in those shapes, not yet on a real export — the first real Spotify zip (Antti's is on order) is
the check. If a file is refused, the browser console (F12) prints what each file parsed to.

## Differences from the personal page

- **Plays, not scrobbles** — the wording is neutral because most visitors won't come from Last.fm.
- **Links to Last.fm** (artist and track names in the favorites lists) appear only when the loaded
  data is a Last.fm export; for Spotify and Apple data the names are plain text.
- **Times are in the device's time zone**, not Helsinki's. Spotify and Apple timestamps are UTC;
  Last.fm exporters give UTC as well.
- **No kids' playlist control** (`KIDS_TRACKS` is empty, which hides the control) and **no milestones**
  (`MILESTONES = []`). Both can be filled in the page's script by anyone who forks it.
- **Mixing sources**: dropping files of the same kind adds them up (duplicates are removed at
  minute precision — exporters differ in how exact their timestamps are); dropping a different kind
  of export replaces what was loaded.
- `?src=<url>` loads a CSV or JSON from a URL instead (for testing; the result is not kept).

Everything else — the favorite definition row, cross-filtering by year, month and artist, the
hidden-favorites list, chart toggles, the collapsible groups — is the same as on the personal page and
described in [`music/README.md`](../music/README.md).

## Regenerating

```
python3 make_music_viewer.py      # reads music/index.html, writes music-viewer/index.html
```

The generator does asserted string replacements, so it fails loudly if the personal page changed
where it expects an anchor; fix the anchor in the script and rerun. It also checks that nothing
personal (the Last.fm profile link, the Helsinki time zone) survives in the output.
