# Endpoints Documentation

---

## 1. Allocate Slot

### `POST /allocate_slot`

**Description:**  
Allocates a free device slot based on the provided criteria (e.g., slot ID or
platform).

**Request Parameters:**

- **`user`** (object):  
  Contains user details.  
  - **`email`** (string): The email of the user requesting the allocation.

- **`slot`** (object):  
  Contains slot search criteria.  
  - **`id`** (integer, optional): The specific slot ID to allocate.  
  - **`platform`** (string, optional): The platform type to allocate a slot from.  
  - **`tags`** (list of strings, optional): Tags to filter the slot.

**Response:**

- **Success (200):**

  ```json
  {
      "message": "Slot allocated",
      "slot_info": "Slot ID: 123",
      "id": 123
  }
  ```

- **Error (400):**

  ```json
  {
      "message": "Either 'id' or 'platform' must be provided"
  }
  ```

- **Error (404):**

  ```json
  {
      "message": "Slot unavailable"
  }
  ```

---

## 2. Deallocate Slot

### `POST /deallocate_slot`

**Description:**  
Frees an allocated device slot. Only the user who allocated the slot can
deallocate it.

**Request Parameters:**

- **`user`** (object):  
  Contains user details.  
  - **`email`** (string): The email of the user requesting the allocation.

- **`slot`** (object):  
  Contains slot search criteria.  
  - **`id`** (integer, optional): The specific slot ID to allocate.

**Response:**

- **Success (200):**

  ```json
  {
      "message": "Slot 123 is now free"
  }
  ```

- **Error (403):**

  ```json
  {
      "message": "Unauthorized: Email mismatch"
  }
  ```

- **Error (404):**

  ```json
  {
      "message": "Slot not found"
  }
  ```

---

## 3. List All Slots

### `GET /list_slots`

**Description:**  
Retrieves a list of all device slots, regardless of their allocation state.

**Request Parameters:**

- None

**Response:**

- **Success (200):**
  Lists the slots.

---

## 4. List Slots with Filters

### `POST /list_slots`

**Description:**  
Filters and retrieves device slots based on the provided criteria.

**Request Parameters:**

- **`platform`** (string, optional): Filter slots by platform type.
- **`description`** (string, optional): Search for slots containing the
  given string in their description.
- **`tags`** (list of strings, optional): Filter slots by matching tags.

**Response:**

- **Success (200):**
  Lists the slots that match the criteria

---

## 5. Add Slot

### `POST /add_slot`

**Description:**  
Adds a new slot in the database.

**Request Parameters:**

- **`rackName`** (string, required); The rack where the slot is located.
- **`platform`** (string, optional): The platform associated with the slot.
- **`description`** (string, optional): Additional details about the slot.
- **`tags`** (list of strings, optional): Tags associated with the slots.
- **`state`** (string, optional, default: "free"): The state of the slot
  ("free" or "allocated").
- **`owner_email`** (string, optional): The email of the owner (if allocated).

**Response:**

- **Success (201):**

  ```json
  {
      "message": "Slot added successfully."
  }
  ```

- **Error (400):**

  ```json
  {
      "message": "Missing required fields: rackName and slotName."
  }
  ```

- **Error (500):**

  ```json
  {
      "message": "Database error message."
  }
  ```

---

## 6. Update Slot

### `POST /update_slot`

**Description:**  
Updates an existing slot's details based on the provided slot_id. Only
specified fields will be updated.

**Request Parameters:**

- **`slot_id`** (integer, required): The ID of the slot to update.
- **`rackName`** (string, required); The new rack name.
- **`platform`** (string, optional): The updated platform.
- **`description`** (string, optional): The updated description.
- **`tags`** (list of strings, optional): The updated list of tags.
- **`state`** (string, optional, default: "free"): The new state of the
  slot ("free" or "allocated").
- **`owner_email`** (string, optional): The updated owner email (if allocated).

**Response:**

- **Success (200):**

  ```json
  {
      "message": "Slot updated successfully."
  }
  ```

- **Error (400):**

  ```json
  {
      "message": "Slot id is required."
  }
  ```

- **Error (404):**

  ```json
  {
      "message": "Slot not found."
  }
  ```

- **Error (500):**

  ```json
  {
      "message": "Database error message."
  }
  ```

---

## 7. Delete Slot

### `POST /delete_slot`

