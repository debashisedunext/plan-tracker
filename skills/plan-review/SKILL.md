---
name: plan-review
description: Review the health of an existing plan-tracker schedule — what is slipping, who is overloaded, what is blocked, which dependencies are still unconfirmed. Use when the user asks how the project is going, why a date moved, or what to do about a slipping milestone.
---

# Reviewing a plan

The chart already says *what* the dates are. Your job is to say *why*, and what
to do about it. Read the data, then form a view.

## Get the current state

```bash
plan refresh          # never review a stale schedule
plan config
```

Then read `<plan_dir>/tasks.csv` — that is the ledger, not `GANTT.md`, which is
a rendering of it.

## The five questions worth answering

**1. Has the finish date moved, and what moved it?**
Compare `forecast_end` against `baseline_end` across the driving chain. One task
slipping on the chain moves everything; twenty slipping off it move nothing.
Name the specific task, not "several delays".

**2. Is anybody overloaded?**
Sum `estimate_days` per owner and compare against working days remaining. Above
about 95% there is no absorption left and the first sick day becomes a slip. The
fix is moving work between people, and it is only cheap early.

**3. What is actually blocked right now?**
Tasks whose predecessors are not `done` and whose owner has nothing else ready.
This is the expensive kind of blocked — somebody idle. Blocked-but-busy is fine.

**4. Are people waiting on things that keep being deprioritised?**
A task flagged `is_cross_stream_blocker` that keeps sliding is worse than it
looks: its cost is multiplied by the number of people waiting, and none of that
shows on its own row.

**5. How much of the critical path is still guesswork?**
Count `pred_confidence == inferred` on the driving chain. If it is most of it,
the date has an error bar nobody has been told about. Say so.

## How to report it

Lead with the answer, not the method. Give the finish date and whether it moved.
Then at most three things that need a decision, each with a specific
recommendation — "move C-025…C-028 to Debashis, who has 27 days of slack", not
"consider rebalancing".

Distinguish clearly between:

- **Slip that is absorbed** — off the chain, float remains, no action.
- **Slip that moved the date** — on the chain, needs a decision now.
- **Risk that has not happened yet** — an unconfirmed estimate, a person at 98%,
  a dependency nobody has validated.

If the plan is fine, say it is fine in one line. Do not manufacture concerns to
justify the review.

## What not to do

Do not re-baseline to make slip disappear. Baselines are frozen deliberately;
regenerating them is how a project arrives three months late having reported
green every week. If the user genuinely wants a new baseline — a re-plan, a
scope change — clear the `baseline_start` and `baseline_end` columns explicitly
and say in the commit message why.

Do not adjust estimates downward because the total is uncomfortable. Report the
total and let the user decide what to cut.
