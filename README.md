"# GHOST---BUS---DETECTOR" 
# Ghost Bus Detector

A real-time system for detecting "ghost buses" in public transit networks using GTFS real-time data. Ghost buses are vehicles that appear in tracking systems but may not be operating legitimately or are exhibiting suspicious behavior.

## 🚀 Features

- **Real-time Vehicle Monitoring**: Ingests and processes GTFS real-time vehicle position data
- **Ghost Bus Detection**: Advanced algorithms to identify potentially fraudulent or malfunctioning vehicles
- **Interactive Dashboard**: Web-based interface with maps, statistics, and real-time updates
- **Historical Analytics**: Track ghost bus patterns over time
- **WebSocket Streaming**: Live updates of vehicle positions and ghost detection results
- **Recurring Ghost Tracking**: Identifies vehicles that frequently exhibit ghost behavior

## 🏗️ Architecture

The system consists of three main components:

- **Backend (FastAPI)**: Handles data ingestion, ghost detection logic, and API endpoints
- **Frontend (React)**: Provides the user interface with maps and dashboards
- **Database**: Redis for real-time data, PostgreSQL for historical storage

## 🔧 Tech Stack

### Backend
- **FastAPI**: High-performance web framework for building APIs
- **Redis**: In-memory data store for real-time vehicle data
- **PostgreSQL**: Relational database for historical analytics
- **GTFS Realtime Bindings**: Protocol buffer parsing for transit data
- **WebSockets**: Real-time communication with frontend

### Frontend
- **React**: Component-based UI framework
- **Material-UI**: Modern component library
- **Leaflet**: Interactive maps for vehicle visualization
- **Recharts**: Data visualization for statistics
- **WebSockets**: Real-time updates from backend

### Infrastructure
- **Docker**: Containerized deployment
- **Docker Compose**: Multi-service orchestration

## 🚦 Ghost Detection Rules

The system uses multiple heuristics to identify ghost buses:

1. **Stale Data**: Vehicles with no position updates for extended periods
2. **Stationary Detection**: Vehicles that haven't moved significantly for too long
3. **Off-Route Detection**: Vehicles positioned far from expected route paths
4. **Speed Anomalies**: Unrealistic speed values (too fast or negative)
5. **Recurring Patterns**: Vehicles that frequently trigger ghost detection

Each vehicle receives a ghost score (0-100), with scores > 50 marked as ghosts.

## 🛠️ Setup and Installation

### Prerequisites
- Docker and Docker Compose
- Git

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd ghost-bus-detector
   ```

2. **Start the services**:
   ```bash
   docker-compose up --build
   ```

3. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Manual Setup (Alternative)

#### Backend Setup
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### Frontend Setup
```bash
cd frontend
npm install
npm start
```

## 📊 API Endpoints

### Core Endpoints
- `GET /` - Health check
- `GET /api/ghost-stats` - Current ghost bus statistics
- `GET /api/vehicles` - List all vehicles (with optional route filter)
- `GET /api/vehicles/{vehicle_id}` - Detailed vehicle information
- `GET /api/recurring-ghosts` - List of recurring ghost vehicles
- `GET /api/historical-stats` - Historical ghost statistics

### Real-time
- `WebSocket /ws/vehicles` - Real-time vehicle position updates

## 🎯 Usage

1. **Dashboard Overview**: View real-time statistics and maps showing vehicle positions
2. **Ghost Bus Monitoring**: Identify and track suspected ghost buses
3. **Route Analysis**: Filter vehicles by route for targeted monitoring
4. **Historical Trends**: Analyze ghost bus patterns over time
5. **Recurring Issues**: Track vehicles with persistent ghost behavior

## 🔄 Data Flow

1. **Data Ingestion**: GTFS real-time feed is consumed and parsed
2. **Vehicle Analysis**: Each vehicle position is analyzed using detection algorithms
3. **Scoring**: Ghost scores are calculated based on multiple criteria
4. **Storage**: Real-time data stored in Redis, historical data in PostgreSQL
5. **Streaming**: Updates are pushed to connected frontend clients via WebSockets

## 📈 Configuration

Key environment variables (set in docker-compose.yml):

- `GTFS_FEED_URL`: URL of the GTFS real-time feed
- `STALE_THRESHOLD`: Seconds before data is considered stale (default: 300)
- `STATIONARY_THRESHOLD`: Seconds before vehicle is considered stationary (default: 600)
- `OFF_ROUTE_THRESHOLD`: Distance threshold for off-route detection (default: 0.5 km)
- `HISTORY_TTL`: Time-to-live for historical data in Redis (default: 86400 seconds)

## 🧪 Testing

Run backend tests:
```bash
cd backend
pytest
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built for detecting transit service irregularities
- Uses GTFS real-time standards for data interchange
- Inspired by real-world transit monitoring needs
