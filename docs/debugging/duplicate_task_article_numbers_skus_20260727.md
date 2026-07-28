# Duplicate article numbers / SKUs across tasks

## Scope

- Database: local PostgreSQL Docker database `beyo_manager` on `127.0.0.1:5433`
- Snapshot date: 2026-07-27
- Workspace scope: `Beyo Workspace` (`ws_01KVX0G0T7Z6NE69YVRVMFAB98`)
- Source relationship: `tasks -> task_items -> items`
- Matching: exact value after trimming leading/trailing whitespace; blank and `NULL` values excluded
- Task-item links: only links with `removed_at IS NULL`
- Deleted tasks: retained in the report so historical reuse is visible

## Result

There are 12 identifier values used by more than one task:

- 11 article numbers
- 1 SKU
- 27 affected tasks in total
- 20 active tasks and 7 soft-deleted tasks
- 7 duplicate groups among active tasks only: 6 article numbers and 1 SKU
- 0 identifier groups repeated twice within the same task

The repeated values are not caused by multiple item rows with the same identifier. Each repeated value points to one item row that is linked to multiple tasks. This indicates item-record reuse across tasks; whether that is valid depends on the intended task lifecycle semantics.

## Repeated identifier summary

| Identifier type | Value | Task links | Active tasks | Deleted tasks | Item row | Item client ID |
|---|---:|---:|---:|---:|---:|---|
| article number | `0000611` | 2 | 1 | 1 | 1 | `itm_01KWW6107561HPG1BZ0YXN6SS3` |
| article number | `0000809` | 4 | 1 | 3 | 1 | `itm_01KWSCWPK1P877CMNETX9XCJ93` |
| article number | `0000824` | 2 | 2 | 0 | 1 | `itm_01KW9BJKK98GMVF1PSFTYN48EB` |
| article number | `0000825` | 2 | 2 | 0 | 1 | `itm_01KW9C9JKZY0NWXRQ66NP4SX1B` |
| article number | `0000874` | 3 | 3 | 0 | 1 | `itm_01KXG1P3TH836GW7BF5TX8SFR1` |
| article number | `0001057` | 2 | 2 | 0 | 1 | `itm_01KWYJFC2R0771XFWVD74ZQBJG` |
| article number | `0001061` | 2 | 1 | 1 | 1 | `itm_01KX0X5JW2ZPHWWN9GCN2H4HYJ` |
| article number | `0001094` | 2 | 2 | 0 | 1 | `itm_01KXDAMDE07BRJ5Q0CJFZ9K0SV` |
| article number | `0001122` | 2 | 1 | 1 | 1 | `itm_01KY0112HA1QPD5D3KJNZQE62` |
| article number | `0723` | 2 | 1 | 1 | 1 | `itm_01KY7GHG386RMR2NY5TJKYB7AY` |
| article number | `T6-260526` | 2 | 2 | 0 | 1 | `itm_01KYFEP0FTKBH3Z74EB4GZYYTQ` |
| SKU | `CH2 15.12` | 2 | 2 | 0 | 1 | `itm_01KWBK1B081QM6HD5Z3DQMY2JK` |

## All affected tasks

`task_status=active` means `tasks.is_deleted = false`; `deleted` means the task is soft-deleted. All listed task-item links have role `primary`, and all linked item rows are active.

