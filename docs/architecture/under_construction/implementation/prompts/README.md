# Codex Prompts — Shopify Pre-Order Product

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

| Prompt | Plan | Type |
|---|---|---|
| `PROMPT_phase_0_dev_store_verification.md` | `PLAN_shopify_preorder_phase_0_dev_store_verification_20260727.md` | **Manual — not a Codex task** |
| `PROMPT_phase_1_minimum_delivery.md` | `PLAN_shopify_preorder_phase_1_minimum_delivery_20260727.md` | Codex — **the critical path** |
| `PROMPT_shopify_product_sync_error_fidelity.md` | `PLAN_shopify_product_sync_error_fidelity_20260727.md` | Codex — standalone improvement |
| `PROMPT_shopify_product_sync_duplicate_fix.md` | `PLAN_shopify_product_sync_duplicate_fix_20260727.md` | Codex — standalone bug fix, **review gate** |

`GUARDRAILS.md` — standing rules referenced by every prompt. Not a plan.

## Ordering

- **Phase 0 first**, or in parallel with nothing else pending. Its four gates take a morning on the
  dev store and gate the minimum delivery. Gate **0.2** especially: if an `UNLISTED` product leaks
  onto the storefront, that is a scope change requiring merchant reauthorization.
- **Phase 1** is the whole pre-order feature. One session.
- **The two standalone tickets** are independent of pre-orders and of each other. Run them whenever.
  The duplicate fix would benefit pre-orders too, but neither blocks the other.

## Review gates

- After **Phase 1** — a human verifies on the dev store before it ships.
- After the **duplicate fix** — a human reads the diff; it touches live product-sync behaviour.

## Parent plan

`../PLAN_shopify_preorder_product_20260727.md` (rev 8) holds the research record (**R1–R13**) and
the hardening **backlog**. It is ~1300 lines. Each plan here is self-contained — read the parent
only when you need the *why* behind a decision, or when picking a backlog item to promote.
