---
name: task-management
description: Task tracking in a shared TASKS.md file with date ranges, categories and a timeline dashboard. Use when the user asks about their tasks, wants to add, complete, reschedule or move a task, or asks what is due, overdue or waiting.
user-invocable: false
---

# Task management

Tasks live in `TASKS.md` in the working folder. The user edits it through the dashboard
(`dashboard.html`); you edit it directly. Both stay in sync: the dashboard watches the
file and reloads when it changes.

The rules for this task list (sections, date defaults, weekend rule, source links,
review-first suggestions) are in the "Task-list rules" part of `CLAUDE.md`. Read them
before changing anything; if the user has changed or removed a rule there, follow
their version.

## File location

- Use `TASKS.md` in the current working folder.
- If it doesn't exist, create it from the template below.
- If `dashboard.html` is missing, copy it from `${CLAUDE_PLUGIN_ROOT}/skills/dashboard.html`
  and tell the user to open it in Chrome or Edge and pick `TASKS.md`.

## Template

```markdown
# Tasks

## Urgent

## Not started

## Active

## Waiting for others

## Some day

## Completed
```

## Task line format

```
- [ ] **Title** - [YYYY-MM-DD → YYYY-MM-DD] `CATEGORY` note [↻ annual] [📧 Sender 27 May](https://…)
  - [ ] [YYYY-MM-DD] Milestone sub-item
```

- **Title** in bold — the dashboard and the weekly diff match tasks by this text, so
  keep titles stable and unique.
- Date range first in the note: start = begin working, end = deadline.
- First backtick tag = category (the timeline swimlane).
- `[↻ monthly|quarterly|annual]` = the dashboard creates the next instance on completion.
- Source link and a one-line quote go at the end of the note.
- Sub-items with a `[YYYY-MM-DD]` prefix render as milestone diamonds on the bar.

Edit lines in place with a read-modify-write of the file. Never retype the whole file
from memory; you may drop content.

## How to respond

**"What's on my list?" / "What's due?"** — Read TASKS.md. Lead with overdue items (end
date before today, not ticked) and anything due in the next 7 days, then Active and
Waiting for others. Say how many days late or how long something has waited.

**"Add a task …"** — Apply the date defaults from CLAUDE.md, choose a category (reuse an
existing tag when one fits), put it in Not started unless told otherwise, and show
the line you added.

**"X is done"** — Tick it (`[x]`) and move it to Completed. Keep the date range.

**"Move / reschedule X"** — Change the range or section; apply the weekend rule.

**"What am I waiting on?"** — List Waiting for others with days waited (today − start).

## Extracting tasks from text

When the user shares meeting notes, an email or a chat thread, look for commitments
they made ("I'll send", "I'll check", "let me find out"), requests addressed to them,
and deadlines. Offer them as suggestions with proposed dates; add only what the user
confirms.
