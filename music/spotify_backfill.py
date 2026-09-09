#!/usr/bin/env python3
"""Turn a Spotify "Extended streaming history" export into music/spotify_backfill.csv.

    python music/spotify_backfill.py my_spotify_data.zip
    python music/spotify_backfill.py "Spotify Extended Streaming History/"     # the unzipped folder works too

The CSV has one row per play of 30 seconds or more, in the same shape as scrobbles.csv plus the play
length: uts (start of the play, UTC), datetime_utc, artist, album, track, ms_played, source=spotify.
fetch_lastfm.py merges it into scrobbles.csv on every run, adding only the plays Last.fm never
received (see merge_backfill there). Podcast and audiobook rows have no track name and are skipped;
the small Streaming_History_Video_*.json files (music videos) are read as well.

Run it once per export; re-run and replace the CSV when a newer export arrives.
"""
from __future__ import annotations

import csv
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

MIN_MS = 30_000            # Spotify itself counts a stream from 30 s; shorter plays are skips
FIELDS = ["uts", "datetime_utc", "artist", "album", "track", "ms_played", "source"]


def iter_json(src: Path):
    """Yield (name, parsed JSON) for every streaming-history file in a zip or folder."""
    if src.is_file() and src.suffix.lower() == ".zip":
        with zipfile.ZipFile(src) as z:
            for n in sorted(z.namelist()):
                if "Streaming_History" in Path(n).name and n.lower().endswith(".json"):
                    with z.open(n) as f:
                        yield Path(n).name, json.load(f)
    elif src.is_dir():
        for p in sorted(src.rglob("Streaming_History*.json")):
            yield p.name, json.loads(p.read_text(encoding="utf-8"))
    elif src.is_file():
        yield src.name, json.loads(src.read_text(encoding="utf-8"))
    else:
        sys.exit(f"not found: {src}")


def rows_from(data, name):
    out, skipped_short, skipped_other = [], 0, 0
    for r in data:
        track, artist = r.get("master_metadata_track_name"), r.get("master_metadata_album_artist_name")
        if not track or not artist:                       # podcasts, audiobooks, rows without metadata
            skipped_other += 1; continue
        ms = int(r.get("ms_played") or 0)
        if ms < MIN_MS:
            skipped_short += 1; continue
        end = datetime.strptime(r["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        uts = int(end.timestamp()) - ms // 1000           # Spotify logs the END of a play; Last.fm stamps the start
        out.append({
            "uts": uts,
            "datetime_utc": datetime.fromtimestamp(uts, timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "artist": artist.strip(), "album": (r.get("master_metadata_album_album_name") or "").strip(),
            "track": track.strip(), "ms_played": ms, "source": "spotify",
        })
    print(f"  {name}: {len(out)} plays ({skipped_short} under 30 s, {skipped_other} without a track skipped)")
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent / "spotify_backfill.csv"
    rows = []
    for name, data in iter_json(src):
        rows += rows_from(data, name)
    # Spotify occasionally writes the same play twice a second apart; keep one
    rows.sort(key=lambda r: (r["uts"], r["artist"], r["track"]))
    out, last = [], {}
    for r in rows:
        k = (r["artist"].lower(), r["track"].lower())
        if k in last and r["uts"] - last[k] < 60:
            continue
        last[k] = r["uts"]; out.append(r)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(out)
    print(f"{len(out)} plays ({len(rows) - len(out)} duplicate rows dropped) → {out_path}"
          + (f"; {out[0]['datetime_utc'][:10]} – {out[-1]['datetime_utc'][:10]}" if out else ""))


if __name__ == "__main__":
    main()
