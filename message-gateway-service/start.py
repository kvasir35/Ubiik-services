from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import Union, Dict, Any
from enum import Enum
import httpx
import logging
import uvicorn
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

DEVICE_SERVICE_URL = os.getenv("DEVICE_SERVICE_URL")
READING_SERVICE_URL = os.getenv("READING_SERVICE_URL")

class MessageType(str, Enum):
    REGISTRATION = "registration"
    READING = "reading"

class RegistrationData(BaseModel):
    username: str

class ReadingData(BaseModel):
    reading: float

class Message(BaseModel):
    deviceId: str
    type: MessageType
    data: Union[RegistrationData, ReadingData]
    
    @validator('data', pre=True)
    def validate_data(cls, v, values):
        message_type = values.get('type')
        
        if message_type == MessageType.REGISTRATION:
            if not isinstance(v, dict) or 'username' not in v:
                raise ValueError('Registration data must contain username')
            return RegistrationData(**v)
        elif message_type == MessageType.READING:
            if not isinstance(v, dict) or 'reading' not in v:
                raise ValueError('Reading data must contain reading value')
            return ReadingData(**v)
        
        return v

class DeviceUpdate(BaseModel):
    username: str

class ReadingPayload(BaseModel):
    deviceId: str
    username: str
    reading: float

class DeviceServiceClient:
    def __init__(self):
        self.base_url = os.getenv("DEVICE_SERVICE_URL", DEVICE_SERVICE_URL)
        self.timeout = 30.0
    
    async def upsert_device(self, device_id: str, username: str) -> Dict[str, Any]:
        """Send PUT request to device service to upsert device-username mapping."""
        url = f"{self.base_url}/devices/{device_id}"
        payload = {"username": username}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.put(url, json=payload)
            response.raise_for_status()
            return response.json()
    
    async def get_device_username(self, device_id: str) -> str:
        """Send GET request to device service to retrieve username."""
        url = f"{self.base_url}/devices/{device_id}/username"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return data["username"]

class ReadingServiceClient:
    def __init__(self):
        self.base_url = os.getenv("READING_SERVICE_URL", READING_SERVICE_URL)
        self.timeout = 30.0
        self.is_available = None
    
    async def check_availability(self) -> bool:
        """Check if reading service is available."""
        if self.is_available is not None:
            return self.is_available
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/docs")
                self.is_available = response.status_code == 200
        except Exception:
            self.is_available = False
        
        return self.is_available
    
    async def store_reading(self, device_id: str, username: str, reading: float) -> Dict[str, Any]:
        """Send POST request to reading service to store reading."""
        if not await self.check_availability():
            logger.warning("Reading service not available, skipping storage")
            return {"message": "Reading service not available, reading skipped"}
        
        url = f"{self.base_url}/readings"
        payload = {
            "deviceId": device_id,
            "username": username,
            "reading": reading
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

app = FastAPI(
    title="Message Gateway Service",
    description="Microservice for handling IoT device messages",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize service clients
device_service = DeviceServiceClient()
reading_service = ReadingServiceClient()

@app.post("/messages")
async def handle_message(message: Message) -> Dict[str, Any]:
    """Handle incoming messages from IoT devices."""
    try:
        logger.info(f"Received message from device {message.deviceId} with type {message.type}")
        
        if message.type == MessageType.REGISTRATION:
            return await handle_registration(message.deviceId, message.data)
        elif message.type == MessageType.READING:
            return await handle_reading(message.deviceId, message.data)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported message type: {message.type}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

async def handle_registration(device_id: str, data: RegistrationData) -> Dict[str, Any]:
    """Handle device registration message."""
    try:
        logger.info(f"Processing registration for device {device_id} with username {data.username}")
        
        result = await device_service.upsert_device(device_id, data.username)
        
        logger.info(f"Successfully registered device {device_id}")
        return {
            "message": "Registration processed successfully",
            "deviceId": device_id,
            "type": "registration"
        }
    
    except Exception as e:
        logger.error(f"Error processing registration for device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to process registration with device service"
        )

async def handle_reading(device_id: str, data: ReadingData) -> Dict[str, Any]:
    """Handle device reading message."""
    try:
        logger.info(f"Processing reading for device {device_id} with value {data.reading}")
        
        # Get username from device service
        try:
            username = await device_service.get_device_username(device_id)
        except Exception as e:
            logger.error(f"Failed to get username for device {device_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {device_id} not found or not registered"
            )
        
        # Store reading in reading service
        try:
            result = await reading_service.store_reading(device_id, username, data.reading)
            logger.info(f"Successfully processed reading for device {device_id}")
        except Exception as e:
            logger.warning(f"Failed to store reading for device {device_id}: {e}")
            result = {"message": "Reading processed but not stored - reading service unavailable"}
        
        return {
            "message": "Reading processed successfully",
            "deviceId": device_id,
            "username": username,
            "reading": data.reading,
            "type": "reading",
            "storage_result": result.get("message", "Stored successfully")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing reading for device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)