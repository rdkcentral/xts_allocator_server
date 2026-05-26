"""Input-validation tests for routes flagged in TODO.md as lacking coverage.

Covers the six route files called out by TODO.md (`device_routes`,
`rack_routes`, `export_routes`, `usage_routes`, `federation_routes`,
`audit_log_routes`) where validation was either absent or only checked
"missing required fields." The cases here probe the security-relevant
shapes that crash routes or admit unbounded input: wrong types,
oversized strings, missing required JSON, and role-boundary violations.

Where a test fails because the route has no validation, the route was
updated to call into the existing helpers in input_validation.py — the
tests-first pattern the plan called for.
"""

import pytest


_OVERSIZED = "x" * 1024
_HUGE = "y" * 100_000
# Query-string values must stay under httpx's client-side URL length cap
# (~8 KB by default). Use this for `?param=` cases where _HUGE would be
# rejected by the test client before reaching the server.
_OVERSIZED_QUERY = "z" * 2048


# ── device_routes ────────────────────────────────────────────────────


class TestDeviceRoutesInputValidation:
    """POST /add_slot, /update_slot, /delete_slot, /list_slots (filter)."""

    def test_add_slot_missing_body(self, test_client, auth_headers_engineer):
        """Empty JSON body must be rejected with 400, not crash with 500."""
        _, response = test_client.post("/add_slot", json={}, headers=auth_headers_engineer)
        assert response.status == 400, f"expected 400 got {response.status}: {response.text}"

    def test_add_slot_wrong_types(self, test_client, sample_racks, auth_headers_engineer):
        """Numeric slotName / list rackName should not produce a 500."""
        _, response = test_client.post(
            "/add_slot",
            json={"rackName": ["not", "a", "string"], "slotName": 42},
            headers=auth_headers_engineer,
        )
        # Acceptable outcomes: 400 (validation) or 200 if route coerced silently.
        # 500 means the route blew up on bad input and is the bug we guard against.
        assert response.status != 500, f"add_slot 500'd on wrong-type input: {response.text}"

    def test_update_slot_missing_slot_id(self, test_client, auth_headers_engineer):
        """update_slot without slot_id must return 400, not crash."""
        _, response = test_client.post(
            "/update_slot", json={"description": "no id"}, headers=auth_headers_engineer
        )
        assert response.status == 400

    def test_delete_slot_missing_slot_id(self, test_client, auth_headers_engineer):
        """delete_slot without slot_id must return 400."""
        _, response = test_client.post(
            "/delete_slot", json={}, headers=auth_headers_engineer
        )
        assert response.status == 400

    @pytest.mark.parametrize("bad_criteria", [
        {"tags": 12345},                    # tags should be list or string
        {"platform": _HUGE},                # oversized platform string
        {"description": _OVERSIZED * 100},  # oversized description
    ])
    def test_list_slots_filter_tolerates_bad_input(self, test_client, sample_devices, bad_criteria):
        """POST /list_slots with malformed filter criteria must not 500."""
        _, response = test_client.post("/list_slots", json=bad_criteria)
        assert response.status != 500, f"list_slots filter 500'd on {bad_criteria!r}: {response.text}"

    def test_add_slot_readonly_role_forbidden(self, test_client, sample_racks, auth_headers_readonly):
        """A readonly user must not be able to add a slot."""
        _, response = test_client.post(
            "/add_slot",
            json={"rackName": "rack-a", "slotName": "new-slot"},
            headers=auth_headers_readonly,
        )
        assert response.status in (401, 403), (
            f"readonly should be denied add_slot but got {response.status}"
        )


# ── rack_routes ──────────────────────────────────────────────────────


class TestRackRoutesInputValidation:
    """GET /list_racks, /rack/<id>, /rack/<id>/devices, POST /devices/search."""

    def test_search_devices_oversized_query(self, test_client, sample_devices):
        """POST /devices/search must tolerate large free-text query without 500."""
        _, response = test_client.post(
            "/devices/search", json={"query": _OVERSIZED * 100}
        )
        assert response.status != 500, f"devices/search 500'd on big query: {response.text}"

    def test_search_devices_wrong_type_for_labels(self, test_client, sample_devices):
        """labels should be a list/string — passing an int must not crash."""
        _, response = test_client.post(
            "/devices/search", json={"labels": 42}
        )
        assert response.status != 500

    def test_get_rack_devices_nonexistent_id(self, test_client):
        """A rack-id that doesn't exist should return 404, not 500."""
        _, response = test_client.get("/rack/99999/devices")
        assert response.status in (404, 200), (
            f"expected 404 (or 200 with empty list) for missing rack, got {response.status}"
        )


# ── export_routes ────────────────────────────────────────────────────


