"""
OpenAPI 3.0 specification generator for XTS Allocator Server.
Provides /openapi.json endpoint and can generate static spec file.
"""

from typing import Dict, Any


def generate_openapi_spec() -> Dict[str, Any]:
    """
    Generate OpenAPI 3.0 specification for all API endpoints.
    
    Returns:
        OpenAPI spec dictionary
    """
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "XTS Allocator Server API",
            "version": "2.0.0",
            "description": "Device allocation and test execution management system for XTS testing framework",
            "contact": {
                "name": "RDK Central",
                "url": "https://github.com/rdkcentral/xts_allocator_server"
            },
            "license": {
                "name": "Apache 2.0",
                "url": "https://www.apache.org/licenses/LICENSE-2.0.html"
            }
        },
        "servers": [
            {
                "url": "http://localhost:5000",
                "description": "Development server"
            }
        ],
        "tags": [
            {"name": "Allocations", "description": "Device allocation and deallocation"},
            {"name": "Devices", "description": "Device management"},
            {"name": "Racks", "description": "Rack management"},
            {"name": "Tests", "description": "Test execution tracking"},
            {"name": "Export", "description": "Configuration export for XTS"},
            {"name": "Federation", "description": "Multi-server federation"},
            {"name": "Health", "description": "Health checks and metrics"},
            {"name": "Usage", "description": "Usage statistics"}
        ],
        "paths": {}
    }
    
    # Allocation endpoints
    spec["paths"]["/allocate_slot"] = {
        "post": {
            "tags": ["Allocations"],
            "summary": "Allocate a device to a user",
            "description": "Allocate a free device with optional duration (temporary allocation)",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/AllocationRequest"}
                    }
                }
            },
            "responses": {
                "200": {
                    "description": "Device allocated successfully",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/AllocationResponse"}
                        }
                    }
                },
                "400": {"description": "Invalid request or validation error"},
                "404": {"description": "Device not found"},
                "409": {"description": "Device not free"},
                "429": {"description": "Rate limit exceeded"}
            }
        }
    }
    
    spec["paths"]["/deallocate_slot"] = {
        "post": {
            "tags": ["Allocations"],
            "summary": "Deallocate a device",
            "description": "Release device back to free state",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/DeallocationRequest"}
                    }
                }
            },
            "responses": {
                "200": {"description": "Device deallocated successfully"},
                "403": {"description": "Unauthorized - email mismatch"},
                "404": {"description": "Device not found"},
                "429": {"description": "Rate limit exceeded"}
            }
        }
    }
    
    spec["paths"]["/change_device_state"] = {
        "post": {
            "tags": ["Allocations"],
            "summary": "Change device state",
            "description": "Manually change device state (maintenance, offline, etc.)",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/StateChangeRequest"}
                    }
                }
            },
            "responses": {
                "200": {"description": "State changed successfully"},
                "400": {"description": "Invalid state or transition not allowed"},
                "404": {"description": "Device not found"},
                "429": {"description": "Rate limit exceeded"}
            }
        }
    }
    
    # Device endpoints
    spec["paths"]["/list_slots"] = {
        "get": {
            "tags": ["Devices"],
            "summary": "List all devices",
            "description": "Get all devices with rack information",
            "responses": {
                "200": {
                    "description": "List of devices",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "slots": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/Device"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "post": {
            "tags": ["Devices"],
            "summary": "Search devices by criteria",
            "description": "Filter devices by platform, state, tags, etc.",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/DeviceSearchRequest"}
                    }
                }
            },
            "responses": {
                "200": {"description": "Matching devices"}
            }
        }
    }
    
    spec["paths"]["/add_slot"] = {
        "post": {
            "tags": ["Devices"],
            "summary": "Add a new device",
            "description": "Create new device entry",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/DeviceCreate"}
                    }
                }
            },
            "responses": {
                "201": {"description": "Device created"},
                "400": {"description": "Validation error"}
            }
        }
    }
    
    # Test endpoints
    spec["paths"]["/start_test"] = {
        "post": {
            "tags": ["Tests"],
            "summary": "Start test execution",
            "description": "Begin test on allocated device, transitions to 'testing' state",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/TestStartRequest"}
                    }
                }
            },
            "responses": {
                "200": {"description": "Test started"},
                "400": {"description": "Device not allocated or expired"},
                "404": {"description": "Device not found"},
                "429": {"description": "Rate limit exceeded"}
            }
        }
    }
    
    spec["paths"]["/test_heartbeat"] = {
        "post": {
            "tags": ["Tests"],
            "summary": "Test execution heartbeat",
            "description": "Keep-alive signal from running test",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "test_id": {"type": "integer"},
                                "status": {"type": "string"}
                            }
                        }
                    }
                }
            },
            "responses": {
                "200": {"description": "Heartbeat received"}
            }
        }
    }
    
    # Health endpoints
    spec["paths"]["/health"] = {
        "get": {
            "tags": ["Health"],
            "summary": "Health check",
            "description": "Server health status",
            "responses": {
                "200": {"description": "Server healthy"}
            }
        }
    }
    
    spec["paths"]["/metrics"] = {
        "get": {
            "tags": ["Health"],
            "summary": "Server metrics",
            "description": "Get metrics in JSON or Prometheus format",
            "parameters": [
                {
                    "name": "format",
                    "in": "query",
                    "description": "Response format (json or prometheus)",
                    "schema": {
                        "type": "string",
                        "enum": ["json", "prometheus"],
                        "default": "json"
                    }
                }
            ],
            "responses": {
                "200": {
                    "description": "Metrics data",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Metrics"}
                        },
                        "text/plain": {
                            "schema": {
                                "type": "string",
                                "description": "Prometheus format metrics"
                            }
                        }
                    }
                }
            }
        }
    }
    
    # Export endpoints
    spec["paths"]["/export/raft_config"] = {
        "get": {
            "tags": ["Export"],
            "summary": "Export RAFT config YAML",
            "description": "Generate XTS-compatible YAML config for allocated devices",
            "parameters": [
                {
                    "name": "allocation_id",
                    "in": "query",
                    "description": "Allocation history ID",
                    "schema": {"type": "integer"}
                }
            ],
            "responses": {
                "200": {
                    "description": "YAML configuration",
                    "content": {
                        "application/x-yaml": {
                            "schema": {"type": "string"}
                        }
                    }
                }
            }
        }
    }
    
    # Components (schemas)
    spec["components"] = {
        "schemas": {
            "User": {
                "type": "object",
                "required": ["email"],
                "properties": {
                    "email": {"type": "string", "format": "email", "maxLength": 254},
                    "username": {"type": "string", "maxLength": 255},
                    "name": {"type": "string", "maxLength": 255}
                }
            },
            "AllocationRequest": {
                "type": "object",
                "required": ["user", "slot"],
                "properties": {
                    "user": {"$ref": "#/components/schemas/User"},
                    "slot": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer", "minimum": 1},
                            "platform": {"type": "string", "maxLength": 255},
                            "tags": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    "duration": {
                        "type": "string",
                        "description": "Allocation duration (e.g., '2h', '30m')",
                        "maxLength": 20,
                        "example": "2h"
                    }
                }
            },
            "AllocationResponse": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "slot_id": {"type": "integer"},
                    "device": {"$ref": "#/components/schemas/Device"},
                    "allocation_history_id": {"type": "integer"},
                    "allocation_expiry": {"type": "string", "format": "date-time"}
                }
            },
            "DeallocationRequest": {
                "type": "object",
                "required": ["user", "slot"],
                "properties": {
                    "user": {"$ref": "#/components/schemas/User"},
                    "slot": {
                        "type": "object",
                        "required": ["id"],
                        "properties": {
                            "id": {"type": "integer", "minimum": 1}
                        }
                    }
                }
            },
            "StateChangeRequest": {
                "type": "object",
                "required": ["device_id", "state"],
                "properties": {
                    "device_id": {"type": "integer", "minimum": 1},
                    "state": {
                        "type": "string",
                        "enum": ["free", "allocated", "testing", "busy", "resetting", "maintenance", "offline"]
                    }
                }
            },
            "Device": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "rack_id": {"type": "integer"},
                    "slot_name": {"type": "string"},
                    "state": {"type": "string"},
                    "platform": {"type": "string"},
                    "make": {"type": "string"},
                    "model": {"type": "string"},
                    "serial_number": {"type": "string"},
                    "host_mac": {"type": "string"},
                    "host_ipv4": {"type": "string"},
                    "owner_email": {"type": "string"},
                    "allocation_type": {"type": "string"},
                    "allocation_expiry": {"type": "string", "format": "date-time"},
                    "tags": {"type": "array", "items": {"type": "string"}}
                }
            },
            "DeviceSearchRequest": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string"},
                    "state": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "rack_id": {"type": "integer"}
                }
            },
            "DeviceCreate": {
                "type": "object",
                "required": ["rack_id", "slot_name", "platform"],
                "properties": {
                    "rack_id": {"type": "integer", "minimum": 1},
                    "slot_name": {"type": "string", "maxLength": 50},
                    "platform": {"type": "string", "maxLength": 255},
                    "make": {"type": "string", "maxLength": 100},
                    "model": {"type": "string", "maxLength": 100},
                    "serial_number": {"type": "string", "maxLength": 100},
                    "host_mac": {"type": "string", "maxLength": 17},
                    "host_ipv4": {"type": "string", "maxLength": 15},
                    "tags": {"type": "array", "items": {"type": "string"}}
                }
            },
            "TestStartRequest": {
                "type": "object",
                "required": ["device_id", "test_name"],
                "properties": {
                    "device_id": {"type": "integer", "minimum": 1},
                    "test_name": {"type": "string", "maxLength": 255},
                    "test_suite": {"type": "string", "maxLength": 255},
                    "expected_duration": {"type": "integer", "minimum": 1, "maximum": 1440},
                    "user_email": {"type": "string", "format": "email"}
                }
            },
            "Metrics": {
                "type": "object",
                "properties": {
                    "device_states": {"type": "object"},
                    "total_devices": {"type": "integer"},
                    "racks": {"type": "integer"},
                    "allocations_today": {"type": "integer"},
                    "tests_running": {"type": "integer"},
                    "tests_completed_today": {"type": "integer"},
                    "avg_allocation_duration_hours": {"type": "number"},
                    "avg_test_duration_minutes": {"type": "number"}
                }
            }
        }
    }
    
    return spec


if __name__ == "__main__":
    import json
    spec = generate_openapi_spec()
    print(json.dumps(spec, indent=2))
