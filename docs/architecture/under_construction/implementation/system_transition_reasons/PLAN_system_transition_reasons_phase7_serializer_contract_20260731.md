# PLAN_system_transition_reasons_phase7_serializer_contract_20260731

## Metadata

- Plan ID: `PLAN_system_transition_reasons_phase7_serializer_contract_20260731`
- Status: `under_construction`
- Owner agent: `<implementer>`
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T00:00:00Z`
- Master plan: `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention plan: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## Goal and intent

- Goal: remove the `startswith("par_")` prefix-sniffing branch from `domain/users/serializers.py`
  and settle what the API surfaces for a typed transition.
- Business/user intent: master-plan success criterion 4 — no field's meaning is determined by
  sniffing an id prefix. That branch is the intention's clearest evidence of the problem; deleting
  it is the visible end of it.
- Non-goals: editing the frontend handoff (operator-owned — this phase **proposes**); historical
  data (phase 8); catalog retirement (phase 9).

## Scope

- In scope: `domain/users/serializers.py` and any other serializer surfacing `reason` /
  `reason_text`; a written handoff-change proposal for the operator.
- Out of scope: every `docs/handoff/to_frontend/` file. Editing one is a scope violation.
- Assumptions: phases 1–6 archived.

## Clarifications required

- [ ] Does the API surface `transition_reason` to clients as a new field, or does it keep producing
      the existing `reason` / `reason_text` shape with the type resolved server-side? Blocks because
      the first is a contract addition needing a handoff and frontend coordination; the second is
      invisible to clients. **Operator decision — escalate.** Default if unanswered: the invisible
      option, because it needs no frontend work.

## Acceptance criteria

1. The `startswith(f"{PauseReason.CLIENT_ID_PREFIX}_")` branch is gone, or is provably dead with a
   test proving no input can reach it. (Success criterion 4 accepts either.)
2. The published three-way `reason_text` contract — absent / string / null — behaves **exactly** as
   documented in the handoff's §5.3 nullability conventions, for: a system transition, a
   worker-chosen catalog pause, a declared state, and a legacy free-text row. Four cases, four
   tests, asserted against the handoff text.
3. **No published contract changes without an operator-approved handoff update.** If this phase
   concludes a change is needed, it writes a proposal into its Review log and STOPS. It does not
   edit the handoff and does not flip a liveness row.
4. Legacy rows still serialize correctly — pre-phase rows with free-text `reason` produce the same
   output they do today. Prove with seeded rows.
5. The kiosk clock-out analytics contract (declared_worker_states, published) is unaffected, or the
   effect is written into the proposal. Re-run the phase 2 compatibility test.
6. No serializer surfaces the raw `transition_reason` enum value where a human-readable label is
   expected, and no client-visible string changes without appearing in the proposal.

## Contracts and skills

### Contracts loaded

- `backend/architecture/46_serialization.md`: output shapes.
- `backend/architecture/23_documentation.md`: handoff discipline.

### File read intent — pattern vs. relational

- Permitted (relational): `domain/users/serializers.py`; the handoff §5.1/§5.3 to know the contract
  being preserved; phase 0's read-path audit.
- Prohibited (pattern): reading other serializers for output-shape style — `46_serialization.md`
  covers it.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`

## Implementation plan

1. Escalate the clarification; wait for the ruling.
2. Remove the prefix branch; resolve the label from `transition_reason` via phase 2's shared map.
3. Write the four contract-conformance tests (criterion 2).
4. Legacy-row serialization tests (criterion 4).
5. Re-run the phase 2 `pause_by_reason` compatibility test.
6. If any contract change is required, write the proposal into the Review log. Do not edit the
   handoff.
7. Review log entry. STOP.

## Risks and mitigations

- Risk: a silent breaking change ships to a frontend that already built against the contract. This
  happened once in this codebase — `pause_by_reason` keys went opaque with no lookup map, caught
  only in post-archive review.
  Mitigation: criteria 2, 3 and 5 — assert against the handoff text, propose rather than edit.
- Risk: the branch is deleted while an input can still reach it, producing a raw id in the UI.
  Mitigation: criterion 1 requires either removal or a proof of deadness.

## Validation plan

- Four contract-conformance tests pass, asserted against handoff §5.3.
- Legacy seeded rows serialize identically to pre-phase output.
- Phase 2 compatibility test still passes.
- Full suite: no new failure nodes vs. baseline. `ruff check` clean on touched files.

## Review log

- `<date>` `<reviewer>`: `<feedback>`

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
