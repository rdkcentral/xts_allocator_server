# Repo TODO Audit (2026-02-11)

Scope: local git repos under `/home/gweatherup/git/fast` with a top-level project TODO file.

## Summary

| Repo | TODO file | Open checklist items |
|---|---|---:|
| `sky/xts_allocator_server` | `TODO.md` | 31 |
| `sky/knowledge_graph_flight_recorder` | `PROJECT_TODO.md` | 86 |
| `sky/pipewire_example` | `PROJECT-TODO.md` | 31 |

## Outstanding By Repo

### `sky/xts_allocator_server`

- Large-fleet UX/API work remains (`/list_slots` and `/devices/search` pagination/sort).
- Compact state/heartbeat/test-status endpoint for RAFT/XTS polling is still needed.
- Cross-repo dependency: xts_core command execution path + shallow clone support.
- Schema/documentation consistency still needs cleanup (slot/platform target terminology).
- Technical debt: migrate away from `datetime.utcnow()` warnings.

### `sky/knowledge_graph_flight_recorder`

- Major migration backlog remains open:
  - Agent emission codegen migration.
  - Graph storage updates for FlatBuffers metadata access.
  - Decision shard reading/codegen updates.
  - Test migration and FlatBuffers compatibility/performance tests.
  - Documentation refresh and legacy TLV removal.

### `sky/pipewire_example`

- Remaining execution/documentation backlog:
  - Run remaining demos and document results.
  - Update README and test result docs.
  - Performance/integration testing.
  - Buildroot embedded workflow validation (QEMU + real hardware).
  - Native PipeWire linking migration + real multiview + DRM secure buffers + audio mixer.
