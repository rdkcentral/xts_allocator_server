import pytest
from unittest.mock import patch, AsyncMock


class TestFederatedServers:
    """Test federated multi-server architecture."""
    
    @pytest.mark.asyncio
    async def test_register_server_new(self, test_client):
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
        
        _, response = await test_client.post("/register", json=server_data)
        
        assert response.status == 200
        data = response.json
        assert data["message"] == "Server registered successfully"
        assert "server_id" in data
        assert data["name"] == "slave-server-1"
        assert data["status"] == "online"
    
    @pytest.mark.asyncio
    async def test_register_server_update_existing(self, test_client):
        """Test updating an existing registered server."""
        server_data = {
            "name": "slave-server-1",
            "url": "http://192.168.1.100:5000",
            "location": "Building A"
        }
        
        # Register first time
        await test_client.post("/register", json=server_data)
        
        # Update with new URL
        updated_data = {
            "name": "slave-server-1",
            "url": "http://192.168.1.101:5000",
            "location": "Building B"
        }
        
        _, response = await test_client.post("/register", json=updated_data)
        
        assert response.status == 200
        assert response.json["message"] == "Server registered successfully"
    
    @pytest.mark.asyncio
    async def test_register_server_missing_fields(self, test_client):
        """Test server registration with missing required fields."""
        # Missing URL
        server_data = {
            "name": "slave-server-1"
        }
        
        _, response = await test_client.post("/register", json=server_data)
        
        assert response.status == 400
        assert "name and url are required" in response.json["error"]
    
    @pytest.mark.asyncio
    async def test_heartbeat_success(self, test_client):
        """Test successful heartbeat from slave server."""
        # Register server first
        server_data = {
            "name": "slave-server-1",
            "url": "http://192.168.1.100:5000",
            "location": "Building A"
        }
        await test_client.post("/register", json=server_data)
        
        # Send heartbeat
        heartbeat_data = {
            "name": "slave-server-1",
            "device_count": 25,
            "status": "online"
        }
        
        _, response = await test_client.post("/heartbeat", json=heartbeat_data)
        
        assert response.status == 200
        data = response.json
        assert data["message"] == "Heartbeat received"
        assert data["status"] == "online"
    
    @pytest.mark.asyncio
    async def test_heartbeat_missing_name(self, test_client):
        """Test heartbeat without server name."""
        heartbeat_data = {
            "device_count": 25
        }
        
        _, response = await test_client.post("/heartbeat", json=heartbeat_data)
        
        assert response.status == 400
        assert "name is required" in response.json["error"]
    
    @pytest.mark.asyncio
    async def test_heartbeat_unregistered_server(self, test_client):
        """Test heartbeat from unregistered server."""
        heartbeat_data = {
            "name": "unknown-server",
            "device_count": 10
        }
        
        _, response = await test_client.post("/heartbeat", json=heartbeat_data)
        
        assert response.status == 404
        assert "not registered" in response.json["error"]
    
    @pytest.mark.asyncio
    async def test_list_servers(self, test_client):
        """Test listing all registered servers."""
        # Register multiple servers
        servers = [
            {"name": "slave-1", "url": "http://192.168.1.100:5000", "location": "Building A"},
            {"name": "slave-2", "url": "http://192.168.1.101:5000", "location": "Building B"}
        ]
        
        for server in servers:
            await test_client.post("/register", json=server)
        
        _, response = await test_client.get("/servers")
        
        assert response.status == 200
        data = response.json
        assert "servers" in data
        assert data["total"] >= 2
        assert any(s["name"] == "slave-1" for s in data["servers"])
        assert any(s["name"] == "slave-2" for s in data["servers"])
    
    @pytest.mark.asyncio
    async def test_list_servers_filter_by_status(self, test_client):
        """Test filtering servers by status."""
        # Register a server
        server_data = {
            "name": "slave-1",
            "url": "http://192.168.1.100:5000",
            "location": "Building A"
        }
        await test_client.post("/register", json=server_data)
        
        _, response = await test_client.get("/servers?status=online")
        
        assert response.status == 200
        data = response.json
        assert all(s["status"] == "online" for s in data["servers"])
    
    @pytest.mark.asyncio
    async def test_get_server_details(self, test_client):
        """Test getting details for a specific server."""
        # Register server
        server_data = {
            "name": "slave-1",
            "url": "http://192.168.1.100:5000",
            "location": "Building A"
        }
        _, reg_response = await test_client.post("/register", json=server_data)
        server_id = reg_response.json["server_id"]
        
        _, response = await test_client.get(f"/servers/{server_id}")
        
        assert response.status == 200
        data = response.json
        assert data["id"] == server_id
        assert data["name"] == "slave-1"
        assert data["url"] == "http://192.168.1.100:5000"
        assert data["location"] == "Building A"
        assert "created_at" in data
        assert "updated_at" in data
    
    @pytest.mark.asyncio
    async def test_get_server_details_not_found(self, test_client):
        """Test getting details for nonexistent server."""
        _, response = await test_client.get("/servers/99999")
        
        assert response.status == 404
        assert "not found" in response.json["error"]
    
    @pytest.mark.asyncio
    async def test_get_server_devices_success(self, test_client, sample_devices):
        """Test proxying device request to slave server."""
        # Register server
        server_data = {
            "name": "slave-1",
            "url": "http://192.168.1.100:5000",
            "location": "Building A"
        }
        _, reg_response = await test_client.post("/register", json=server_data)
        server_id = reg_response.json["server_id"]
        
        # Mock the HTTP client response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "slots": [
                {"id": 1, "rackName": "Rack1", "slotName": "Slot1", "state": "free"}
            ]
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            _, response = await test_client.get(f"/servers/{server_id}/devices")
            
            assert response.status == 200
            data = response.json
            assert data["server_id"] == server_id
            assert data["server_name"] == "slave-1"
            assert "devices" in data
    
    @pytest.mark.asyncio
    async def test_get_server_devices_unreachable(self, test_client):
        """Test handling unreachable slave server."""
        # Register server
        server_data = {
            "name": "slave-1",
            "url": "http://192.168.1.100:5000",
            "location": "Building A"
        }
        _, reg_response = await test_client.post("/register", json=server_data)
        server_id = reg_response.json["server_id"]
        
        # Mock network error
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = Exception("Connection refused")
            
            _, response = await test_client.get(f"/servers/{server_id}/devices")
            
            assert response.status == 503
            assert "Unable to reach server" in response.json["error"]
    
    @pytest.mark.asyncio
    async def test_list_federated_devices(self, test_client):
        """Test aggregating devices from all slave servers."""
        # Register servers
        servers = [
            {"name": "slave-1", "url": "http://192.168.1.100:5000", "location": "Building A"},
            {"name": "slave-2", "url": "http://192.168.1.101:5000", "location": "Building B"}
        ]
        
        for server in servers:
            await test_client.post("/register", json=server)
        
        # Mock responses from slave servers
        mock_response1 = AsyncMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "slots": [{"id": 1, "state": "free"}]
        }
        
        mock_response2 = AsyncMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            "slots": [{"id": 2, "state": "allocated"}]
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = [mock_response1, mock_response2]
            
            _, response = await test_client.get("/devices/federated")
            
            assert response.status == 200
            data = response.json
            assert "devices" in data
            assert data["total_devices"] >= 2
            assert data["servers_queried"] == 2
