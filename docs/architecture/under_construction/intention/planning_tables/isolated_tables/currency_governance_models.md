# Currency Governance Models Plan

Status: DRAFT - Bounded Operational Currency Governance
Domain: isolated_tables
Contracts: 01, 03, 08, 21, 24, 25, 36, 40, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define the bounded currency governance used by shared reference tables in this planning phase.

Currency is enum-governed in this phase. A formal currency table is intentionally deferred unless a later phase proves that a richer monetary infrastructure is required.

## 1) Bounded currency enum

### 1.1 currency_enum

Supported values:
- SWEDISH_KRONA
- DANISH_KRONA
- EURO

Governance semantics:
- these values represent supported business currencies for the current application phase
- they are not accounting systems
- they are not a full monetary ledger design
- they are not a foreign-exchange engine
- they are not a general-purpose ISO-4217 registry in this phase

## 2) Currency storage rules

- Shared cost tables should store currency as the bounded enum.
- Do not store money as float.
- currency determines minor-unit interpretation for cost_minor.
- Monetary values should be interpreted as integer-like fixed storage in minor units.
- Future money helper or value-object logic may be introduced in a domain layer later, but the table plan remains enum-governed for now.

## 3) Currency and shared cost semantics

- Currency support is part of operational configuration governance.
- Currency rows are not needed as a standalone table in this phase.
- The bounded enum is sufficient for current shared configuration needs.
- If future applications require broader currency support, exchange-rate handling, or global monetary metadata, that should be introduced deliberately as a new contract rather than by expanding the shared reference layer informally.

## 4) Minor-unit interpretation

The same integer value means different real-world amounts depending on currency, so the currency must always travel with the cost.

Examples:
- 100 SEK = 10000 in öre-level minor units
- 15 EUR = 1500 in cent-level minor units

This means cost_minor is not self-describing without currency.

## 5) Scope boundary

In scope:
- bounded currency enumeration
- minor-unit storage guidance for shared cost tables
- current-phase currency support policy

Out of scope:
- exchange-rate modeling
- accounting ledger currency normalization
- tax systems
- treasury systems
- full monetary infrastructure
- a standalone currency registry table in this phase

## 6) Future evolution notes

Future phases may introduce:
- a formal currency table
- exchange-rate history
- monetary value objects in domain code
- richer rounding or conversion policies
- broader currency support beyond the current business phase

Those additions should happen only when there is a clear operational reason, not preemptively.

## 7) Clarification checklist before implementation

1. Is the bounded currency enum enough for this phase, or is a formal currency table required later?
2. Should any shared table default its currency from workspace settings when omitted, or must currency always be explicit?
3. If broader currency support is needed later, should that live in a dedicated monetary contract rather than expanding this shared reference layer?
