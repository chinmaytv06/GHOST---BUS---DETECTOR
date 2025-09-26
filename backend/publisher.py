import redis
import json
import os
import time
import random
import threading
from app.detector import get_detector
from app.storage import get_storage

# Connect to Redis (from docker-compose service name)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

detector = get_detector(r)
storage = get_storage()

# Multiple bus configurations (Boston area coordinates)
buses = [
    {
        "id": "bus_001",
        "route_id": "1",
        "start_lat": 42.3601,
        "start_lon": -71.0589,
        "speed_range": (5, 30),
        "movement_pattern": "normal"
    },
    {
        "id": "bus_002",
        "route_id": "23",
        "start_lat": 42.3650,
        "start_lon": -71.0500,
        "speed_range": (8, 25),
        "movement_pattern": "normal"
    },
    {
        "id": "bus_003",
        "route_id": "57",
        "start_lat": 42.3550,
        "start_lon": -71.0650,
        "speed_range": (10, 35),
        "movement_pattern": "normal"
    },
    {
        "id": "ghost_bus_001",  # Stationary ghost bus in Boston
        "route_id": "99",
        "start_lat": 42.3700,
        "start_lon": -71.0600,
        "speed_range": (0, 0),  # Stationary
        "movement_pattern": "stationary"
    },
    {
        "id": "ghost_bus_002",  # Off-route ghost bus (north of Boston)
        "route_id": "88",
        "start_lat": 42.4000,
        "start_lon": -71.1000,
        "speed_range": (15, 20),
        "movement_pattern": "off_route"
    }
]

def simulate_bus(bus_config):
    """Simulate a single bus movement with detection and storage."""
    lat, lon = bus_config["start_lat"], bus_config["start_lon"]

    while True:
        current_time = time.time()

        # Simulate different behaviors
        if bus_config["movement_pattern"] == "stationary":
            # Ghost bus: stay in same position, old timestamp for stale detection
            speed = 0
            timestamp = current_time - 400  # 6.67 min old to trigger stale
        elif bus_config["movement_pattern"] == "off_route":
            # Off-route ghost bus: small movement but location triggers off-route
            lat += random.uniform(-0.0005, 0.0005)
            lon += random.uniform(-0.0005, 0.0005)
            speed = random.randint(*bus_config["speed_range"])
            timestamp = current_time
        else:
            # Normal bus: small random movement
            lat += random.uniform(-0.001, 0.001)
            lon += random.uniform(-0.001, 0.001)
            speed = random.randint(*bus_config["speed_range"])
            timestamp = current_time

        vehicle_data = {
            "vehicle_id": bus_config["id"],
            "trip_id": f"trip_{bus_config['id']}",
            "route_id": bus_config["route_id"],
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "timestamp": timestamp,
            "speed": speed,
            "bearing": random.randint(0, 360)
        }

        # Run ghost bus detection
        enhanced_msg = detector.analyze_vehicle(vehicle_data)

        # Convert booleans and nested structures to strings for Redis compatibility
        def convert_for_redis(obj):
            if isinstance(obj, bool):
                return str(obj).lower()
            elif isinstance(obj, (dict, list)):
                return json.dumps(obj)
            else:
                return str(obj)

        enhanced_msg = {str(k): convert_for_redis(v) for k, v in enhanced_msg.items()}

        # Store in Redis hash (TTL = 180 seconds)
        r.hset(f"vehicle:{vehicle_data['vehicle_id']}", mapping=enhanced_msg)
        r.expire(f"vehicle:{vehicle_data['vehicle_id']}", 180)

        # Store historical data in Postgres (original with bools)
        original_msg = detector.analyze_vehicle(vehicle_data)
        storage.save_vehicle_position(original_msg)

        # Publish to pub/sub with detection results (strings for consistency)
        r.publish("vehicles:updates", json.dumps(enhanced_msg))

        # Log
        if enhanced_msg.get('is_ghost', False):
            print(f"👻 Ghost bus detected: {bus_config['id']} (score: {enhanced_msg['ghost_score']}) at ({lat:.4f}, {lon:.4f})")
        else:
            print(f"🚌 Normal bus: {bus_config['id']} at ({lat:.4f}, {lon:.4f}), score: {enhanced_msg.get('ghost_score', 0)}")

        time.sleep(3)  # Update every 3 seconds

# Start simulation threads for each bus
threads = []
for bus in buses:
    thread = threading.Thread(target=simulate_bus, args=(bus,))
    thread.daemon = True
    threads.append(thread)
    thread.start()

print(f"🚀 Started simulation with {len(buses)} buses (including 2 ghosts)")

# Keep main thread alive
while True:
    time.sleep(1)
