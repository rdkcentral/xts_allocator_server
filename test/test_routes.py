import requests

BASE_URL = "http://localhost:5000"

def test_list_slots():
    response = requests.get(f"{BASE_URL}/list_slots")
    assert response.status_code == 200
    print("List slots successful:", response.json())

def test_list_slots_filters():
    filters = {"platform": "Cisco", "tags": ["network"]}
    response = requests.post(f"{BASE_URL}/list_slots", json=filters)
    assert response.status_code == 200
    print("Filter slots successful:", response.json())

if __name__ == "__main__":
    test_list_slots()
    test_list_slots_filters()
