"""Tests for allocation history tracking."""

import pytest
from datetime import datetime


class TestAllocationHistory:
    """Test allocation history functionality."""
    
    def test_history_created_on_allocation(self, test_client, sample_devices):
        """Test that history record is created on allocation."""
        request, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {
                    "email": "test@example.com",
                    "username": "testuser",
                    "name": "Test User"
                },
                "slot": {"id": sample_devices[0].id},
                "duration": "1h"
            }
        )
        
        assert response.status == 200
        history_id = response.json["allocation_history_id"]
        
        # Check history endpoint
        request, response = test_client.get(
            f"/allocation_history?device_id={sample_devices[0].id}"
        )
        
        assert response.status == 200
        history = response.json["history"]
        assert len(history) == 1
        assert history[0]["id"] == history_id
        assert history[0]["email"] == "test@example.com"
        assert history[0]["is_active"] is True
        assert history[0]["duration_requested"] == 60
    
    def test_history_closed_on_deallocation(self, test_client, sample_devices):
        """Test that history record is closed on deallocation."""
        # Allocate
        test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "test@example.com"},
                "slot": {"id": sample_devices[0].id}
            }
        )
        
        # Deallocate
        test_client.post(
            "/deallocate_slot",
            json={
                "user": {"email": "test@example.com"},
                "slot": {"id": sample_devices[0].id}
            }
        )
        
        # Check history
        request, response = test_client.get(
            f"/allocation_history?device_id={sample_devices[0].id}"
        )
        
        assert response.status == 200
        history = response.json["history"]
        assert len(history) == 1
        assert history[0]["is_active"] is False
        assert history[0]["end_time"] is not None
        assert history[0]["duration_actual"] is not None
    
    def test_history_filter_by_email(self, test_client, sample_devices):
        """Test filtering history by email."""
        # Create allocations with different users
        test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user1@example.com"},
                "slot": {"id": sample_devices[0].id}
            }
        )
        test_client.post(
            "/deallocate_slot",
            json={
                "user": {"email": "user1@example.com"},
                "slot": {"id": sample_devices[0].id}
            }
        )
        
        test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user2@example.com"},
                "slot": {"id": sample_devices[1].id}
            }
        )
        
        # Filter by user1
        request, response = test_client.get(
            "/allocation_history?email=user1@example.com"
        )
        
        assert response.status == 200
        history = response.json["history"]
        assert len(history) == 1
        assert history[0]["email"] == "user1@example.com"
    
    def test_history_limit(self, test_client, sample_devices):
        """Test history result limiting."""
        # Create multiple allocations
        for i in range(5):
            test_client.post(
                "/allocate_slot",
                json={
                    "user": {"email": f"user{i}@example.com"},
                    "slot": {"id": sample_devices[0].id}
                }
            )
            test_client.post(
                "/deallocate_slot",
                json={
                    "user": {"email": f"user{i}@example.com"},
                    "slot": {"id": sample_devices[0].id}
                }
            )
        
        # Request with limit
        request, response = test_client.get("/allocation_history?limit=3")
        
        assert response.status == 200
        history = response.json["history"]
        assert len(history) == 3
