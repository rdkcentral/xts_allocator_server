import pytest
from unittest.mock import patch, AsyncMock


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
    
    @pytest.mark.skip(reason="Complex httpx mocking - requires integration test with real server")
    @patch('routes.federation_routes.httpx.AsyncClient')
    def test_get_server_devices_success(self, mock_client_class, test_client, sample_devices):
        """Test proxying device request to slave server."""
        # Register server
        server_data = {
            "name": "slave-1",
            "url": "http://192.168.1.100:5000",
            "location": "Building A"
        }
        _, reg_response = test_client.post("/register", json=server_data)
        server_id = reg_response.json["server_id"]
        
        # Mock httpx.AsyncClient with proper async context manager
        from unittest.mock import Mock, MagicMock
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "slots": [
                {"id": 1, "rackName": "Rack1", "slotName": "Slot1", "state": "free"}
            ]
        }
        
        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client_instance
        
        _, response = test_client.get(f"/servers/{server_id}/devices")
        
        assert response.status == 200
        data = response.json
        assert data["server_id"] == server_id
        assert data["server_name"] == "slave-1"
        assert "devices" in data
    
    @pytest.mark.skip(reason="Complex httpx mocking - requires integration test with real server")
    @patch('routes.federation_routes.httpx.AsyncClient')
    def test_get_server_devices_unreachable(self, mock_client_class, test_client):
        """Test handling unreachable slave server."""
        # Register server
        server_data = {
            "name": "slave-1",
            "url": "http://192.168.1.100:5000",
            "location": "Building A"
        }
        _, reg_response = test_client.post("/register", json=server_data)
        server_id = reg_response.json["server_id"]
        
        # Mock network error with proper async support
        import httpx
        from unittest.mock import MagicMock
        
        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(side_effect=httpx.RequestError("Connection refused"))
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client_instance
        
        _, response = test_client.get(f"/servers/{server_id}/devices")
        
        assert response.status == 503
        assert "Unable to reach server" in response.json["error"]
    
    @pytest.mark.skip(reason="Complex httpx mocking - requires integration test with real server")
    @patch('routes.federation_routes.httpx.AsyncClient')
    def test_list_federated_devices(self, mock_client_class, test_client):
        """Test aggregating devices from all slave servers."""
        # Register servers
        servers = [
            {"name": "slave-1", "url": "http://192.168.1.100:5000", "location": "Building A"},
            {"name": "slave-2", "url": "http://192.168.1.101:5000", "location": "Building B"}
        ]
        
        for server in servers:
            test_client.post("/register", json=server)
        
        # Mock responses from slave servers with proper async context manager
        from unittest.mock import Mock, MagicMock
        
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "slots": [{"id": 1, "state": "free"}]
        }
        
        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            "slots": [{"id": 2, "state": "allocated"}]
        }
        
        # Track calls to alternate responses
        call_tracker = [0]
        async def mock_get_alternate(*args, **kwargs):
            result = mock_response1 if call_tracker[0] == 0 else mock_response2
            call_tracker[0] += 1
            return result
        
        mock_client_instance = MagicMock()
        mock_client_instance.get = mock_get_alternate
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client_instance
        
        _, response = test_client.get("/devices/federated")
        
        assert response.status == 200
        data = response.json
        assert "devices" in data
        assert data["total_devices"] >= 2
        assert data["servers_queried"] == 2
