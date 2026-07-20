Intention: Automated Connecteam Clock Activity Parser and Dedicated Ingestion Worker

1. Objective

Implement an automated Connecteam clock-activity ingestion capability that retrieves near-live employee clock-in, clock-out, pause, and related time activity data without relying on Connecteam webhooks or the official Connecteam API.

The integration must use an authenticated Connecteam browser session to access the same time-clock data available to an authorized Connecteam administrator.

The ingestion process must:

* Run automatically.
* Retrieve updated clock activity approximately every minute.
* Support an adjustable polling interval.
* Operate through a dedicated worker service.
* Remain isolated from other application workers and queues.
* Securely manage authentication and session state.
* Be resilient to expired sessions, frontend changes, temporary network failures, and duplicated data.
* Persist normalized clock activity idempotently.
* Provide sufficient structured logging and operational tooling for debugging and recovery.
* Align with the backend contract selection and implementation rules defined in:

backend/task_system/backend_contract_goal_mapping_guide.md

This is an interim integration strategy. The long-term direction is for ManagerBeyo to provide its own worker clock-in and clock-out application.

⸻

2. Terminology

Use the following terminology consistently.

Connecteam browser adapter

The isolated component responsible for authenticating with Connecteam and retrieving time-clock data from the authenticated web application.

Poll cycle

One execution in which the worker:

1. Determines the required synchronization window.
2. Retrieves relevant Connecteam time activity.
3. Normalizes the retrieved records.
4. Reconciles them against locally persisted records.
5. Advances synchronization state only after successful persistence.

Source record

A raw or minimally transformed Connecteam activity object retrieved from the authenticated Connecteam application.

Normalized time activity

The internal ManagerBeyo representation of clock-in, clock-out, pause, resume, correction, or related employee time events.

Integration cursor

Persisted synchronization state describing the latest successfully reconciled source position or time window.

Browser session

The authenticated Connecteam session represented by cookies, local storage values, tokens, CSRF state, or other browser-controlled authentication material.

⸻

3. Scope

3.1 Included

The implementation must support:

* A dedicated Connecteam ingestion worker.
* Configurable polling, initially defaulting to one minute.
* Secure Connecteam credential and browser-session handling.
* Authenticated retrieval of time-clock activity.
* Browser automation or authenticated application-request replay when appropriate.
* Incremental synchronization.
* Overlapping reconciliation windows.
* Idempotent create and update behavior.
* Detection of corrected or deleted source activities where technically observable.
* Source-record snapshots suitable for debugging.
* Worker health reporting.
* Structured logs with correlation identifiers.
* Retry and backoff behavior.
* Authentication-expiration detection.
* Operational commands for manual synchronization and diagnostics.
* Integration status exposure for the ManagerBeyo administration interface.
* Tests covering parsing, reconciliation, session expiration, retries, and duplicate prevention.

3.2 Excluded

This intention does not include:

* Building the future native ManagerBeyo clock-in and clock-out interface.
* Replacing Connecteam scheduling.
* Circumventing CAPTCHA, MFA, device approval, or other explicit access controls.
* Automatically defeating bot-detection mechanisms.
* Storing Connecteam passwords in plaintext.
* Treating scraped page layout as the canonical internal data model.
* Sharing browser sessions across workspaces.
* Running Connecteam polling inside the general tasks worker.
* Using UI-generated identifiers as ManagerBeyo domain identifiers.
* Depending exclusively on a DOM table when a stable authenticated JSON request is available.
* Guaranteeing payroll-grade correctness without reconciliation and human-visible integration status.

⸻

4. Architectural direction

Implement Connecteam ingestion as an external-system adapter with strict separation between:

1. Authentication and browser-session management.
2. Connecteam transport and retrieval.
3. Raw source-data capture.
4. Source parsing and normalization.
5. Time-activity reconciliation.
6. Persistence.
7. Worker scheduling and runtime control.
8. Observability and operations.

The Connecteam-specific parser must not directly mutate unrelated task, analytics, or worker-domain models.

The adapter should produce normalized source DTOs or records that are passed to an application command responsible for reconciliation and persistence.

The design must make it possible to replace the parser later with:

* The official Connecteam API.
* Connecteam webhooks.
* A native ManagerBeyo clock source.

The normalized time-activity contract must therefore remain independent from the Connecteam retrieval mechanism.

⸻

5. Contract selection requirements

Claude must begin the implementation plan by resolving the required backend contracts through:

backend/task_system/backend_contract_goal_mapping_guide.md

