# Derives music-viewer/index.html from music/index.html: drop-in page for Last.fm exporter CSVs, Spotify extended
# streaming history JSON and Apple Music play-activity CSV. Every replacement asserts its anchor.
# Lives in music-viewer/ next to the page it produces: python3 music-viewer/make_music_viewer.py (from anywhere).
import os, re
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE if os.path.isfile(os.path.join(HERE, "music", "index.html")) else os.path.dirname(HERE)   # repo root, whether the script sits there or in music-viewer/
SRC = os.path.join(ROOT, "music", "index.html")
OUT = os.path.join(ROOT, "music-viewer" if os.path.isdir(os.path.join(ROOT, "music-viewer")) else "music_viewer", "index.html")
s = open(SRC, encoding="utf-8").read()
def region(start, end, new):
    """Replace from the first `start` through the following `end` (inclusive) with `new`."""
    global s
    a = s.index(start); b = s.index(end, a) + len(end)
    s = s[:a] + new + s[b:]
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:100])
    s = s.replace(old, new)
def cut(start, end):
    global s
    a = s.index(start); b = s.index(end, a); s = s[:a] + s[b:]

# ---------------- head / header / nav / intro
rep("<title>Antti's Last.fm diary</title>", "<title>Music diary viewer</title>")
rep('<meta name="description" content="Dashboard of Antti\'s Last.fm scrobbles — forgotten favorites, listening by year, month and hour — read from scrobbles.csv in the same repository.">',
    '<meta name="description" content="Drop your Last.fm, Spotify or Apple Music listening history on the page and get an interactive dashboard: forgotten favorites, listening by year, month and hour. Nothing is uploaded.">')
rep("""      <h1>Antti's <span>Last.fm</span> diary</h1>
      <div class="sub" id="subtitle">Loading the scrobbles…</div>""",
"""      <h1>Your <span>music</span> diary</h1>
      <div class="sub" id="subtitle">An interactive dashboard of your listening history, made from your own export.</div>""")
region('<nav class="nav" aria-label="Media dashboards">', '</nav>',
"""<nav class="nav" aria-label="Data">
      <button class="chip" id="pickBtn" type="button" hidden>Add files…</button>
      <button class="chip warn" id="forgetBtn" type="button" hidden title="Remove the loaded data from this browser">Forget my data</button>
      <a href="../letterboxd-viewer/">Films</a>
      <a href="../storygraph-viewer/">Books</a>
      <a class="active" href="./">Music</a>
      <a class="profile" href="../music/" title="The dashboard this viewer is made from">Antti's music ↗</a>
    </nav>""")
region('<p class="intro">', '</p>', '<p class="intro">Every streaming service keeps a log of what you played and when. This page reads yours — from a Last.fm export, Spotify\'s extended streaming history or Apple Music\'s play activity — and shows what got played, when, and which old favorites have gone quiet. Everything happens in your browser; nothing is uploaded.</p>')
rep("""  <div id="status"></div>

  <div class="top">""",
"""  <div id="status"></div>

  <section class="drop" id="drop" tabindex="0" role="button" aria-label="Choose or drop your listening history files">
    <h2>Drop your listening history here</h2>
    <p>Several files at once is fine — Spotify's export comes as many. Nothing leaves your browser.</p>
    <div class="how">
      <div><b>Last.fm</b><br>Last.fm has no export button; use a community exporter such as <a href="https://benjaminbenben.com/lastfm-to-csv/" target="_blank" rel="noopener">Last.fm to CSV</a> or <a href="https://lastfmstats.com" target="_blank" rel="noopener">lastfmstats.com</a> and drop the CSV it gives you.</div>
      <div><b>Spotify</b><br>Account → Privacy settings → <i>Download your data</i>, tick <i>Extended streaming history</i>. It arrives by email in up to 30 days as <code>Streaming_History_Audio_….json</code> files — drop them all.</div>
      <div><b>Apple Music</b><br><a href="https://privacy.apple.com" target="_blank" rel="noopener">privacy.apple.com</a> → <i>Request a copy of your data</i> → Apple Media Services. Drop <code>Apple Music Play Activity.csv</code>.</div>
      <div><b>Tidal, Qobuz, Deezer…</b><br>These don't export a play log. The way around it is to connect the service to Last.fm (it logs every play as a %%SCRB1%%) and export from there.</div>
    </div>
    <div><button class="chip" type="button" id="pickBtn2">Choose files…</button></div>
    <div class="fine">Your data is kept in this browser (nothing else) until you press <i>Forget my data</i>. Also accepts a <code>%%SCRB2%%.csv</code> in the format of <a href="../music/">Antti's dashboard</a>.</div>
  </section>
  <input type="file" id="file" accept=".csv,.json,text/csv,application/json" multiple>
  <div class="overlay" aria-hidden="true">Drop the files to load them</div>

  <div class="dash" id="dash" hidden>
  <div class="top">""")
