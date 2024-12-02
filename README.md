<div><img src="logo.png" width="150" style="border-radius: 50%;"/></div>
</br>

# XTS Allocator Server

The XTS Allocator Server is a tool for managing device allocation within a shared testing environment. It allows users to allocate, deallocate, and search for devices while preventing conflicts between users.

---

## Installation

### Prerequisites
- Python 3.8 or later
- All the packages listed in requirements.txt
    - Can be installed using `$ pip install -r requirements.txt`

### Steps
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/rdkcentral/xts_allocator_server.git
   cd xts_allocator_server
   ```

2. **Set Up the Database**:
   Initialize the SQLite database:
   ```bash
   python database_setup.py
   ```

3. **Run the Server**:
   Start the XTS Allocator Server:
   ```bash
   python app.py
   ```

---

## Usage

### Server
Start the server with the following command:
```bash
python app.py
```

### Client Commands
1. **Allocate a Device**:
   ```bash
   xts allocate --id <device_id> --platform <platform_name> --tags <tag1,tag2> --duration <time>
   ```

2. **List All Slots**:
   ```bash
   xts allocator list
   ```

3. **Search for a Slot**:
   ```bash
   xts allocator search --platform <platform_name> --tags <tag1,tag2>
   ```

4. **Deallocate a Slot**:
   ```bash
   xts deallocate --id <device_id>
   ```

5. **Run a Test**:
   ```bash
   xts run --test <test_name> --allocate <device_id>
   ```

---

## Documentation

### API Endpoints
1. **Allocate Slot (`POST /allocate_slot`)**:
   - Allocates a device based on ID, platform, or tags.
   - Parameters:
     ```json
     {
       "user": {
         "username": "user01",
         "name": "John Doe",
         "email": "john.doe@example.com"
       },
       "slot": {
         "id": "1",
         "platform": "alpha.uk",
         "tags": ["tag1", "tag2"]
       }
     }
     ```

2. **List Slots (`GET /list_slots`)**:
   - Lists all available and allocated slots.

3. **Search Slots (`POST /search_slots`)**:
   - Searches for slots matching specific criteria (platform, tags, etc.).

4. **Deallocate Slot (`POST /deallocate_slot`)**:
   - Deallocates a slot based on its ID and user ownership.


## Contributing

See contributing file: [CONTRIBUTING.md](CONTRIBUTING.md)

## License

See license file: [LICENSE](LICENSE)
