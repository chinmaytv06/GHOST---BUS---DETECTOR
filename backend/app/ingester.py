import aiohttp
import asyncio
import json
import os
import redis
from .detector import get_detector
from .storage import get_storage
from google.transit import gtfs_realtime_pb2

# Redis connection (uses the docker-compose service name 'redis')
REDIS = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, decode_responses=True)

# GTFS-Realtime feed URL (replace with your city transit feed)
GTFS_FEED_URL = os.getenv("GTFS_FEED_URL", "https://cdn.mbta.com/realtime/VehiclePositions.pb")

async def fetch_feed(url: str) -> bytes:
    """Fetch raw GTFS-Realtime protobuf feed."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.read()

async def parse_and_publish(feed_bytes: bytes):
    """Parse GTFS-RT feed and publish vehicle updates to Redis."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(feed_bytes)

    # Get detector and storage instances
    detector = get_detector(REDIS)
    storage = get_storage()

    for entity in feed.entity:
        if entity.HasField("vehicle"):
            v = entity.vehicle
            msg = {
                "vehicle_id": v.vehicle.id,
                "trip_id": v.trip.trip_id,
                "route_id": v.trip.route_id,
                "lat": v.position.latitude,
                "lon": v.position.longitude,
                "timestamp": v.timestamp,
                "speed": getattr(v.position, "speed", None),
                "bearing": getattr(v.position, "bearing", None),
            }

            # Run ghost bus detection
            enhanced_msg = detector.analyze_vehicle(msg)

            # Store in Redis (TTL = 180 seconds) - convert to strings
            redis_data = {k: str(v) for k, v in enhanced_msg.items()}
            REDIS.hset(f"vehicle:{msg['vehicle_id']}", mapping=redis_data)
            REDIS.expire(f"vehicle:{msg['vehicle_id']}", 180)

            # Store historical data in Postgres (non-blocking)
            try:
                storage.save_vehicle_position(enhanced_msg)
            except Exception as e:
                print(f"⚠️ Postgres save error for {msg['vehicle_id']}: {e}")

            # Publish to pub/sub with detection results
            REDIS.publish("vehicles:updates", json.dumps(enhanced_msg))

            # Log ghost buses
            if enhanced_msg.get('is_ghost', False):
                print(f"👻 Ghost bus detected: {msg['vehicle_id']} (score: {enhanced_msg['ghost_score']})")

async def loop(url: str, interval: int = 10):
    """Main loop: fetch & publish every interval seconds."""
    while True:
        try:
            raw = await fetch_feed(url)
            await parse_and_publish(raw)
            print(f"✅ Published GTFS updates to Redis")
        except Exception as e:
            print("⚠️ Error:", e)

        await asyncio.sleep(interval)

if __name__ == "__main__":
    asyncio.run(loop(GTFS_FEED_URL, interval=10))