region('  <footer>', '</footer>',
"""  </div><!-- /dash -->

  <footer>
    <span id="fetchedAt"></span>
    <details><summary>About this viewer</summary><span id="creditsNote"></span><span id="kidsNote"></span> Times are shown in your device's time zone. Your files are parsed in the browser and kept only in this browser's storage; nothing is sent to a server. A viewer for listening-history exports, made from <a href="../music/">Antti's music dashboard</a> — source on <a href="https://github.com/akaukora/dashboards" target="_blank" rel="noopener">GitHub</a>.</details>
  </footer>""")
# drop-zone CSS (shared look with the other viewers)
rep("""  footer { color: var(--text-3); font-size: 12px; margin-top: 22px; line-height: 1.6; }""",
"""  .drop { border: 2px dashed var(--line-2); border-radius: var(--radius); padding: 36px 24px; text-align: center; color: var(--text-2); background: var(--card); margin: 8px 0 14px; cursor: pointer; transition: border-color .15s, background .15s; }
  .drop:hover, body.dragging .drop { border-color: var(--green); background: #1f2a2a; }
  .drop h2 { margin: 0 0 6px; font-size: 20px; color: var(--text); font-weight: 600; } .drop p { margin: 4px 0 14px; font-size: 14px; }
  .drop .how { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; text-align: left; font-size: 12px; color: var(--text-2); line-height: 1.5; max-width: 1000px; margin: 0 auto; }
  .drop .how div { background: var(--card-2); border-radius: 8px; padding: 10px 12px; } .drop .how b { color: var(--text); } .drop .how a { color: var(--text); text-decoration: underline; }
  .drop code { color: var(--text); font-size: 11px; background: var(--bg); padding: 1px 5px; border-radius: 4px; }
  .drop .chip { margin-top: 16px; padding: 8px 18px; font-size: 14px; background: var(--green-mark); border-color: var(--green-mark); color: #fff; font-weight: 600; }
  .drop .fine { color: var(--text-3); font-size: 12px; margin-top: 14px; } .drop .fine a { color: var(--text-2); }
  .drop[hidden], .dash[hidden] { display: none !important; } #file { display: none; }
  .overlay { position: fixed; inset: 0; z-index: 50; display: none; place-items: center; background: rgba(20,24,28,0.82); color: var(--text); font-size: 20px; font-weight: 600; pointer-events: none; } body.dragging .overlay { display: grid; }
  .nav .chip.warn { color: var(--text-3); } .nav .chip.warn:hover { color: var(--orange); border-color: var(--orange); }
  @media (max-width: 860px) { .drop .how { grid-template-columns: 1fr 1fr; } } @media (max-width: 520px) { .drop .how { grid-template-columns: 1fr; } }
  footer { color: var(--text-3); font-size: 12px; margin-top: 22px; line-height: 1.6; }""")

