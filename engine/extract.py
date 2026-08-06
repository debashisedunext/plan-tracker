#!/usr/bin/env python3
"""
Build (or refresh) the task ledger from the project's backlog files.

Titles, milestones and blocker flags come from the markdown backlogs, which stay
the human-readable source. Estimates and dependency edges come from an optional
`seed.txt` the first time a task is seen.

Re-running is safe and non-destructive: anything already in `tasks.csv` wins.
New task IDs are appended; a task removed from a backlog is kept and flagged
`dropped` rather than deleted, because a row that vanishes takes its history
with it.
"""
import csv
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import planconfig  # noqa: E402

HEAD_RE = re.compile(r"^## (.+)$")
SUBHEAD_RE = re.compile(r"^### (.+)$")
SCREEN_RE = re.compile(r"\*\*(S-\d{2})\*\*")
REF_RE = re.compile(r"§([\d.]+[A-Za-z]?[\d.]*)")
SEED_RE = re.compile(r"^\s*([^|\s]+)\s*\|\s*([\d.]+)\s*\|\s*([^|]*)\|?\s*(\w*)\s*$")

SEPARATORS = (" — ", " – ", ": ", ". ", " (")

COLUMNS = [
    "id", "stream", "owner", "github", "milestone", "section", "title",
    "screen", "blueprint_ref", "is_cross_stream_blocker",
    "estimate_days", "predecessors", "pred_confidence",
    "baseline_start", "baseline_end",
    "forecast_start", "forecast_end",
    "status", "pct", "actual_start", "actual_end",
    "float_days", "is_critical", "evidence", "notes",
]


def clean_title(text, limit):
    """
    Reduce a backlog line to a label that fits a chart row.

    A backlog entry carries the task *and* its rationale. All of that belongs in
    the backlog file; a chart row needs the name. So cut at the last natural
    break that still fits — which keeps "Flyway baseline 1/5 — identity" rather
    than either a bare "Flyway baseline 1/5" or the whole trailing column list.
    The full text stays on the row's title attribute and in the tooltip.
    """
    t = re.sub(r"🔴\s*", "", text)
    t = re.sub(r"\*\*(S-\d{2})\*\*", "", t)
    t = re.sub(r"\*\*|`|\*", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) <= limit:
        return t.rstrip(" .:—–")

    cuts = sorted({t.find(s) for s in SEPARATORS if 0 < t.find(s)})
    fitting = [c for c in cuts if c <= limit]
    if fitting:
        return t[:max(fitting)].rstrip(" .:—–,(")
    head = t[:cuts[0]] if cuts else t
    if len(head) <= limit:
        return head.rstrip(" .:—–,(")
    return head[:limit].rsplit(" ", 1)[0].rstrip(" .:—–,(") + "…"


def load_seed(cfg):
    """Optional `seed.txt`:  ID | estimate_days | pred,pred | c|i"""
    path = cfg.path("seed.txt")
    out = {}
    if not os.path.exists(path):
        return out
    for n, raw in enumerate(open(path, encoding="utf-8"), 1):
        line = raw.split("#")[0].strip()
        if not line:
            continue
        m = SEED_RE.match(line)
        if not m:
            print("  seed.txt:%d ignored — expected `ID | days | preds | c`" % n)
            continue
        tid, est, preds, conf = m.groups()
        out[tid] = (float(est),
                    [p.strip() for p in preds.split(",") if p.strip()],
                    "confirmed" if conf.lower().startswith("c") else "inferred")
    return out


def backlog_files(cfg):
    """Every file matching the configured globs, per stream where declared."""
    found = []
    for key, s in cfg.streams.items():
        if s["backlog"]:
            for p in sorted(glob.glob(os.path.join(cfg.root, s["backlog"]))):
                found.append((key, p))
    if found:
        return found
    # No per-stream backlog: fall back to the global globs and read the stream
    # key out of each task ID's first character.
    for pattern in cfg.backlogs:
        for p in sorted(glob.glob(os.path.join(cfg.root, pattern))):
            found.append((None, p))
    return found


