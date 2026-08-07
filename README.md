# plan-tracker

Project scheduling from a markdown backlog. Point it at a list of tasks and it
derives status from git, schedules the work under real resource constraints, and
publishes a Gantt chart plus a daily brief to each developer — every morning, on
its own, forever.

Built for [EduTrack](https://github.com/debashisedunext/EduTrack); it knows
nothing about that project. Everything project-specific lives in one config file.

```
plan init            scaffold plan.config.json and the plan directory
plan refresh         re-derive status from git, reschedule, rebuild outputs
plan brief           post today's briefs to GitHub issues
plan daily           refresh + commit + push + brief   (what the 09:00 job runs)
plan publish         push gantt.html to the configured claude.ai Artifact
plan watch           poll the remote; on any push, refresh + publish
plan watch install   run that poll every 60s in the background
plan cron install    run `plan daily` at 09:00, Monday to Friday
plan check           prove the chart actually renders
plan config          show what this project is configured as
```

---

## Install

```bash
git clone https://github.com/debashisedunext/plan-tracker.git ~/Documents/Projects/plan-tracker
ln -s ~/Documents/Projects/plan-tracker/plan /usr/local/bin/plan
```

For the Claude Code skills — `/plan-init` to build a plan for a new project,
`/plan-review` to interrogate an existing one:

```bash
mkdir -p ~/.claude/plugins
ln -s ~/Documents/Projects/plan-tracker ~/.claude/plugins/plan-tracker
```

Requires Python 3.8+, git, and node (only for `plan check`).
`plan cron install` is macOS; on Linux use the crontab line it prints.
Publishing additionally needs the [Claude Code CLI](https://claude.ai/install.sh)
— set `PLAN_CLAUDE` if it is somewhere unusual.

---

## Sharing the chart as a link

`gantt.html` is self-contained, so it can be published as a claude.ai Artifact
and shared with people who will never clone the repo.

**A published artifact cannot pull.** Its CSP blocks every external host and the
runtime grants no network capability, so the page can never fetch the repo —
least of all a private one, where a token embedded in a shareable page would be
a credential leak. The only direction that works is push.

Publish it once by hand to get a URL, then put it in `plan.config.json`:

```json
"artifact": {
  "url": "https://claude.ai/code/artifact/<uuid>",
  "favicon": "📊",
  "model": "haiku"
}
```

```bash
plan publish            # push the current chart to that URL
plan watch install      # …and do it within 60s of anyone pushing
```

Three things make this cheap enough to run continuously:

- **It skips when nothing changed.** The published bytes are hashed; an
  identical chart costs nothing and takes 80ms.
- **It runs on Haiku.** Publishing is one tool call and no reasoning. On Opus
  the same job costs 33× more and takes 8× longer, for an identical result.
- **It records the remote's refs *after* its own push**, so the commit it just
  made is already accounted for and cannot trigger the next round. Without
  that, a push-triggered refresh that commits is an infinite loop.

`force: true` is used deliberately: `gantt.html` is regenerated wholesale on
every run, so there is never anything in the live version worth merging — and
without it every run would 409, since a fresh session holds no baseline.

**Known gap:** the watcher polls git refs, so it sees pushes, not PR
open/close. Those usually follow a push within minutes; the 09:00 job catches
whatever slipped through.

---

## Set up a project

```bash
cd ~/Projects/whatever
plan init
# edit plan.config.json — streams, owners, GitHub handles, repo, start date
# write the backlog, or run /plan-init in Claude Code and let it draft one
plan refresh
plan cron install
```

The backlog is plain markdown, one file per stream:

```markdown
# Stream A — Backend

## Phase 1 — foundation
- [ ] **A-001** Database schema and migrations
- [ ] **A-002** 🔴 **Auth service** — the frontend cannot log in without it
```

`## headings` become milestones. **🔴** marks a task another stream is waiting
on. Estimates and dependencies go in `<plan_dir>/seed.txt` the first time, and
in `tasks.csv` after that.

---

## How it decides what is done

Nobody reports status. It is read out of git:

| Git says | Status |
|---|---|
| Task ID in a commit subject merged to the integration branch | **done** |
| Task ID on an open pull request | **in review** |
| Task ID in a branch name or unmerged commit subject | **in progress** |
| Nothing | **to do** |

So the one habit the team needs is the task ID in the commit subject —
`feat(auth): A-012 login endpoint`. A body trailer (`Tasks: A-020, A-021`) works
for a commit finishing several at once.

Task IDs mentioned in prose in a commit *body* are deliberately ignored. A docs
commit listing the whole backlog would otherwise mark the whole backlog done —
which is exactly what happened the first time this ran.

When git genuinely cannot see the truth, `overrides.json` takes an entry with a
reason. An override without one is how a plan starts reporting what people wish
were true.

---

## How it schedules

- **Working calendar** — Monday to Friday, minus org holidays and per-developer
  leave. Half-day granularity.
- **Resource-constrained** — one developer does one task at a time. Each morning
  each developer takes whichever of their *ready* tasks can start soonest; ties
  go to whatever another stream is waiting on, then down the backlog in order.
  Work fills gaps rather than idling behind a cross-stream wait.
- **A handoff costs a day.** You continue your own work the same afternoon; work
  passed to someone else lands the next working day.
- **Float and the driving chain** come from a backward pass over both the
  dependency edges and the resource links.

**Float and "critical" are not the same thing.** With developers loaded above
90% almost everything has zero float — that says the team is saturated, not what
to watch. The driving chain is the single path that actually sets the finish
date. That is the one to defend.

**Baselines freeze on first sight and are never rewritten.** If a plan
re-baselines itself every morning, every slip quietly erases itself overnight
and nobody can say how late the project is. Re-baseline deliberately, by
clearing the baseline columns, not by accident.

---

## What it produces

| | |
|---|---|
| `tasks.csv` | the ledger — every task, estimate, dependency, baseline, forecast, float |
| `GANTT.md` | summary, driving chain, milestone bars, full task table. Renders in GitHub |
| `gantt.html` | interactive chart — filter by developer, milestone, status; zoom; hover for detail |
| `standup/YYYY-MM-DD.md` | one brief per developer per working day |

Briefs post to a long-lived GitHub issue per stream, so each developer gets an
email and the thread becomes the record of what they were asked to do and when.

---

## Configuration

`plan.config.json`, in the project root:

```json
{
  "project": "EduTrack",
  "repo": "debashisedunext/EduTrack",
  "start": "2026-08-03",
  "branch": "develop",
  "plan_dir": "docs/plan",
  "task_id": "[A-D]-\\d{3}",
  "streams": {
    "A": { "title": "Platform", "owner": "Shivendra", "github": "shivendraedunext-18",
           "backlog": "docs/streams/STREAM-A-PLATFORM.md" }
  }
}
```

`repo` empty disables PR status and briefs; everything else still works.
Eight streams maximum — past that no two chart colours are reliably
distinguishable, and the answer is two plans, not a ninth hue.

Holidays and leave go in `<plan_dir>/calendar.json`. Fill them in before anyone
reads a date off the plan.

---

## Layout

```
plan                      the CLI
engine/
  planconfig.py           finds and validates plan.config.json
  extract.py              backlog markdown → tasks.csv
  schedule.py             git status, CPM, resource levelling, all outputs
  notify.py               briefs → GitHub issues
  gantt_template.html     the interactive chart
  test/render_check.js    executes the chart's JS and asserts it builds
skills/
  plan-init/              Claude: turn a spec into a backlog and a ledger
  plan-review/            Claude: interrogate an existing schedule
templates/                what `plan init` copies in
```

`plan check` runs the render test. It exists because a syntax check passes a
scope error straight through — the chart shipped blank once for exactly that
reason.