This is primarily a:

* Worker-driven backend goal.
* Replayable async runtime goal.
* Observability-sensitive external integration.
* Rate-limited polling process.
* Recoverable and operationally debuggable background service.

At minimum, evaluate the following contracts in addition to all required core contracts:

* ../architecture/16_background_jobs.md
* ../architecture/12_infra_redis.md
* ../architecture/51_worker_runtime.md
* ../architecture/49_observability_runtime.md
* ../architecture/52_replayability.md
* ../architecture/11_infra_events.md
* ../architecture/53_operational_cli.md
* ../architecture/17_*.md where required for correlation and logging
* ../architecture/31_health_observability.md
* ../architecture/18_*.md for rate limiting
* ../architecture/02_*.md for request and operation timeouts
* ../architecture/15_testing.md
* ../architecture/30_migrations.md
* ../architecture/46_serialization.md if integration status or activity responses are exposed
* ../architecture/55_*.md if administrative activity queries include date filtering or text search

For every selected canonical contract, check for a corresponding *_local.md extension and load the canonical contract before the local extension.

Claude must include the guide-required sections before producing implementation steps:

* Selected contracts
* Added from guide
* Local extensions loaded
* Excluded contracts
* Read order
* Applied precedence

Implementation files may be inspected to understand:

* Existing models.
* Existing worker registration.
* Existing queue configuration.
* Existing integration patterns.
* Existing encryption utilities.
* Existing Connecteam webhook implementation.
* Existing time-activity response shapes.
* Existing upholstery parser infrastructure.

Implementation files must not be used as substitutes for contracts when determining how commands, queries, workers, routers, events, serializers, or errors should be structured.

⸻

6. Dedicated worker service

Create a dedicated service for Connecteam ingestion.

Suggested service identity:

managerbeyo-connecteam-worker

The final name should follow existing project conventions.

The worker must:

* Run independently through its own systemd unit.
* Have an independent process lifecycle.
* Use a dedicated Redis queue or dedicated scheduling mechanism.
* Not consume generic tasks intended for unrelated domains.
* Have explicit concurrency controls.
* Prevent simultaneous poll cycles for the same integration.
* Support graceful shutdown.
* Report health and last successful execution.
* Continue processing other Connecteam integrations when one integration fails.
* Avoid unbounded memory growth from long-lived browser contexts.
* Recycle browser contexts or processes according to configurable thresholds.
* Use bounded timeouts for login, navigation, retrieval, parsing, and persistence.

The implementation plan must specify:

* Worker entrypoint.
* Queue or scheduler ownership.
* systemd service definition.
* Environment configuration.
* Restart policy.
* Health-check strategy.
* Logging configuration.
* Deployment changes.
* Required browser-runtime dependencies.
* Whether Chromium is installed system-wide or managed by the Python package.
* How browser binaries are deployed consistently to EC2.

⸻

7. Scheduling and polling behavior

7.1 Default interval

Use a default poll interval of 60 seconds.

The interval must be configurable:

* Globally through environment configuration.
* Per integration where appropriate.
* With a safe minimum interval enforced by the backend.

Example conceptual settings:

CONNECTEAM_POLL_INTERVAL_SECONDS=60
CONNECTEAM_POLL_MIN_INTERVAL_SECONDS=30
CONNECTEAM_POLL_TIMEOUT_SECONDS=45

Exact names must follow project conventions.

7.2 Scheduling model

Do not implement the worker as an uncontrolled infinite loop that sleeps without persisted state or observability.

Use the project’s approved worker-runtime and scheduling patterns.

The scheduler must create or trigger one poll operation per due integration while ensuring:

* Only one active poll per integration.
* Poll cycles are recoverable after process restarts.
* A failed poll does not permanently stop future polls.
* Delayed cycles do not create an uncontrolled backlog.
* Poll jobs are coalesced when the worker is temporarily unavailable.
* The current integration state determines the next eligible poll time.

7.3 Jitter

Apply small configurable jitter when multiple integrations exist so they do not all authenticate or retrieve data at exactly the same second.

7.4 Overlapping time window

Do not synchronize exclusively from the exact latest observed timestamp.

Each cycle must re-read an overlapping historical window to detect:

* Late clock-outs.
* Manual corrections.
* Added pauses.
* Edited timestamps.
* Reassigned jobs.
* Deleted or invalidated activities.

Suggested initial overlap:

Current time minus 24 hours

The overlap must be configurable and validated against expected Connecteam correction behavior.

For the initial implementation, correctness is more important than minimizing retrieved rows.

