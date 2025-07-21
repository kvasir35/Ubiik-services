from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func
from pydantic import BaseModel
import logging
import uvicorn
import os

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./device_service.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Models
class Device(Base):
    __tablename__ = "devices"
    
    device_id = Column(String, primary_key=True, index=True)
    username = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class DeviceUpdate(BaseModel):
    username: str

class DeviceResponse(BaseModel):
    username: str
    
    class Config:
        from_attributes = True

# Create tables
Base.metadata.create_all(bind=engine)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Device Service",
    description="Microservice for managing device-username mappings",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.put("/devices/{device_id}")
async def upsert_device(
    device_id: str,
    device_data: DeviceUpdate,
    db: Session = Depends(get_db)
):
    """Create or update a device-username mapping."""
    try:
        device = db.query(Device).filter(Device.device_id == device_id).first()
        
        if device:
            device.username = device_data.username
            logger.info(f"Updated device {device_id} with username {device_data.username}")
        else:
            device = Device(device_id=device_id, username=device_data.username)
            db.add(device)
            logger.info(f"Created new device {device_id} with username {device_data.username}")
        
        db.commit()
        db.refresh(device)
        
        return {"message": "Device updated successfully", "device_id": device_id}
    
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.get("/devices/{device_id}/username", response_model=DeviceResponse)
async def get_device_username(device_id: str, db: Session = Depends(get_db)):
    """Retrieve the username associated with a device ID."""
    try:
        device = db.query(Device).filter(Device.device_id == device_id).first()
        
        if not device:
            logger.warning(f"Device {device_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {device_id} not found"
            )
        
        logger.info(f"Retrieved username for device {device_id}")
        return DeviceResponse(username=device.username)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)