class TestExportRoutesInputValidation:
    """GET /export/raft_config and the three other export endpoints."""

    @pytest.mark.parametrize("path", [
        "/export/raft_config",
        "/export/python_raft_config",
        "/export/python_raft_device_profile",
        "/export/python_raft_rack_config",
    ])
    def test_export_oversized_owner_email_query(self, test_client, sample_devices, path):
        """Export endpoints filter by owner_email — must not 500 on oversized input."""
        _, response = test_client.get(f"{path}?owner_email={_OVERSIZED_QUERY}")
        assert response.status != 500, f"{path} 500'd on oversized owner_email: {response.text}"

    def test_export_no_required_filter_returns_400(self, test_client, sample_devices):
        """Without allocation_id or owner_email the route returns 400 (existing contract)."""
        _, response = test_client.get("/export/raft_config")
        assert response.status == 400


# ── usage_routes ─────────────────────────────────────────────────────


class TestUsageRoutesInputValidation:
    """GET /device/<id>/usage_stats and /usage_summary."""

    @pytest.mark.parametrize("bad_days", ["nope", "-1", "999999999999", "1.5"])
    def test_usage_summary_bad_days_param(self, test_client, sample_devices, bad_days):
        """`days=` query string with a non-positive-integer must not 500."""
        _, response = test_client.get(f"/usage_summary?days={bad_days}")
        # Acceptable: 400 (validated) or 200 (fell back to default). 500 = bug.
        assert response.status != 500, f"usage_summary 500'd on days={bad_days!r}: {response.text}"

    def test_usage_stats_nonexistent_device(self, test_client):
        """Already covered elsewhere — keep here as a guard for the contract."""
        _, response = test_client.get("/device/99999/usage_stats")
        assert response.status == 404


# ── federation_routes ────────────────────────────────────────────────


class TestFederationRoutesInputValidation:
    """POST /register, /heartbeat and GET /servers."""

    def test_register_missing_both_required(self, test_client):
        """Empty payload returns 400 (existing behaviour — guard against regression)."""
        _, response = test_client.post("/register", json={})
        assert response.status == 400
        assert "name and url are required" in response.json["error"]

    def test_register_oversized_name(self, test_client):
        """Massive name string must not 500 the registration endpoint."""
        _, response = test_client.post(
            "/register",
            json={"name": _HUGE, "url": "http://example.com:5000", "location": "X"},
        )
        assert response.status != 500, f"register 500'd on huge name: {response.text}"

    def test_register_malformed_url(self, test_client):
        """A non-URL string should not crash the route (currently no URL validation)."""
        _, response = test_client.post(
            "/register",
            json={"name": "slave-x", "url": "not even a url", "location": "X"},
        )
        # Either 400 (validated) or 200 (accepted-and-stored). 500 = bug.
        assert response.status != 500

    def test_heartbeat_missing_name(self, test_client):
        """Heartbeat without name returns 400."""
        _, response = test_client.post("/heartbeat", json={"device_count": 10})
        assert response.status == 400

    def test_heartbeat_wrong_type_for_device_count(self, test_client):
        """device_count is read with `data.get(..., 0)` — a list must not crash."""
        test_client.post("/register", json={
            "name": "slave-x", "url": "http://example.com:5000", "location": "X"
        })
        _, response = test_client.post(
            "/heartbeat",
            json={"name": "slave-x", "device_count": ["not", "a", "number"]},
        )
        assert response.status != 500

    def test_list_servers_status_filter_oversized(self, test_client):
        """GET /servers?status=<huge> must not crash even though it's just a filter."""
        _, response = test_client.get(f"/servers?status={_OVERSIZED_QUERY}")
        assert response.status != 500


# ── audit_log_routes ─────────────────────────────────────────────────


class TestAuditLogRoutesInputValidation:
    """GET /audit/logs, /audit/summary, /audit/events/types."""

    def test_audit_logs_bad_limit(self, test_client, auth_headers_admin):
        """`limit=` with garbage value already returns 400 — keep as a contract."""
        _, response = test_client.get("/audit/logs?limit=notanumber", headers=auth_headers_admin)
        assert response.status in (400, 200)
        assert response.status != 500

    def test_audit_logs_bad_offset(self, test_client, auth_headers_admin):
        _, response = test_client.get("/audit/logs?offset=-1", headers=auth_headers_admin)
        assert response.status in (400, 200)
        assert response.status != 500

    def test_audit_logs_oversized_event_type_filter(self, test_client, auth_headers_admin):
        _, response = test_client.get(
            f"/audit/logs?event_type={_OVERSIZED_QUERY}", headers=auth_headers_admin
        )
        assert response.status != 500

    def test_audit_logs_requires_admin_readonly_denied(self, test_client, auth_headers_readonly):
        """Readonly role must not see audit logs (admin-only endpoint)."""
        _, response = test_client.get("/audit/logs", headers=auth_headers_readonly)
        assert response.status in (401, 403), (
            f"readonly should be denied /audit/logs, got {response.status}"
        )