⸻

8. Browser automation strategy

8.1 Preferred extraction hierarchy

Use the following priority order:

1. Authenticated JSON or GraphQL requests used internally by the Connecteam web application.
2. Structured application state embedded in the page.
3. Semantically stable DOM elements.
4. Visual or positional scraping only as a last resort.

The implementation must first inspect the authenticated browser network traffic to identify whether Connecteam’s web application retrieves clock activities through internal JSON endpoints.

When such requests exist, prefer executing or replaying those requests inside the authenticated browser context rather than parsing rendered table text.

This provides a more reliable architecture while still using the authorized web session.

8.2 Playwright

Use Playwright for the authenticated browser adapter unless project research identifies a more appropriate maintained browser automation framework.

The implementation plan must evaluate and add the required dependency to:

backend/app/requirements.txt

The plan must include browser installation and deployment commands.

Potential dependency:

playwright

The exact version must be pinned according to project dependency policy.

8.3 Session model

Each Connecteam integration must have isolated session state.

Do not share cookies, local storage, CSRF tokens, or browser profiles between workspaces.

Potential approaches include:

* One encrypted Playwright storage-state document per integration.
* One isolated browser context per poll cycle, initialized from encrypted storage state.
* A bounded reusable context where safe and observable.

The plan must select one approach and explain:

* Isolation guarantees.
* Memory implications.
* Session refresh behavior.
* Process restart behavior.
* Secret rotation.
* Failure recovery.

8.4 Authentication modes

Support an initial administrative setup flow that captures an authenticated session.

The implementation plan must evaluate whether Connecteam login requires:

* Username and password.
* One-time codes.
* MFA.
* Device confirmation.
* CAPTCHA.
* SSO.

The system must not attempt to bypass MFA, CAPTCHA, SSO, or device approval.

Where interactive login is required, provide an explicit integration setup or session-refresh process initiated by an authorized ManagerBeyo administrator.

After authentication succeeds, persist only the minimum session material required for background retrieval.

8.5 Credential use

Prefer session reuse over logging in with the Connecteam password every minute.

Credentials, when required, must only be used to establish or refresh a session.

The worker should:

1. Load encrypted session state.
2. Validate whether the session remains authenticated.
3. Retrieve time activities.
4. Refresh persisted session state if Connecteam rotates tokens or cookies.
5. Mark the integration as requiring reauthentication when automated refresh is impossible.

⸻

9. Security requirements

9.1 Encryption

All sensitive Connecteam material must be encrypted at rest, including:

* Passwords, if stored at all.
* Session cookies.
* Access tokens.
* Refresh tokens.
* CSRF tokens where sensitive.
* Browser storage state.
* Device identifiers used for authentication.

Reuse the application’s existing encryption facilities where available.

Do not add a separate undocumented encryption mechanism without first inspecting the current integration-secret architecture.

9.2 Secret exposure prevention

Never include the following in logs:

* Passwords.
* Full cookies.
* Authorization headers.
* Session-storage contents.
* CSRF token values.
* MFA codes.
* Full authenticated request headers.
* Raw browser storage-state documents.

Logs may include:

* Token fingerprints.
* Cookie names without values.
* Session creation timestamps.
* Session expiry estimates.
* Authentication state classification.
* Redacted endpoint names.
* Request identifiers.

9.3 Workspace isolation

Every command and query must be scoped by workspace context according to backend contracts.

The worker must not trust workspace identifiers obtained from the Connecteam page.

The selected ManagerBeyo integration configuration determines workspace ownership.

9.4 Least privilege

Use a dedicated Connecteam administrative account for ManagerBeyo ingestion where possible.

The account should have only the permissions required to view time-clock and timesheet information.

9.5 Audit history

Create auditable integration events for at least:

* Integration configured.
* Authentication established.
* Session refreshed.
* Authentication expired.
* Poll started.
* Poll completed.
* Poll failed.
* Parser contract changed.
* Source records created.
* Source records updated.
* Source records marked missing or deleted.
* Manual synchronization requested.
* Integration paused.
* Integration resumed.

⸻

10. Integration configuration and persistence

The implementation plan must inspect existing Connecteam integration models and extend them rather than introducing an unrelated duplicate integration concept.

Persist configuration sufficient to manage:

