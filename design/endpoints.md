# Endpoints Documentation

---

## 1. Allocate Slot

### `POST /allocate_slot`

**Description:**  
Allocates a free device slot based on the provided criteria (e.g., slot ID or platform).

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

- **Error (400):**
  ```json
  {
      "message": "Either 'id' or 'platform' must be provided"
  }

- **Error (404):**
  ```json
  {
      "message": "Slot unavailable"

  }    

---

## 2. Deallocate Slot

### `POST /deallocate_slot`

**Description:**  
Frees an allocated device slot. Only the user who allocated the slot can deallocate it.

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
      "message": "Slot 123 is now free",
  }

- **Error (403):**
  ```json
  {
      "message": "Unauthorized: Email mismatch"
  }

- **Error (404):**
  ```json
  {
      "message": "Slot not found"

  }    

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
- **`description`** (string, optional): Search for slots containing the given string in their description.
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
- **`state`** (string, optional, default: "free"): The state of the slot ("free" or "allocated").
- **`owner_email`** (string, optional): The email of the owner (if allocated).

**Response:**
- **Success (201):**
  ```json
  {
      "message": "Slot added successfully.",
  }

- **Error (400):**
  ```json
  {
      "message": "Missing required fields: rackName and slotName."
  }

- **Error (500):**
  ```json
  {
      "message": "Database error message."

  }    

---

## 6. Update Slot

### `POST /update_slot`

**Description:**  
Updates an existing slot's details based on the provided slot_id. Only specified fields will be updated.

**Request Parameters:**
- **`slot_id`** (integer, required): The ID of the slot to update.
- **`rackName`** (string, required); The new rack name.
- **`platform`** (string, optional): The updated platform.
- **`description`** (string, optional): The updated description.
- **`tags`** (list of strings, optional): The updated list of tags.
- **`state`** (string, optional, default: "free"): The new state of the slot ("free" or "allocated").
- **`owner_email`** (string, optional): The updated owner email(if allocated).

**Response:**
- **Success (200):**
  ```json
  {
      "message": "Slot updated successfully.",
  }

- **Error (400):**
  ```json
  {
      "message": "Slot id is required."
  }

- **Error (404):**
  ```json
  {
      "message": "Slot not found."

  } 

- **Error (500):**
  ```json
  {
      "message": "Database error message."

  } 

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
      "message": "Slot deleted successfully.",
  }

- **Error (400):**
  ```json
  {
      "message": "Slot id is required."
  }

- **Error (404):**
  ```json
  {
      "message": "Slot not found."

  } 

- **Error (500):**
  ```json
  {
      "message": "Database error message."

  } 

---
