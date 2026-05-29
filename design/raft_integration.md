# RAFT integration — design

How [python_raft](https://github.com/rdkcentral/python_raft) and this
allocator fit together: what the allocator should expose, what RAFT
should accept, where the current shapes disagree, and what changes
are needed on both sides.

This is a **design doc**, not built yet. Code lives only in the
schemas, exports, and tests already on this branch — see
[5-todays-allocator-exports](#5-todays-allocator-exports) for that
current surface.

## Contents

- [1-context](#1-context)
- [2-rafts-two-files-the-canonical-shapes](#2-rafts-two-files-the-canonical-shapes)
- [3-what-raft-actually-reads](#3-what-raft-actually-reads)
- [4-the-include-bug-in-raft](#4-the-include-bug-in-raft)
- [5-todays-allocator-exports](#5-todays-allocator-exports)
- [6-gap-analysis](#6-gap-analysis)
- [7-proposed-allocation-bundle-schema-v3](#7-proposed-allocation-bundle-schema-v3)
- [8-the-vts-element-pattern-permanent-plus-borrow](#8-the-vts-element-pattern-permanent-plus-borrow)
- [9-monitor-during-test-the-optional-callback-hook](#9-monitor-during-test-the-optional-callback-hook)
- [10-backwards-compatibility-strategy](#10-backwards-compatibility-strategy)
- [11-changes-required-allocator-side](#11-changes-required-allocator-side)
- [12-changes-required-python-raft-side](#12-changes-required-python-raft-side)
- [13-rollout-and-test-plan](#13-rollout-and-test-plan)

## 1. Context

RAFT today drives tests against real boxes by reading two YAML files
at startup:

- **`device.yaml`** — *platform-shared defaults* keyed by a logical
  device class (e.g. `cpe1`). One file per platform; everyone who has
  that platform uses the same file. Long-lived, source-controlled.
- **`rackConfig.yaml`** (`config.yaml`) — *the engineer's allocation*:
  which rack, which slot, which physical box(es), how to reach each
  one (consoles, power, IR, CEC, AV-sync). Short-lived (one per test
  session / one per allocation).

The allocator already exposes a YAML at `/export/python_raft_config`
that tries to produce a `rackConfig.yaml`. It's close but not quite
right (see [6-gap-analysis](#6-gap-analysis)), and it doesn't yet
carry the optional test-monitoring hook the user has asked for.

The aim is:
1. Allocator becomes the canonical source for the **rackConfig** an
   engineer needs after they allocate.
2. `device.yaml` stays mostly out-of-tree (platform owners maintain
   it), but the allocator can either include-by-reference or bundle
   it inline on request.
3. RAFT learns to handle the dict-form `includes:` the current
   examples already document (today only the list-form `include:`
   works — see [4-the-include-bug-in-raft](#4-the-include-bug-in-raft)).
4. RAFT learns to optionally call back to the allocator during a test
   run so the allocator's `box_status` always reflects reality.
5. The existing v1/v2 export endpoints keep working unchanged — old
   RAFT versions don't break.

## 2. RAFT's two files — the canonical shapes

### 2.1 `device.yaml` — platform-shared defaults

From [git/python_raft/examples/configs/example_device_config.yml](../../python_raft/examples/configs/example_device_config.yml):

```yaml
deviceConfig:
    cpe1:
        platform:   "linux"
        model:      "PC"
        prompt:     "raft@test-linux:~ $"
```

Top-level key: `deviceConfig`. Children keyed by **logical device
class** name (any string; convention is `cpe<n>`). Each class
declares the platform-wide constants — platform, model, default
shell prompt, image URLs, memory map, etc.

There can be multiple classes per file (one for each device type the
team uses). The file is read once and applies to every allocation
that references any of its `cpe*` keys.

### 2.2 `rackConfig.yaml` — the engineer's allocation

From [git/python_raft/examples/configs/example_rack_config.yml](../../python_raft/examples/configs/example_rack_config.yml):

```yaml
globalConfig:
    includes:
        deviceConfig: "example_device_config.yml"   # pointer to (2.1)
    local:
        log:
            directory: "./logs"
            delimiter: "/"

rackConfig:
    rack1:
        name: "rack1"
        description: "example config at my desk"
        slot1:
            name: "slot1"
            devices:
                - dut:
                    ip: "127.0.0.1"
                    description: "local PC"
                    platform: "linux PC"
                    consoles:
                        - default: { type: serial, port: /dev/ttyUSB0 }
                        - ssh:     { port: 22, username: root, ip: 192.168.99.1 }
                    powerSwitch:        { ... }    # optional
                    remoteController:   { ... }    # optional
                    outbound:           { ... }    # optional
                    hdmiCECController:  { ... }    # optional
                    avSyncController:   { ... }    # optional
                - pi2:
                    ip: "192.168.99.1"
                    platform: "pi4"
                    consoles:
                        - ssh: { type: ssh, port: 22, username: root }
```

Top-level keys: `globalConfig` and `rackConfig`. Inside `rackConfig`
there can be many rack entries; inside each rack many slots; inside
each slot one **list** of named devices (because a slot can carry a
DUT plus a helper Pi plus a serial concentrator etc.).

Each named device dict carries the per-allocation "how do I reach
this specific physical box" information. The schema is open —
optional sections are skipped if absent.

## 3. What RAFT actually reads

Confirmed in
[git/python_raft/framework/core/deviceManager.py](../../python_raft/framework/core/deviceManager.py)
(`__init__` lines 174–194). From each device dict it pulls exactly:

| key | type | what RAFT does with it |
|---|---|---|
| `powerSwitch` | dict | constructs the right power-control driver (`kasa`, `tapo`, `apc`, `olimex`, `SLP`, `orvbioS20`, `hs100`, `none`) |
| `consoles` | list of `{name: {...}}` | opens a `serial` / `ssh` / `telnet` channel for each; respects `enabled: false` to skip a console |
| `outbound` | dict | builds an `outboundClientClass` for upload/download/proxy/workspace |
| `remoteController` | dict | constructs the right IR/key-injection driver (`olimex`, `skyProc`, `redrat`, `keySimulator`, `none`) |
| `hdmiCECController` | dict | constructs a CEC controller (`cec-client`, `remote-cec-client`, `virtual-cec-client`) |
| `avSyncController` | dict | constructs an A/V sync analyser (`SyncOne2`) |

Everything else in the dict (`ip`, `description`, `platform`, etc.)
is metadata that the test code can read but RAFT itself doesn't act
on at the driver level.

## 4. The include bug in RAFT

The example `rackConfig.yml` shows:

```yaml
globalConfig:
    includes:
        deviceConfig: "example_device_config.yml"
```

But the actual loader at
[framework/core/configParser.py:88-104](../../python_raft/framework/core/configParser.py#L88-L104):

```python
def processIncludes(self, config):
    if isinstance(config, dict):
        if "include" in config:                    # singular, list form
            deviceConfigFilePaths = config["include"]
            for configFilePath in deviceConfigFilePaths:
                newConfig = self.loadYaml(configFilePath)
                self.processIncludes(newConfig)
                config.update(newConfig)
            config.pop("include")
        for key, value in config.items():
            self.processIncludes(value)
    elif isinstance(config, list):
        for item in config:
            self.processIncludes(item)
```

`processIncludes` only matches `include:` (singular, list of paths).
It never matches `includes:` (plural, dict form) that the example
file uses. Result: the canonical example *does not actually wire the
device config through*. Anyone copying the example sees `cpe1` is
undefined at test time and has to merge the file by hand.

The RAFT side needs both:
1. **Fix the parser** to also handle the `includes:` dict form the
   examples document.
2. **Optionally accept a URL** (not just a local path) so RAFT can
   fetch the `device.yaml` directly from the allocator's
   `/export/device_config` endpoint (see
   [12-changes-required-python-raft-side](#12-changes-required-python-raft-side)).

## 5. Today's allocator exports

In [routes/export_routes.py](../routes/export_routes.py):

| endpoint | what it currently returns | RAFT can consume it? |
|---|---|---|
| `GET /export/raft_config?owner_email=…` | "allocator-optimized" YAML: top-level `version`, `allocator`, `allocations: [{device, rack, metadata, …}]`. Bespoke shape, not the RAFT shape. | **No** — wrong top-level structure |
| `GET /export/python_raft_config` | `globalConfig` + `rackConfig` close to the RAFT shape, plus extra `schema_version`, `profile_type`, `generated_at`, `allocator.url` keys | **Almost** — RAFT ignores the extra keys; the include is `includes:` (dict form) which RAFT's parser doesn't handle (see [4-the-include-bug-in-raft](#4-the-include-bug-in-raft)) |
| `GET /export/python_raft_device_profile` | `deviceConfig.platformProfiles` (new) + `legacyDeviceConfig` (per-cpe). Hybrid format. | **Partial** — RAFT looks for `deviceConfig.cpe<n>`, not `deviceConfig.platformProfiles` |
| `GET /export/python_raft_rack_config` | Same body as `python_raft_config` | **Same as that row** |

Tests exist for each endpoint in
[tests/test_export.py](../tests/test_export.py) but verify the
*allocator's* output shape, not round-trip RAFT consumption.

## 6. Gap analysis

| concern | today | needs to be |
|---|---|---|
| `deviceConfig` shape | nested under `platformProfiles` + `legacyDeviceConfig` keys | flat `deviceConfig.<cpeKey>` matching RAFT's reader |
| `rackConfig` include | `globalConfig.includes.deviceConfig: "<path>"` | either fix RAFT to parse `includes:` OR switch to `include: [<path>]` list-form for compatibility today |
| `device.yaml` source | not separately exported | new endpoint: `GET /export/device_config?platform=<p>` returning only the `deviceConfig:` for one platform |
| Devices array per slot | always a single-element `[{dut: {...}}]` | allow multi-device slots (e.g. DUT + helper Pi) — the data model already supports this via `Device.external_equipment`, just needs surfacing |
| Per-device `consoles` | always `[{default: {ssh, ...}}]` synthesised from `host_ipv4` | sourced from `Device.control_uris` JSON which can carry `serial`, `ssh`, `telnet` entries with full config |
| `powerSwitch` / `remoteController` / `hdmiCEC` / `avSync` | not exported at all | sourced from `Device.external_equipment` and/or new typed columns |
| Test-monitor callback | absent | new optional `monitor:` block in the rackConfig that points RAFT at the allocator's heartbeat endpoint (see [9-monitor-during-test-the-optional-callback-hook](#9-monitor-during-test-the-optional-callback-hook)) |
| vts-element / "borrow" surfacing | model supports it (`allocation_type = permanent`, `/borrow_slot` endpoint) but not documented as the canonical pattern | section [8-the-vts-element-pattern-permanent-plus-borrow](#8-the-vts-element-pattern-permanent-plus-borrow) makes it the explicit recommendation |

## 7. Proposed allocation bundle — schema v3

Single YAML returned from a new `GET /export/raft_bundle` (or
overload the existing `/export/python_raft_config?schema=v3`). RAFT
upgrade lets it consume this directly without needing two separate
files.

```yaml
# schema marker so RAFT can branch on shape without guessing
schema:
  name: "xts-allocator-raft-bundle"
  version: 3
  generated_at: "2026-05-28T11:00:00Z"
  allocator:
    url: "http://allocator.lab:5000"
    allocation_history_id: 1742

# Inlined device.yaml — the platform defaults for every cpe class
# this allocation will need. Allocator pulls these from the same
# place /export/device_config?platform=<p> does.
#
# Engineers who want their own override can drop a sibling override
# block at the top of their local rackConfig and RAFT merges.
deviceConfig:
  cpe1:
    platform: "linux"
    model:    "PC"
    prompt:   "raft@test-linux:~ $"

# Either of these is acceptable on the RAFT side:
#
#   globalConfig.include: [/path/to/device.yaml, https://allocator/...]
#   globalConfig.includes.deviceConfig: "..."  (dict form, needs parser fix)
#
# When the allocator inlines `deviceConfig:` above, neither is needed.
globalConfig:
  local:
    log:
      directory: "./logs"
      delimiter: "/"

rackConfig:
  rack1:                       # = Device.rack.name
    name:        "rack1"
    description: "Geri's desk"
    slot1:                     # = Device.slot_name (normalised)
      name:        "slot1"
      devices:
        - dut:                 # primary device under test
            ip:          "10.242.30.30"        # host_ipv4
            description: "vts-element"
            platform:    "linux"
            consoles:
              # Sourced from Device.control_uris JSON
              - ssh:
                  type:     "ssh"
                  ip:       "10.242.30.30"
                  port:     10022
                  username: "root"
                  # ProxyJump etc. live here too
              - serial:
                  type:     "serial"
                  port:     "/dev/ttyUSB0"
                  baudRate: 115200
                  enabled:  false              # supported by RAFT today
            powerSwitch:        { type: "kasa", ip: "10.242.30.31", options: "--plug" }
            remoteController:   { type: "redrat", hub_ip: "10.242.30.32", map: "SKY+" }
            outbound:
              download_url:       "https://artifacts.lab/..."
              workspaceDirectory: "./logs/workspace"
            # CEC / AV-sync omitted when not present on the box
        - pi-helper:           # multi-device slot example
            ip:          "10.242.30.45"
            platform:    "pi4"
            consoles:
              - ssh: { type: "ssh", port: 22, username: "pi" }

# OPTIONAL: callback hook the allocator hands to RAFT so RAFT can
# stream test status back. RAFT only acts on this block if BOTH:
#   * its version understands the block, AND
#   * `schema.allocator.url` above is reachable from the RAFT host.
# If either is false at startup, RAFT logs once and skips monitor
# entirely. If reachability is lost mid-run, RAFT disables monitor
# for the rest of the test and continues — the test never fails
# because monitoring failed. See section 9 for the full contract.
monitor:
  enabled: true                                # engineer-overridable: set false to opt out
  allocator_url:       "http://allocator.lab:5000"
  test_execution_id:    null                   # filled in by /start_test response before the run
  heartbeat:
    endpoint:          "/test_heartbeat"
    interval_seconds:  60
    timeout_seconds:   600                     # server-side "hung" mark after this without a beat
  on_start: { endpoint: "/start_test", auto: true }
  on_end:   { endpoint: "/end_test",   auto: true }
  auth:
    type:   "bearer"
    token:  "<JWT pulled from the allocator-side allocation context>"
  # Optional reachability probe before the test starts. If this
  # fails, RAFT logs a single WARN and never enables monitor for
  # this run.
  preflight:
    endpoint:           "/health"
    timeout_seconds:    3
```

The shape is a **strict superset** of today's RAFT input — drop the
`schema:` and `monitor:` blocks and a current RAFT can read it.

## 8. The vts-element pattern — permanent plus borrow

Real boxes on engineers' desks (the `vts-element`, `vts-llama`,
`vts-mytv`, `vts-xione`, … entries in `~/.ssh/config`) follow a
specific pattern the allocator already supports but doesn't
document. Making it explicit:

```
                  ┌──────────────────────────────────────────────┐
                  │   vts-element (perm. allocated to Bob)       │
                  │                                              │
                  │   Device.allocation_type = "permanent"       │
                  │   Device.owner_email     = "bob@…"           │
                  │   Device.allocation_expiry = null            │
                  └────────────────┬─────────────────────────────┘
                                   │
                  ┌────────────────▼────────────────────────────┐
                  │  Visible to everyone in GET /list_slots     │
                  │  state shows "allocated", owner_email = Bob │
                  └────────────────┬────────────────────────────┘
                                   │
        Alice wants it for an hour │
                                   ▼
                  ┌────────────────────────────────────────────┐
                  │  POST /borrow_slot                         │
                  │    user.email = alice@…                    │
                  │    slot.id    = <box-id>                   │
                  │    duration   = "1h"                       │
                  │                                            │
                  │  → Device.borrower_email = alice@…         │
                  │  → primary owner_email STAYS bob@…         │
                  │  → allocation_expiry = now + 1h            │
                  │  → AllocationHistory row opened against    │
                  │    Alice for the borrow window             │
                  │  → audit event: borrow_start               │
                  └────────────────┬───────────────────────────┘
                                   │
                       Alice's test runs
                                   │
                                   ▼
                  ┌────────────────────────────────────────────┐
                  │  POST /return_borrowed_slot                │
                  │  → borrower_email cleared                  │
                  │  → Bob's permanent allocation persists     │
                  │  → audit event: borrow_end                 │
                  └────────────────────────────────────────────┘
```

Current state on this branch:

- ✅ `Device.allocation_type = "permanent"` field exists and is
  honoured (no expiry, immune to the background expiry sweep).
- ✅ `POST /allocate_permanent` endpoint exists
  ([routes/allocation_routes.py](../routes/allocation_routes.py)).
- ✅ `POST /borrow_slot` and `POST /return_borrowed_slot` endpoints
  exist for the temporary hand-off.
- ✅ Visibility — `GET /list_slots` shows everything regardless of
  ownership; no role gate on the read path.
- ⚠️ The `borrower_email` is implemented as transient owner
  overwrite in some code paths rather than a separate column. Worth
  auditing — having both `owner_email` (perm) and `borrower_email`
  (transient) cleanly separated makes UI and audit much easier.
- ❌ No "ask the owner" notification flow. Pure ask-on-Slack today.

A small follow-up issue should formalise the borrower-as-separate-field
distinction and decide whether to ship an in-band "request access"
ping or leave that to out-of-band coordination.

## 9. Monitor-during-test — the optional callback hook

Two hard preconditions before monitoring can run at all:

1. **The bundle was generated by an allocator.** If the engineer is
   running RAFT against a hand-written rackConfig with no `schema:`
   block, there is no `monitor:` to honour — nothing to do. The
   `schema.allocator.url` field in the v3 bundle is the unambiguous
   "this came from the allocator" signal RAFT keys off; if it's
   absent or empty, monitoring is skipped silently.
2. **The RAFT host can reach `schema.allocator.url` on the network.**
   Same subnet, routable, no firewall in between. Monitoring is *not*
   a thing the allocator can will into existence from across an
   unreachable boundary. RAFT must probe reachability once at startup
   before scheduling any callbacks (see "Failure modes" below).

Given both preconditions, the allocator already has the *receiving*
side: `POST /start_test`, `POST /test_heartbeat`, `POST /end_test`,
plus the `TestExecution` model with `last_heartbeat`,
`heartbeat_timeout`, and the `GET /device/<id>/box_status` polling
endpoint that reports `active_test.heartbeat_age_seconds`.

What's missing is the *handshake*: when the allocator hands a
rackConfig to an engineer, it should hand a small `monitor:` block
along with it so RAFT (if upgraded to honour the block) calls back:

```
   engineer runs:                     allocator                       RAFT
   raft -c rackConfig.yaml
   ───────────────────────────────────────────────────────────────────────
                                                                ┌──────┐
   1. download config            ──► /export/raft_bundle  ──►   │RAFT  │
                                      → body includes            │loads │
                                        monitor: { ... }         │config│
                                                                 └──┬───┘
   2. RAFT starts                                                   │
                                ◄── POST /start_test ───────────────┤
                                    { device_id, test_name, ... }   │
                                ──► { test_execution_id: 91 } ─────►│
                                                                    │
   3. while running, every 60s                                      │
                                ◄── POST /test_heartbeat ───────────┤
                                    { test_execution_id: 91 }       │
                                                                    │
   4. test finishes                                                 │
                                ◄── POST /end_test ─────────────────┤
                                    { test_execution_id: 91,        │
                                      status: "success" }           │
                                                                ┌───┴──┐
                                                                │ done │
                                                                └──────┘

  meanwhile, anyone polling /device/<id>/box_status sees:
    state=testing, active_test.{name, elapsed_minutes, heartbeat_age_seconds}
```

Design points:

- **Always optional.** If RAFT is older, the bundle has no `schema:`
  block (hand-written rackConfig), the engineer wants to run silent,
  or `monitor.enabled: false`, then nothing calls back. Box state
  stays "allocated" through the test run rather than transitioning
  to "busy".
- **Auth threads through.** The allocator stamps a short-lived JWT
  scoped to this allocation onto `monitor.auth.token`. RAFT echoes
  it back on every callback. No new credential plumbing for the
  engineer.
- **Hung detection is server-side.** Heartbeat timeout
  (`monitor.heartbeat.timeout_seconds`) lives on `TestExecution`
  already; the background expiry tick marks the test `hung` if the
  beat stops. RAFT doesn't need to know about that — it just keeps
  beating.
- **Failure modes are graceful — and the test always wins.**
  Monitoring is best-effort: a network-loss to the allocator (whether
  at startup or mid-run) **must never** fail or abort the test.
  RAFT's contract on a callback failure is:
  1. Log a single clear warning at WARN level — once when monitoring
     is disabled, not once per failed heartbeat.
     Example:
     `monitor: allocator http://allocator.lab:5000 unreachable
     (Connection refused) — disabling monitor for the rest of this
     test`.
  2. Mark `monitor.enabled = false` internally for the remainder of
     this test run. No retry-storm, no further callback attempts.
  3. Continue the test to completion. The test's own pass/fail
     result is the source of truth.

  On the allocator side, the absence of heartbeats trips the
  existing `heartbeat_timeout` mechanism and the `TestExecution` is
  marked `hung` (separately surfaceable in
  `GET /device/<id>/box_status`). That visibility outcome is
  independent of, and cannot influence, the test result the engineer
  sees in their own RAFT logs.

This is the shape the user asked to "be in the allocator design
already." It's now documented here and in
[architecture.md](./architecture.md) (linked from the preface).

## 10. Backwards compatibility strategy

Hard requirement from the user: existing v1/v2 consumers keep
working.

| consumer | what they call today | post-change behaviour |
|---|---|---|
| Legacy scripts hitting `GET /export/raft_config` | bespoke v1 shape | **unchanged** — endpoint remains as-is |
| Engineers hitting `GET /export/python_raft_config` | v2 RAFT-ish shape | **unchanged by default**; new query param `?schema=v3` opts into the new bundle. v2 stays the default for ~one release cycle. |
| Old RAFT (without the parser fix) | reads its own files | works against v3 bundle if `deviceConfig` is **inlined** (no `includes:` indirection needed); allocator should inline by default. |
| New RAFT (with parser fix + monitor support) | reads same v3 | gets the monitor block, can either inline or include-by-URL the device config. |

Deprecation: cut v2 after the v3 endpoint has been live for at least
one release on the consumer side. Audit-log every v1/v2 hit so we
know who's still on the old endpoints before flipping.

## 11. Changes required — allocator side

**Data model** ([models.py](../models.py)):

- `Device.borrower_email` (string?, indexed) — make the temporary
  borrow distinct from the permanent owner. Currently borrow
  overwrites `owner_email`, which loses the perm-owner info during a
  borrow window.
- `Device.console_config` (JSON) — *or* repurpose `control_uris`
  with a documented sub-schema for `consoles: [{name, type, port,
  …}]`. Surfaced directly into `rackConfig.<rack>.<slot>.devices[*].consoles`.
- `Device.power_switch` / `Device.remote_controller` /
  `Device.hdmi_cec` / `Device.av_sync` (each JSON, all nullable) —
  one column per RAFT optional section, populated by the rack-admin
  when the box is added.

**Routes** ([routes/export_routes.py](../routes/export_routes.py)):

- `GET /export/device_config?platform=<p>` — returns only the
  `deviceConfig:` block for one platform. Lets RAFT include-by-URL
  (or a human cache).
- `GET /export/raft_bundle?allocation_id=<id>` — the v3 schema above.
  Inlines `deviceConfig:` from the platform's device config so RAFT
  doesn't need to chase includes.
- Both new endpoints: explicit `schema_version: 3`, stable wire
  shape locked by a new `tests/test_raft_bundle_contract.py`.

**Allocation flow** ([routes/test_routes.py](../routes/test_routes.py)):

- When `POST /start_test` succeeds, mint a short-lived JWT scoped to
  `(allocation_history_id, test_execution_id)` and return it on the
  response so the engineer's RAFT can carry it on heartbeats. (For
  unauth `monitor.enabled: false` flows, skip the JWT entirely.)
- `GET /export/raft_bundle` includes the `monitor:` block when the
  caller passes `?include_monitor=1` (default off for backwards
  compat).

**Tests:**

- New `tests/test_raft_bundle_contract.py` — round-trip: build a
  bundle from a known allocation, parse it as YAML, assert
  `deviceConfig.cpe1.platform`, assert `rackConfig.<r>.<s>.devices[0].dut.consoles`,
  assert `monitor.heartbeat.interval_seconds` when opted in.
- Round-trip against actual python_raft: stand python_raft up in CI,
  point it at a fixture bundle, assert `configParser.processIncludes`
  resolves and the device classes hydrate. (May land later, once the
  RAFT parser fix is in.)

## 12. Changes required — python_raft side

Tracked as a follow-up against
[rdkcentral/python_raft](https://github.com/rdkcentral/python_raft):

1. **Parser fix** — `configParser.processIncludes` should also
   accept `includes:` (dict form) used by the canonical examples:
   ```python
   if "includes" in config:
       for kind, path in config["includes"].items():   # kind is informational
           merged = self.loadYaml(path)
           self.processIncludes(merged)
           config.update(merged)
       config.pop("includes")
   ```
   Plus a unit test covering both `include: [...]` and
   `includes: {...}` forms.

2. **URL includes** — `loadYaml(path)` currently assumes a local
   filesystem path. Extend it to recognise `http(s)://` and fetch
   via `requests` (or stdlib `urllib`) with sensible timeouts and
   the response cached under `~/.raft/cache/` so test loops don't
   spam the allocator. Mirrors what xts_core needs for `.xts`
   aliases (see [rdkcentral/xts_core#59](https://github.com/rdkcentral/xts_core/issues/59)).

3. **Monitor block honour** — new module `framework/core/monitor.py`:
   - **Preflight check at startup.** Refuse to enable monitor unless
     `schema.allocator.url` is present *and* the optional
     `monitor.preflight` probe (defaults to `GET /health` with a 3-s
     timeout) succeeds. On preflight failure, log a single WARN line
     identifying the unreachable allocator URL and proceed with
     monitor permanently disabled for this run.
   - On `testControl` start, if monitor is still enabled, POST to
     `monitor.allocator_url + monitor.on_start.endpoint` with the
     bearer token.
   - Start a background thread that POSTs heartbeats at
     `monitor.heartbeat.interval_seconds` cadence until the test
     finishes.
   - On test end (any path — success, failure, exception, SIGINT),
     POST to `monitor.on_end.endpoint` with the final status.
   - **Network-loss contract.** On the first callback failure
     (`start_test`, any heartbeat, `end_test`), log a single WARN
     line, set the in-memory enabled flag to false, and continue.
     No retries, no second WARN. The test continues to completion
     and its own result is reported as normal. Monitoring being
     unreachable can never fail a test.

4. **Schema version awareness** — read `schema.version` at the top
   of the rackConfig; warn if it's a version the current RAFT
   doesn't understand, but degrade gracefully (process whatever
   sections it does recognise).

These are four separable PRs; no single one is a prerequisite for
the others.

## 13. Rollout and test plan

Phasing — neither side requires the other to ship in a specific
release because v3 is opt-in and v2 stays as the default:

1. **Allocator** lands schema-v3 endpoint behind `?schema=v3` /
   `/export/raft_bundle`. Contract test locks the wire shape.
   Existing v1/v2 endpoints unchanged.
2. **python_raft** lands the parser fix + URL include + monitor
   honour as separate PRs. Each is small.
3. **Engineers** opt in by changing their `raft -c <url>` invocation
   to point at `/export/raft_bundle?include_monitor=1` once they're
   on a RAFT version that knows the monitor block.
4. **Eventually** flip the default `/export/python_raft_config` to
   the v3 shape. Audit-log shows when nobody is still hitting v2.

Test plan for the allocator-side work:

- [ ] `pytest tests/test_raft_bundle_contract.py` — schema-locking
      contract tests against the new bundle endpoint.
- [ ] `pytest tests/test_borrow_flow.py` (new) — exercises
      borrower-vs-owner separation, audit events, and the visibility
      invariant ("borrowed boxes still appear in /list_slots with
      both owner_email and borrower_email distinguishable").
- [ ] `pytest tests/test_export_backwards_compat.py` (new) —
      asserts that `/export/python_raft_config` *without* a schema
      parameter still returns the existing v2 shape byte-for-byte.
- [ ] `bin/allocator smoke --schema v3` (new flag) — drives the
      full lifecycle including downloading the v3 bundle and
      parsing it as YAML to confirm shape.
- [ ] End-to-end against a real python_raft (post parser fix):
      check out python_raft branch with the include fix, run a
      trivial test using a fixture rackConfig generated by the
      allocator, assert the device classes hydrate and at least one
      console opens.

Test plan for the python_raft-side monitor module (per section 9
contract):

- [ ] `test_monitor_skipped_when_no_schema_block` — hand-written
      rackConfig with no `schema:` block ⇒ monitor stays disabled,
      no callbacks attempted, no WARN noise.
- [ ] `test_monitor_skipped_when_preflight_fails` — bundle with
      `monitor.enabled: true` but allocator unreachable at startup
      ⇒ exactly one WARN line identifying the URL, monitor
      permanently disabled for the run, test runs to completion and
      reports its own result.
- [ ] `test_monitor_disables_on_first_callback_failure` — bundle
      reachable at preflight, then allocator goes away after
      `start_test` succeeds. First failed heartbeat ⇒ one WARN
      line, monitor disabled, no subsequent heartbeat attempts,
      test runs to completion.
- [ ] `test_monitor_disabled_does_not_affect_test_result` — force
      both a passing and a failing test under
      monitor-unreachable-mid-run and assert the RAFT exit code
      matches the test outcome, not the monitor status.
- [ ] `test_monitor_happy_path` — fully reachable allocator,
      `start_test` ⇒ N heartbeats ⇒ `end_test`, each call carries
      the bearer token from `monitor.auth.token`.
