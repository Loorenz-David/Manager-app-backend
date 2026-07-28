# Codex Prompts — Shopify Pre-Order Product

> ## ⚠️ Spent — all five plans were implemented and archived on 2026-07-27
>
> Every plan these prompts point at now lives in
> `backend/docs/architecture/archives/implementation/`, with an `ARCHIVE_RECORD_*` in
> `backend/docs/architecture/archives/` and a `SUMMARY_*` in
> `backend/docs/architecture/implemented_summaries/`. **The plan paths inside these prompt files
> are stale** — the files are kept only as a record of how the delivery was driven.
>
> Do not hand any of them to an agent as-is. If you need to redo a piece of the work, cut a fresh
> plan and write a fresh prompt.
>
> Two items remain outstanding, neither of them a prompt: the **Phase 1 dev-store verification**
> (which carries deferred gate 0.2, storefront absence) and the **duplicate-fix human diff review**.
>
> The retained backlog lives in `../PLAN_shopify_preorder_product_20260727.md` (R13). To promote a
> backlog item, cut a new plan citing the relevant research finding.

One prompt per plan. **Start a new Codex session per plan** so context does not accumulate.

> **Rev 8 note.** This folder previously held twelve phase prompts. The scope audit (parent plan
> **R13**) found most of that work was optional hardening rather than pre-order requirements, and
> the public-bucket finding (**R3**) collapsed the image path. Those prompts have been removed —
> keeping precise prompts built on a false premise is worse than having none.

## How to use

1. Open a fresh Codex session.
2. Paste the contents of one prompt file.
3. Let it run to its stated done signal.
4. Review, then move on in a new session.

## Files

| Order | Prompt | Plan | Type |
|---|---|---|---|
| — | `PROMPT_phase_0_dev_store_verification.md` | `…phase_0_dev_store_verification…` | **Manual — David, not Codex.** One gate left |
| **1st** | `PROMPT_shopify_product_sync_characterisation_net.md` | `…product_sync_characterisation_net…` | Codex — safety net, no production changes |
| **2nd** | `PROMPT_phase_1_minimum_delivery.md` | `…phase_1_minimum_delivery…` | Codex — **the critical path** |
| any | `PROMPT_shopify_product_sync_error_fidelity.md` | `…product_sync_error_fidelity…` | Codex — standalone improvement |
| after 1st | `PROMPT_shopify_product_sync_duplicate_fix.md` | `…product_sync_duplicate_fix…` | Codex — standalone bug fix, **review gate** |

`GUARDRAILS.md` — standing rules referenced by every prompt. Not a plan.

## Ordering

1. **Characterisation net** — must land before anything touches
   `_product_sync_orchestrator.py` or `product_sync_client.py`. No production changes; about an hour.
2. **Phase 1** — the whole pre-order feature, one session.
3. **Duplicate fix** and **error fidelity** — whenever. Error fidelity touches only
   `graphql_client.py` and `errors/external_service.py`, so it is safe to run concurrently with
   anything.

**Do not run Phase 1 and the duplicate fix in parallel** — both edit
`_product_sync_orchestrator.py` and two sessions will conflict.

**Phase 0 is complete and blocks nothing.** Three gates resolved; the fourth (storefront absence)
was **deliberately deferred** into Phase 1's post-implementation dev-store verification, where
acceptance criterion 4 already covers it. If it turns out to fail, that is a **scope change** —
two new OAuth scopes plus merchant reauthorization — not a bug fix.

## Review gates

- After **Phase 1** — a human verifies on the dev store before it ships.
- After the **duplicate fix** — a human reads the diff; it touches live product-sync behaviour.

## Parent plan

`../PLAN_shopify_preorder_product_20260727.md` (rev 8) holds the research record (**R1–R13**) and
the hardening **backlog**. It is ~1300 lines. Each plan here is self-contained — read the parent
only when you need the *why* behind a decision, or when picking a backlog item to promote.
