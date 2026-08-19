---
plan: 2
role: implementer
round: 1c
date: 2026-08-19
project: simple_valuation_editor
supersedes: 2026-08-19_phase2_implement_r1b.md, 2026-08-19_phase2_implement_r1.md
---

# Session prompt — implement r1c, phase 2 (`simple_valuation_editor`)

## 0. Third attempt — read this first

You have blocked twice, on two instances of **one pattern**: an obligation requiring a
comment at *two* sites while only *one* site was inside the perimeter. **You were right both
times.** The fault was mine both times, and worse, the r1b fix patched the instance you had
found instead of searching for its siblings — which is why you hit the next one immediately.

**That has now been done properly.** Every "comment at both sites" obligation across the
master plan, `plan_2.md` and the intention was swept in one pass. **There are exactly two,
and both are now fully authorized.** There is no third. If a fourth blocker exists it is a
new pattern, not another instance of this one.

Three corrections since r1b:

1. **`app/beyo_manager/domain/cases/serializers.py` is now exception 4** — comment only,
   beside `serialize_user_light` at `:102-108`, naming the re-declared shape in
   `item_economics/serializers.py`. Intention §6 and master plan §4 always required this
   pair; the existing site had never been in any perimeter.
2. **The perimeter roster now lives in `plan_2.md` §2 and nowhere else: 7 table files +
   4 exceptions = 11 files.** My "nine" in r1b was wrong (7 + 3 = 10). **Do not recompute
   it from this prompt — read the roster.**
3. **§2's "Two edits" header and C16's "three exceptions" are corrected** to four, and C16
   gained clause (c) for the `serialize_user_light` pair.

## 1. The two reciprocal pairs, in full

Each pair lands **in the same commit**. A one-way pointer is worse than none — the entire
purpose is that a later consolidation finds *both* sites.

| Pair | Site A | Site B |
|---|---|---|
| `_shape_error` | `price_scenario.py:53-57` (exception 3) | `calculator.py:124-128` (exception 2) |
| `serialize_user_light`'s three-key shape | `item_economics/serializers.py` (in the §2 table) | `cases/serializers.py:102-108` (exception 4) |

**No executable line changes in any of the four exception files.** They are comments and one
test assertion; nothing else.

## 2. Gate check — it has changed again, re-run it

- `plan_2.md` §2 carries a **perimeter roster** reading **7 + 4 = 11**, and enumerates **four**
  exceptions.
- `plan_2.md` §2's blanket line reads *"No change to any **executable line** of
  `price_scenario.py`"*.
- C16 requires the **exact `SliderDomain(step_minor=110, min_minor=3_080, max_minor=12_100)`
  literal** — never a call-to-call equality — and its clause (c) names the
  `serialize_user_light` pair.
- `planning/intention.md` carries **§9.2A**, **§4.4B** and §9A.1's `†` qualification.
- `git status` clean; baseline **2373 / 26 / 1**.

**If any is still false, stop again.** You have been right three times; the presumption is
with you.

## 3. Everything else stands

Read **`prompts/implementer/2026-08-19_phase2_implement_r1.md` §§1–11** for role, workspace,
read order, the five settled projection findings, the three delegations, standing rules,
environment and the closing protocol — with §0–§2 above winning wherever they conflict.

The two that matter most, repeated because they are the expensive ones:

- **D-7 carries a STOP.** Serializing router-side makes an existing test feed
  `fake_run_service`'s `{"ok": "test"}` into your serializer, needing more of
  `test_item_economics_router.py` than the perimeter allows. **Stop and report rather than
  widen it.** Service-side keeps the roster accurate; precedent
  `get_task_production_time.py:82`.
- **The assertion-form rule.** A named mutation's check is on the **assertion form**, not the
  fixture — `f(0) == f(1)` is invariant under any mutation mapping both call sites to the
  same value. Prefer an exact literal. Compute both sides, run the **whole file** (never
  `-k`), record every test that reddens.

## 4. Handoff

As r1 §§10–11, at `handoffs/implementer/2026-08-19_phase2_implement_r1c_handoff.md`. Add:

- the **file count you actually touched, against the roster's 11**;
- confirmation that **no executable line** changed in `price_scenario.py`, `calculator.py` or
  `cases/serializers.py`;
- both reciprocal pairs, each with the two paths and the commit they landed in.
