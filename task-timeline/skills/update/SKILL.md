---
name: update
description: Weekly sweep of the task list — what changed since last time, archive old completed tasks, top up recurring tasks, look for new commitments in connected email/chat, flag overdue and stale items, and report. Use when the user asks for an update, a weekly review, "what changed", "what's overdue", or when a scheduled weekly run fires.
---

# Update (weekly sweep)

Read `CLAUDE.md` and `TASKS.md` first. The task-list rules in CLAUDE.md (sections, date
defaults, weekend rule, review-first suggestions) apply throughout; if the user has
changed or removed a rule there, follow their version and skip the matching step.

**What you may change without asking:** recurring instances (step 2), archive moves
(step 1) and the snapshot file (step 0). Everything else goes into the report as a
suggestion.

Edit files with a read-modify-write of the actual file contents — never retype a whole
file from memory.

## Step 0 — Diff since last sweep

Look for `memory/.update-snapshots/last.md` (a copy of TASKS.md saved by the previous
run). If it exists, match tasks in both versions by their **bold title** and classify:

- **Added** — in current, not in snapshot
- **Removed** — in snapshot, not in current (but not ones archived in step 1)
- **Completed** — was open, now `[x]` or in Completed
- **Reopened** — the reverse
- **Rescheduled** — date range changed (report old → new)
- **Moved section** — section changed (report old → new)
- **Category changed** — backtick tag changed
- **Note edited** — note text changed materially

If there is no snapshot, skip the diff (first run).

**At the very end of the run**, write the final TASKS.md content to
`memory/.update-snapshots/last.md` (create the folder if needed).

## Step 1 — Archive old completed tasks

For each task in Completed whose end date is more than **90 days** before today:
append the line verbatim to `memory/archive/completed-<end-date year>.md` (create it with
the header `# Completed tasks archive — <year>` if missing) and remove it from TASKS.md.
Keep completed tasks without an end date. Count what you moved.

## Step 2 — Top up recurring tasks

Read `memory/recurring.md`. For each rule marked `Confirmed: yes`, find its instances in
TASKS.md. If the latest instance ends less than **6 months** from today, add the next
instances until the series reaches **today + 12 months**. Use the rule's title pattern,
category, section and note template; apply the weekend rule (end on a weekend → move
to Friday, move the start by the same amount). Don't add an instance that already
exists, including in Completed or the archive.

## Step 3 — New commitments from email and chat (if connected)

If an email, chat or calendar connector is available **and the user's CLAUDE.md doesn't
say to leave it off**, search the last 7 days for:

- messages where the user committed to something ("I'll send", "I'll check", "will do",
  "let me find out") or was asked to do something
- notices that imply a task without asking (a new entity to set up in a system,
  a renamed company, a changed deadline)
- meetings in the next 14 days that need preparation

Before suggesting anything, drop it if:
- a task with the same or very similar title exists anywhere in TASKS.md (including Completed)
- the title appears in any `memory/archive/completed-*.md`
- it matches `memory/dismissed-suggestions.md` (`email:` id, `title:` substring,
  `subject:` substring; ignore `#` lines)

For each remaining item propose a task line with dates per the date defaults, the
source link and a short quote. **Never add these yourself.**

If no connector is available or the user keeps it off, skip this step and say so in one
line. If the user pastes findings from another assistant (for example a Copilot summary
of their inbox), treat those the same way.

## Step 4 — Triage

Flag:
- open tasks with an end date before today (overdue), with days late
- Waiting for others items older than 14 days (today − start)
- Active items started 30+ days ago with no recent change

## Step 5 — Report

One concise message, under ~40 lines, skipping empty sections:

- **Overdue (N)** — title, days late
- **Due this week** — end date within 7 days
- **Changes since last sweep** — grouped by type; cap each group at ~10
- **Archived this run** — count only
- **Recurring instances added** — titles
- **Possible new tasks** — "consider adding", one line each with reason, source date,
  link and message id so the user can dismiss precisely
- **Waiting for others — long-stale**

If this is a scheduled run and nothing needs attention (no overdue, nothing due, no
changes, no suggestions), keep the report to one line or stay silent if the tool allows.
