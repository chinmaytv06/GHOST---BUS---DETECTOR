from fastapi import FastAPI, WebSocket
import redis
import asyncio
import json
import os

app = FastAPI()   # <-- define FastAPI app first

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

connections = set()

@app.get("/")
def root():
    return {"message": "Ghost Bus Backend is running with WebSocket"}

@app.websocket("/ws/vehicles")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    connections.add(ws)

    try:
        pubsub = r.pubsub()
        pubsub.subscribe("vehicles:updates")

        for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                for conn in list(connections):
                    await conn.send_text(data)
    except Exception as e:
        print("⚠️ WebSocket error:", e)
    finally:
        connections.remove(ws)
