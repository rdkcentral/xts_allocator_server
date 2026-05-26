"""End-to-end workflow tests — full device lifecycle through the API."""



class TestAllocateTestReleaseCycle:
    """Full allocate → start_test → heartbeat → end_test → deallocate flow."""

    def test_full_lifecycle(self, test_client, sample_devices, auth_headers_engineer):
        device = sample_devices[0]

        # 1. Allocate
        _, resp = test_client.post("/allocate_slot", json={
            "user": {"email": "e2e@example.com"},
            "slot": {"id": device.id},
            "duration": "2h"
        }, headers=auth_headers_engineer)
        assert resp.status == 200
        assert resp.json["slot_id"] == device.id

        # Confirm device is allocated
        _, list_resp = test_client.get("/list_slots")
        slot = next(s for s in list_resp.json["slots"] if s["id"] == device.id)
        assert slot["state"] == "allocated"
        assert slot["owner_email"] == "e2e@example.com"

        # 2. Start test
        _, resp = test_client.post("/start_test", json={
            "device_id": device.id,
            "test_name": "e2e_smoke",
            "test_suite": "e2e",
            "expected_duration": 30,
            "user_email": "e2e@example.com"
        }, headers=auth_headers_engineer)
        assert resp.status == 200
        test_id = resp.json["test_execution_id"]
        assert resp.json["device_state"] == "testing"

        # 3. Heartbeat
        _, resp = test_client.post("/test_heartbeat", json={
            "test_execution_id": test_id
        })
        assert resp.status == 200
        assert resp.json["elapsed_minutes"] >= 0

        # 4. End test
        _, resp = test_client.post("/end_test", json={
            "test_execution_id": test_id,
            "status": "success",
            "exit_code": 0
        }, headers=auth_headers_engineer)
        assert resp.status == 200
        assert resp.json["device_state"] == "allocated"
        assert resp.json["status"] == "success"
        assert resp.json["duration_minutes"] >= 0

        # 5. Release
        _, resp = test_client.post("/deallocate_slot", json={
            "user": {"email": "e2e@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        assert resp.status == 200

        # Confirm device is free
        _, list_resp = test_client.get("/list_slots")
        slot = next(s for s in list_resp.json["slots"] if s["id"] == device.id)
        assert slot["state"] == "free"
        assert slot["owner_email"] is None

    def test_lifecycle_with_failed_test(self, test_client, sample_devices, auth_headers_engineer):
        """Full cycle where the test fails — device should return to allocated."""
        device = sample_devices[1]

        # Allocate
        _, resp = test_client.post("/allocate_slot", json={
            "user": {"email": "fail@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        assert resp.status == 200

        # Start test
        _, resp = test_client.post("/start_test", json={
            "device_id": device.id,
            "test_name": "failing_test",
            "user_email": "fail@example.com"
        }, headers=auth_headers_engineer)
        assert resp.status == 200
        test_id = resp.json["test_execution_id"]

        # End with failure
        _, resp = test_client.post("/end_test", json={
            "test_execution_id": test_id,
            "status": "failure",
            "exit_code": 1,
            "error_message": "Assertion failed in test_something"
        }, headers=auth_headers_engineer)
        assert resp.status == 200
        assert resp.json["status"] == "failure"
        assert resp.json["device_state"] == "allocated"

        # Verify test shows up in execution list
        _, resp = test_client.get(f"/test_executions?device_id={device.id}")
        assert resp.status == 200
        execs = resp.json["test_executions"]
        assert any(e["status"] == "failure" and e["test_name"] == "failing_test" for e in execs)

        # Release
        _, resp = test_client.post("/deallocate_slot", json={
            "user": {"email": "fail@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        assert resp.status == 200

    def test_multiple_tests_on_same_allocation(self, test_client, sample_devices, auth_headers_engineer):
        """Run two tests back-to-back on the same allocation."""
        device = sample_devices[0]

        # Allocate
        test_client.post("/allocate_slot", json={
            "user": {"email": "multi@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)

        for test_name in ["test_one", "test_two"]:
            # Start
            _, resp = test_client.post("/start_test", json={
                "device_id": device.id,
                "test_name": test_name,
                "user_email": "multi@example.com"
            }, headers=auth_headers_engineer)
            assert resp.status == 200
            test_id = resp.json["test_execution_id"]

            # End
            _, resp = test_client.post("/end_test", json={
                "test_execution_id": test_id,
                "status": "success"
            }, headers=auth_headers_engineer)
            assert resp.status == 200
            assert resp.json["device_state"] == "allocated"

        # Both tests should appear in history
        _, resp = test_client.get(f"/test_executions?device_id={device.id}")
        assert resp.json["total"] == 2

        # Release
        test_client.post("/deallocate_slot", json={
            "user": {"email": "multi@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)


class TestHeartbeatByDeviceId:
    """Test heartbeat and end_test using device_id instead of test_execution_id."""

    def test_heartbeat_by_device_id(self, test_client, sample_devices, auth_headers_engineer):
        device = sample_devices[0]

        # Allocate + start test
        test_client.post("/allocate_slot", json={
            "user": {"email": "hb@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        test_client.post("/start_test", json={
            "device_id": device.id,
            "test_name": "heartbeat_test",
            "user_email": "hb@example.com"
        }, headers=auth_headers_engineer)

        # Heartbeat by device_id
        _, resp = test_client.post("/test_heartbeat", json={
            "device_id": device.id
        })
        assert resp.status == 200
        assert resp.json["device_id"] == device.id

    def test_end_test_by_device_id(self, test_client, sample_devices, auth_headers_engineer):
        device = sample_devices[0]

        # Allocate + start test
        test_client.post("/allocate_slot", json={
            "user": {"email": "end@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        test_client.post("/start_test", json={
            "device_id": device.id,
            "test_name": "end_by_device",
            "user_email": "end@example.com"
        }, headers=auth_headers_engineer)

        # End test by device_id
        _, resp = test_client.post("/end_test", json={
            "device_id": device.id,
            "status": "success"
        }, headers=auth_headers_engineer)
        assert resp.status == 200
        assert resp.json["device_state"] == "allocated"


class TestWrongUserCannotStartTest:
    """Verify ownership checks on test operations."""

    def test_wrong_user_cannot_start_test(self, test_client, sample_devices, auth_headers_engineer):
        device = sample_devices[0]

        # Allocate to user A
        test_client.post("/allocate_slot", json={
            "user": {"email": "owner@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)

        # User B tries to start test
        _, resp = test_client.post("/start_test", json={
            "device_id": device.id,
            "test_name": "sneaky_test",
            "user_email": "intruder@example.com"
        }, headers=auth_headers_engineer)
        assert resp.status == 403
        assert "owner@example.com" in resp.json["error"]


class TestTestExecutionFilters:
    """Test filtering on /test_executions endpoint."""

    def test_filter_active_only(self, test_client, sample_devices, auth_headers_engineer):
        device = sample_devices[0]

        # Allocate + start test (leave it running)
        test_client.post("/allocate_slot", json={
            "user": {"email": "filter@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        test_client.post("/start_test", json={
            "device_id": device.id,
            "test_name": "running_test",
            "user_email": "filter@example.com"
        }, headers=auth_headers_engineer)

        # Filter for active tests
        _, resp = test_client.get("/test_executions?active_only=true")
        assert resp.status == 200
        assert resp.json["total"] >= 1
        for ex in resp.json["test_executions"]:
            assert ex["end_time"] is None

    def test_filter_by_status(self, test_client, sample_devices, auth_headers_engineer):
        device = sample_devices[0]

        # Create a completed test
        test_client.post("/allocate_slot", json={
            "user": {"email": "status@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        _, start_resp = test_client.post("/start_test", json={
            "device_id": device.id,
            "test_name": "completed_test",
            "user_email": "status@example.com"
        }, headers=auth_headers_engineer)
        test_client.post("/end_test", json={
            "test_execution_id": start_resp.json["test_execution_id"],
            "status": "success"
        }, headers=auth_headers_engineer)

        # Filter by status=success
        _, resp = test_client.get("/test_executions?status=success")
        assert resp.status == 200
        for ex in resp.json["test_executions"]:
            assert ex["status"] == "success"

    def test_filter_by_device_id(self, test_client, sample_devices, auth_headers_engineer):
        device = sample_devices[0]

        # Create a test on this device
        test_client.post("/allocate_slot", json={
            "user": {"email": "devfilter@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        test_client.post("/start_test", json={
            "device_id": device.id,
            "test_name": "device_filter_test",
            "user_email": "devfilter@example.com"
        }, headers=auth_headers_engineer)

        # Filter by device_id
        _, resp = test_client.get(f"/test_executions?device_id={device.id}")
        assert resp.status == 200
        for ex in resp.json["test_executions"]:
            assert ex["device_id"] == device.id
