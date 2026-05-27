# XTS Allocator — Architecture Overview

This document is the developer-facing tour of the allocator: what it is,
what data it holds, what you can put into it, and what you can pull
back out. Read [endpoints.md](./endpoints.md) for full request/response
schemas of every route.

## Contents

- [1-tldr](#1-tldr)
- [2-system-shape](#2-system-shape)
- [3-data-model](#3-data-model)
- [4-allocation-lifecycle](#4-allocation-lifecycle)
- [5-what-you-can-store](#5-what-you-can-store)
- [6-what-you-can-retrieve](#6-what-you-can-retrieve)
- [7-federation](#7-federation)
- [8-auth-and-rate-limiting](#8-auth-and-rate-limiting)
- [9-test-coverage](#9-test-coverage)
- [10-gaps-and-things-not-yet-built](#10-gaps-and-things-not-yet-built)

## 1. TL;DR

The XTS allocator is a single Sanic HTTP service backed by SQLite
(SQLite-by-default, PostgreSQL-ready) that gives a fleet of test
devices ("slots") to humans and automation that ask for them, holds
them for a duration, and tracks what happens during the hold (test
runs, heartbeats, errors). It is its own service — `xts_core` is one
of several possible clients. The standalone [bin/allocator](../bin/allocator)
CLI drives the same REST API directly with zero external dependencies.

```
                          ┌──────────────────────┐
   any HTTP client ──────►│  xts allocator       │──► SQLite / PostgreSQL
   (curl, xts, RAFT,      │  (Sanic, port 5000)  │
    bin/allocator,        │                      │──► federated slaves
    CI runners, …)        │  /allocate_slot      │     (other allocators)
                          │  /deallocate_slot    │
                          │  /list_slots         │
                          │  /device/<id>/...    │
                          │  /start_test, ...    │
                          │  /audit/logs         │
                          │  /allocator.xts      │
                          │  /health, /metrics   │
                          └──────────────────────┘
```

## 2. System shape

Single Python process, single SQLite (or Postgres) database, one
mid-layer state machine, optional federation peers. No background
queue, no message bus. Background work is one Sanic-managed asyncio
task ([app.py:check_expired_allocations](../app.py)) that times out
temporary allocations on a tick.

```
 ┌─────────────────────────── allocator process ────────────────────────────┐
 │                                                                          │
 │   ┌────────────┐   ┌──────────────────────────┐   ┌───────────────────┐  │
 │   │   Sanic    │   │  routes/                 │   │  state_machine.py │  │
 │   │  blueprints│──►│  allocation_routes       │──►│  6-state FSM      │  │
 │   │            │   │  device_routes           │   │  transition_device│  │
 │   │  CORS,     │   │  rack_routes             │   └─────────┬─────────┘  │
 │   │  rate      │   │  test_routes             │             │            │
 │   │  limiter,  │   │  federation_routes       │             ▼            │
 │   │  JWT auth  │   │  audit_log_routes        │   ┌───────────────────┐  │
 │   │            │   │  health, export, usage   │   │   audit_log.py    │  │
 │   └────────────┘   │  auth                    │   │   (every state    │  │
 │                    └────────┬─────────────────┘   │    change logged) │  │
 │                             │                     └─────────┬─────────┘  │
 │                             ▼                               │            │
 │                    ┌────────────────────────────────────────▼─────────┐  │
 │                    │             models.py (SQLAlchemy ORM)           │  │
 │                    │  Rack, Device, AllocationHistory, TestExecution, │  │
 │                    │  Server, AuditLog                                │  │
 │                    └────────────────────┬─────────────────────────────┘  │
 │                                         │                                │
 │  ┌──────────────────────────────────────▼─────────────────────────────┐  │
 │  │   SQLite (xts_allocator.db)  /  PostgreSQL (config-switched)       │  │
 │  └────────────────────────────────────────────────────────────────────┘  │
 │                                                                          │
 │   background:  asyncio task → expire temporary allocations every tick    │
 └──────────────────────────────────────────────────────────────────────────┘
                                  ▲     ▲
                                  │     │
                                  │     └── HTTP from other allocator masters
                                  │            (federation: /servers/<id>/devices,
                                  │             /devices/federated)
                                  │
                                  └── HTTP polling from RAFT / xts_core /
                                      bin/allocator / curl
```

## 3. Data model

Six entities. All defined in [models.py](../models.py). Relationships
shown with `─►` for "one to many" (parent → children).

```
 Rack ─► Device ─► AllocationHistory ─► TestExecution
                                       (also FK to Device directly)

 Server   (federation peers, no FK to local rows)
 AuditLog (FK-free; carries resource_type + resource_id as soft refs)
```

### 3.1 Rack

The physical chassis / cabinet that holds slots. One Rack has many
Devices.

| field | type | notes |
|---|---|---|
| `id` | int PK | autoincrement |
| `name` | string, unique | e.g. `190.02`, `cats-rack-sn-627` |
| `location` | string? | room / floor identifier |
| `building` | string? | building name or code |
| `description` | string? | free text |
| `created_at` | datetime | UTC |

### 3.2 Device (a slot in a rack)

This is the "thing you allocate." A device is always tied to exactly
one rack via `rack_id`. The whole device record is per-slot — there is
no concept of a shared "device template" today (see
[10-gaps-and-things-not-yet-built](#10-gaps-and-things-not-yet-built)).

| group | field | type | notes |
|---|---|---|---|
| **identity** | `id` | int PK | |
| | `rack_id` | int FK → racks.id | required |
| | `slot_name` | string | slot label inside the rack, e.g. `Slot1`, `14(A14)` |
| | `platform` | string?, indexed | classification used for matching: `Cisco`, `raspberry-pi`, … |
| | `tags` | string? | comma-separated free-form labels for search/filter |
| | `description` | string? | free text |
| **hardware** | `make`, `model`, `model_alias` | strings | |
| | `serial_number`, `manufacturer`, `firmware` | strings | |
| | `host_mac`, `host_ipv4`, `host_ipv6` | strings | |
| **config** | `control_uris` | **JSON** | per-device control endpoints (e.g. serial console URL, IPMI, PDU port) |
| | `external_equipment` | **JSON** | array describing attached test gear — see [5-what-you-can-store](#5-what-you-can-store) |
| **lifecycle** | `state` | enum string, indexed | `free` / `allocated` / `busy` / `resetting` / `maintenance` / `offline` (see [4-allocation-lifecycle](#4-allocation-lifecycle)) |
| | `state_changed_at` | datetime | UTC |
| | `owner_email` | string?, indexed | who currently holds it; cleared on dealloc |
| | `allocation_type` | enum string | `temporary` (expires) or `permanent` |
| | `allocation_expiry` | datetime? | when a temporary allocation ends |
| **runtime** | `software_version` | string? | what's currently flashed on the device |
| | `last_verified` | datetime? | last health-check pass |
| | `last_seen` | datetime? | last `/report_status` |
| | `connectivity_status` | string? | `online` / `offline` / `unreachable` |
| | `system_metrics` | **JSON** | last-reported CPU / memory / uptime / arbitrary keys |
| **bookkeeping** | `created_at`, `updated_at` | datetimes | |

### 3.3 AllocationHistory

One row per allocation (started by `/allocate_slot`, closed by
`/deallocate_slot` or expiry). Survives the device — querying
allocation history is how you ask "who had box X yesterday."

| field | type | notes |
|---|---|---|
| `id` | int PK | |
| `device_id` | int FK → devices.id | |
| `user`, `email`, `name` | strings | who allocated |
| `start_time` | datetime | when allocated |
| `end_time` | datetime? | when deallocated; null while open |
| `duration_requested` | int? | minutes the caller asked for |
| `allocation_type` | enum | `temporary` / `permanent` |
| `state_before`, `state_after` | strings | bookend states |
| `software_version` | string? | what was on the device at alloc time |
| `test_execution_count` | int | how many tests ran during this allocation |
| `total_test_time` | int | minutes in `busy`/`testing` |
| `idle_time` | int | minutes allocated-but-not-testing |

### 3.4 TestExecution

One row per test run on a device. May reference an `AllocationHistory`
row but doesn't have to. Heartbeat-driven hang detection lives here.

| field | type | notes |
|---|---|---|
| `id` | int PK | |
| `device_id` | int FK → devices.id | |
| `allocation_history_id` | int? FK | optional link to the allocation that owned the box |
| `test_name`, `test_suite` | strings | |
| `expected_duration`, `max_duration` | int minutes | hard cap defaults to 240 |
| `start_time` | datetime, indexed | |
| `end_time` | datetime? | null while running |
| `last_heartbeat` | datetime? | updated by `/test_heartbeat` |
| `heartbeat_timeout` | int | minutes-without-heartbeat → "hung", default 10 |
| `status` | string? | `success` / `failure` / `error` / `timeout` / `hung` |
| `exit_code` | int? | |
| `logs_url` | string? | external log location |
| `error_message` | string? | |
| `test_metadata` | **JSON** | per-test arbitrary structured data |

### 3.5 Server (federation peer)

Used by master/slave aggregation. A master allocator records the
existence of other allocator instances here and proxies/aggregates
through them. See [7-federation](#7-federation).

| field | notes |
|---|---|
| `name`, `url` (unique), `location` | who they are, where they live |
| `role` | `master` or `slave` |
| `status` | `online` / `offline` / `unreachable` |
| `device_count` | cached count from last heartbeat |
| `last_heartbeat` | freshness signal |
| `server_metadata` | **JSON** | arbitrary peer metadata |

### 3.6 AuditLog

Append-only event log. Every state change, allocation, dealloc, auth
event, test start/end, unauthorized access attempt is written here.
Queryable via `GET /audit/logs` (admin-only). FK-free by design —
carries `resource_type` + `resource_id` so soft refs survive resource
deletion.

Key fields: `timestamp`, `event_type`, `event_category`, `severity`,
`user_email`, `user_role`, `source_ip`, `endpoint`, `http_method`,
`success`, `status_code`, `error_message`, `details` (JSON), plus a
`request_id` for correlation across log lines.

## 4. Allocation lifecycle

The allocator is a 6-state FSM, enforced in
[state_machine.py](../state_machine.py). All `/allocate_slot`,
`/deallocate_slot`, `/start_test`, `/end_test`, `/change_device_state`
calls funnel through `transition_device()` so the wire endpoint can't
do anything the FSM forbids.

```
                 ┌─────────────┐   change_device_state (admin)
                 │   offline   │◄─────────────────────────────┐
                 └──────▲──────┘                              │
                        │                                     │
                        │  change_device_state (admin)        │
                        ▼                                     │
                  ┌───────────┐    /allocate_slot     ┌──────────────┐
                  │   free    │───────────────────────►   allocated  │
                  │           │◄──────────────────────│              │
                  └─────▲─────┘    /deallocate_slot   └──────┬───────┘
                        │                                    │
       /change_device_  │                                    │  /start_test
       state (admin)    │                                    │
                        │                                    ▼
                 ┌──────┴──────┐                      ┌─────────────┐
                 │ maintenance │                      │   testing   │  (busy)
                 └─────────────┘                      └──────┬──────┘
                        ▲                                    │ /end_test
                        │       admin overrides              │
                        │                                    ▼
                        │                             ┌─────────────┐
                        └─────────────────────────────│  resetting  │
                                                      └──────┬──────┘
                                                             │
                                                             │ /change_device_state
                                                             ▼ (admin → free)
                                                          (free)
```

Transitions explicitly allowed by [state_machine.py](../state_machine.py):

| from \ to  | free | allocated | busy | resetting | maintenance | offline |
|---|---|---|---|---|---|---|
| **free**        | -   | ✓ | -   | -   | ✓ | ✓ |
| **allocated**   | ✓ | -   | ✓ | -   | ✓ | ✓ |
| **busy**        | -   | -   | -   | ✓ | ✓ | ✓ |
| **resetting**   | ✓ | -   | -   | -   | ✓ | ✓ |
| **maintenance** | ✓ | -   | -   | -   | -   | ✓ |
| **offline**     | ✓ | -   | -   | -   | ✓ | -   |

Any other transition is rejected with HTTP 400 *before* any DB write.

## 5. What you can store

This is the explicit answer to "I'm expecting to be able to store
common device_configs and also racks + slot information."

### 5.1 Racks

Full first-class entity. Create via `POST /add_rack` (or implicit
when you `POST /add_slot` with a previously-unseen `rackName`).
Stores name, location, building, description.

### 5.2 Slots (devices)

First-class entity. One row per physical slot. See
[3-2-device-a-slot-in-a-rack](#3-2-device-a-slot-in-a-rack) for the
field list. Per-device config lives in three JSON fields:

- **`control_uris`** — how to reach the box. E.g.
  ```json
  {
    "serial": "telnet://console.lab/12345",
    "ipmi":   "http://ipmi.lab/box-42",
    "pdu":    "http://pdu.lab/?port=14"
  }
  ```
- **`external_equipment`** — attached test gear, an array of
  `{type, name, …}` objects. E.g.
  ```json
  [
    {"type": "rf_chamber", "name": "Candela LF350"},
    {"type": "power_meter", "name": "PM-200", "port": "/dev/ttyUSB2"}
  ]
  ```
- **`system_metrics`** — last-reported runtime telemetry (CPU%,
  memory, uptime, anything). Pushed by `POST /report_status`.

### 5.3 "Common device configs"

**Important caveat — there is no shared device-config template entity
today.** Each device row carries its own copy of `control_uris` /
`external_equipment`. If you have 50 identical boxes, you store the
same JSON 50 times.

Two ways forward, neither implemented yet:

1. **Add a `DeviceConfigTemplate` entity** with name + JSON payload,
   plus a nullable `device.config_template_id` FK. Devices either
   point at a template OR carry an override JSON. Most natural for
   "rack of identical boxes" use cases.
2. **Add server-side `includes:` resolution** so the `.xts` command
   surface (already served at `/allocator.xts`) can reference shared
   config blobs — but this is more about command UX than device state.

The user-facing decision is whether configs are "device attributes
that happen to be JSON" (today's model) or "first-class shared assets
that devices reference" (the template model). Tracked-able as a new
issue if you want this — neither approach exists yet.

### 5.4 Allocations and their history

Every allocation creates an `AllocationHistory` row (open-ended,
`end_time = null`) and closes it on dealloc. You don't store
"allocations" directly — the device's `state` + `owner_email` +
`allocation_expiry` are the *current* truth, and history is the
audit trail.

### 5.5 Test executions

`TestExecution` rows per test run, with heartbeat-driven hang
detection. Carry `test_metadata` (JSON) for whatever per-test data
your test framework wants to record alongside.

### 5.6 Federation peers

Other allocator instances you want this one to aggregate from. Stored
in `Server` with name, URL, role, last-heartbeat. See
[7-federation](#7-federation).

### 5.7 Audit log

Every state-changing action lands in `AuditLog`. Including the
`details` JSON for arbitrary before/after diffs, request payloads,
etc. This is the "what happened in the last hour" answer.

## 6. What you can retrieve

Grouped by purpose. Full schemas in
[endpoints.md](./endpoints.md). Auth notes in
[8-auth-and-rate-limiting](#8-auth-and-rate-limiting).

### 6.1 Browse the fleet (read-only, no auth)

- `GET /list_slots` — full device list, every column.
- `POST /list_slots` — same, with filter body (`platform`, `tags`,
  `state`, `owner_email`, free-text `query`, …).
- `POST /devices/search` — richer search (joins `Rack`, filters by
  rack name/equipment type, etc.).
- `GET /list_racks` — racks plus device counts and per-state breakdown.
- `GET /rack/<id>` and `GET /rack/<id>/devices` — single rack drill-in.
- `GET /device/<id>/box_status` — **compact** payload designed for
  high-frequency polling: state, target_id, owner, active test
  summary, heartbeat age. No rack metadata, no history.
  Unauthenticated by design — RAFT/xts pollers don't carry JWTs.

### 6.2 Allocate / deallocate (auth: engineer)

- `POST /allocate_slot` — by `id`, `platform[+tags]`, or `target_id`.
  Returns `slot_id`, `rackName`, `slotName`, `target_id`, `state`,
  `owner_email`, `allocation_history_id` (+ `allocation_expiry` for
  temporary allocations).
- `POST /deallocate_slot` — free a held box.
- `POST /allocate_permanent` — admin: hold indefinitely, no expiry.
- `POST /borrow_slot` / `POST /return_borrowed_slot` — short hand-off
  flow without changing primary owner.
- `POST /change_device_state` — admin: force into any state the FSM
  permits (maintenance, offline, etc.).
- `GET /device/<device_id>/valid_states` — what transitions are legal
  from the device's current state.

### 6.3 Test execution (auth: engineer)

- `POST /start_test`, `POST /test_heartbeat`, `POST /end_test` — the
  test lifecycle.
- `GET /test_executions` — list (filter by `device_id`, `status`,
  `active_only`).
- `GET /device/<id>/box_status` — compact "is this box still working?"
  used by pollers.

### 6.4 History and audit

- `GET /allocation_history` — every allocation ever (filter by
  `device_id`, `email`, `from`, `to`).
- `GET /audit/logs` — full audit trail (admin-only). Filter by user,
  event type, category, time range, severity. Paginated.
- `GET /audit/summary` — counts grouped by category / severity.
- `GET /audit/events/types` — enumerate event-type values.

### 6.5 Usage analytics

- `GET /device/<id>/usage_stats` — utilization for one box.
- `GET /usage_summary?days=N` — fleet-wide stats: total allocations,
  unique users, average per day, top devices.

### 6.6 Export for downstream consumers (RAFT, python_raft)

- `GET /export/raft_config?owner_email=…` — allocator → RAFT YAML.
- `GET /export/python_raft_config` — older python-RAFT format.
- `GET /export/python_raft_device_profile` and
  `/export/python_raft_rack_config` — sub-pieces of the same export.

### 6.7 Federation

- `GET /servers` — peers, with status filter.
- `GET /servers/<id>` — one peer's detail.
- `GET /servers/<id>/devices` — proxy to that peer's `/list_slots`.
- `GET /devices/federated` — aggregate across every online peer.

### 6.8 Operational

- `GET /health` — DB + service health.
- `GET /metrics` — Prometheus text format.
- `GET /allocator.xts` — the `.xts` command-surface file (xts_core
  pulls this for its dynamic command load).
- `POST /login`, `POST /refresh`, `GET /auth/verify`,
  `GET /auth/roles` — JWT auth flow.

## 7. Federation

Optional. If you want a single "show me every box anywhere" view,
register slave allocators on a master:

```
                       master allocator
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   slave-1                slave-2             slave-N
   (its own DB,           (its own DB)        (its own DB)
    racks, slots)
```

- Slaves call `POST /register` then `POST /heartbeat` on the master.
- `GET /servers/<id>/devices` proxies through to one slave.
- `GET /devices/federated` fan-outs and aggregates. Per-device rows
  in the response carry `server_id`, `server_name`,
  `server_location` so the caller knows which slave it lives on.

Federation is *optional* — a single allocator can run alone. The
master is a regular allocator instance with peers registered to it;
nothing structurally different.

## 8. Auth and rate limiting

JWT, three roles, sliding-window rate limit per user email.

| role | can do |
|---|---|
| `readonly` | GETs only (list, browse, history, status). |
| `engineer` | + allocate / dealloc / start_test / heartbeat / end_test / add_slot / update_slot. |
| `admin` | + change_device_state (any FSM-legal transition), `/audit/*`, force-dealloc. |

Demo users baked in for local dev are in [auth.py](../auth.py)
(`admin@example.com / admin123`, `engineer@example.com / engineer123`,
`viewer@example.com / viewer123`) — replace before production.

Rate limit: 30 req/min/user-email on write endpoints, 60 read.
Returns 429 with a `Retry-After` header on breach. State is
process-local; tests reset between cases via fixture.

## 9. Test coverage

411 tests passing (0 skipped, 0 failed) across 22 files. Allocation
and adjacent areas are particularly well-covered — that's what most
of the test surface exercises.

| file | tests | focus |
|---|---:|---|
| `test_allocation.py` | 20 | by-id, by-platform, by-tags, by-target_id, error paths |
| `test_phase2_allocations.py` | 11 | permanent allocations + `/report_status` |
| `test_concurrency.py` | 11 | atomicity, rollback, state consistency, expiry |
| `test_state_machine.py` | 4 | FSM via HTTP |
| `test_state_machine_unit.py` | 21 | FSM as a pure unit (parametrised over every state pair) |
| `test_state_transitions_api.py` | 16 | every legal/illegal transition via the API |
| `test_workflow_e2e.py` | 9 | allocate → start_test → heartbeat → end → dealloc lifecycles |
| `test_test_execution.py` | 12 | test-execution endpoints, filters |
| `test_history.py` | 4 | `AllocationHistory` retrieval |
| `test_audit_log.py` | 19 | every event type, admin-only access, time filters, pagination |
| `test_xts_core_contract.py` | 11 | locks wire shape downstream clients depend on |
| `test_route_input_validation.py` | 23 | every flagged 500-on-bad-input path returns 400 |
| `test_rate_limiting.py` | 9 | per-email throttle |
| `test_auth.py` | 19 | JWT login, role guards |
| `test_devices.py`, `test_racks.py`, `test_export.py`, `test_federation.py`, `test_health.py`, `test_usage_stats.py`, `test_input_validation.py`, `test_allocator_xts.py` | … | the rest |

Run:
```
./test.sh                 # full suite, ~18s
./test.sh tests/test_allocation.py
./test.sh -k expiry       # ad-hoc selector
```

Or drive a real running instance end-to-end via the standalone CLI:
```
bin/allocator smoke       # login → add → allocate → start_test →
                          # heartbeat → box_status → end → dealloc
```

`smoke` is non-zero exit on the first failure and uses no xts / .xts /
xts_core code path — it's the "is this allocator actually working?"
check you can point at any deploy.

## 10. Gaps and things not yet built

Honest list — not blockers, but worth knowing before you build on
top.

- **No shared device-config template entity.** Per-device config
  fields (`control_uris`, `external_equipment`) are duplicated across
  every device row. See [5-3-common-device-configs](#5-3-common-device-configs).
- **Async SQLAlchemy sessions.** All routes use sync sessions inside
  async handlers; under heavy concurrent load this blocks the event
  loop. Fine for current scale; flagged in `TODO.md`.
- **Pagination on `/list_slots` is absent.** Returns the whole fleet.
  At 100+ devices this should grow `limit` / `offset` / stable sort.
- **OpenAPI spec is 13 of ~42 endpoints.** [openapi_spec.py](../openapi_spec.py)
  needs to catch up with reality before client generation.
- **`xts_core`'s bundled allocator plugin calls older endpoint names**
  (`/allocate`, `/deallocate`, `/slot/<id>/rack-config`) — tracked in
  [rdkcentral/xts_core#59](https://github.com/rdkcentral/xts_core/issues/59).
  The contract tests in `test_xts_core_contract.py` document the
  current ground truth.
- **No background worker.** Heartbeat-timeout handling and allocation
  expiry both run on the Sanic asyncio loop. Survives a single process
  fine; doesn't survive process restart unless restarted state is
  reconstructed from DB on boot.
