# Memory

Working memory for your AI assistant. Keep it short (~100 lines): the people, terms and
projects you mention most, plus the rules for how your task list works. Everything
else goes in `memory/`.

> This is a fictional example. Replace the "Me", "People", "Terms" and "Projects"
> sections with your own; keep or delete the rules below as you like.

## Me
Alex Example — finance controller at Example Holdings. Budgeting, reporting, lender
covenants, board materials.

## People
| Who | Role |
|-----|------|
| **Maria** | Maria Lind, CFO |
| **Sam** | Sam Okafor, accounting manager |
→ Full list: memory/glossary.md, profiles: memory/people/

## Terms
| Term | Meaning |
|------|---------|
| CC | Compliance certificate to a lender |
| The pack | Monthly KPI report for management |
→ Full glossary: memory/glossary.md

## Projects
| Name | What |
|------|------|
| **Harbor** | Property portfolio purchase, due diligence phase |
→ Details: memory/projects/

## Preferences
- Reports and summaries in English
- (Add yours: tone, words to avoid, where files are saved…)

---

# Task-list rules

## Sections (in TASKS.md)
- **Urgent** — needs attention now (orange on the dashboard, same hue as overdue)
- **Not started** — needs to begin but hasn't (grey; bars touching the current week show at full strength)
- **Active** — being worked on now (green)
- **Waiting for others** — blocked on someone else; may need a reminder (blue)
- **Some day** — not now (receding grey)
- **Completed** — done (faded green, struck through)

## Task line format
```
- [ ] **Title** - [YYYY-MM-DD → YYYY-MM-DD] `CATEGORY` note text [↻ annual] [📧 Sender 27 May](https://link-to-source)
  - [ ] [YYYY-MM-DD] Milestone sub-item (shows as a diamond on the bar)
```
- The date range goes first in the note. Start = when to begin, end = deadline.
- The first backtick tag is the category (timeline swimlane).
- `[↻ monthly|quarterly|annual]` makes the dashboard create the next instance when
  the task is ticked done.
- A task with no dates sits in the "Unscheduled" tray under the timeline.

## Date defaults (when adding a task from an email or message)
1. No due date mentioned → start = message date, end = message date + 7 days
2. Due date given and at least 7 days away → start = due − 7 days, end = due date
3. Due date given but less than 7 days away → start = message date, end = due date
4. No source date (you just asked) → start = today, end = today + 7 days

Default prep window is 7 days unless the message implies more ("this takes a month").

**Weekend rule:** an end date never falls on Saturday or Sunday. Move it back to Friday
and move the start by the same amount.

## Source links
When a task comes from an email or chat message, put a link to it at the end of the
note — `[📧 Sender date](link)` for email, `[💬 Sender date](link)` for chat — plus a
one-line quote of the relevant sentence, so the task makes sense without clicking.

## Suggestions are review-first
When the weekly update finds possible new tasks in email, chat or meetings, it lists
them as **suggestions** in its report; it never adds them on its own. The only things
it changes directly are recurring instances (from `memory/recurring.md`), archiving old
completed tasks, and its own snapshot file.

To silence a suggestion for good, add a line to `memory/dismissed-suggestions.md`.

## Completed-task archive
The weekly update moves Completed tasks whose end date is more than **90 days** ago
into `memory/archive/completed-<year>.md` (year of the end date). Nothing is deleted.
Completed tasks without an end date stay put.

## Recurring tasks
Rules live in `memory/recurring.md`. The weekly update keeps instances materialized
12 months ahead and tops a series up when its last instance is under 6 months away.
Rules marked `Confirmed: no` are skipped.
