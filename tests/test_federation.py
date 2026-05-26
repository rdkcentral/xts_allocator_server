import json as json_module
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest


@contextmanager
def _fake_slave_server(payload_by_path, *, fail_with=None):
    """Spin up an in-process HTTP server on an ephemeral port that returns
    canned JSON for each path in ``payload_by_path``.

    The master federation routes use ``httpx.AsyncClient`` to proxy to the
    slave's real URL, so we need an actual listening socket rather than a
    mocked transport (sanic_testing also drives requests through httpx and
    a global patch hijacks the test client itself).

    If ``fail_with`` is provided, the handler returns that HTTP status for
    every request, letting tests exercise the master's error path.
    """
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # silence stderr access logs

        def do_GET(self):
            if fail_with is not None:
                self.send_response(fail_with)
                self.end_headers()
                return
            body = payload_by_path.get(self.path)
            if body is None:
                self.send_response(404)
                self.end_headers()
                return
            encoded = json_module.dumps(body).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class TestFederatedServers:
    """Test federated multi-server architecture."""
    
    def test_register_server_new(self, test_client):
        """Test registering a new slave server."""
        server_data = {
            "name": "slave-server-1",
            "url": "http://192.168.1.100:5000",
            "location": "Building A, Floor 3",
            "metadata": {
                "capacity": 50,
                "region": "US-West"
            }
        }
        
        _, response = test_client.post("/register", json=server_data)
        
        assert response.status == 200
        data = response.json
        assert data["message"] == "Server registered successfully"
        assert "server_id" in data
        assert data["name"] == "slave-server-1"
        assert data["status"] == "online"
    
    def test_register_server_update_existing(self, test_client):
        """Test updating an existing registered server."""
        server_data = {
            "name": "slave-server-1",
            "url": "http://192.168.1.100:5000",
            "location": "Building A"
        }
        
        # Register first time
        test_client.post("/register", json=server_data)
        
        # Update with new URL
        updated_data = {
            "name": "slave-server-1",
            "url": "http://192.168.1.101:5000",
            "location": "Building B"
        }
        
        _, response = test_client.post("/register", json=updated_data)
        
        assert response.status == 200
        assert response.json["message"] == "Server registered successfully"
    
    def test_register_server_missing_fields(self, test_client):
        """Test server registration with missing required fields."""
        # Missing URL
        server_data = {
            "name": "slave-server-1"
        }
        
        _, response = test_client.post("/register", json=server_data)
        
        assert response.status == 400
        assert "name and url are required" in response.json["error"]
    
    def test_heartbeat_success(self, test_client):
        """Test successful heartbeat from slave server."""
        # Register server first
        server_data = {
            "name": "slave-server-1",
            "url": "http://192.168.1.100:5000",
            "location": "Building A"
        }
        test_client.post("/register", json=server_data)
        
        # Send heartbeat
        heartbeat_data = {
            "name": "slave-server-1",
            "device_count": 25,
            "status": "online"
        }
        
        _, response = test_client.post("/heartbeat", json=heartbeat_data)
        
        assert response.status == 200
        data = response.json
        assert data["message"] == "Heartbeat received"
        assert data["status"] == "online"
    
    def test_heartbeat_missing_name(self, test_client):
        """Test heartbeat without server name."""
        heartbeat_data = {
            "device_count": 25
        }
        
        _, response = test_client.post("/heartbeat", json=heartbeat_data)
        
        assert response.status == 400
        assert "name is required" in response.json["error"]
    
    def test_heartbeat_unregistered_server(self, test_client):
        """Test heartbeat from unregistered server."""
        heartbeat_data = {
            "name": "unknown-server",
            "device_count": 10
        }
        
        _, response = test_client.post("/heartbeat", json=heartbeat_data)
        
        assert response.status == 404
        assert "not registered" in response.json["error"]
    
    def test_list_servers(self, test_client):
        """Test listing all registered servers."""
        # Register multiple servers
        servers = [
            {"name": "slave-1", "url": "http://192.168.1.100:5000", "location": "Building A"},
            {"name": "slave-2", "url": "http://192.168.1.101:5000", "location": "Building B"}
        ]
        
        for server in servers:
            test_client.post("/register", json=server)
        
        _, response = test_client.get("/servers")
        
        assert response.status == 200
        data = response.json
        assert "servers" in data
        assert data["total"] >= 2
        assert any(s["name"] == "slave-1" for s in data["servers"])
        assert any(s["name"] == "slave-2" for s in data["servers"])
    
    def test_list_servers_filter_by_status(self, test_client):
        """Test filtering servers by status."""
        # Register a server
        server_data = {
            "name": "slave-1",
            "url": "http://192.168.1.100:5000",
            "location": "Building A"
        }
        test_client.post("/register", json=server_data)
        
        _, response = test_client.get("/servers?status=online")
        
        assert response.status == 200
        data = response.json
        assert all(s["status"] == "online" for s in data["servers"])
    
    def test_get_server_details(self, test_client):
        """Test getting details for a specific server."""
        # Register server
        server_data = {
            "name": "slave-1",
            "url": "http://192.168.1.100:5000",
            "location": "Building A"
        }
        _, reg_response = test_client.post("/register", json=server_data)
        server_id = reg_response.json["server_id"]
        
        _, response = test_client.get(f"/servers/{server_id}")
        
        assert response.status == 200
        data = response.json
        assert data["id"] == server_id
        assert data["name"] == "slave-1"
        assert data["url"] == "http://192.168.1.100:5000"
        assert data["location"] == "Building A"
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_get_server_details_not_found(self, test_client):
        """Test getting details for nonexistent server."""
        _, response = test_client.get("/servers/99999")
        
        assert response.status == 404
        assert "not found" in response.json["error"]
    
    def test_get_server_devices_success(self, test_client, sample_devices):
        """Master proxies /list_slots to a slave and wraps the response."""
        slave_slots = [
            {"id": 1, "rackName": "Rack1", "slotName": "Slot1", "state": "free"}
        ]
        with _fake_slave_server({"/list_slots": {"slots": slave_slots}}) as slave_url:
            _, reg_response = test_client.post("/register", json={
                "name": "slave-1", "url": slave_url, "location": "Building A"
            })
            server_id = reg_response.json["server_id"]

            _, response = test_client.get(f"/servers/{server_id}/devices")

        assert response.status == 200
        data = response.json
        assert data["server_id"] == server_id
        assert data["server_name"] == "slave-1"
        assert data["devices"] == slave_slots

    def test_get_server_devices_unreachable(self, test_client):
        """When the slave is unreachable, master returns 503 and marks the server unreachable."""
        # Bind-and-immediately-close a socket to grab an unused port, then point
        # the registered slave at it — the master's httpx call will get
        # ECONNREFUSED, which is exactly the path we want to exercise.
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        dead_port = s.getsockname()[1]
        s.close()

        _, reg_response = test_client.post("/register", json={
            "name": "slave-1",
            "url": f"http://127.0.0.1:{dead_port}",
            "location": "Building A",
        })
        server_id = reg_response.json["server_id"]

        _, response = test_client.get(f"/servers/{server_id}/devices")

        assert response.status == 503
        assert "Unable to reach server" in response.json["error"]

        # The route marks the server as unreachable on its way out.
        _, details = test_client.get(f"/servers/{server_id}")
        assert details.json["status"] == "unreachable"

    def test_list_federated_devices(self, test_client):
        """/devices/federated aggregates /list_slots responses across online slaves."""
        with _fake_slave_server({"/list_slots": {"slots": [{"id": 1, "state": "free"}]}}) as url_a, \
             _fake_slave_server({"/list_slots": {"slots": [{"id": 2, "state": "allocated"}]}}) as url_b:
            for name, url, location in (
                ("slave-1", url_a, "Building A"),
                ("slave-2", url_b, "Building B"),
            ):
                test_client.post("/register", json={"name": name, "url": url, "location": location})

            _, response = test_client.get("/devices/federated")

        assert response.status == 200
        data = response.json
        assert data["total_devices"] == 2
        assert data["servers_queried"] == 2
        # Each device should carry the server context the aggregator stamped on.
        server_names = {d["server_name"] for d in data["devices"]}
        assert server_names == {"slave-1", "slave-2"}
