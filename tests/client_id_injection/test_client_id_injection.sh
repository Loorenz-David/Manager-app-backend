#!/usr/bin/env bash
set -euo pipefail

# End-to-end client_id validation for PLAN_client_id_injection_20260518.
# Run from: backend/ or backend/app/
# Usage: bash tests/client_id_injection/test_client_id_injection.sh [email] [password]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
APP_DIR="$BACKEND_DIR/app"

EMAIL="${1:-user_test@test.local}"
PASSWORD="${2:-Test1234!}"
BASE_URL="${BASE_URL:-http://localhost:8000/api/v1}"

if [ ! -f "$APP_DIR/.venv/bin/python" ]; then
  echo "ERROR: Python venv not found at $APP_DIR/.venv/bin/python"
  exit 1
fi

cd "$APP_DIR"

"$APP_DIR/.venv/bin/python" - "$BASE_URL" "$EMAIL" "$PASSWORD" <<'PY'
import random
import string
import sys
import time

import httpx


BASE_URL = sys.argv[1].rstrip("/")
EMAIL = sys.argv[2]
PASSWORD = sys.argv[3]

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def ulid_like() -> str:
	return "".join(random.choice(ALPHABET) for _ in range(26))


def cid(prefix: str) -> str:
	return f"{prefix}_{ulid_like()}"


class Runner:
	def __init__(self) -> None:
		self.token = ""
		self.passed = 0
		self.failed = 0
		self.session = httpx.Client(timeout=30)

	def log(self, msg: str) -> None:
		print(msg)

	def pass_case(self, idx: int, title: str) -> None:
		self.passed += 1
		print(f"[PASS {idx:02d}] {title}")

	def fail_case(self, idx: int, title: str, details: str) -> None:
		self.failed += 1
		print(f"[FAIL {idx:02d}] {title} :: {details}")

	def req(self, method: str, path: str, json: dict | None = None, expected: int | None = 200):
		headers = {"Content-Type": "application/json"}
		if self.token:
			headers["Authorization"] = f"Bearer {self.token}"
		resp = self.session.request(method, f"{BASE_URL}{path}", headers=headers, json=json)
		try:
			body = resp.json() if resp.text else {}
		except Exception:
			body = {"raw": resp.text}
		if expected is not None and resp.status_code != expected:
			raise AssertionError(f"HTTP {resp.status_code} != {expected}; body={body}")
		return resp.status_code, body

	def assert_true(self, value: bool, msg: str) -> None:
		if not value:
			raise AssertionError(msg)


r = Runner()

# Wait until server answers.
for _ in range(30):
	try:
		resp = r.session.get(f"{BASE_URL}/../health".replace("/api/v1/../", "/"), timeout=2)
		if resp.status_code == 200:
			break
	except Exception:
		pass
	time.sleep(1)
else:
	print("Server is not reachable on http://localhost:8000")
	sys.exit(1)

# Auth
_, auth = r.req(
	"POST",
	"/auth/sign-in",
	{
		"email": EMAIL,
		"password": PASSWORD,
		"app_scope": "admin",
	},
	expected=200,
)
r.token = auth.get("data", {}).get("access_token", "")
if not r.token:
	print("Failed to authenticate; no access_token")
	sys.exit(1)

created = {}

def run_case(i: int, title: str, fn):
	try:
		fn()
		r.pass_case(i, title)
	except Exception as exc:
		r.fail_case(i, title, str(exc))


def get_first_working_section_id() -> str:
	_, body = r.req("GET", "/working-sections?limit=1&offset=0", expected=200)
	sections = body.get("data", {}).get("working_sections", [])
	if not sections:
		raise AssertionError("No working sections available")
	return sections[0]["client_id"]


def get_first_upholstery_id_fallback() -> str:
	# Common seeded fixture used by item tests.
	return "uph_test_velvet_001"


def case_01():
	item_cid = cid("itm")
	created["item_1"] = item_cid
	_, body = r.req("PUT", "/items", {"client_id": item_cid, "article_number": f"A-{ulid_like()}", "sku": f"S-{ulid_like()}"}, expected=200)
	got = body.get("data", {}).get("client_id")
	r.assert_true(got == item_cid, f"Expected {item_cid}, got {got}")


def case_02():
	_, body = r.req("PUT", "/items", {"article_number": f"A-{ulid_like()}", "sku": f"S-{ulid_like()}"}, expected=200)
	got = body.get("data", {}).get("client_id", "")
	r.assert_true(got.startswith("itm_"), f"Expected server generated itm_*, got {got}")
	created["item_2"] = got


def case_03():
	status, body = r.req("PUT", "/items", {"client_id": cid("tsk"), "article_number": f"A-{ulid_like()}", "sku": f"S-{ulid_like()}"}, expected=None)
	r.assert_true(status in (400, 409, 422), f"Expected validation status, got {status}")
	r.assert_true(body.get("ok") is False, f"Expected ok=false, got {body}")