| Identifier | Task scalar ID | Task client ID | Type | State | Task status | Item client ID | Task-item client ID |
|---|---:|---|---|---|---|---|---|
| `0000611` | 76 | `tsk_01KWW610752SYM6A4AFVEV9QE1` | internal | working | deleted | `itm_01KWW6107561HPG1BZ0YXN6SS3` | `tim_01KWW61DRJEQKPZQBG6FTK776T` |
| `0000611` | 204 | `tsk_01KXX4NWRCGRAC0VJNP44JQHPS` | pre_order | working | active | `itm_01KWW6107561HPG1BZ0YXN6SS3` | `tim_01KXX4TC011GQAJ60B7EXZ5ZE6` |
| `0000809` | 54 | `tsk_01KWSCWPK1M0MT808XD6GKABBD` | pre_order | working | deleted | `itm_01KWSCWPK1P877CMNETX9XCJ93` | `tim_01KWSDAS05K5SZF3KQS6HGC22M` |
| `0000809` | 113 | `tsk_01KX5BB167B2WV0TTD9J87A3QW` | internal | ready | active | `itm_01KWSCWPK1P877CMNETX9XCJ93` | `tim_01KX5BD0S0CVFXWJZCZVQZANJ4` |
| `0000809` | 114 | `tsk_01KX5FFXY6MMVYYX1FAGV5T71M` | internal | working | deleted | `itm_01KWSCWPK1P877CMNETX9XCJ93` | `tim_01KX5FJKV8PABSAD1Y4K5FYCH2` |
| `0000809` | 182 | `tsk_01KXJJ89JA3C9HNH07Q72WXP7G` | internal | assigned | deleted | `itm_01KWSCWPK1P877CMNETX9XCJ93` | `tim_01KXJJAYQ8A36B6C8EQMBS6JQR` |
| `0000824` | 36 | `tsk_01KW9BJKK9ZF3AZENESXBKNFFH` | internal | ready | active | `itm_01KW9BJKK98GMVF1PSFTYN48EB` | `tim_01KW9BMKW9R97MWFZ2B8DKR67C` |
| `0000824` | 276 | `tsk_01KYA6F8C9FDSR4KCK21XWVCWP` | internal | working | active | `itm_01KW9BJKK98GMVF1PSFTYN48EB` | `tim_01KYA6FTZ76N34ZCJT0Q9VP7H6` |
| `0000825` | 37 | `tsk_01KW9C9JKY4GDCTDY4C1N6DB5K` | internal | ready | active | `itm_01KW9C9JKZY0NWXRQ66NP4SX1B` | `tim_01KW9CAZC67PKB2E6S0X454EME` |
| `0000825` | 201 | `tsk_01KXR3XRH9839BX02R85SD79BP` | internal | ready | active | `itm_01KW9C9JKZY0NWXRQ66NP4SX1B` | `tim_01KXR3YCXYRPCTZQQ9HY8K26T8` |
| `0000874` | 153 | `tsk_01KXG1P3TH734JTRBW0PQYHQT6` | internal | ready | active | `itm_01KXG1P3TH836GW7BF5TX8SFR1` | `tim_01KXG1PFQ1PN4KN7WYF2JM861D` |
| `0000874` | 206 | `tsk_01KXXF8BCC6DF8C4SXW1DPR0VV` | return | ready | active | `itm_01KXG1P3TH836GW7BF5TX8SFR1` | `tim_01KXXFAKHEF3ZJBZ7BYG0A9YHV` |
| `0000874` | 232 | `tsk_01KY1ZK91F1YZ1GBBDB77NR9XC` | internal | ready | active | `itm_01KXG1P3TH836GW7BF5TX8SFR1` | `tim_01KY1ZKQ8TZJ2Y0AP0T2WWYK1Y` |
| `0001057` | 91 | `tsk_01KWYJFC2RDQ1PAW3NRWCBN4JD` | internal | pending | active | `itm_01KWYJFC2R0771XFWVD74ZQBJG` | `tim_01KWYJG0KCX6GE2C7SET519E96` |
| `0001057` | 98 | `tsk_01KX0Q4DSBJB0D6ESRC716YC93` | internal | ready | active | `itm_01KWYJFC2R0771XFWVD74ZQBJG` | `tim_01KX0Q4QTF3Q9CRKDJD511MWQW` |
| `0001061` | 99 | `tsk_01KX0X5JW11QMNHH95XDA4M1VV` | internal | pending | deleted | `itm_01KX0X5JW2ZPHWWN9GCN2H4HYJ` | `tim_01KX0X6EZQHQPQ0B87Q2F1VCNF` |
| `0001061` | 100 | `tsk_01KX0YVX4QSP6V9PNBZGC4HJAB` | internal | ready | active | `itm_01KX0X5JW2ZPHWWN9GCN2H4HYJ` | `tim_01KX0YWBQHGAZHN98QJ44WNGEV` |
| `0001094` | 129 | `tsk_01KXDAMDE0WJFX9HNMXANJPP5D` | internal | ready | active | `itm_01KXDAMDE07BRJ5Q0CJFZ9K0SV` | `tim_01KXDAMXRD51T8XW8TZ8B842MY` |
| `0001094` | 143 | `tsk_01KXFW7KJY4X659S0E8SKD5AG0` | internal | ready | active | `itm_01KXDAMDE07BRJ5Q0CJFZ9K0SV` | `tim_01KXFW8VTSR51XPY072R6T4R1Y` |
| `0001122` | 223 | `tsk_01KY0112HA8H8QQA53HRWQG8EH` | internal | assigned | deleted | `itm_01KY0112HA1QPD5D3KJNZQE62` | `tim_01KY011AWJ53178WMF0W99DSJP` |
| `0001122` | 224 | `tsk_01KY011YWSH34CY4CG2J7JP1SR` | internal | ready | active | `itm_01KY0112HA1QPD5D3KJNZQE62` | `tim_01KY0125887P2Q7NN12QFY0ZKQ` |
| `0723` | 263 | `tsk_01KY7GHG38VAD9QWCADNKQZ99F` | internal | assigned | deleted | `itm_01KY7GHG386RMR2NY5TJKYB7AY` | `tim_01KY7GSP6565VGGGARV52H6TMM` |
| `0723` | 264 | `tsk_01KY7GWZMYTGXQPKA19ZQJKVXK` | return | assigned | active | `itm_01KY7GHG386RMR2NY5TJKYB7AY` | `tim_01KY7H0KV425QT7GW625ZDMS44` |
| `T6-260526` | 284 | `tsk_01KYFEP0FTB9XCHV2KSN13ZJ8Q` | return | assigned | active | `itm_01KYFEP0FTKBH3Z74EB4GZYYTQ` | `tim_01KYFF0NFMNB3Z8HWYMBK8V8XE` |
| `T6-260526` | 285 | `tsk_01KYFF1FA8RJJ6T16SHABE75TW` | return | pending | active | `itm_01KYFEP0FTKBH3Z74EB4GZYYTQ` | `tim_01KYFFCD7QAS6B2HCZ334AKJ7W` |
| `CH2 15.12` | 40 | `tsk_01KWBK1B07DNBTNJP9Q1YKH49R` | return | ready | active | `itm_01KWBK1B081QM6HD5Z3DQMY2JK` | `tim_01KWBKG4E3ZZ39MSZXZKP63GZ7` |
| `CH2 15.12` | 96 | `tsk_01KX0A5D22X9JKWFW3YDWC52WV` | return | ready | active | `itm_01KWBK1B081QM6HD5Z3DQMY2JK` | `tim_01KX0ASBTM7FYTH029VHT06HKW` |