# ---------------- personal config out
rep("""const SCROBBLES_URL = "scrobbles.csv";        // relative to the page; ?src= overrides for testing
const LASTFM_USER = "akaukora";""", """const STORE_DB = "music-viewer", STORE_KEY = "plays";   // IndexedDB: the normalized plays, so a reload doesn't need the files again
let SOURCE = "";                                          // lastfm | spotify | apple | csv — set by the parser; Last.fm library links only make sense for lastfm
let LASTFM_USER = "";                                     // filled from a Last.fm export when it carries a username (it usually doesn't)""")
rep("""const MILESTONES = [{ date: "2009-01-11", label: "Streaming (Spotify)" }];""", """const MILESTONES = [];                                    // add your own: { date: "YYYY-MM-DD", label: "…" }""")
a = s.index("const KIDS_TRACKS = ["); b = s.index("\n];", a) + 3
s = s[:a] + "const KIDS_TRACKS = [];                                   // your own [artist, track, liked] list, if you have one; empty hides the control" + s[b:]
rep("""      <span class="def" style="margin-left:auto" title="Songs on the kids' playlist (KIDS_TRACKS in the page)">Kids' songs""", """      <span class="def" id="kidsWrap" style="margin-left:auto" title="Songs on the kids' playlist (KIDS_TRACKS in the page)">Kids' songs""")
rep("""  $("#minTrackPlaysWrap").hidden = tracks;""", """  $("#minTrackPlaysWrap").hidden = tracks; $("#kidsWrap").hidden = !KIDS_TRACKS.length;""")
# links only for Last.fm sources
rep("""const lfmArtist = (a) => `https://www.last.fm/user/${LASTFM_USER}/library/music/${encodeURIComponent(a).replace(/%20/g, "+")}`;""",
    """const lfmArtist = (a) => SOURCE === "lastfm" ? `https://www.last.fm/${LASTFM_USER ? `user/${LASTFM_USER}/library/` : ""}music/${encodeURIComponent(a).replace(/%20/g, "+")}` : null;""")
rep("""const lfmTrack = (a, t) => `${lfmArtist(a)}/_/${encodeURIComponent(t).replace(/%20/g, "+")}`;""", """const lfmTrack = (a, t) => lfmArtist(a) ? `${lfmArtist(a)}/_/${encodeURIComponent(t).replace(/%20/g, "+")}` : null;""")
rep("""<a href="${tracks ? lfmTrack(f.a.artist, f.a.name) : lfmArtist(f.a.name)}" target="_blank" rel="noopener" title="Open in your Last.fm library">${esc(f.a.name)}</a>""",
    """${(tracks ? lfmTrack(f.a.artist, f.a.name) : lfmArtist(f.a.name)) ? `<a href="${tracks ? lfmTrack(f.a.artist, f.a.name) : lfmArtist(f.a.name)}" target="_blank" rel="noopener" title="Open on Last.fm">${esc(f.a.name)}</a>` : `<span style="color:var(--text);font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block">${esc(f.a.name)}</span>`}""", count=3)   # forgotten-favorites rows, newest-favorites rows, selected-artist row
rep("""Bars are plays per year over your whole history; the name opens your library on Last.fm, the plays count filters the dashboard to the artist.`""",
    """Bars are plays per year over your whole history; ${SOURCE === "lastfm" ? "the name opens your library on Last.fm, " : ""}the plays count filters the dashboard to the artist.`""")
# device time zone instead of Helsinki
rep("""function localDate(uts) {
  const d = new Date(uts * 1000), y = d.getUTCFullYear();
  const lastSun = (m) => { const x = new Date(Date.UTC(y, m + 1, 0, 1)); x.setUTCDate(x.getUTCDate() - x.getUTCDay()); return x.getTime(); };
  const t = d.getTime(), dst = t >= lastSun(2) && t < lastSun(9);
  return new Date(t + (dst ? 3 : 2) * 3600 * 1000);   // a Date whose UTC fields ARE Helsinki wall-clock — use getUTC* on it
}""", """function localDate(uts) {   // a Date whose UTC fields are the device's local wall-clock — the rest of the page reads getUTC* on it
  const d = new Date(uts * 1000);
  return new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate(), d.getHours(), d.getMinutes(), d.getSeconds()));
}""")
rep("""Helsinki time. Busiest hour""", """Busiest hour""")
rep("""// Helsinki time without Intl per row (fast for 100k+ rows): EET +2, EEST +3 between the last Sundays of March and October, 01:00 UTC.
""", """// Times are shown in this device's time zone.
""")

