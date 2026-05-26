"""Contract tests for the surfaces xts_core (and other automation clients)
consume from this allocator.

These tests do NOT exercise xts_core itself. They lock down the wire
shape on the **allocator** side so that:

  - The `/allocator.xts` static endpoint keeps serving the command-surface
    file xts_core can dynamically pull (alias-from-URL flow planned in
    xts_core's XTS_ENHANCEMENT_PLAN).
  - POST /allocate_slot keeps returning the fields the allocator
    documents as the canonical response (`slot_id`, `state`, etc.) so a
    breaking change here fails loudly here, not silently downstream.
  - POST /deallocate_slot keeps its current contract.
  - The new GET /device/<id>/box_status compact polling endpoint keeps
    its lightweight shape so RAFT/XTS pollers can rely on it.

Note: xts_core's bundled plugin (xts_allocator_client.py at the time of
this commit) targets older endpoint names (`/allocate`, `/deallocate`).
That mismatch is tracked as an xts_core follow-up; the allocator's
endpoint names here are the ground truth.
"""

import os

import pytest
import yaml


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── /allocator.xts static file (command-surface dynamic load) ────────


class TestAllocatorXtsServed:
    """Verify the .xts file xts_core consumes is reachable and parseable."""

    def test_allocator_xts_is_served(self, test_client):
        _, response = test_client.get("/allocator.xts")
        assert response.status == 200, (
            f"/allocator.xts must be served so xts_core can pull command surface; "
            f"got {response.status}"
        )

    def test_allocator_xts_payload_matches_file(self, test_client):
        """The served bytes must match the on-disk allocator.xts exactly."""
        with open(os.path.join(REPO_ROOT, "allocator.xts"), "rb") as f:
            on_disk = f.read()
        _, response = test_client.get("/allocator.xts")
        assert response.body == on_disk

    def test_allocator_xts_is_valid_yaml(self):
        """The .xts file is YAML — must round-trip without error."""
        with open(os.path.join(REPO_ROOT, "allocator.xts")) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), "allocator.xts must parse to a top-level mapping"
        # xts_core needs the alias name and at least one allocate command at
        # the top level — the .xts schema puts each command at the top, not
        # nested under "commands:".
        assert "alias_name" in data, "allocator.xts must declare alias_name"
        assert "command_groups" in data, "allocator.xts must declare command_groups"
        # The canonical user-facing commands xts_core will surface via the
        # allocator alias. If these top-level keys disappear, xts users break.
        for cmd in ("alloc", "active_test", "describe_box", "end_test"):
            assert cmd in data, f"allocator.xts is missing top-level command '{cmd}'"


# ── POST /allocate_slot response shape ───────────────────────────────


class TestAllocateSlotContract:
    """Lock the response keys the allocator promises for /allocate_slot."""

    def test_allocate_slot_by_platform_returns_canonical_shape(
        self, test_client, sample_devices, auth_headers_engineer
    ):
        # sample_devices includes a free platform=raspberry-pi device.
        _, response = test_client.post(
            "/allocate_slot",
            json={"user": {"email": "contract@example.com"}, "slot": {"platform": "Cisco"}},
            headers=auth_headers_engineer,
        )
        assert response.status == 200, f"unexpected status: {response.text}"
        body = response.json

        # The canonical shape downstream automation depends on.
        # Field names are mixed snake_case + camelCase because the API has
        # accreted both styles; downstream clients pin to these spellings.
        for key in ("slot_id", "rackName", "slotName", "target_id", "state",
                    "owner_email", "allocation_history_id"):
            assert key in body, f"/allocate_slot response missing required key '{key}': {body!r}"
        assert body["state"] == "allocated"
        assert isinstance(body["slot_id"], int)
        assert isinstance(body["allocation_history_id"], int)

    def test_allocate_slot_no_match_returns_200_with_empty_slots(
        self, test_client, sample_devices, auth_headers_engineer
    ):
        """The "no free slots match" case must stay 200 + slots:[] (PR #23 contract)."""
        _, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "contract@example.com"},
                "slot": {"platform": "platform-that-does-not-exist"},
            },
            headers=auth_headers_engineer,
        )
        assert response.status == 200, f"expected 200, got {response.status}: {response.text}"
        assert response.json.get("slots") == []

    def test_allocate_slot_by_id_not_found_returns_404(
        self, test_client, auth_headers_engineer
    ):
        _, response = test_client.post(
            "/allocate_slot",
            json={"user": {"email": "contract@example.com"}, "slot": {"id": 99999}},
            headers=auth_headers_engineer,
        )
        assert response.status == 404


