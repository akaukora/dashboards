# Weekly update — prompt for a scheduled task

Paste this as the prompt of a weekly scheduled task (for example Friday morning) in
Claude, or in any assistant that can run on a schedule **and** edit files in your folder.
Replace the folder path.

---

Weekly task-list update. Work in the folder `<PATH TO YOUR TASK FOLDER>`, which
contains `CLAUDE.md` (working memory and task-list rules) and `TASKS.md` (tasks with
`[YYYY-MM-DD → YYYY-MM-DD]` date ranges). Read both first.

Follow the update procedure:

0. Diff `TASKS.md` against `memory/.update-snapshots/last.md` (match by bold title):
   added, removed (excluding archived), completed, reopened, rescheduled (old → new),
   moved section, category changed, note edited. Skip on the first run.
1. Move Completed tasks whose end date is more than 90 days ago to
   `memory/archive/completed-<year>.md`. Count them.
2. Top up rules in `memory/recurring.md` marked `Confirmed: yes` so each series reaches
   12 months ahead whenever its last instance is under 6 months away. Weekend rule: an
   end date on Saturday/Sunday moves to Friday, start moves by the same amount.
3. If an email/chat connector is available and CLAUDE.md doesn't say to keep it off,
   look at the last 7 days for commitments and requests. Filter out anything already in
   TASKS.md, in the archive, or matching `memory/dismissed-suggestions.md`. Suggest
   only — never add.
4. Flag overdue tasks, Waiting for others older than 14 days, and Active items with no
   change in 30+ days.
5. Report in under 40 lines: Overdue, Due this week, Changes since last sweep,
   Archived (count), Recurring instances added, Possible new tasks (with source link
   and message id), Long-stale waiting items.

Only recurring instances, archive moves and the snapshot may be changed without
asking. At the end, save the final TASKS.md to `memory/.update-snapshots/last.md`.

If nothing needs attention, say so in one line.
