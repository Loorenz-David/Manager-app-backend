#!/usr/bin/env python3
"""Derive the criterion-row and criteria totals for the stock_report plan set.

Charter manifest property 3: every count is derived, never typed. Run this at every
gate and paste its output; do not increment a published number by hand.

    python3 docs/architecture/under_construction/implementation/stock_report/count_criteria.py

Two things this script gets right that ad-hoc greps got wrong on 2026-09-21:

1. **Scope.** It counts only inside each plan's `## 6. Criteria` section, stopping at the
   next `## ` heading. Plans also carry `| C…` lines in their §7 mutation ledgers and §8
   Review logs; counting the whole file inflates the total (it produced a bogus 713 against
   the true 645).
2. **Shorthand.** A line like `| C8(a)–C8(d) | … |` is ONE table line standing for FOUR
   criterion rows, and `| C2(a)–(f) |` repeats the group only on the left. Both forms are
   expanded. Across the set this is worth +62 rows (583 table lines -> 645 rows).

Withdrawn rows (struck through with `~~`) are excluded and reported separately.
"""

import re
import sys
from pathlib import Path

PLANS = [
    "plan_1", "plan_2", "plan_3", "plan_4", "plan_5", "plan_6", "plan_7", "plan_8",
    "plan_8A", "plan_9", "plan_10", "plan_11", "plan_12", "plan_13", "plan_13A", "plan_14",
]

# C3(f)–C3(i)  or  C2(a)–(f)   — en dash, em dash or hyphen
RANGE_RE = re.compile(r"\*{0,2}~{0,2}C(\d+)\(([a-z])\)\s*[–—-]\s*(?:C(\d+))?\(?([a-z])\)")
SINGLE_RE = re.compile(r"\*{0,2}~{0,2}C(\d+)\(([a-z])\)")


def count(path: Path):
    lines = path.read_text().split("\n")
    start = next((i for i, l in enumerate(lines) if re.match(r"^## 6\.", l)), None)
    if start is None:
        raise SystemExit(f"{path.name}: no '## 6.' section")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))

    table_lines = rows = withdrawn = 0
    criteria: set[int] = set()

    for line in lines[start:end]:
        if not line.startswith("| C"):
            continue
        first = line.strip().strip("|").split("|")[0].strip()
        struck = "~~" in first
        table_lines += 1

        m = RANGE_RE.match(first)
        if m:
            g1, a, g2, b = int(m.group(1)), m.group(2), int(m.group(3) or m.group(1)), m.group(4)
            n = ord(b) - ord(a) + 1
            if struck:
                withdrawn += n
                continue
            rows += n
            criteria.update(range(g1, g2 + 1))
            continue

        m = SINGLE_RE.match(first)
        if m:
            if struck:
                withdrawn += 1
                continue
            rows += 1
            criteria.add(int(m.group(1)))

    return table_lines, rows, len(criteria), withdrawn


def main() -> int:
    here = Path(__file__).parent / "plans"
    t_lines = t_rows = t_crit = t_wd = 0

    print(f"{'plan':10s} {'lines':>6s} {'rows':>6s} {'criteria':>9s}  notes")
    for name in PLANS:
        lines_n, rows, crit, wd = count(here / f"{name}.md")
        t_lines += lines_n
        t_rows += rows
        t_crit += crit
        t_wd += wd
        notes = []
        if rows != lines_n:
            notes.append(f"+{rows - lines_n} from shorthand")
        if wd:
            notes.append(f"{wd} withdrawn, excluded")
        print(f"{name:10s} {lines_n:6d} {rows:6d} {crit:9d}  {'; '.join(notes)}")

    print(
        f"\nDERIVED TOTAL: {t_rows} criterion rows in {t_crit} criteria across {len(PLANS)} plans"
        f"\n  table lines {t_lines} + {t_rows - t_lines} shorthand expansion = {t_rows} rows"
        + (f"\n  {t_wd} withdrawn rows excluded" if t_wd else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
