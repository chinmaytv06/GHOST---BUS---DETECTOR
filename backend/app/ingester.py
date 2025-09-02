import aiohttp
import asyncio
import json
import os
import redis
from google.transit import gtfs_realtime_pb2

# Redis connection (uses the docker-compose service name 'redis')
REDIS = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, decode_responses=True)

# GTFS-Realtime feed URL (replace with your city transit feed)
GTFS_FEED_URL = os.getenv("GTFS_FEED_URL", "https://your-city-gtfs-feed-url")

async def fetch_feed(url: str) -> bytes:
    """Fetch raw GTFS-Realtime protobuf feed."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.read()

async def parse_and_publish(feed_bytes: bytes):
    """Parse GTFS-RT feed and publish vehicle updates to Redis."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(feed_bytes)

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

            # Store in Redis (TTL = 180 seconds)
            REDIS.hmset(f"vehicle:{msg['vehicle_id']}", msg)
            REDIS.expire(f"vehicle:{msg['vehicle_id']}", 180)

            # Publish to pub/sub
            REDIS.publish("vehicles:updates", json.dumps(msg))

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
