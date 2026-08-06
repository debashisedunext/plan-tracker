"""
Locate and load a project's `plan.config.json`.

Everything project-specific lives in that one file. The engine holds no
knowledge of any particular project — point it at a config and it works.

Search order: `PLAN_CONFIG` in the environment, then the current directory and
each parent up to the filesystem root. So any command works from anywhere
inside the project tree.
"""
import json
import os
import re
import sys

CONFIG_NAME = "plan.config.json"

# Validated categorical palette — eight hues, each pair separated by ΔE ≥ 15 in
# normal vision and ≥ 8 under deuteranopia and protanopia. Streams are assigned
# in order. Do not extend this by picking a "nice next colour": a ninth stream
# means the chart needs faceting, not another hue.
PALETTE = ["#4F46E5", "#F59E0B", "#BE185D", "#06B6D4",
           "#9A3412", "#84CC16", "#9333EA", "#0891B2"]

REQUIRED = ("project", "start", "streams")


class ConfigError(SystemExit):
    pass


def _lighten(hex_color, amount=0.38):
    """Mix towards white for the dark-theme variant of a stream colour."""
    h = hex_color.lstrip("#")
    rgb = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02X%02X%02X" % tuple(int(c + (255 - c) * amount) for c in rgb)


class Config(object):
    def __init__(self, path, data):
        self.config_path = path
        self.root = os.path.dirname(path)
        self.raw = data

        missing = [k for k in REQUIRED if not data.get(k)]
        if missing:
            raise ConfigError("%s is missing: %s" % (path, ", ".join(missing)))

        self.project = data["project"]
        self.repo = data.get("repo", "")
        self.start = data["start"]
        self.backlogs = data.get("backlogs") or ["docs/streams/*.md"]
        self.task_id_pattern = data.get("task_id", r"[A-Z]-\d{3}")
        self.plan_dir = os.path.join(self.root, data.get("plan_dir", "docs/plan"))
        self.branch = data.get("branch", "develop")
        self.notify = data.get("notify", "github-issues")
        self.title_max = int(data.get("title_max", 68))
        self.hours_per_day = float(data.get("hours_per_day", 8))

        self.streams = {}
        for i, (key, s) in enumerate(sorted(data["streams"].items())):
            if not re.match(r"^[A-Za-z0-9]{1,4}$", key):
                raise ConfigError(
                    "Stream key %r must be 1-4 letters or digits — it becomes a CSS "
                    "custom property name in the chart." % key)
            if not s.get("owner"):
                raise ConfigError("Stream %s has no owner." % key)
            self.streams[key] = {
                "key": key,
                "title": s.get("title", key),
                "owner": s["owner"],
                "github": s.get("github", ""),
                "color": s.get("color", PALETTE[i % len(PALETTE)]),
                "backlog": s.get("backlog", ""),
            }
        if len(self.streams) > len(PALETTE):
            raise ConfigError(
                "%d streams but only %d distinguishable colours. Merge streams, or "
                "run two plans." % (len(self.streams), len(PALETTE)))

    # ── derived ────────────────────────────────────────────────────────────
    @property
    def task_re(self):
        """Matches a backlog line:  - [ ] **A-001** Do the thing."""
        return re.compile(r"^- \[([ x])\] \*\*(%s)\*\*\s*(.*)$" % self.task_id_pattern)

    @property
    def id_re(self):
        """Matches a bare task ID anywhere — commit subjects, branch names."""
        return re.compile(r"\b(%s)\b" % self.task_id_pattern)

    def owner_of(self, key):
        return self.streams[key]["owner"]

    def stream_colors_css(self):
        """The `--sA: #…` blocks the chart template needs, light and dark."""
        light = " ".join("--s%s: %s;" % (k, s["color"]) for k, s in self.streams.items())
        dark = " ".join("--s%s: %s;" % (k, _lighten(s["color"]))
                        for k, s in self.streams.items())
        return light, dark

    def path(self, *parts):
        return os.path.join(self.plan_dir, *parts)


def find(start=None):
    env = os.environ.get("PLAN_CONFIG")
    if env:
        if not os.path.exists(env):
            raise ConfigError("PLAN_CONFIG points at %s, which does not exist." % env)
        return env
    here = os.path.abspath(start or os.getcwd())
    while True:
        candidate = os.path.join(here, CONFIG_NAME)
        if os.path.exists(candidate):
            return candidate
        parent = os.path.dirname(here)
        if parent == here:
            raise ConfigError(
                "No %s found here or in any parent directory.\n"
                "Run `plan init` in the project root to create one." % CONFIG_NAME)
        here = parent


def load(start=None):
    path = find(start)
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except ValueError as e:
        raise ConfigError("%s is not valid JSON: %s" % (path, e))
    return Config(path, {k: v for k, v in data.items() if not k.startswith("_")})


if __name__ == "__main__":
    cfg = load()
    print("config   %s" % cfg.config_path)
    print("project  %s" % cfg.project)
    print("repo     %s" % (cfg.repo or "(none)"))
    print("start    %s" % cfg.start)
    print("plan dir %s" % os.path.relpath(cfg.plan_dir, cfg.root))
    print("backlogs %s" % ", ".join(cfg.backlogs))
    print("task ids %s" % cfg.task_id_pattern)
    for k, s in cfg.streams.items():
        print("  %-3s %-22s %-12s %s %s"
              % (k, s["title"], s["owner"], s["color"],
                 "@" + s["github"] if s["github"] else ""))
    sys.exit(0)