* Workspace ownership.
* Connecteam company or account identity.
* Connecteam time-clock identity.
* Parser mode.
* Poll interval.
* Overlap duration.
* Enabled or paused state.
* Authentication state.
* Encrypted browser-session state.
* Last poll attempt.
* Last successful poll.
* Last authentication success.
* Consecutive failure count.
* Last failure classification.
* Last source activity timestamp.
* Next eligible poll time.
* Parser version.
* Reauthentication-required state.

Do not place all operational state in one unstructured JSON field when fields are required for querying, scheduling, alerting, or indexing.

JSON may be used for:

* Redacted parser diagnostics.
* Source metadata not yet promoted to canonical columns.
* Versioned raw response snapshots.
* Non-query-critical adapter metadata.

⸻

11. Raw source capture

Preserve enough source data to debug parsing and reconciliation without repeatedly reproducing the original browser request.

For each retrieved source record, store or otherwise retain:

* Connecteam source identifier, when available.
* Source record type.
* Source employee identifier.
* Source clock or job identifier.
* Source timestamps.
* Source updated timestamp, when available.
* Retrieval timestamp.
* Parser version.
* Integration identifier.
* A canonical source checksum.
* Sanitized raw payload or versioned source snapshot.
* Normalization outcome.
* Reconciliation outcome.

Sensitive authentication data must never be included in source snapshots.

Apply an explicit retention policy to raw source payloads.

The plan must specify whether raw payloads are:

* Persisted in PostgreSQL.
* Stored in S3.
* Retained only for failed or changed records.
* Compressed.
* Expired after a defined period.

For initial rollout, retaining sanitized payloads for debugging is preferred.

⸻

12. Source parsing and normalization

12.1 Parser boundary

The parser converts Connecteam-specific records into a versioned source DTO.

It must not directly write final database rows.

Example conceptual DTO:

{
  "source": "connecteam_browser",
  "integration_client_id": "ctmint_...",
  "source_activity_id": "connecteam-activity-id",
  "source_user_id": "connecteam-user-id",
  "source_clock_id": "14995959",
  "activity_type": "working_session",
  "started_at": "2026-07-20T08:00:00Z",
  "ended_at": null,
  "pause_intervals": [],
  "job": {
    "source_id": "job-id",
    "name": "Job name"
  },
  "source_updated_at": "2026-07-20T08:01:00Z",
  "source_checksum": "...",
  "retrieved_at": "2026-07-20T08:01:10Z",
  "parser_version": 1,
  "raw_payload_reference": "..."
}

The exact shape must be derived from the Connecteam data currently observable through the browser and from the existing ManagerBeyo time-activity domain.

12.2 Versioning

The parser must have an explicit version.

When extraction logic or field interpretation changes:

* Increment the parser version.
* Log the active parser version.
* Preserve compatibility with previously stored raw records.
* Allow historical reprocessing where feasible.

12.3 Time handling

Normalize all timestamps to timezone-aware UTC values.

Preserve the source timezone or offset where available.

Do not infer timezone silently from the EC2 host.

The integration configuration should identify the expected Connecteam workspace timezone when the source response does not provide it.

Explicitly handle:

* Daylight saving transitions.
* Open shifts with no clock-out.
* Overnight shifts.
* Activities spanning midnight.
* Duplicate local times during DST fallback.
* Nonexistent local times during DST transition.
* Manual timestamp corrections.

12.4 Employee mapping

Connecteam users must be mapped to ManagerBeyo users or workers using a stable mapping table.

Do not depend only on display names.

Preferred mapping identifiers:

1. Connecteam user ID.
2. Verified email address.
3. Explicit administrator-created mapping.

When a source employee is unmapped:

* Preserve the source record.
* Do not discard it.
* Mark it as requiring identity mapping.
* Expose the condition through integration status.
* Continue processing mapped users.

⸻

13. Reconciliation and idempotency

13.1 Source identity

Use Connecteam’s stable source activity identifier when available.

When no stable identifier exists, generate a deterministic identity from carefully selected immutable or mostly stable source fields.

Do not use only:

* Employee name.
* Row number.
* Current table position.
* Retrieval timestamp.

13.2 Upsert behavior

Each poll may retrieve records already seen.

The reconciliation command must classify each source record as:

* Created.
* Updated.
* Unchanged.
* Invalid.
* Unmapped.
* Missing from source.
* Deleted or voided, when observable.

Use source checksums to avoid unnecessary updates.

13.3 Corrections

A previous clock activity may be edited after initial ingestion.

The system must update the normalized record when the source checksum or source update timestamp changes.

Preserve audit history showing:

* Previous normalized value.
* New normalized value.
* Source retrieval time.
* Parser version.
* Reason for reconciliation.