def case_04():
	dup = created["item_1"]
	status, body = r.req("PUT", "/items", {"client_id": dup, "article_number": f"A-{ulid_like()}", "sku": f"S-{ulid_like()}"}, expected=None)
	r.assert_true(status == 409, f"Expected 409 for duplicate, got {status}")
	r.assert_true(body.get("ok") is False, f"Expected ok=false, got {body}")


def case_05():
	find_sku = f"FIND-{ulid_like()}"
	seed_id = cid("itm")
	_, seed = r.req(
		"PUT",
		"/items",
		{"client_id": seed_id, "article_number": f"A-{ulid_like()}", "sku": find_sku},
		expected=200,
	)
	existing = seed.get("data", {}).get("client_id")
	_, body = r.req("POST", "/items/find-or-create", {"client_id": cid("itm"), "sku": find_sku}, expected=200)
	got = body.get("data", {}).get("client_id")
	r.assert_true(got == existing, f"Expected existing {existing}, got {got}")


def case_06():
	x = cid("itm")
	_, body = r.req("POST", "/items/find-or-create", {"client_id": x, "article_number": f"A-{ulid_like()}", "sku": f"S-{ulid_like()}"}, expected=200)
	got = body.get("data", {}).get("client_id")
	r.assert_true(got == x, f"Expected {x}, got {got}")
	created["item_for_task"] = got


def case_07():
	t = cid("tsk")
	created["task"] = t
	_, body = r.req("PUT", "/tasks", {"client_id": t, "task_type": "internal", "title": f"Task {ulid_like()}"}, expected=200)
	got = body.get("data", {}).get("client_id")
	r.assert_true(got == t, f"Expected {t}, got {got}")


def case_08():
	ws = get_first_working_section_id()
	t = cid("tsk")
	step = cid("tsp")
	_, body = r.req(
		"PUT",
		"/tasks",
		{
			"client_id": t,
			"task_type": "internal",
			"title": f"Task {ulid_like()}",
			"steps": [{"client_id": step, "working_section_id": ws}],
		},
		expected=200,
	)
	task_id = body.get("data", {}).get("client_id")
	_, g = r.req("GET", f"/tasks/{task_id}", expected=200)
	steps = g.get("data", {}).get("task_steps", [])
	ids = [s.get("client_id") for s in steps]
	r.assert_true(step in ids, f"Expected inline step {step}, got {ids}")
	created["task_for_step_note"] = task_id


def case_09():
	t = cid("tsk")
	note = cid("tno")
	_, body = r.req(
		"PUT",
		"/tasks",
		{
			"client_id": t,
			"task_type": "internal",
			"title": f"Task {ulid_like()}",
			"notes": [{"client_id": note, "note_type": "user_note", "content": {"text": "hello"}}],
		},
		expected=200,
	)
	task_id = body.get("data", {}).get("client_id")
	_, g = r.req("GET", f"/tasks/{task_id}", expected=200)
	notes = g.get("data", {}).get("task_notes", [])
	ids = [n.get("client_id") for n in notes]
	r.assert_true(note in ids, f"Expected inline note {note}, got {ids}")


def case_10():
	t = cid("tsk")
	item = cid("itm")
	_, body = r.req(
		"PUT",
		"/tasks",
		{
			"client_id": t,
			"task_type": "internal",
			"title": f"Task {ulid_like()}",
			"item": {"client_id": item, "article_number": f"A-{ulid_like()}", "sku": f"S-{ulid_like()}"},
		},
		expected=200,
	)
	task_id = body.get("data", {}).get("client_id")
	_, g = r.req("GET", f"/tasks/{task_id}", expected=200)
	task_item = g.get("data", {}).get("item", {})
	got = task_item.get("client_id")
	r.assert_true(got == item, f"Expected inline item {item}, got {got}")
	created["item_for_upholstery"] = item


def case_11():
	ws = get_first_working_section_id()
	step = cid("tsp")
	t = created["task_for_step_note"]
	_, body = r.req("POST", f"/tasks/{t}/steps", {"client_id": step, "working_section_id": ws}, expected=200)
	got = body.get("data", {}).get("step_id")
	r.assert_true(got == step, f"Expected {step}, got {got}")


def case_12():
	note = cid("tno")
	t = created["task_for_step_note"]
	_, body = r.req("POST", f"/tasks/{t}/notes", {"client_id": note, "note_type": "user_note", "content": {"text": "post note"}}, expected=200)
	got = body.get("data", {}).get("client_id")
	r.assert_true(got == note, f"Expected {note}, got {got}")