## Database row counts at inspection

| Table | Total rows | Active/current rows |
|---|---:|---:|
| `tasks` | 360 | 325 |
| `task_items` | 300 | 300 (`removed_at IS NULL`) |
| `items` | 285 | 285 (`is_deleted = false`) |

## Reproduction query

```sql
WITH linked AS (
    SELECT
        t.workspace_id,
        t.client_id AS task_id,
        t.is_deleted AS task_is_deleted,
        ti.item_id,
        i.article_number,
        i.sku
    FROM tasks t
    JOIN task_items ti
      ON ti.task_id = t.client_id
     AND ti.removed_at IS NULL
    JOIN items i
      ON i.client_id = ti.item_id
), identifiers AS (
    SELECT workspace_id, 'article_number' AS identifier_type,
           NULLIF(BTRIM(article_number), '') AS identifier_value,
           task_id, task_is_deleted, item_id
    FROM linked
    UNION ALL
    SELECT workspace_id, 'sku', NULLIF(BTRIM(sku), ''),
           task_id, task_is_deleted, item_id
    FROM linked
)
SELECT
    workspace_id,
    identifier_type,
    identifier_value,
    COUNT(*) AS task_links,
    COUNT(DISTINCT task_id) AS affected_tasks,
    COUNT(DISTINCT item_id) AS distinct_item_rows
FROM identifiers
WHERE identifier_value IS NOT NULL
GROUP BY workspace_id, identifier_type, identifier_value
HAVING COUNT(*) > 1
ORDER BY identifier_type, identifier_value;
```

## Suggested follow-up

Confirm whether one `items` row is allowed to participate in multiple business tasks. If it is not allowed, the next investigation should trace task creation/import paths for the 12 item IDs above and decide whether the fix belongs in task creation validation, item cloning, or the task-item relationship model.