# ── POST /deallocate_slot response shape ─────────────────────────────


class TestDeallocateSlotContract:
    """Round-trip: allocate then deallocate, lock the dealloc response shape."""

    def test_deallocate_slot_returns_state_free(
        self, test_client, sample_devices, auth_headers_engineer
    ):
        _, alloc_response = test_client.post(
            "/allocate_slot",
            json={"user": {"email": "contract@example.com"}, "slot": {"platform": "Cisco"}},
            headers=auth_headers_engineer,
        )
        assert alloc_response.status == 200
        slot_id = alloc_response.json["slot_id"]

        _, dealloc_response = test_client.post(
            "/deallocate_slot",
            json={"user": {"email": "contract@example.com"}, "slot": {"id": slot_id}},
            headers=auth_headers_engineer,
        )
        assert dealloc_response.status == 200, f"unexpected: {dealloc_response.text}"
        # Whatever fields the body carries, the box must end up free again.
        _, list_response = test_client.get("/list_slots")
        device = next(d for d in list_response.json["slots"] if d["slot_id"] == slot_id)
        assert device["state"] == "free"


# ── GET /device/<id>/box_status compact polling endpoint ─────────────


class TestBoxStatusCompactEndpoint:
    """The new compact box-status endpoint for RAFT/XTS polling."""

    EXPECTED_KEYS = {
        "device_id",
        "target_id",
        "state",
        "owner_email",
        "allocation_expiry",
        "active_test",
    }

    def test_box_status_idle_device_shape(self, test_client, sample_devices):
        device_id = sample_devices[0].id
        _, response = test_client.get(f"/device/{device_id}/box_status")
        assert response.status == 200
        body = response.json
        assert set(body.keys()) == self.EXPECTED_KEYS, (
            f"compact box_status response added/removed keys — "
            f"this is a breaking change for RAFT/XTS pollers. Got: {sorted(body.keys())}"
        )
        assert body["device_id"] == device_id
        assert body["active_test"] is None, "idle device should report active_test=None"

    def test_box_status_active_test_shape(
        self, test_client, sample_devices, auth_headers_engineer
    ):
        device_id = sample_devices[0].id

        # Allocate then start a test so there is an active TestExecution.
        test_client.post(
            "/allocate_slot",
            json={"user": {"email": "poll@example.com"}, "slot": {"id": device_id}},
            headers=auth_headers_engineer,
        )
        _, start_response = test_client.post(
            "/start_test",
            json={
                "device_id": device_id,
                "test_name": "smoke",
                "test_suite": "contract",
                "user_email": "poll@example.com",
            },
            headers=auth_headers_engineer,
        )
        assert start_response.status == 200, start_response.text

        _, response = test_client.get(f"/device/{device_id}/box_status")
        assert response.status == 200
        body = response.json
        assert body["state"] == "testing"
        active = body["active_test"]
        assert active is not None
        # Keys downstream pollers (RAFT) rely on for "is this box still working?"
        for key in ("id", "name", "suite", "status", "elapsed_minutes", "heartbeat_age_seconds"):
            assert key in active, f"active_test missing key '{key}': {active!r}"
        assert active["name"] == "smoke"
        assert active["suite"] == "contract"
        assert active["elapsed_minutes"] >= 0

    def test_box_status_unknown_device_returns_404(self, test_client):
        _, response = test_client.get("/device/99999/box_status")
        assert response.status == 404

    def test_box_status_is_unauthenticated(self, test_client, sample_devices):
        """Polling endpoint must not require auth — pollers run without user JWTs."""
        device_id = sample_devices[0].id
        _, response = test_client.get(f"/device/{device_id}/box_status")
        assert response.status == 200, (
            f"box_status must be reachable without auth headers (got {response.status}); "
            f"RAFT/XTS pollers do not carry user JWTs."
        )
