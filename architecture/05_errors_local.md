> Extends: 05_errors.md

# 05 — Error Contract: App-Local Extensions

## Standing divergence — there is no `code` field

`05_errors.md` defines a class attribute `code: str` on `DomainError` and every subclass
(`not_found`, `forbidden`, `bad_request`, `conflict`), and a `STATUS_MAP` in the response
builder that maps error type → HTTP status.

**Neither exists in this application.** `errors/base.py:3-10` is:

```python
class DomainError(Exception):
    """Only DomainError subclasses cross layer boundaries."""
    http_status: int = 500

    def __init__(self, message: str = "An unexpected error occurred.") -> None:
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        return self.message
```

Two differences, and both matter to anything you write:

1. **No `code` attribute.** A `DomainError` carries `message` and nothing else that
   reaches the client.
2. **`http_status` lives on the class, not in a map.** `ValidationError` → 422 (not the
   canonical 400), `ConflictError` → 409, `NotFound` → 404, `PermissionDenied` → 403,
   `AuthenticationRequired` / `RefreshTokenRejected` → 401, `ExternalServiceError` → 502,
   bare `DomainError` → 500. `build_err` (`routers/http/response.py`) reads
   `error.http_status` directly; adding a `STATUS_MAP` would be a second source of truth
   for the same fact.

The error payload is therefore:

```json
{ "error": "<the message>", "ok": false }
```

There is no `code` key. Do not add one to a single error class — a `code` that appears on
some errors and not others is worse than none at all, because clients then branch on its
presence.

*(One partial exception exists and is not a precedent: `PermissionDenied` accepts an
optional `code` **instance** argument, used only by `RefreshTokenRejected` to carry
`auth_refresh_rejected` for internal auth logging. `build_err` never reads it, so it never
reaches a client.)*

---

## The consequence: an error identity is the leading token of the message

Because there is no machine-readable code field, any error a client must **branch on**
carries its identity in the message, in the shape:

```
<IDENTITY>: <human sentence>
```

- `IDENTITY` is `SCREAMING_SNAKE_CASE`, unique across the application, and stable — it is
  the contract. Renaming one is a breaking API change.
- The sentence after the colon is display copy and may be reworded freely.
- Clients match on the leading token, never on the sentence. Tests assert the exact
  leading token plus the class and `http_status`, never the whole sentence.

Examples in the tree:

```python
raise ValidationError("ITEM_COST_ITEM_UNVALUED: item has no current valuation")
raise ValidationError("ITEM_MONEY_MOVED: item money fields moved to the item-valuation endpoint")
raise ConflictError("ITEM_COST_CONCURRENT_COMMIT: configuration conflicts with an existing row")
```

### When an identity is required

- The client has to do something different for this failure than for its siblings on the
  same endpoint (show a different screen, retry, route to a setup flow).
- Two failures on one endpoint share an HTTP status and must be told apart.
- A test needs to prove that *this specific* refusal fired, and not a neighbouring one
  that happens to produce the same status.

A plain sentence with no identity is correct for a one-of-a-kind failure the client can
only surface verbatim.

### Rules for identities

- **Register the name before using it.** An identity invented at implementation time is
  an unregistered public API. Route it through whatever registry the current work is
  governed by.
- **One identity per meaning, across every path that can produce it.** When a rule is
  enforced both by an application pre-check and by a database constraint, both paths raise
  the *same* identity — the pre-check as `ValidationError`, the database conflict as
  `ConflictError`. A client that has to know which layer caught it has been handed an
  implementation detail.
- **Put the discriminating values in the sentence**, not in extra keys: which two
  currencies disagreed, which ids collided, which category was already taken.
- **Never build an identity by string concatenation at the raise site** unless the prefix
  itself is a registered family (`ITEM_COST_BASIS_VERSION` + `_EFFECTIVE_FROM_FUTURE` is a
  registered family; ad-hoc f-strings are not) — otherwise the identity is ungreppable and
  the registry cannot be checked against the code.

---

## `run_service` remains the only error boundary

Unchanged from the canonical contract: `services/run_service.py` catches `DomainError` and
returns `StatusOutcome(success=False, error=exc)`; the router calls `build_err`. Commands
and queries raise; they never build responses, never catch their own domain errors to
reshape them, and never return an error dict.

**Pydantic-side validators raise the repo's `DomainError`, not `ValueError`.** A
`ValueError` raised inside a pydantic validator reaches the client mangled by pydantic's
field-locator prefix, which destroys the leading-token contract. A `DomainError` raised
there propagates unwrapped through pydantic to `run_service` and surfaces exactly as
written.