def case_13():
	c = cid("cus")
	_, body = r.req(
		"PUT",
		"/customers",
		{"client_id": c, "display_name": "ClientId Customer", "primary_email": f"cid-{ulid_like()}@test.local"},
		expected=200,
	)
	got = body.get("data", {}).get("client_id")
	r.assert_true(got == c, f"Expected {c}, got {got}")


def case_14():
	c = cid("ca")
	_, body = r.req("POST", "/cases", {"client_id": c, "type_label": "ClientId Case"}, expected=200)
	got = body.get("data", {}).get("case_client_id")
	r.assert_true(got == c, f"Expected {c}, got {got}")
	created["case"] = c


def case_15():
	conv = cid("ccv")
	cas = created["case"]
	_, body = r.req("POST", f"/cases/{cas}/conversations", {"client_id": conv, "case_client_id": cas}, expected=200)
	got = body.get("data", {}).get("conversation", {}).get("client_id")
	r.assert_true(got == conv, f"Expected {conv}, got {got}")
	created["conversation"] = conv


def case_16():
	msg = cid("ccm")
	conv = created["conversation"]
	_, body = r.req(
		"POST",
		f"/cases/conversations/{conv}/messages",
		{"client_id": msg, "conversation_client_id": conv, "content": [{"type": "text", "text": "client id msg"}]},
		expected=200,
	)
	got = body.get("data", {}).get("message", {}).get("client_id")
	r.assert_true(got == msg, f"Expected {msg}, got {got}")


def case_17():
	ws = cid("wsec")
	_, body = r.req("PUT", "/working-sections", {"client_id": ws, "name": f"WS {ulid_like()}"}, expected=200)
	got = body.get("data", {}).get("client_id")
	r.assert_true(got == ws, f"Expected {ws}, got {got}")


def case_18():
	iup = cid("iup")
	item_id = created["item_for_upholstery"]
	_, body = r.req(
		"PUT",
		"/item-upholsteries",
		{"client_id": iup, "item_id": item_id, "source": "customer", "name": "CustFabric", "code": "CF-001", "amount_meters": 1.25},
		expected=200,
	)
	got = body.get("data", {}).get("client_id")
	r.assert_true(got == iup, f"Expected {iup}, got {got}")


def case_19():
	inv = cid("uin")
	upholstery_id = get_first_upholstery_id_fallback()
	status, body = r.req(
		"PUT",
		"/upholstery-inventories",
		{"client_id": inv, "upholstery_id": upholstery_id},
		expected=None,
	)
	if status == 200:
		got = body.get("data", {}).get("client_id")
		r.assert_true(got == inv, f"Expected {inv}, got {got}")
		return
	# In seeded environments inventory for this upholstery may already exist.
	r.assert_true(status == 409, f"Expected 200 or 409, got {status}; body={body}")


def case_20():
	item = cid("itm")
	_, create_body = r.req("PUT", "/items", {"client_id": item, "article_number": f"A-{ulid_like()}", "sku": f"S-{ulid_like()}"}, expected=200)
	created_id = create_body.get("data", {}).get("client_id")
	r.assert_true(created_id == item, f"Expected created item {item}, got {created_id}")

	# We validate that image upload-url accepts a pre-generated entity_client_id
	# that now exists.
	_, up = r.req(
		"POST",
		"/images/upload-url",
		{
			"entity_type": "item",
			"entity_client_id": item,
			"file_name": "cid-check.png",
			"content_type": "image/png",
			"file_size_bytes": 128,
		},
		expected=200,
	)
	pending = up.get("data", {}).get("pending_upload_client_id")
	r.assert_true(bool(pending), f"Expected pending_upload_client_id, got {up}")


cases = [
	(1, "Create item with pre-generated client_id", case_01),
	(2, "Create item without client_id", case_02),
	(3, "Create item with invalid prefix", case_03),
	(4, "Create item with duplicate client_id", case_04),
	(5, "Find-or-create item FIND path", case_05),
	(6, "Find-or-create item CREATE path", case_06),
	(7, "Create task with client_id", case_07),
	(8, "Create task with inline step client_id", case_08),
	(9, "Create task with inline note client_id", case_09),
	(10, "Create task with inline item client_id", case_10),
	(11, "Add task step with client_id", case_11),
	(12, "Add task note with client_id", case_12),
	(13, "Create customer with client_id", case_13),
	(14, "Create case with client_id", case_14),
	(15, "Create conversation with client_id", case_15),
	(16, "Send message with client_id", case_16),
	(17, "Create working section with client_id", case_17),
	(18, "Create item upholstery with client_id", case_18),
	(19, "Create upholstery inventory with client_id", case_19),
	(20, "Image upload-url after pre-generated entity_client_id", case_20),
]

for idx, title, fn in cases:
	run_case(idx, title, fn)

print("=" * 70)
print(f"RESULT: {r.passed} passed, {r.failed} failed")
print("=" * 70)
if r.failed:
	sys.exit(1)
PY