# ---------------- build from normalized plays instead of CSV rows
rep("""  if (rows) {
  const hdr = rows[0].map((h) => h.trim().toLowerCase()), ix = (n) => hdr.indexOf(n);
  const iU = ix("uts"), iA = ix("artist"), iT = ix("track"), iAl = ix("album"), iL = ix("loved");
  if (iU < 0 || iA < 0) throw new Error(`Unexpected header: ${hdr.join(", ")}`);
  S = [];
  for (let i = 1; i < rows.length; i++) {
    const r = rows[i], uts = +r[iU]; if (!uts) continue;
    const ld = localDate(uts);
    S.push({ uts, y: ld.getUTCFullYear(), m: ld.getUTCMonth(), d: ld.getUTCDate(), dow: (ld.getUTCDay() + 6) % 7, h: ld.getUTCHours(), artist: r[iA], track: r[iT] || "", album: iAl >= 0 ? r[iAl] || "" : "", loved: iL >= 0 && r[iL] === "1" });
  }
  }""", """  if (rows) {   // rows: normalized plays [{ uts, artist, track, album, ms? }]
  S = [];
  for (const p of rows) {
    const uts = +p.uts; if (!uts || !p.artist) continue;
    const ld = localDate(uts);
    S.push({ uts, y: ld.getUTCFullYear(), m: ld.getUTCMonth(), d: ld.getUTCDate(), dow: (ld.getUTCDay() + 6) % 7, h: ld.getUTCHours(), artist: p.artist, track: p.track || "", album: p.album || "", loved: false, ms: p.ms || 0 });
  }
  }""")