**Description:**  
Deletes an existing slot from the database based on the provided slot_id.

**Request Parameters:**

- **`slot_id`** (integer, required): The ID of the slot to delete.

**Response:**

- **Success (200):**

  ```json
  {
      "message": "Slot deleted successfully."
  }
  ```

- **Error (400):**

  ```json
  {
      "message": "Slot id is required."
  }
  ```

- **Error (404):**

  ```json
  {
      "message": "Slot not found."
  }
  ```

- **Error (500):**

  ```json
  {
      "message": "Database error message."
  }
  ```

---

## 8. Export Allocator-Optimized Config

### `GET /export/raft_config`

**Description:**  
Export allocator-optimized YAML configuration for allocated devices. This format is optimized for XTS allocator integration with unified structure combining device, rack, and allocation metadata.

**Query Parameters:**
- **`allocation_id`** (integer, optional): Device ID to export config for.
- **`owner_email`** (string, optional): Filter by owner email.

**Note:** Either `allocation_id` or `owner_email` must be provided.

**Response:**
- **Success (200):**
  Returns YAML content with `application/x-yaml` content type.
  
  Example structure:
  ```yaml
  version: "1.0"
  generated_at: "2026-02-05T15:21:42Z"
  allocator:
    server_url: "http://localhost:5000"
    api_version: "v1"
  allocations:
    - allocation_id: 1
      allocation_expiry: "2026-02-05T16:21:42Z"
      owner_email: "user@example.com"
      state: "allocated"
      device:
        id: 1
        platform: "Cisco"
        network:
          host_ipv4: "192.168.1.100"
        control_uris: {}
      rack:
        name: "Rack1"
        location: "Lab A"
        slot_name: "Slot1"
  ```

- **Error (400/404/500):** JSON error response

---

## 9. Export Python RAFT Compatible Config

### `GET /export/python_raft_config`

**Description:**  
Export python_raft-compatible manual format configuration for allocated devices. Follows existing rack_config.yml + device_config.yml structure.

**Query Parameters:**
- **`allocation_id`** (integer, optional): Device ID to export config for.
- **`owner_email`** (string, optional): Filter by owner email.

**Note:** Either `allocation_id` or `owner_email` must be provided.

**Response:**
- **Success (200):**
  Returns YAML content with `application/x-yaml` content type.
  
  Example structure:
  ```yaml
  rack_config:
    version: "1.0"
    racks:
      - name: "Rack1"
        location: "Lab A"
        slots:
          - slot_name: "Slot1"
            device_id: 1
  device_config:
    version: "1.0"
    devices:
      - id: 1
        name: "Rack1_Slot1"
        platform: "Cisco"
        network:
          host_ipv4: "192.168.1.100"
        allocation:
          owner: "user@example.com"
  ```

- **Error (400/404/500):** JSON error response

---

## 10. Allocation History

### `GET /allocation_history`

**Description:**  
Retrieve allocation history records with optional filters. Tracks all allocation and deallocation events for audit trail and compliance.

**Query Parameters:**
- **`device_id`** (integer, optional): Filter by specific device ID.
- **`email`** (string, optional): Filter by user email.
- **`start_date`** (string, optional): Filter records from this date (ISO format: 2026-02-01).
- **`end_date`** (string, optional): Filter records until this date (ISO format).
- **`limit`** (integer, optional, default: 100): Maximum number of records to return.

**Response:**
- **Success (200):**
  Returns JSON with history records.
  
  Example:
  ```json
  {
    "count": 2,
    "history": [
      {
        "id": 1,
        "device_id": 2,
        "device_name": "Rack2_Slot2",
        "platform": "Dell",
        "user": "testuser",
        "email": "test@example.com",
        "name": "Test User",
        "start_time": "2026-02-05T15:44:06Z",
        "end_time": "2026-02-05T17:44:06Z",
        "duration_requested": 120,
        "duration_actual": 120,
        "state_before": "free",
        "state_after": "free",
        "software_version": "v2.1.0",
        "is_active": false
      }
    ]
  }
  ```

- **Error (400):** Invalid parameter format
- **Error (500):** Server error

**Notes:**
- Records are ordered by most recent first
- `is_active: true` indicates allocation is still active (not yet deallocated)
- `duration_actual` is calculated from start_time to end_time in minutes
- History records are automatically created on allocate and closed on deallocate

---
