# Duolingo weekly progress tracker

Keeps the [Duolingo weekly progress dashboard](index.html) up to date
automatically, without handing your mailbox to any third party (ChatGPT,
Claude, or otherwise) — the only thing that ever touches the inbox is a
GitHub Actions job running under your own repo secrets.

This folder follows the same layout as your other dashboards in
`akaukora/dashboards` (e.g. `books-read/`): everything for one dashboard
lives in its own top-level folder, and `index.html` right here is what
GitHub Pages serves.

## How it works

1. A dedicated mailbox receives forwarded copies of Duolingo's weekly
   progress-report emails (nothing else needs to go there).
2. A GitHub Actions workflow (`.github/workflows/duolingo-weekly.yml`) runs
   every Monday morning, logs into that mailbox over IMAP, finds new
   Duolingo emails since the last run, and parses out minutes / XP / lessons
   per week (`duolingo/parse_duolingo.py`).
3. New weeks are appended to `duolingo/data/weekly_duolingo.json`.
4. The dashboard (`duolingo/index.html`) is regenerated from that data
   (`duolingo/build_dashboard.py`) and committed back to the repo.
5. GitHub Pages serves `duolingo/index.html` as a normal shareable web page.

Already seeded with 76 weeks (Aug 2024 – Feb 2026) — combining your Proton
Mail export with weekly-report emails recovered from an old Gmail account
for the Oct–Dec 2025 stretch — pulled on 2026-09-07, so history isn't lost.

## One-time setup

**1. Create the dedicated mailbox.** A free Gmail account works well (good
IMAP support, free app passwords). Don't use it for anything else — the
Actions job only ever reads mail there, but it's good hygiene to keep it
single-purpose.

**2. Forward Duolingo's emails to it**, without changing your Duolingo
account's login email:
   - In Proton Mail: **Settings → Filters → Forwarding rules** (or a simple
     Filter with a "Forward to" action) — condition: From contains
     `duolingo.com`, action: forward to the new Gmail address. Proton will
     ask you to confirm the forwarding address once.
   - This keeps your real inbox as the source of truth; the Gmail account
     just gets a copy of Duolingo mail going forward.

**3. Turn on 2-Step Verification on the Gmail account**, then generate an
   **App Password** for it (Google Account → Security → 2-Step Verification
   → App passwords). Use the app password below, never the real Google
   account password.

**4. This `duolingo/` folder and the workflow file go straight into your
   `akaukora/dashboards` repo** — `duolingo/` at the repo root, alongside
   `books-read/` and your other dashboard folders, and
   `.github/workflows/duolingo-weekly.yml` merged in next to
   `update-lastfm.yml` / `update-letterboxd.yml`.

**5. Add two repository secrets** (repo → Settings → Secrets and variables →
   Actions → New repository secret):
   | Secret name | Value |
   |---|---|
   | `DUOLINGO_MAILBOX_USER` | the Gmail address |
   | `DUOLINGO_MAILBOX_APP_PASSWORD` | the 16-character app password from step 3 |

   These secrets are only ever readable inside your own Actions runs — not
   by GitHub Support, not by any AI tool, not by anyone you haven't added as
   a repo collaborator.

**6. GitHub Pages**: this assumes Pages is already set to serve from the
   repo root (branch `main`, folder `/`) the way your other dashboard
   folders are served — no change needed there. Your dashboard will be at
   `https://akaukora.github.io/dashboards/duolingo/`.

**7. Run it once by hand** to check everything's wired up: repo → Actions →
   "Update Duolingo weekly dashboard" → Run workflow. Check the run log —
   it'll print each new week it finds — then confirm `duolingo/index.html`
   updated and the Pages URL reflects it.

After that it runs unattended every Monday. No Claude, ChatGPT, or any other
AI needs to be involved at any point after setup.

## Adjusting things later

- **Schedule**: edit the `cron` line in the workflow file. Cron is UTC.
- **Which mailbox folder is scanned**: set `IMAP_FOLDER` as another workflow
  env var if Duolingo mail lands somewhere other than `INBOX` (e.g. if you
  set up a Gmail filter that labels and archives it).
- **A new Duolingo email template Duolingo starts sending**: if a run stops
  finding weeks it should be finding, the subject probably uses new wording.
  `parse_duolingo.py`'s `extract_stats()` has the parsing rules for the ~10
  template variants seen so far — send me (or a future Claude/ChatGPT
  session) a sample and it can add a rule for the new one.