13.4 Open sessions

Clocked-in users may have activities with no end timestamp.

Open sessions must be persisted and updated on later cycles when:

* A pause begins.
* A pause ends.
* The worker clocks out.
* A manager corrects the record.

13.5 Missing records

A record absent from one poll must not immediately be deleted because:

* Pagination may be incomplete.
* Filtering may change.
* Connecteam may temporarily return partial data.
* The browser request may fail mid-cycle.

Use a conservative missing-record policy.

A source record may only be marked missing, voided, or deleted after:

* A complete authoritative reconciliation window succeeds.
* The record was expected within that window.
* Absence is confirmed according to a defined threshold or source deletion signal.

Never hard-delete normalized time history during ordinary polling.

⸻

14. Poll-cycle transaction and checkpoint behavior

A poll cycle must have explicit phases:

1. Acquire per-integration lock.
2. Load integration and synchronization state.
3. Validate authentication.
4. Determine retrieval window.
5. Retrieve all required pages.
6. Validate response completeness.
7. Persist sanitized raw source records.
8. Normalize source records.
9. Reconcile normalized activities.
10. Record metrics and integration events.
11. Advance synchronization state.
12. Release lock.

The synchronization cursor must only advance after all required pages and persistence operations complete successfully.

If retrieval succeeds but persistence fails:

* Do not advance the cursor.
* Allow safe replay.
* Use idempotent source identities to prevent duplicates.

Use the project’s approved transaction patterns, including local transaction extensions defined by the command contracts.

⸻

15. Pagination and completeness

The parser must identify and support Connecteam’s internal pagination mechanism.

Potential mechanisms include:

* Cursor pagination.
* Offset pagination.
* Page numbers.
* Infinite scrolling.
* Date-window segmentation.

The poll result must record:

* Pages requested.
* Pages completed.
* Rows received.
* Expected total where exposed.
* Whether the dataset was complete.
* Whether pagination terminated normally.

A partially retrieved dataset must never be treated as an authoritative complete reconciliation window.

⸻

16. Concurrency control

Use a distributed per-integration lock so multiple worker processes cannot poll the same integration concurrently.

The lock must:

* Have a bounded lease.
* Include an owner or execution identifier.
* Be renewable for long cycles if the approved Redis pattern supports it.
* Be released safely.
* Recover from worker crashes.
* Produce observable lock-contention events.

The lock key must include the integration identity.

Do not use only an in-process Python lock.

⸻

17. Retry and failure behavior

Classify failures instead of treating all exceptions identically.

Required categories include:

* Authentication expired.
* Reauthentication required.
* Invalid credentials.
* MFA or device approval required.
* CAPTCHA or bot challenge encountered.
* Connecteam permission denied.
* Browser startup failure.
* Browser navigation timeout.
* Internal request timeout.
* Response-shape mismatch.
* Parser failure.
* Pagination incomplete.
* Rate-limited response.
* Temporary Connecteam server failure.
* Network failure.
* Persistence failure.
* Lock contention.
* Worker shutdown.

Retry transient failures using bounded exponential backoff with jitter.

Do not repeatedly retry failures requiring human action.

Examples requiring integration status changes rather than aggressive retries:

* Invalid credentials.
* MFA required.
* CAPTCHA encountered.
* Permission denied.
* Unrecognized login flow.
* Persistent parser contract mismatch.

The worker must continue scheduling health checks or low-frequency recovery checks according to the approved runtime contract.

⸻

18. Parser contract-change detection

Connecteam may change internal endpoints or response structures.

The adapter must detect unexpected structural changes.

Validation must include required fields and expected data types.

When a response-shape mismatch occurs:

* Do not silently interpret incorrect fields.
* Do not advance synchronization state.
* Store a sanitized diagnostic sample.
* Emit a structured parser-contract error.
* Include parser version and response fingerprint.
* Mark the integration as degraded.
* Alert through the existing observability mechanism.
* Continue preserving the last known valid normalized state.

Where possible, implement parser fixtures from captured sanitized responses.

⸻

19. Performance and resource constraints

The worker must remain efficient even when polling every minute.

Requirements:

* Avoid launching a completely new browser process per individual HTTP request.
* Avoid retaining unbounded browser pages or contexts.
* Close pages, contexts, streams, and responses deterministically.
* Reuse authenticated session state safely.
* Request only the required date window and time-clock scope.
* Avoid screenshots during normal successful polls.
* Capture screenshots or HTML diagnostics only on selected failures.
* Bound diagnostic artifact size.
* Apply retention and cleanup policies.
* Batch database reconciliation where appropriate.
* Avoid loading the full historical timesheet on every cycle.
* Use checksums to skip unchanged persistence work.
* Emit metrics for browser startup duration, authentication validation, retrieval, parsing, and persistence.

