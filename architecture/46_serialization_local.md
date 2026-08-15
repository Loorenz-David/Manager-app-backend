> Extends: 46_serialization.md

# 46 — Serialization Contract: App-Local Extensions

## Standing divergence — serialization lives in the query layer, not the router

`46_serialization.md` mandates **router-owned serialization**: services return dataclasses
or ORM instances, and the router turns them into wire shapes ("services never call
serializer functions"; dataclasses, never dicts).

**This application does the opposite in its task, item and working-section query layers.**
Those services build the response dict themselves — they import `serialize_*` helpers from
`domain/<area>/serializers.py` and return a plain dict, which the router hands to
`build_ok` unchanged. This is not an oversight in a handful of files; it is the shape of
the entire read layer.

### The rule that binds

**A change keeps serialization where the code it modifies already has it.**

- Modifying a query service that serializes inline → keep serializing inline there.
- Writing a genuinely new surface with no surrounding precedent → follow the canonical
  contract and serialize in the router.
- Re-emitting the contract bundle before a change is **never** licence to relocate
  serialization mid-change. A refactor that moves serialization from the query layer to
  the router is its own piece of work, deliberately scoped, and is not something a feature
  change does on the way past.

The reason is not that the canonical contract is wrong. It is that a partial migration is
strictly worse than either end state: two conventions in the same layer means the next
reader cannot tell which one a given file is supposed to follow, and every review argues
it again.

### The one place the divergence must not spread

Serialization location is a style question. **Which fields a serializer emits is not.**
Where a payload is money- or role-sensitive, the safeguard is a declared field of the
serializer's interface, failing closed — a keyword-only parameter with no default, so a
new call site cannot inherit the sensitive field by silence. See
`domain/tasks/serializers.py::serialize_step` and
`architecture/28_roles_permissions.md`. That discipline is canonical and is not affected
by where the call happens.

## Overridden behaviour

| Canonical rule | Local reality |
|---|---|
| Services never call serializer functions | Task / item / working-section / item-economics query services call them directly |
| Services return dataclasses, never dicts | Those services return dicts; the router passes them to `build_ok` |
| The router owns the wire shape | The query owns it; the router owns only the envelope and the role gate |

Everything else in `46_serialization.md` stands unchanged — in particular the envelope
(`{"data": …, "ok": true, "warnings": []}` / `{"error": …, "ok": false}`), the
`<entity>` / `<entity_plural>` key naming, `Decimal`-as-string, and ISO-8601 UTC datetimes.

## Local decisions

- **Decimals serialize as strings**, never as floats — money is integer minor units and
  rates/percentages are `Decimal`. A float in a payload is a defect, not a formatting
  choice.
- **A redacted field is absent from the dict, not null.** A null key still tells the
  caller that the value exists and is being withheld, which for money is itself the leak.
- **Role-split payloads get separate serializer functions**, not a flag threaded through
  one function, wherever the two shapes differ by more than one key.
