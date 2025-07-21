import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import os

from start import app, get_db, Base, Device

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def setup_function():
    """Clean up database before each test."""
    with TestingSessionLocal() as db:
        db.query(Device).delete()
        db.commit()

def test_upsert_device_create():
    response = client.put("/devices/1", json={"username": "test-user"})
    assert response.status_code == 200
    assert response.json()["device_id"] == "1"

def test_get_device_username():
    # Create device
    client.put("/devices/2", json={"username": "test-user-2"})
    
    # Get username
    response = client.get("/devices/2/username")
    assert response.status_code == 200
    assert response.json()["username"] == "test-user-2"

def test_upsert_device_update():    
    # Update device
    response = client.put("/devices/1", json={"username": "updated-user"})
    assert response.status_code == 200
    
    # Verify update
    response = client.get("/devices/1/username")
    assert response.status_code == 200
    assert response.json()["username"] == "updated-user"


def test_get_device_username_not_found():
    response = client.get("/devices/10/username")
    assert response.status_code == 404