# ⚠ OWNER DECISIONS REQUIRED (4) — worker_compensation intention

```
role: owner-decision ledger (companion to intention.md §16)
date: 2026-08-11
state: OPEN — all four unanswered; every gate they block holds until answered
```

Answer each card in one line in its `ANSWER:` slot (or reply in a session — the shaper
will fold answers into `intention.md` as a new changelog round). Per the pipeline
charter: on silence the gate holds; nothing is guessed.

---

## Card 1 — Salary fields on the user API

**Question:** Remove both salary fields from the user API — register becomes the input
for an initial hourly compensation, and `salary_per_hour_after_tax` is dropped without
migration?

**Story:** You register a worker at 200 SEK before tax / 140 after tax; both come back in
every `GET /users/{id}` today, so the frontend may render them. After the change,
compensation lives in its own records — if the old fields keep echoing, the app shows a
number nothing maintains; and after-tax has never fed a single calculation anywhere.

**Branches:**
- (a) hard-remove both now — cleanest, frontend must update in step;
- (b) keep before-tax as a read-only mirror of current compensation during transition;
- (c) keep both writable — prolongs the broken semantics.

**Recommendation:** (b) — register seeds an initial hourly compensation, GET mirrors the
current version's rate, PATCH stops accepting both, after-tax dropped everywhere.

**On silence:** gate holds — no bridge built, columns not dropped, migration blocked.

**Trace:** intention §4.3, §9.3–9.5, §16.

**ANSWER:** _(pending)_

---

## Card 2 — Statutory default components

**Question:** Seed a workspace-default statutory component set (arbetsgivaravgift
31.42%, semester ~12%) that is auto-applied when a compensation version is created?

**Story:** You enter 35,000 SEK/month and forget arbetsgivaravgift. The dashboard prices
the worker at ~202 SEK/h when the real employer cost is ~265 SEK/h — every item's labor
cost silently understated by a third. With a seeded default set, each new version starts
realistic and you only edit exceptions.

**Branches:**
- yes — costs realistic by default, defaults copied onto the version (never live-linked);
- no — components empty until each admin configures them.

**Recommendation:** yes — the feature's whole point is *real* costs.

**On silence:** gate holds — the v1 must-ship line stays undecided.

**Trace:** intention §4.2, §6.3, §12.

**ANSWER:** _(pending)_

---

## Card 3 — Cutover reprice of history

**Question:** Run the scoped reprice over all historical analytics at cutover?

**Story:** After migration, old days were priced by the legacy live-rate code and new
days by the compensation pipeline. The migrated versions copy the same rate, so numbers
should match — but nothing proves it until the reprice runs. Running it stamps all
history with pipeline provenance and surfaces any drift immediately, instead of during
some future correction.

**Branches:**
- yes — drained queue, dry-run first, expected delta ≈ 0;
- no — history stays legacy-priced until a correction first touches it.

**Recommendation:** yes — provenance plus early drift detection, at near-zero numeric
risk.

**On silence:** gate holds on migration step §9.6.

**Trace:** intention §9.6, §10.

**ANSWER:** _(pending)_

---

## Card 4 — Who manages compensation

**Question:** Which roles may write and read compensation records?

**Story:** Today a MANAGER can PATCH any worker's salary and read it back. Compensation
records expose the full pay structure — base pay, pension, employer costs. Keep manager
write access and any floor manager can see and change everyone's terms; go ADMIN-only
and managers lose a workflow they may use today.

**Branches:**
- ADMIN-only write+read — tightest, breaks manager workflow;
- ADMIN write / MANAGER read — pay changes are admin acts, managers keep visibility;
- keep today's ADMIN+MANAGER write — no behavior change.

**Recommendation:** ADMIN write, ADMIN+MANAGER read — managers already see cost
analytics.

**On silence:** gate holds on every endpoint's role gate.

**Trace:** intention §2.1, §10.

**ANSWER:** _(pending)_
