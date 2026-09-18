#!/usr/bin/env python3
"""Translation-pipeline monitor: are the subagents alive and producing?

Reads a run directory (workdir passed to translators) and reports:
  - expected units vs units present, per chapter
  - file mtimes: how long since the last progress (stall detection)
Exit codes: 0 = healthy (progress < STALL_MIN), 1 = stalled, 2 = dead/incomplete.

Usage: python3 tools/watchdog.py <run-dir> [--stall-min 25]
"""
import os, sys, time, json

run = sys.argv[1]
stall_min = 25
if "--stall-min" in sys.argv:
    stall_min = int(sys.argv[sys.argv.index("--stall-min") + 1])

meta = json.load(open(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools", "digest", "index.json"), encoding="utf-8"))

now = time.time()
worst = 0.0
problems = []
for ch in sorted(os.listdir(run)):
    chdir = os.path.join(run, ch)
    udir = os.path.join(chdir, "units")
    if not os.path.isdir(udir):
        continue
    expect = meta[ch]["items"]
    have = sorted(f for f in os.listdir(udir) if f.endswith(".md"))
    newest = max(os.path.getmtime(os.path.join(udir, f)) for f in have) if have else 0
    age = (now - newest) / 60
    worst = max(worst, age)
    if age > stall_min:
        problems.append(f"ch.{ch}: no writes for {age:.0f} min")
    if len(have) < expect + 1:  # +1 for unit 00
        problems.append(f"ch.{ch}: units {len(have)}/{expect + 1}")

if not problems:
    print(f"HEALTHY: all units present, last write {worst:.0f} min ago")
    sys.exit(0)
for p in problems:
    print(p)
sys.exit(1 if worst > stall_min else 2)