# ---------------- load(): files → parsers → plays → IndexedDB
a = s.index("async function load() {"); b = s.index("window.addEventListener(\"hashchange\"", a)
s = s[:a] + r'''/* ---------- parsers: each returns { source, plays: [{ uts, artist, track, album, ms }], note } or null if the file isn't its kind ---------- */
const MIN_MS = 30000;   // a Spotify / Apple play shorter than 30 s is a skip, not a listen (Last.fm scrobbles are already filtered by the service)
function parseDateish(v) {   // → unix seconds, or null. Accepts unix seconds / milliseconds, ISO 8601, Last.fm's "06 Sep 2026, 14:23" (UTC), "2026-09-06 14:23" (UTC)
  if (v == null) return null; const t = String(v).trim(); if (!t) return null;
  if (/^\d{9,10}$/.test(t)) return +t; if (/^\d{12,13}$/.test(t)) return Math.floor(+t / 1000);
  let m = /^(\d{1,2}) ([A-Za-z]{3}) (\d{4}),? (\d{1,2}):(\d{2})/.exec(t);
  if (m) { const d = Date.parse(`${m[1]} ${m[2]} ${m[3]} ${m[4]}:${m[5]} UTC`); return isNaN(d) ? null : Math.floor(d / 1000); }
  m = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?$/.exec(t);
  if (m) return Math.floor(Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0)) / 1000);
  const d = Date.parse(t); return isNaN(d) || d < 1e11 ? null : Math.floor(d / 1000);   // ISO with zone, RFC 2822 …; d < 1e11 rejects bare numbers-as-years
}
function parseDelimited(text, delim) {   // RFC 4180-ish: quoted fields may hold the delimiter, quotes ("") and line breaks
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
  const rows = []; let row = [], field = "", q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) { if (c === '"') { if (text[i + 1] === '"') { field += '"'; i++; } else q = false; } else field += c; }
    else if (c === '"') q = true;
    else if (c === delim) { row.push(field); field = ""; }
    else if (c === "\n" || c === "\r") { if (c === "\r" && text[i + 1] === "\n") i++; row.push(field); field = ""; if (row.length > 1 || row[0] !== "") rows.push(row); row = []; }
    else field += c;
  }
  row.push(field); if (row.length > 1 || row[0] !== "") rows.push(row);
  return rows;
}
function sniffDelim(text) { const head = text.slice(0, 5000); const n = (ch) => (head.match(new RegExp("\\" + ch, "g")) || []).length; return n(";") > n(",") && n(";") > n("\t") ? ";" : n("\t") > n(",") ? "\t" : ","; }
function playsFromRows(rows, cols, source, name) {   // cols: { a, t, al, d, ms, type } column indexes (-1 = absent)
  const plays = []; let skipped = 0, noDate = 0;
  for (const r of rows) {
    const artist = (r[cols.a] || "").trim(), track = (r[cols.t] || "").trim(); if (!artist || !track) continue;
    if (cols.type >= 0 && r[cols.type] && !/PLAY_END/i.test(r[cols.type])) continue;            // Apple logs several event kinds per play; PLAY_END carries the duration
    const ms = cols.ms >= 0 ? +r[cols.ms] || 0 : 0; if (cols.ms >= 0 && (source !== "lastfm" || String(r[cols.ms] ?? "") !== "") && ms < MIN_MS) { skipped++; continue; }   // 0 ms = nothing was played
    const uts = parseDateish(r[cols.d]); if (!uts) { noDate++; continue; }                        // Last.fm "now playing" rows have no date
    plays.push({ uts, artist, track, album: cols.al >= 0 ? (r[cols.al] || "").trim() : "", ms });
  }
  return plays.length ? { source, plays, note: `${name}: ${fmt(plays.length)} plays${skipped ? `, ${fmt(skipped)} under 30 s left out` : ""}${noDate ? `, ${fmt(noDate)} rows without a date` : ""}` } : null;
}
function parseJsonHistory(text, name) {
  let data; try { data = JSON.parse(text); } catch (e) { return null; }
  if (data && !Array.isArray(data) && Array.isArray(data.scrobbles)) data = data.scrobbles;   // lastfmstats.com: { username, scrobbles: [{ track, artist, album, date (ms) }] }
  if (!Array.isArray(data) || !data.length) return null;
  const x = data.find((r) => r && typeof r === "object") || {};
  const objs = (a, t, al, d, ms, source, label) => playsFromRows(data.map((r) => [r[a], r[t], al ? r[al] : "", typeof d === "function" ? d(r) : r[d], ms ? r[ms] : ""]), { a: 0, t: 1, al: 2, d: 3, ms: ms ? 4 : -1, type: -1 }, source, `${name} (${label})`);
  if ("ts" in x && ("master_metadata_track_name" in x || "episode_name" in x || "spotify_track_uri" in x))        // Spotify extended streaming history
    return objs("master_metadata_album_artist_name", "master_metadata_track_name", "master_metadata_album_album_name", "ts", "ms_played", "spotify", "Spotify extended history");
  if ("endTime" in x && "artistName" in x)                                                                           // Spotify "Account data" StreamingHistory (last year only)
    return objs("artistName", "trackName", null, "endTime", "msPlayed", "spotify", "Spotify streaming history");
  if ("artist" in x && ("track" in x || "name" in x) && ("date" in x || "uts" in x))                                 // lastfmstats.com JSON, ghan.nl JSON, other Last.fm dumps
    return objs("artist", "track" in x ? "track" : "name", "album" in x ? "album" : null, (r) => r.uts ?? (r.date && typeof r.date === "object" ? r.date.uts : r.date), null, "lastfm", "Last.fm export");
  return null;
}
function parseCsvHistory(text, name) {
  const rows = parseDelimited(text, sniffDelim(text)); if (rows.length < 2) return null;
  const first = rows[0].map((h) => h.trim().toLowerCase().replace(/^﻿/, ""));
  const pick = (...names) => { for (const n of names) { const i = first.findIndex((h) => h === n || h.startsWith(n + "#")); if (i >= 0) return i; } return -1; };
  const hasHeader = first.some((h) => /^(artist|track|song|album|date|time|uts|name|ts)/.test(h)) && !first.some((h) => /^\d{9,13}$/.test(h)) && parseDateish(rows[0].find((v) => /\d{4}/.test(v)) || "") == null;
  let cols, source, label;
  if (hasHeader) {
    if (pick("event start timestamp") >= 0 || pick("play duration milliseconds") >= 0) {                              // Apple Music Play Activity
      cols = { a: pick("artist name"), t: pick("song name", "content name"), al: pick("album name"), d: pick("event start timestamp", "event end timestamp"), ms: pick("play duration milliseconds"), type: pick("event type") }; source = "apple"; label = "Apple Music play activity";
    } else if (pick("master_metadata_track_name") >= 0) {                                                             // Spotify history converted to CSV
      cols = { a: pick("master_metadata_album_artist_name"), t: pick("master_metadata_track_name"), al: pick("master_metadata_album_album_name"), d: pick("ts"), ms: pick("ms_played"), type: -1 }; source = "spotify"; label = "Spotify history";
    } else {                                                                                                           // ghan.nl / lastfmstats.com CSV, this dashboard's own scrobbles.csv, anything with sensible headers
      cols = { a: pick("artist", "artist name", "artist_name", "artistname"), t: pick("track", "track name", "track_name", "trackname", "song", "song name", "title", "name"),
        al: pick("album", "album name", "album_name", "albumname"), d: pick("uts", "timestamp", "unix timestamp", "date", "datetime", "datetime_utc", "utc_time", "time", "played at", "played_at", "ts", "scrobble time", "listened_at"),
        ms: pick("ms_played", "msplayed", "ms played"), type: -1 }; source = "lastfm"; label = "Last.fm export";
    }
    if (cols.a < 0 || cols.t < 0 || cols.d < 0) return null;
    return playsFromRows(rows.slice(1), cols, source, `${name} (${label})`);
  }
  // headerless: lastfm-to-csv (benjaminbenben.com) writes artist, album, track, "06 Sep 2026, 14:23" — find the date column by content, the rest by order
  const probe = rows.slice(0, 20); let d = -1;
  for (let c = 0; c < rows[0].length && d < 0; c++) if (probe.filter((r) => parseDateish(r[c]) != null).length >= Math.min(3, probe.length) - 1) d = c;
  if (d < 0 || rows[0].length < 3) return null;
  const rest = rows[0].map((_, i) => i).filter((i) => i !== d);
  return playsFromRows(rows, { a: rest[0], al: rest.length >= 3 ? rest[1] : -1, t: rest.length >= 3 ? rest[2] : rest[1], d, ms: -1, type: -1 }, "lastfm", `${name} (Last.fm to CSV)`);
}
function parseAny(text, name) { return (/^\s*[\[{]/.test(text.slice(0, 50).replace(/^﻿/, "")) ? parseJsonHistory(text, name) : parseCsvHistory(text, name)); }

/* ---------- IndexedDB persistence (localStorage is too small for 100k plays) ---------- */
function idb() { return new Promise((res, rej) => { const r = indexedDB.open(STORE_DB, 1); r.onupgradeneeded = () => r.result.createObjectStore("kv"); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); }); }
async function idbGet(k) { try { const db = await idb(); return await new Promise((res, rej) => { const t = db.transaction("kv").objectStore("kv").get(k); t.onsuccess = () => res(t.result); t.onerror = () => rej(t.error); }); } catch (e) { return null; } }
async function idbSet(k, v) { try { const db = await idb(); await new Promise((res, rej) => { const t = db.transaction("kv", "readwrite"); t.objectStore("kv").put(v, k); t.oncomplete = res; t.onerror = () => rej(t.error); }); } catch (e) { console.warn("Could not keep the data in this browser:", e); } }
async function idbDel(k) { try { const db = await idb(); await new Promise((res) => { const t = db.transaction("kv", "readwrite"); t.objectStore("kv").delete(k); t.oncomplete = res; t.onerror = res; }); } catch (e) {} }

let LOADED = { plays: [], files: [], source: "" };
function showStatus(html) { $("#status").innerHTML = html; $("#status").classList.add("show"); }
function usePlays(loaded, { remember = true } = {}) {
  const seen = new Set(), plays = [];
  for (const p of loaded.plays) { const k = `${Math.floor(p.uts / 60)}|${p.artist.toLowerCase()}|${p.track.toLowerCase()}`;   /* minute resolution: exporters differ in precision */ if (seen.has(k)) continue; seen.add(k); plays.push(p); }
  plays.sort((a, b) => a.uts - b.uts);
  LOADED = { plays, files: loaded.files, source: loaded.source }; SOURCE = loaded.source;
  if (remember) idbSet(STORE_KEY, LOADED);
  Object.values(charts).forEach((c) => c.destroy()); charts = {};
  build(plays);
  if (!S.length) { showStatus("<b>The files parsed, but held no plays.</b>"); return; }
  buildFilters(); if (!wired) { wire(); wired = true; } readHash(); paintChips(); paintGroups(); subtitle();
  $("#fetchedAt").innerHTML = `Loaded ${loaded.files.map((f) => `<code>${esc(f)}</code>`).join(", ")}${remember ? ", kept in this browser" : ""}. ${SOURCE === "spotify" || SOURCE === "apple" ? "Plays shorter than 30 seconds are left out. " : ""}`;
  $("#status").classList.remove("show"); $("#drop").hidden = true; $("#dash").hidden = false; $("#pickBtn").hidden = false; $("#forgetBtn").hidden = !remember;
  render();
}
let wired = false;
async function readFiles(list) {
  const files = [...list].filter((f) => /\.(csv|json)$/i.test(f.name));
  if (!files.length) { showStatus("<b>No CSV or JSON files found.</b> Unzip the export first, then drop the files themselves."); return; }
  const parsed = [], bad = [];
  for (const f of files) { const text = await f.text(); const r = parseAny(text, f.name); if (r && r.plays.length) parsed.push({ ...r, name: f.name }); else bad.push(f.name); }
  if (!parsed.length) { showStatus(`<b>Couldn't read a listening history from ${bad.map((n) => `<code>${esc(n)}</code>`).join(", ")}.</b> Expected a Last.fm exporter CSV (artist, album, track, date), Spotify's <code>Streaming_History_Audio_….json</code> or Apple's <code>Apple Music Play Activity.csv</code>.`); return; }
  const source = parsed[0].source, plays = [...(LOADED.source === source ? LOADED.plays : []), ...parsed.flatMap((p) => p.plays)];   // more files of the same kind add up; a different source replaces
  const names = [...new Set([...(LOADED.source === source ? LOADED.files : []), ...parsed.map((p) => p.name)])];
  usePlays({ plays, files: names, source });
  if (bad.length) showStatus(`Loaded ${parsed.length} file${parsed.length === 1 ? "" : "s"}; skipped ${bad.map((n) => `<code>${esc(n)}</code>`).join(", ")} (not a listening history).`);
  console.log(parsed.map((p) => p.note).join("\n"));
}
$("#file").addEventListener("change", (e) => { readFiles(e.target.files); e.target.value = ""; });
$("#pickBtn").addEventListener("click", () => $("#file").click());
$("#pickBtn2").addEventListener("click", (e) => { e.stopPropagation(); $("#file").click(); });
$("#drop").addEventListener("click", () => $("#file").click());
$("#drop").addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); $("#file").click(); } });
$("#forgetBtn").addEventListener("click", async () => { await idbDel(STORE_KEY); LOADED = { plays: [], files: [], source: "" }; S = []; S_ALL = []; Object.values(charts).forEach((c) => c.destroy()); charts = {}; F.year = []; F.last12 = false; F.month = null; F.artist = null; syncHash(); $("#dash").hidden = true; $("#drop").hidden = false; $("#pickBtn").hidden = true; $("#forgetBtn").hidden = true; $("#subtitle").textContent = "An interactive dashboard of your listening history, made from your own export."; $("#fetchedAt").textContent = ""; });
let dragDepth = 0;
document.addEventListener("dragenter", (e) => { if ([...e.dataTransfer.types].includes("Files")) { dragDepth++; document.body.classList.add("dragging"); } });
document.addEventListener("dragleave", () => { if (--dragDepth <= 0) { dragDepth = 0; document.body.classList.remove("dragging"); } });
document.addEventListener("dragover", (e) => e.preventDefault());
document.addEventListener("drop", (e) => { e.preventDefault(); dragDepth = 0; document.body.classList.remove("dragging"); if (e.dataTransfer.files.length) readFiles(e.dataTransfer.files); });

async function load() {
  const src = new URLSearchParams(location.search).get("src");
  if (src) { try { const res = await fetch(src, { cache: "no-store" }); if (!res.ok) throw new Error(`HTTP ${res.status}`); const r = parseAny(await res.text(), src.split("/").pop()); if (!r) throw new Error("not a listening history"); usePlays({ plays: r.plays, files: [src.split("/").pop()], source: r.source }, { remember: false }); return; } catch (e) { showStatus(`<b>Couldn't load</b> <code>${esc(src)}</code>: ${esc(e.message)}. You can still drop files below.`); } }
  const stored = await idbGet(STORE_KEY);
  if (stored && stored.plays && stored.plays.length) usePlays(stored);
}
''' + s[b:]
rep("""window.addEventListener("hashchange", () => { if (S.length) { readHash(); paintChips(); render(); } });""", """window.addEventListener("hashchange", () => { if (S.length) { readHash(); paintChips(); render(); } });""")
# the kids and credits footer notes are set inside the old load(); set them in usePlays instead (credits still apply)
rep("""  $("#status").classList.remove("show"); $("#drop").hidden = true; $("#dash").hidden = false;""",
    """  $("#creditsNote").textContent = CREDITS.plays ? ` Collaboration credits ("A, B", "A feat. B") are counted under the first-named artist (${fmt(CREDITS.plays)} plays).` : "";
  $("#status").classList.remove("show"); $("#drop").hidden = true; $("#dash").hidden = false;""")

# ---------------- wording: scrobble → play (everything user-visible; identifiers checked below)
# wording: the page talks about plays, not scrobbles — but leave the parser block alone (it names Last.fm's own fields)
cut = s.index("/* ---------- parsers:"); head, tail = s[:cut], s[cut:]
head = re.sub(r"Scrobbled", "Played", head); head = re.sub(r"scrobbled", "played", head)
head = re.sub(r"Scrobbles", "Plays", head); head = re.sub(r"scrobbles", "plays", head); head = re.sub(r"Scrobble\b", "Play", head); head = re.sub(r"scrobble\b", "play", head)
s = (head + tail).replace("%%SCRB1%%", "&ldquo;scrobble&rdquo;").replace("%%SCRB2%%", "scrobbles")
# CREDITS.plays identifier got renamed consistently (both definition and uses) — fine. Check nothing else broke:
for bad in ["last.fm/user/akaukora", 'LASTFM_USER = "akaukora"', "Helsinki", "farbeach", "SCROBBLES_URL"]:
    assert bad not in s, bad
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write(s)
print("ok", len(s), "→", os.path.relpath(OUT, ROOT))