def parse(cfg, stream_key, path):
    task_re = cfg.task_re
    milestone = section = ""
    out = []
    for line in open(path, encoding="utf-8"):
        h = HEAD_RE.match(line)
        if h:
            milestone, section = h.group(1).replace("·", "—").strip(), ""
            continue
        s = SUBHEAD_RE.match(line)
        if s:
            section = s.group(1).strip()
            continue
        m = task_re.match(line)
        if not m:
            continue
        checked, tid, body = m.groups()
        key = stream_key or tid[0]
        if key not in cfg.streams:
            print("  %s: task %s has no stream %r in plan.config.json — skipped"
                  % (os.path.basename(path), tid, key))
            continue
        st = cfg.streams[key]
        screens = SCREEN_RE.findall(body)
        refs = REF_RE.findall(body)
        out.append({
            "id": tid, "stream": key, "owner": st["owner"], "github": st["github"],
            "milestone": milestone, "section": section,
            "title": clean_title(body, cfg.title_max),
            "screen": screens[0] if screens else "",
            "blueprint_ref": ("§" + refs[0]) if refs else "",
            "is_cross_stream_blocker": "yes" if "🔴" in body else "",
        })
    return out


def main():
    cfg = planconfig.load()
    out_path = cfg.path("tasks.csv")
    os.makedirs(cfg.plan_dir, exist_ok=True)

    existing = {}
    if os.path.exists(out_path):
        with open(out_path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                existing[row["id"]] = row

    seeds = load_seed(cfg)
    files = backlog_files(cfg)
    if not files:
        raise planconfig.ConfigError(
            "No backlog files matched %s.\nCheck `backlogs` (or each stream's "
            "`backlog`) in %s." % (", ".join(cfg.backlogs), cfg.config_path))

    rows, seen, unseeded = [], set(), []
    for key, path in files:
        for t in parse(cfg, key, path):
            if t["id"] in seen:
                print("  duplicate task ID %s — later definition ignored" % t["id"])
                continue
            seen.add(t["id"])
            prev = existing.get(t["id"], {})
            est, preds, conf = seeds.get(t["id"], (1.0, [], "inferred"))
            if t["id"] not in seeds and t["id"] not in existing:
                unseeded.append(t["id"])
            row = {c: "" for c in COLUMNS}
            row.update(t)
            row.update({
                # Existing values win — the CSV is the source of truth once written.
                "estimate_days": prev.get("estimate_days") or ("%g" % est),
                "predecessors": prev.get("predecessors") or ",".join(preds),
                "pred_confidence": prev.get("pred_confidence") or conf,
                "baseline_start": prev.get("baseline_start", ""),
                "baseline_end": prev.get("baseline_end", ""),
                "notes": prev.get("notes", ""),
            })
            rows.append(row)

    dropped = [r for tid, r in existing.items() if tid not in seen]
    for r in dropped:
        r["notes"] = (r.get("notes", "") + " | dropped from backlog").strip(" |")
        rows.append({c: r.get(c, "") for c in COLUMNS})

    rows.sort(key=lambda r: r["id"])
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    new = len(seen - set(existing))
    print("tasks.csv: %d rows (%d new, %d dropped) from %d backlog file(s)"
          % (len(rows), new, len(dropped), len(files)))
    if unseeded:
        print("  no estimate yet, defaulted to 1 day: %s%s"
              % (", ".join(unseeded[:12]),
                 " …and %d more" % (len(unseeded) - 12) if len(unseeded) > 12 else ""))
        print("  → set them in %s, or in %s"
              % (os.path.relpath(out_path, cfg.root),
                 os.path.relpath(cfg.path("seed.txt"), cfg.root)))


if __name__ == "__main__":
    main()
