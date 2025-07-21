# Ubiik test interview

A microservices-based IoT data processing system built with FastAPI, SQLAlchemy, and Docker. This system handles device registration and sensor data processing through a scalable microservices architecture.

## Architecture

The system consists of the following microservices:

- **Device Service** (Port 8001): Manages device-username mappings and device registration
- **Message Gateway Service** (Port 8000): Handles incoming IoT messages and routes them to appropriate services
- **Reading Service** (Port 8002): Not in the scoop of this project

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   IoT Device    │───▶│ Message Gateway │───▶│ Device Service  │
│                 │    │    Service      │    │                 │
└─────────────────┘    │   (Port 8000)   │    │   (Port 8001)   │
                       │                 │    │                 │
                       │                 │───▶│ Reading Service │
                       │                 │    │   (Port 8002)   │
                       └─────────────────┘    └─────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.13+
- Git

### Using Docker Compose (Recommended)

1. **Clone the repository**

   ```bash
   git clone https://github.com/kvasir35/Ubiik-services
   cd iot-data-processing-system
   ```

2. **Start all services**

   ```bash
   docker-compose up --build
   ```

3. **Access the services**
   - Message Gateway: http://localhost:8000/docs
   - Device Service: http://localhost:8001/docs

### Local Development Setup

If you prefer to run services locally:

1. **Install dependencies for each service**

   ```bash
   # Device Service
   cd services/device-service
   pip install -r requirements.txt

   # Message Gateway Service
   cd ../message-gateway-service
   pip install -r requirements.txt
   ```

2. **Run the services**

   ```bash
   # Terminal 1 - Device Service
   cd services/device-service
   python start.py

   # Terminal 2 - Message Gateway Service
   cd services/message-gateway-service
   python start.py
   ```

## API Usage Exemple

### Register a Device

```bash
curl -X POST http://localhost:8000/messages \
  -H "Content-Type: application/json" \
  -d '{
    "deviceId": "sensor-001",
    "type": "registration",
    "data": {"username": "alice"}
  }'
```

### Send a Sensor Reading

```bash
curl -X POST http://localhost:8000/messages \
  -H "Content-Type: application/json" \
  -d '{
    "deviceId": "sensor-001",
    "type": "reading",
    "data": {"reading": 23.5}
  }'
```

### Query Device Information

```bash
curl -X GET http://localhost:8001/devices/sensor-001/username
```

## Testing

Run tests for all services:

```bash
# Test Device Service
cd services/device-service
pytest

# Test Message Gateway Service
cd services/message-gateway-service
pytest
```

## Project Structure

```
iot-data-processing-system/
├── services/
│   ├── device-service/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── start.py
│   │   ├── test_device_service.py
│   │   └── README.md
│   ├── message-gateway-service/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── start.py
│   │   ├── test_gateway_service.py
│   │   ├── .env
│   │   └── README.md
│   └── docker-compose.yml
├── README.md
└── .gitignore
```

## Configuration

### Environment Variables

#### Message Gateway Service

- `DEVICE_SERVICE_URL`: URL for the device service (default: http://localhost:8001)
- `READING_SERVICE_URL`: URL for the reading service (default: http://localhost:8002)

### Docker Environment

When running with Docker Compose, services communicate using internal network names:

- Device Service: `http://device-service:8001`
- Reading Service: `http://reading-service:8002`

## License

MIT License

**Contact**: yohann.person@hotmail.fr
