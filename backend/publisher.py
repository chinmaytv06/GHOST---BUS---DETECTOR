import redis
import json
import os
import time
import random

# Connect to Redis (from docker-compose service name)
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

# Start position (Bangalore coords as example)
lat, lon = 12.9716, 77.5946

while True:
    # Simulate small random movement
    lat += random.uniform(-0.001, 0.001)
    lon += random.uniform(-0.001, 0.001)

    vehicle_data = {
        "vehicle_id": "123",
        "route_id": "42",
        "lat": round(lat, 6),
        "lon": round(lon, 6),
        "speed": random.randint(5, 30)
    }

    # Publish to Redis
    r.publish("vehicles:updates", json.dumps(vehicle_data))
    print(f"✅ Published: {vehicle_data}")

    time.sleep(5)  # wait 5 seconds before sending next update