The implementation plan must estimate expected worker cost for:

* One integration.
* Multiple integrations.
* One-minute polling.
* Browser process memory.
* Database writes.
* Redis jobs and locks.

⸻

20. Observability

Every poll cycle must have a correlation or execution identifier.

Structured logs should include:

* Integration client ID.
* Workspace client ID.
* Poll execution ID.
* Worker process identity.
* Parser version.
* Retrieval window.
* Poll trigger.
* Authentication status.
* Pages retrieved.
* Source rows received.
* Created count.
* Updated count.
* Unchanged count.
* Invalid count.
* Unmapped count.
* Open-session count.
* Duration by phase.
* Retry number.
* Failure classification.
* Cursor before and after.
* Lock acquisition outcome.

Do not log sensitive session content.

Metrics should include:

* Poll attempts.
* Poll successes.
* Poll failures by category.
* Consecutive failures.
* Authentication failures.
* Parser-contract failures.
* Poll duration.
* Time since last successful poll.
* Source-data lag.
* Records created and updated.
* Current open sessions.
* Browser restarts.
* Lock contention.
* Worker queue depth.
* Worker heartbeat age.

⸻

21. Health and integration status

Expose sufficient state to determine whether the data is currently reliable.

Suggested integration states:

* setup_required
* authenticating
* active
* degraded
* reauthentication_required
* paused
* disabled

Integration status should expose:

{
  "status": "active",
  "poll_interval_seconds": 60,
  "last_poll_attempt_at": "2026-07-20T19:00:00Z",
  "last_successful_poll_at": "2026-07-20T19:00:04Z",
  "source_data_lag_seconds": 8,
  "consecutive_failure_count": 0,
  "last_failure_code": null,
  "authentication_status": "authenticated",
  "reauthentication_required": false,
  "parser_version": 1
}

The exact serializer must follow the backend serialization contract.

The UI or API must clearly distinguish:

* The worker is healthy.
* The integration is authenticated.
* The last poll succeeded.
* The data itself is current.
* Some employees are unmapped.
* A parser contract change has occurred.

⸻

22. Administrative operations

Provide approved administrative operations for:

* Triggering an immediate synchronization.
* Pausing an integration.
* Resuming an integration.
* Starting or refreshing authentication.
* Inspecting sanitized integration diagnostics.
* Viewing the last successful poll.
* Viewing the last failure.
* Replaying a historical time window.
* Reprocessing stored raw records with a selected parser version.
* Resetting synchronization state safely.
* Testing session validity.
* Testing Connecteam permissions.
* Listing unmapped Connecteam users.
* Mapping Connecteam users to ManagerBeyo users.

Operational commands must use the project’s approved CLI contract.

Manual synchronization must use the same application command and reconciliation path as scheduled polling.

Do not create a separate unsafe “debug sync” implementation.

⸻

23. Replayability

The architecture must permit reprocessing without contacting Connecteam when sanitized raw records are already available.

A replay operation should be able to:

1. Select raw records by integration and date range.
2. Parse them using a specified parser version.
3. Compare the result with currently normalized records.
4. Perform a dry run.
5. Report proposed creates, updates, and conflicts.
6. Apply changes through the standard reconciliation command.

Replay must not directly bypass audit, validation, or workspace scope.

⸻

24. Browser diagnostics

On selected failures, capture diagnostic artifacts such as:

* Screenshot.
* Current URL.
* Page title.
* Sanitized HTML fragment.
* Network request summary.
* Response status summary.
* Parser validation errors.
* Browser console errors.

Diagnostics must:

* Be disabled or minimized during successful polls.
* Be size-limited.
* Be redacted.
* Have a retention period.
* Be linked to the poll execution ID.
* Never include authentication secrets.

Avoid storing full-page HTML when a smaller relevant sanitized fragment is sufficient.

⸻

25. Testing requirements

25.1 Unit tests

Cover:

* Response parsing.
* Schema validation.
* Timezone normalization.
* Open sessions.
* Pause intervals.
* Overnight shifts.
* Deterministic source identity.
* Checksum generation.
* Employee mapping.
* Parser-version behavior.
* Missing-field handling.
* Unexpected response shapes.
* Redaction.

25.2 Reconciliation tests

Cover:

