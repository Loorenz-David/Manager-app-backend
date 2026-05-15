> Extends: 07_queries.md

# 07 — Query Contract: App-Local Extensions

## Pagination override — offset-based (replaces cursor-based section)

This app uses **offset-based pagination**, not cursor-based. The cursor-based section
in `07_queries.md` does not apply here. Use the pattern below exclusively.

### Query params

| Param | Type | Default | Max |
|---|---|---|---|
| `limit` | int | 50 | 200 |
| `offset` | int | 0 | — |

### Implementation pattern (copy exactly)

```python
_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_<entities>(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))

    result = await ctx.session.execute(
        select(<Entity>)
        .where(
            <Entity>.workspace_id == ctx.workspace_id,
            <Entity>.is_deleted.is_(False),
        )
        .order_by(<Entity>.created_at.asc())
        .offset(offset)
        .limit(limit + 1)          # fetch one extra to detect has_more
    )
    rows = result.scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "<entity_plural>": [serialize_<entity>(r) for r in page],
        "<entity_plural>_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }
```

### Router pattern (mirrors the query)

```python
@router.get("")
async def list_<entities>_route(
    claims: dict = Depends(require_roles([...])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"limit": limit, "offset": offset},
        identity=claims,
        session=session,
    )
    ...
```

---

## Completion gate — list queries

**A list query is INCOMPLETE if any of the following are true. Do not mark it done
or submit it for review until every item is satisfied.**

- [ ] Response includes `<entity_plural>_pagination` as a top-level key
- [ ] `has_more` is derived from fetching `limit + 1` rows (not a count query)
- [ ] Both the empty-list path and the non-empty path return the pagination key
- [ ] Router declares `limit: int = Query(50, le=200)` and `offset: int = Query(0, ge=0)`
- [ ] Router passes `query_params={"limit": limit, "offset": offset}` into `ServiceContext`
- [ ] `_MAX_LIMIT = 200` and `_DEFAULT_LIMIT = 50` constants are defined in the query module

Missing `<entity_plural>_pagination` in any list query response is a contract
violation — treat it the same as a missing workspace filter.
