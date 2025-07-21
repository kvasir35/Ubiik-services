from fastapi.testclient import TestClient
from start import app, device_service, reading_service
import pytest
from unittest.mock import AsyncMock

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_services(monkeypatch):
    # Mock upsert_device
    monkeypatch.setattr(device_service, "upsert_device", AsyncMock(return_value={"message": "Device updated successfully"}))
    
    # Mock get_device_username
    monkeypatch.setattr(device_service, "get_device_username", AsyncMock(return_value="user_test"))
    
    # Mock store_reading
    monkeypatch.setattr(reading_service, "store_reading", AsyncMock(return_value={"message": "Reading stored successfully"}))

def test_handle_registration_message():
    payload = {
        "deviceId": "reg123",
        "type": "registration",
        "data": {
            "username": "user_test"
        }
    }
    response = client.post("/messages", json=payload)
    assert response.status_code == 200
    assert response.json()["type"] == "registration"

def test_handle_reading_message():
    payload = {
        "deviceId": "read123",
        "type": "reading",
        "data": {
            "reading": 99.9
        }
    }
    response = client.post("/messages", json=payload)
    assert response.status_code == 200
    assert response.json()["type"] == "reading"
    assert response.json()["reading"] == 99.9

def test_invalid_message_type():
    payload = {
        "deviceId": "bad123",
        "type": "invalid",
        "data": {}
    }
    response = client.post("/messages", json=payload)
    assert response.status_code == 422  # Validation Error
