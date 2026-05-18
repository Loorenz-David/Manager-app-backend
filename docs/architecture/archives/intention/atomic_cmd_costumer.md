creating a costumer is straight forward as it only creates a costumer instance with the mandatory fields name and contact information.

we will need a command for updating a costumer, this command will update only the costumer columns, and it will not update the linked items or tasks of the costumer.

we will need a command for deleting a costumer, this command will use the soft delete pattern, and it will not delete the linked items or tasks of the costumer.

we will need a command that allows for quering a costumer by email or phone number if not found it creates one, this is because later higher commands ( task commands ) will need to link a costumer to a task, and in some cases ( majority ) the costumer might not exist yet, so this command will allow for creating or getting a costumer in one step.

listing  costumers has the common command pattern we have stablish, list of costumers which accepts a query with filters "q" and pagination, and get costumer by id which accepts the costumer client_id as path parameter and returns the costumer serialized with items count.

getting a costumer by id returns the costumer with its linked items serialized with the item serializer.

---

## Linked implementation plans

| Plan ID | Status | Plan path | Summary path | Archive record |
|---|---|---|---|---|
| `PLAN_customer_crud_20260517` | `archived` | `backend/docs/architecture/archives/implementation/PLAN_customer_crud_20260517.md` | `backend/docs/architecture/implemented_summaries/SUMMARY_customer_crud_20260517.md` | `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_customer_crud_20260517.md` |

## Progress notes

- `2026-05-17`: Customer CRUD/query/router scope implemented and validated.
- `2026-05-17`: Formal shell test suite added at `backend/tests/costumer/test_costumer.sh` and executed with all checks passing.
- `2026-05-17`: Lifecycle completed for this implementation plan (summary + archive).

