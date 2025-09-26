import time
import math
from typing import Dict, List, Optional, Tuple
import redis
import os

class GhostBusDetector:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.stale_threshold = int(os.getenv("STALE_THRESHOLD", 300))  # 5 minutes
        self.stationary_threshold = int(os.getenv("STATIONARY_THRESHOLD", 600))  # 10 minutes
        self.off_route_threshold = float(os.getenv("OFF_ROUTE_THRESHOLD", 0.5))  # 500 meters
        self.history_ttl = int(os.getenv("HISTORY_TTL", 86400))  # 24 hours

    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers."""
        R = 6371  # Earth's radius in km

        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    def get_vehicle_history(self, vehicle_id: str) -> List[Dict]:
        """Get historical positions for a vehicle."""
        history_key = f"vehicle:history:{vehicle_id}"
        history_data = self.redis.lrange(history_key, 0, -1)

        history = []
        for item in history_data:
            try:
                history.append(eval(item))  # Convert string back to dict
            except:
                continue
        return history

    def update_vehicle_history(self, vehicle_id: str, vehicle_data: Dict):
        """Update historical data for a vehicle."""
        history_key = f"vehicle:history:{vehicle_id}"
        # Keep only last 50 positions
        self.redis.lpush(history_key, str(vehicle_data))
        self.redis.ltrim(history_key, 0, 49)
        self.redis.expire(history_key, self.history_ttl)

    def detect_stale_data(self, vehicle_data: Dict) -> bool:
        """Check if vehicle data is stale (no updates for too long)."""
        current_time = time.time()
        last_update = vehicle_data.get('timestamp', current_time)

        if current_time - last_update > self.stale_threshold:
            return True
        return False

    def detect_stationary(self, vehicle_id: str, current_pos: Tuple[float, float]) -> bool:
        """Check if vehicle has been stationary for too long."""
        history = self.get_vehicle_history(vehicle_id)

        if len(history) < 2:
            return False

        # Check if position hasn't changed significantly in the last stationary_threshold seconds
        current_time = time.time()
        recent_positions = []

        for pos_data in history:
            if current_time - pos_data.get('timestamp', 0) <= self.stationary_threshold:
                recent_positions.append((pos_data['lat'], pos_data['lon']))

        if len(recent_positions) < 2:
            return False

        # Check if all recent positions are within a small radius (50 meters)
        first_pos = recent_positions[0]
        for pos in recent_positions[1:]:
            distance = self.haversine_distance(first_pos[0], first_pos[1], pos[0], pos[1])
            if distance > 0.05:  # 50 meters
                return False

        return True

    def point_to_line_distance(self, point: Tuple[float, float], line_start: Tuple[float, float], line_end: Tuple[float, float]) -> float:
        """Calculate perpendicular distance from a point to a line segment."""
        px, py = point
        x1, y1 = line_start
        x2, y2 = line_end

        # Convert to radians for distance calculation
        px_rad, py_rad = math.radians(px), math.radians(py)
        x1_rad, y1_rad = math.radians(x1), math.radians(y1)
        x2_rad, y2_rad = math.radians(x2), math.radians(y2)

        # Vector from line_start to line_end
        dx = x2_rad - x1_rad
        dy = y2_rad - y1_rad

        # Vector from line_start to point
        dx_p = px_rad - x1_rad
        dy_p = py_rad - y1_rad

        # Project point onto line
        dot = dx_p * dx + dy_p * dy
        len_sq = dx * dx + dy * dy

        if len_sq == 0:
            # Line segment is a point
            return self.haversine_distance(px, py, x1, y1)

        param = dot / len_sq

        if param < 0:
            # Closest point is line_start
            closest_x, closest_y = x1_rad, y1_rad
        elif param > 1:
            # Closest point is line_end
            closest_x, closest_y = x2_rad, y2_rad
        else:
            # Closest point is on the line segment
            closest_x = x1_rad + param * dx
            closest_y = y1_rad + param * dy

        # Convert back to degrees for distance calculation
        closest_lat = math.degrees(closest_x)
        closest_lon = math.degrees(closest_y)

        return self.haversine_distance(px, py, closest_lat, closest_lon)

    def get_route_geometry(self, route_id: str) -> List[List[Tuple[float, float]]]:
        """Get route geometry for map-matching (placeholder - would load from GTFS static)."""
        # In a real implementation, this would load route shapes from GTFS static data
        # For now, return some sample route segments for demonstration

        # Sample route geometries (lat, lon pairs)
        sample_routes = {
            "route_1": [
                [(12.9716, 77.5946), (12.9750, 77.6000), (12.9800, 77.6050)],
                [(12.9800, 77.6050), (12.9850, 77.6100), (12.9900, 77.6150)]
            ],
            "route_2": [
                [(12.9500, 77.5800), (12.9550, 77.5850), (12.9600, 77.5900)],
                [(12.9600, 77.5900), (12.9650, 77.5950), (12.9700, 77.6000)]
            ]
        }

        return sample_routes.get(route_id, [])

    def detect_off_route(self, vehicle_data: Dict) -> bool:
        """Advanced off-route detection using map-matching."""
        # Temporarily disabled for MBTA (no static GTFS routes loaded)
        return False

    def calculate_ghost_score(self, vehicle_data: Dict, vehicle_id: str) -> int:
        """Calculate ghost bus score (0-100, higher = more likely ghost)."""
        score = 0

        # Stale data: +40 points
        if self.detect_stale_data(vehicle_data):
            score += 40

        # Stationary: +30 points
        if self.detect_stationary(vehicle_id, (vehicle_data['lat'], vehicle_data['lon'])):
            score += 30

        # Off-route: +30 points
        if self.detect_off_route(vehicle_data):
            score += 30

        # Speed anomalies (too fast or stopped)
        speed = vehicle_data.get('speed', 0)
        if speed > 80 or speed < 0:  # Unrealistic speeds
            score += 20

        return min(score, 100)

    def analyze_vehicle(self, vehicle_data: Dict) -> Dict:
        """Main analysis function - returns vehicle data with ghost detection results."""
        vehicle_id = vehicle_data['vehicle_id']

        # Update history
        self.update_vehicle_history(vehicle_id, vehicle_data)

        # Calculate ghost score
        ghost_score = self.calculate_ghost_score(vehicle_data, vehicle_id)

        # Determine if it's a ghost bus (score > 50)
        is_ghost = ghost_score > 50

        # Add detection results to vehicle data
        enhanced_data = vehicle_data.copy()
        enhanced_data.update({
            'ghost_score': ghost_score,
            'is_ghost': is_ghost,
            'detection_timestamp': time.time(),
            'detection_rules': {
                'stale': self.detect_stale_data(vehicle_data),
                'stationary': self.detect_stationary(vehicle_id, (vehicle_data['lat'], vehicle_data['lon'])),
                'off_route': self.detect_off_route(vehicle_data)
            }
        })

        # Update recurring ghost statistics if we have storage
        try:
            from .storage import get_storage
            storage = get_storage()
            storage.update_recurring_ghost_stats(vehicle_id, ghost_score, is_ghost)

            # Check if this vehicle is a recurring ghost
            recurring_ghosts = storage.get_recurring_ghosts()
            vehicle_recurring = any(rg['vehicle_id'] == vehicle_id for rg in recurring_ghosts)
            enhanced_data['is_recurring_ghost'] = vehicle_recurring

        except Exception as e:
            # Storage might not be available during initialization
            enhanced_data['is_recurring_ghost'] = False
            print(f"⚠️ Storage not available for recurring ghost detection: {e}")

        return enhanced_data

# Global detector instance
_detector = None

def get_detector(redis_client: redis.Redis = None) -> GhostBusDetector:
    """Get or create detector instance."""
    global _detector
    if _detector is None:
        if redis_client is None:
            redis_client = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, decode_responses=True)
        _detector = GhostBusDetector(redis_client)
    return _detector
