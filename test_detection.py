#!/usr/bin/env python3
"""
Standalone test script for Ghost Bus Detection
Tests the detection logic without requiring Redis/WebSocket
"""

import time
import json
from backend.app.detector import GhostBusDetector

def simulate_vehicle_data():
    """Generate test vehicle data including normal and ghost buses"""
    vehicles = [
        {
            "vehicle_id": "bus_001",
            "trip_id": "trip_001",
            "route_id": "route_42",
            "lat": 12.9716,
            "lon": 77.5946,
            "timestamp": time.time(),
            "speed": 25,
            "bearing": 90
        },
        {
            "vehicle_id": "bus_002",
            "trip_id": "trip_002",
            "route_id": "route_15",
            "lat": 12.9750,
            "lon": 77.6000,
            "timestamp": time.time(),
            "speed": 15,
            "bearing": 45
        },
        {
            "vehicle_id": "ghost_stationary",  # Stationary ghost bus
            "trip_id": "trip_ghost1",
            "route_id": "route_99",
            "lat": 12.9800,
            "lon": 77.6100,
            "timestamp": time.time() - 800,  # 13 minutes ago (stale + stationary)
            "speed": 0,
            "bearing": 0
        },
        {
            "vehicle_id": "ghost_off_route",  # Off-route ghost bus
            "trip_id": "trip_ghost2",
            "route_id": "route_88",
            "lat": 13.0827,  # Chennai coordinates (way off route)
            "lon": 80.2707,
            "timestamp": time.time(),
            "speed": 20,
            "bearing": 180
        }
    ]
    return vehicles

def test_detection():
    """Test the ghost bus detection system"""
    print("🚌 Ghost Bus Detection Test")
    print("=" * 50)

    # Create a mock Redis client (in-memory for testing)
    class MockRedis:
        def __init__(self):
            self.data = {}

        def hmset(self, key, mapping):
            self.data[key] = mapping

        def expire(self, key, ttl):
            pass

        def lrange(self, key, start, end):
            return self.data.get(key, [])

        def lpush(self, key, value):
            if key not in self.data:
                self.data[key] = []
            self.data[key].append(value)

        def ltrim(self, key, start, end):
            if key in self.data:
                self.data[key] = self.data[key][start:end+1]

    # Initialize detector with mock Redis
    mock_redis = MockRedis()
    detector = GhostBusDetector(mock_redis)

    # Test vehicles
    test_vehicles = simulate_vehicle_data()

    print(f"Testing {len(test_vehicles)} vehicles...\n")

    # First, simulate some historical data for the stationary ghost bus
    print("📝 Simulating historical data for stationary detection...")
    stationary_vehicle = test_vehicles[2]  # ghost_stationary

    # Add 5 historical positions at the same location over 15 minutes
    base_time = time.time() - 900  # 15 minutes ago
    for i in range(5):
        historical_data = stationary_vehicle.copy()
        historical_data['timestamp'] = base_time + (i * 180)  # Every 3 minutes
        detector.update_vehicle_history(stationary_vehicle['vehicle_id'], historical_data)

    print("✅ Historical data added\n")

    for i, vehicle in enumerate(test_vehicles, 1):
        print(f"Vehicle {i}: {vehicle['vehicle_id']}")

        # Run detection
        result = detector.analyze_vehicle(vehicle)

        # Display results
        ghost_score = result['ghost_score']
        is_ghost = result['is_ghost']

        if is_ghost:
            status = "👻 GHOST BUS"
            color = "🔴"
        elif ghost_score > 0:
            status = "⚠️  MONITORING"
            color = "🟡"
        else:
            status = "✅ NORMAL"
            color = "🟢"

        print(f"  Status: {color} {status}")
        print(f"  Ghost Score: {ghost_score}/100")
        print(f"  Location: ({vehicle['lat']:.4f}, {vehicle['lon']:.4f})")
        print(f"  Speed: {vehicle['speed']} m/s")

        # Show detection rules that triggered
        rules = result['detection_rules']
        triggered_rules = [rule for rule, triggered in rules.items() if triggered]
        if triggered_rules:
            print(f"  Triggered Rules: {', '.join(triggered_rules)}")

        print()

    # Summary
    ghost_count = sum(1 for v in test_vehicles if detector.analyze_vehicle(v)['is_ghost'])
    print("📊 Summary:")
    print(f"  Total Vehicles: {len(test_vehicles)}")
    print(f"  Ghost Buses: {ghost_count}")
    print(f"  Normal Buses: {len(test_vehicles) - ghost_count}")
    print(f"  Ghost Percentage: {(ghost_count / len(test_vehicles)) * 100:.1f}%")

if __name__ == "__main__":
    test_detection()