* First-time create.
* Duplicate poll.
* Unchanged activity.
* Clock-out added later.
* Pause added later.
* Manual timestamp correction.
* Employee reassignment where observable.
* Deleted or voided activity.
* Incomplete pagination.
* Failed persistence followed by replay.
* Overlapping windows.
* Concurrent poll prevention.

25.3 Worker tests

Cover:

* Scheduling.
* Lock acquisition.
* Lock expiry.
* Retry classification.
* Graceful shutdown.
* Browser timeout.
* Authentication expiration.
* Integration isolation.
* Queue coalescing.
* Health-state updates.

25.4 Browser adapter tests

Use sanitized captured fixtures wherever possible.

Keep live Connecteam tests separate and opt-in.

Do not make the standard CI pipeline depend on external Connecteam availability.

The plan must define:

* Mocked browser tests.
* Fixture-based parser tests.
* Optional staging integration tests.
* How session secrets are excluded from fixtures.
* How network requests are recorded and sanitized.

⸻

26. Deployment requirements

The implementation plan must cover:

* Python dependencies.
* Playwright browser installation.
* EC2 package requirements.
* systemd unit creation.
* Environment variables.
* Secret provisioning.
* Redis queue configuration.
* Database migration execution.
* Worker startup order.
* Health verification.
* Log inspection commands.
* Rollback.
* Browser binary compatibility.
* Memory limits.
* Restart policy.
* Diagnostic artifact storage permissions.

Suggested operational commands should include examples for:

sudo systemctl status managerbeyo-connecteam-worker
sudo journalctl -u managerbeyo-connecteam-worker -f
sudo journalctl -u managerbeyo-connecteam-worker --since today --no-pager
sudo systemctl restart managerbeyo-connecteam-worker

Use the final service name selected by the implementation.

⸻

27. Configuration

Evaluate configuration for:

CONNECTEAM_PARSER_ENABLED
CONNECTEAM_POLL_INTERVAL_SECONDS
CONNECTEAM_POLL_MIN_INTERVAL_SECONDS
CONNECTEAM_RECONCILIATION_OVERLAP_SECONDS
CONNECTEAM_BROWSER_HEADLESS
CONNECTEAM_BROWSER_TIMEOUT_SECONDS
CONNECTEAM_POLL_TIMEOUT_SECONDS
CONNECTEAM_MAX_RETRIES
CONNECTEAM_DIAGNOSTICS_ENABLED
CONNECTEAM_DIAGNOSTIC_RETENTION_DAYS
CONNECTEAM_RAW_PAYLOAD_RETENTION_DAYS
CONNECTEAM_BROWSER_RECYCLE_AFTER_POLLS

These are conceptual names. Adapt them to current project naming rules.

Do not use environment variables for per-workspace credentials or browser sessions.

Per-integration sensitive state belongs in encrypted persistence.

⸻

28. Initial discovery phase

Before defining the final extraction implementation, Claude must include a controlled discovery phase.

The discovery phase should:

1. Log into a Connecteam test or authorized client account interactively.
2. Open the relevant time-clock and timesheet pages.
3. Inspect browser network requests.
4. Identify the request or requests that supply historical and open clock activities.
5. Determine pagination.
6. Determine available source identifiers.
7. Determine whether records expose update timestamps.
8. Determine whether open sessions are included.
9. Determine how pauses are represented.
10. Determine how corrected and deleted entries appear.
11. Determine how the time-clock ID is included.
12. Determine required cookies, headers, CSRF state, and request payload.
13. Save sanitized response fixtures.
14. Document the observed response contract.
15. Confirm whether the internal request can be executed through the authenticated Playwright context without DOM scraping.

The discovery tooling must not be the final production implementation unless it is converted into a bounded, validated, and observable adapter.

⸻

29. Incremental delivery phases

Phase 1: Discovery and authenticated retrieval

Deliver:

* Playwright dependency and EC2 installation procedure.
* Interactive authentication proof.
* Session-state capture.
* Session validation.
* One successful retrieval of time activity.
* Sanitized response fixture.
* Documented internal response shape.
* No production polling yet.

Phase 2: Parser and normalized source records

Deliver:

* Versioned Connecteam response parser.
* Source DTO.
* Timezone normalization.
* Employee source identity extraction.
* Raw record persistence.
* Fixture-based tests.

Phase 3: Idempotent reconciliation

Deliver:

* Source identity.
* Checksums.
* Create, update, and unchanged classification.
* Open-session updates.
* Overlapping-window reconciliation.
* Audit events.
* Replay tests.

