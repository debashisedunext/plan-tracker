---
name: plan-init
description: Set up automated task tracking for a project — turn its spec or backlog into a scheduled ledger with estimates, dependencies, a Gantt chart, daily developer briefs and a 09:00 refresh job. Use when the user wants a project plan, a Gantt chart, a task breakdown across developers, or asks to track who is doing what and what is blocked.
---

# Setting up plan-tracker on a project

Your job is the part no script can do: turn what the project *is* into a ledger
of tasks with owners, estimates and dependency edges. Everything after that —
scheduling, the chart, the briefs, the cron — is mechanical and already built.

Work through these in order. Do not skip step 1.

---

## 1. Read the project before proposing anything

Find and read whatever describes the work: a spec, a PRD, a README, existing
issues, `docs/`. If there is genuinely nothing written, interview the user
instead — you cannot estimate what nobody has described.

You are looking for four things:

- **The surface area** — screens, services, endpoints, jobs. What has to exist.
- **The natural seams** — where work divides with the fewest handoffs.
- **The hard parts** — what is genuinely difficult, versus what merely sounds it.
- **The things that block everything** — a schema, an auth layer, a shared
  component library, an API contract.

Say what you found before you propose a breakdown. If the spec is thin, say so
plainly and estimate wider.

## 2. Propose the streams

One stream per developer. Split **vertically** — each person owns a slice of the
product end to end, backend and frontend — not horizontally by layer. Horizontal
splits (one person does all the APIs, another all the UI) generate a handoff for
every single feature and serialise a team that should be parallel.

Ask the user for names and GitHub handles. Confirm the split before writing
anything: a wrong seam costs weeks and is expensive to undo once IDs are issued.

## 3. Write the backlog

One markdown file per stream. The format is fixed — the extractor depends on it:

```markdown
# Stream A — Platform & Security · Task Backlog

**Owner:** Name · @github-handle
**Branch prefix:** `feat/platform/…`

## Sprint 0 — weeks 1–2

- [ ] **A-001** Maven multi-module skeleton
- [ ] **A-002** 🔴 **Auth profile for local development** — every other stream is blocked without it

## M1 — Authentication · weeks 3–7

- [ ] **A-020** Login endpoint, Argon2id, generic error messages *(spec §10.1)*
```

Rules that matter:

- **`## headings` become milestones** on the chart. `### headings` become sections.
- **🔴 marks a cross-stream blocker** — someone else is waiting. These get
  scheduling priority and appear in the daily briefs of whoever is waiting.
- **`§4.2` references** are picked up and shown on the chart, so link tasks back
  to the spec section that defines them.
- **Task IDs are permanent.** They end up in commit messages and git history.
  Never renumber. To drop a task, delete the line — the ledger keeps the row and
  flags it rather than losing its history.
- **One task ≈ 0.5 to 3 days.** Bigger than that and progress is invisible for a
  week; smaller and the ledger becomes noise.

## 4. Estimate and connect — the part that decides whether this is useful

Write `<plan_dir>/seed.txt`:

```
A-001 | 1.0 |             | c
A-002 | 1.5 | A-001       | c
B-001 | 2.0 | A-002       | i
```

**Estimates** are working days of one developer, half-day granularity, including
tests. Then check the totals against reality: a developer has roughly 5 working
days a week minus meetings, review and rework — plan at about 80% of the calendar.
If a stream's total exceeds the available days, **say so instead of shaving
estimates to fit**. An overloaded stream is the single most useful thing this
exercise surfaces, and it is invisible until you add the numbers up.

**Dependencies.** Mark each `c` (confirmed — the spec or the owner says so) or
`i` (inferred — you worked it out). Be honest about which. Cross-stream edges
matter far more than within-stream ones: they are what actually stalls people.

Then **look for the decouplers** — the two or three tasks that let people work in
parallel who would otherwise queue. A mock API server, a no-auth development
profile, a seed data corpus. These are worth pulling forward ahead of features,
and they are easy to miss because none of them ships to a user.

## 5. Configure, run, report

```bash
plan init                    # scaffolds plan.config.json and the plan directory
# edit plan.config.json: streams, owners, GitHub handles, repo, start date
plan refresh
plan cron install            # 09:00 Mon–Fri
plan check                   # proves the chart renders
```

Fill in `<plan_dir>/calendar.json` with org holidays and known leave. Do this
before anyone reads a date off the plan — without holidays every forecast is
optimistic by exactly the number of holidays in the project.

Then **report what the schedule found**, not just that you built it:

- The finish forecast, and how it compares to what the user expected.
- Any developer loaded above ~95%, and what to move off them.
- The driving chain — the path that actually sets the end date.
- How many edges are still `i`, and that the owners need to confirm them.

## What to tell the user at the end

Three things, briefly:

1. **Put the task ID in the commit subject** — `feat(auth): A-012 login endpoint`.
   That one habit is what keeps status honest with no status meeting. Without it
   everything shows as "to do" forever.
2. **Correct the inferred edges.** One pass, each developer on their own stream.
   Until then the critical path is a hypothesis.
3. **Nothing else is needed.** The 09:00 job refreshes and posts from here on.

---

## Getting it wrong in the usual ways

**Estimates that sum to exactly the time available.** They never do in reality.
If the numbers come out suspiciously neat, they were fitted to the deadline
rather than to the work.

**Every dependency marked confirmed.** If you inferred it, mark it `i`. A plan
that overstates its own confidence is worse than one that admits the gap,
because people act on it.

**A backlog that mirrors the spec's table of contents.** Specs are organised for
reading; work is organised by what has to exist before what else. Reorganise.

**Silent scope.** If the spec omits deployment, migrations, or test data, add
those tasks and say you added them. They are always real work and they are
almost always missing from the document.
