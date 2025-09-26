from fastapi import FastAPI, WebSocket, Query
import redis
import asyncio
import json
import os
from typing import Optional, List
from .detector import get_detector
from .storage import get_storage

app = FastAPI()   # <-- define FastAPI app first

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

connections = set()

@app.get("/")
def root():
    return {"message": "Ghost Bus Backend is running with WebSocket"}

@app.get("/api/ghost-stats")
def get_ghost_statistics():
    """Get ghost bus statistics."""
    try:
        # Get all vehicle keys
        vehicle_keys = [key for key in r.keys("vehicle:*") if r.type(key) == 'hash']
        total_vehicles = len(vehicle_keys)
        ghost_count = 0
        monitoring_count = 0
        normal_count = 0
        recurring_ghost_count = 0

        ghost_vehicles = []
        monitoring_vehicles = []

        for key in vehicle_keys:
            vehicle_data = r.hgetall(key)
            if vehicle_data:
                try:
                    lat = float(vehicle_data.get('lat', 0)) if vehicle_data.get('lat') else None
                    lon = float(vehicle_data.get('lon', 0)) if vehicle_data.get('lon') else None
                    if lat is None or lon is None or not (abs(lat) <= 90 and abs(lon) <= 180):
                        continue  # Skip invalid location vehicles
                except ValueError:
                    continue  # Skip if can't parse to float

                ghost_score = int(vehicle_data.get('ghost_score', 0))
                is_ghost = vehicle_data.get('is_ghost', 'false').lower() == 'true'
                is_recurring = vehicle_data.get('is_recurring_ghost', 'false').lower() == 'true'

                if is_ghost:
                    ghost_count += 1
                    if is_recurring:
                        recurring_ghost_count += 1
                    ghost_vehicles.append({
                        'vehicle_id': vehicle_data.get('vehicle_id'),
                        'ghost_score': ghost_score,
                        'lat': lat,
                        'lon': lon,
                        'last_update': vehicle_data.get('timestamp'),
                        'is_recurring_ghost': is_recurring
                    })
                elif ghost_score > 0:
                    monitoring_count += 1
                    monitoring_vehicles.append({
                        'vehicle_id': vehicle_data.get('vehicle_id'),
                        'ghost_score': ghost_score,
                        'lat': lat,
                        'lon': lon
                    })
                else:
                    normal_count += 1

        return {
            "total_vehicles": total_vehicles,
            "ghost_buses": ghost_count,
            "recurring_ghosts": recurring_ghost_count,
            "monitoring_buses": monitoring_count,
            "normal_buses": normal_count,
            "ghost_percentage": (ghost_count / total_vehicles * 100) if total_vehicles > 0 else 0,
            "ghost_vehicles": ghost_vehicles,
            "monitoring_vehicles": monitoring_vehicles
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/vehicles/{vehicle_id}")
def get_vehicle_details(vehicle_id: str):
    """Get detailed information about a specific vehicle."""
    try:
        vehicle_data = r.hgetall(f"vehicle:{vehicle_id}")
        if not vehicle_data:
            return {"error": "Vehicle not found"}

        try:
            lat = float(vehicle_data.get('lat', 0)) if vehicle_data.get('lat') else None
            lon = float(vehicle_data.get('lon', 0)) if vehicle_data.get('lon') else None
            if lat is None or lon is None or not (abs(lat) <= 90 and abs(lon) <= 180):
                return {"error": "Invalid location data for vehicle"}
        except ValueError:
            return {"error": "Invalid location data for vehicle"}

        return {
            "vehicle_id": vehicle_data.get('vehicle_id'),
            "route_id": vehicle_data.get('route_id'),
            "trip_id": vehicle_data.get('trip_id'),
            "lat": lat,
            "lon": lon,
            "speed": float(vehicle_data.get('speed', 0)),
            "bearing": float(vehicle_data.get('bearing', 0)),
            "timestamp": vehicle_data.get('timestamp'),
            "ghost_analysis": {
                "ghost_score": int(vehicle_data.get('ghost_score', 0)),
                "is_ghost": vehicle_data.get('is_ghost', 'false').lower() == 'true',
                "is_recurring_ghost": vehicle_data.get('is_recurring_ghost', 'false').lower() == 'true',
                "detection_timestamp": vehicle_data.get('detection_timestamp'),
                "rules_triggered": vehicle_data.get('detection_rules', {})
            }
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/recurring-ghosts")
def get_recurring_ghosts():
    """Get list of recurring ghost vehicles."""
    try:
        storage = get_storage()
        recurring_ghosts = storage.get_recurring_ghosts()
        return {
            "recurring_ghosts": recurring_ghosts,
            "count": len(recurring_ghosts)
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/vehicles")
def get_vehicles_by_route(route_id: Optional[str] = Query(None, description="Filter by route ID")):
    """Get vehicles, optionally filtered by route."""
    try:
        all_keys = r.keys("vehicle:*")
        print(f"DEBUG: All keys matching 'vehicle:*': {all_keys}")
        vehicle_keys = [key for key in all_keys if r.type(key) == 'hash']
        print(f"DEBUG: Vehicle keys (hash type): {vehicle_keys}")
        vehicles = []

        for key in vehicle_keys:
            vehicle_data = r.hgetall(key)
            if vehicle_data:
                try:
                    lat_str = vehicle_data.get('lat')
                    lon_str = vehicle_data.get('lon')
                    if not lat_str or not lon_str:
                        continue
                    lat = float(lat_str)
                    lon = float(lon_str)
                    if not (abs(lat) <= 90 and abs(lon) <= 180):
                        continue
                except ValueError:
                    continue  # Skip invalid lat/lon

                vehicle_route = vehicle_data.get('route_id', '')

                # Apply route filter if specified
                if route_id and vehicle_route != route_id:
                    continue

                vehicles.append({
                    "vehicle_id": vehicle_data.get('vehicle_id'),
                    "route_id": vehicle_route,
                    "trip_id": vehicle_data.get('trip_id'),
                    "lat": lat,
                    "lon": lon,
                    "speed": float(vehicle_data.get('speed', 0)),
                    "bearing": float(vehicle_data.get('bearing', 0)),
                    "timestamp": vehicle_data.get('timestamp'),
                    "ghost_analysis": {
                        "ghost_score": int(vehicle_data.get('ghost_score', 0)),
                        "is_ghost": vehicle_data.get('is_ghost', 'false').lower() == 'true',
                        "is_recurring_ghost": vehicle_data.get('is_recurring_ghost', 'false').lower() == 'true'
                    }
                })

        return {
            "vehicles": vehicles,
            "count": len(vehicles),
            "route_filter": route_id
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/historical-stats")
def get_historical_stats(days: int = Query(7, description="Number of days to analyze")):
    """Get historical ghost bus statistics."""
    try:
        storage = get_storage()
        stats = storage.get_ghost_statistics(days)
        return stats
    except Exception as e:
        return {"error": str(e)}

@app.websocket("/ws/vehicles")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    connections.add(ws)

    try:
        pubsub = r.pubsub()
        pubsub.subscribe("vehicles:updates")

        while True:
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                raw_message = message["data"]
                print(f"DEBUG WS Raw message: {raw_message[:500]}...")  # Truncate for log
                try:
                    # Parse the raw data (assuming it's JSON string)
                    raw_data = json.loads(raw_message)
                    print(f"DEBUG WS Parsed data type: {type(raw_data)}, length: {len(raw_data) if isinstance(raw_data, list) else 'N/A'}")
                    if isinstance(raw_data, list) and len(raw_data) > 0:
                        print(f"DEBUG WS Sample vehicle: {raw_data[0]}")
                    if isinstance(raw_data, list):
                        # Filter vehicles with invalid lat/lon
                        filtered_vehicles = []
                        for vehicle in raw_data:
                            try:
                                lat_str = vehicle.get('lat')
                                lon_str = vehicle.get('lon')
                                if not lat_str or not lon_str:
                                    continue
                                lat = float(lat_str)
                                lon = float(lon_str)
                                if not (abs(lat) <= 90 and abs(lon) <= 180):
                                    continue
                                # Ensure flat structure
                                vehicle['lat'] = lat
                                vehicle['lon'] = lon
                                filtered_vehicles.append(vehicle)
                            except (ValueError, TypeError):
                                continue  # Skip invalid
                        print(f"DEBUG WS Filtered vehicles count: {len(filtered_vehicles)}")
                        data = json.dumps(filtered_vehicles)
                    else:
                        data = raw_message  # Fallback if not list
                except json.JSONDecodeError as e:
                    print(f"DEBUG WS JSON decode error: {e}")
                    data = raw_message  # Fallback if not JSON

                for conn in list(connections):
                    try:
                        await conn.send_text(data)
                    except Exception as e:
                        print("⚠️ WebSocket send error:", e)
                        connections.remove(conn)
            await asyncio.sleep(0.1)
    except Exception as e:
        print("⚠️ WebSocket error:", e)
    finally:
        connections.remove(ws)