Phase 4: Dedicated worker runtime

Deliver:

* Dedicated queue or scheduling mechanism.
* Dedicated worker entrypoint.
* Per-integration locking.
* Configurable one-minute polling.
* Retry classification.
* Graceful shutdown.
* systemd service.

Phase 5: Operations and administration

Deliver:

* Integration health status.
* Reauthentication state.
* Manual synchronization.
* Pause and resume.
* Unmapped-user management.
* Diagnostic retrieval.
* Operational CLI.

Phase 6: Production hardening

Deliver:

* Parser-contract monitoring.
* Browser recycling.
* Diagnostic retention.
* Performance metrics.
* Load testing.
* Security review.
* Rollout and rollback procedure.

⸻

30. Rollout strategy

Do not immediately replace the functioning webhook integration.

Support parallel ingestion modes during validation:

* Webhook mode.
* Browser-parser mode.
* Optional comparison mode.

For a controlled test workspace:

1. Keep webhooks active.
2. Run the parser in shadow mode.
3. Retrieve and normalize records without making them authoritative.
4. Compare parser results against webhook-ingested data.
5. Measure missing, delayed, duplicated, and corrected records.
6. Resolve discrepancies.
7. Enable parser persistence.
8. Monitor for an agreed validation period.
9. Only then remove dependency on the paid webhook plan.

Comparison results should include:

* Records present in both.
* Records present only through webhooks.
* Records present only through the parser.
* Timestamp differences.
* Pause differences.
* Update-latency differences.
* Open-session differences.
* Identity-mapping differences.

⸻

31. Reliability acceptance criteria

The implementation is considered ready for production only when:

* Polling runs automatically at the configured interval.
* One integration cannot create overlapping poll cycles.
* Duplicate polls do not create duplicate activities.
* Open sessions are updated when clock-out occurs.
* Manual corrections are detected through the overlap window.
* A worker restart does not lose synchronization state.
* An expired session is detected and reported.
* Authentication secrets do not appear in logs.
* Partial pagination does not advance the cursor.
* Parser contract mismatches do not corrupt normalized activities.
* A failed poll is replayable.
* An integration failure does not stop other integrations.
* Worker health and source-data freshness are visible.
* Manual synchronization uses the same reconciliation path.
* The dedicated service can be deployed, restarted, and inspected independently.
* Browser memory remains bounded during prolonged operation.
* Sanitized fixtures cover the observed Connecteam response contract.

⸻

32. Security and operational acceptance criteria

The implementation is considered secure and operable only when:

* Browser-session state is encrypted at rest.
* Workspace sessions are isolated.
* Logs are redacted.
* Diagnostic artifacts have retention controls.
* CAPTCHA, MFA, and device verification are not bypassed.
* A human-readable reauthentication workflow exists.
* Source account permissions are documented.
* Integration access can be revoked.
* Pausing the integration stops retrieval without deleting data.
* Secret rotation is supported.
* The system records who configured, authenticated, paused, resumed, or reset the integration.

⸻

33. Future migration requirement

The normalized domain and reconciliation path must be reusable by the future native ManagerBeyo time-clock application.

Connecteam-specific concepts must remain in the adapter and source-mapping layers.

The future clock application should be able to produce the same normalized activity command input without depending on:

* Playwright.
* Connecteam sessions.
* Connecteam response shapes.
* Connecteam activity identifiers.

The browser parser is therefore a temporary source adapter, not the foundation of the time-tracking domain.

⸻

34. Required implementation-plan output

Claude must create the implementation plan using the repository’s TEMPLATE_PLAN.

The plan must include:

1. Contract selection and read order.
2. Existing implementation files to inspect and why.
3. Discovery tasks.
4. Data-model changes.
5. Migration steps.
6. Encryption and secret-management changes.
7. Browser adapter modules.
8. Parser modules.
9. Commands and queries.
10. Worker runtime and scheduling.
11. Redis queues and locks.
12. Reconciliation behavior.
13. Router and serializer changes.
14. Integration status endpoints.
15. Operational CLI.
16. Structured logging and metrics.
17. Tests.
18. systemd and deployment changes.
19. Rollout phases.
20. Rollback procedure.
21. Risks and mitigations.
22. Explicit non-goals.
23. File-by-file implementation sequence.
24. Validation commands and expected outcomes.

The plan must identify all assumptions that can only be confirmed during authenticated Connecteam discovery.

It must not invent Connecteam internal endpoints or response fields before they have been observed and documented.