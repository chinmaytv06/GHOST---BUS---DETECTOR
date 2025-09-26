import pytest
import time
import math
from unittest.mock import Mock, MagicMock
import sys
sys.path.append('.')
from app.detector import GhostBusDetector

class MockRedis:
    """Mock Redis client for testing."""
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

class TestGhostBusDetector:

    @pytest.fixture
    def mock_redis(self):
        return MockRedis()

    @pytest.fixture
    def detector(self, mock_redis):
        return GhostBusDetector(mock_redis)

    def test_haversine_distance(self, detector):
        """Test distance calculation between two points."""
        # Test same point
        distance = detector.haversine_distance(0, 0, 0, 0)
        assert distance == 0

        # Test known distance (New York to London approx 5570 km)
        nyc_lat, nyc_lon = 40.7128, -74.0060
        london_lat, london_lon = 51.5074, -0.1278
        distance = detector.haversine_distance(nyc_lat, nyc_lon, london_lat, london_lon)
        assert 5500 < distance < 5700  # Approximate range

        # Test small distance
        distance = detector.haversine_distance(12.9716, 77.5946, 12.9717, 77.5947)
        assert distance < 0.02  # Less than 20 meters

    def test_detect_stale_data(self, detector):
        """Test stale data detection."""
        current_time = time.time()

        # Fresh data
        fresh_data = {'timestamp': current_time}
        assert not detector.detect_stale_data(fresh_data)

        # Stale data (older than 5 minutes)
        stale_data = {'timestamp': current_time - 400}  # 400 seconds ago
        assert detector.detect_stale_data(stale_data)

        # No timestamp
        no_timestamp = {}
        assert detector.detect_stale_data(no_timestamp)

    def test_detect_stationary(self, detector, mock_redis):
        """Test stationary detection."""
        vehicle_id = "test_bus"

        # No history
        current_pos = (12.9716, 77.5946)
        assert not detector.detect_stationary(vehicle_id, current_pos)

        # Add some history at same location
        base_time = time.time() - 900  # 15 minutes ago
        for i in range(5):
            historical_data = {
                'lat': 12.9716,
                'lon': 77.5946,
                'timestamp': base_time + (i * 180)  # Every 3 minutes
            }
            detector.update_vehicle_history(vehicle_id, historical_data)

        # Should detect as stationary
        assert detector.detect_stationary(vehicle_id, current_pos)

        # Test with different locations (not stationary)
        moving_vehicle = "moving_bus"
        for i in range(3):
            historical_data = {
                'lat': 12.9716 + i * 0.001,  # Moving
                'lon': 77.5946 + i * 0.001,
                'timestamp': base_time + (i * 180)
            }
            detector.update_vehicle_history(moving_vehicle, historical_data)

        assert not detector.detect_stationary(moving_vehicle, (12.9716 + 0.003, 77.5946 + 0.003))

    def test_detect_off_route(self, detector):
        """Test off-route detection."""
        # Within bounds (Bangalore area)
        on_route = {'lat': 12.95, 'lon': 77.60}
        assert not detector.detect_off_route(on_route)

        # Outside bounds
        off_route = {'lat': 13.08, 'lon': 80.27}  # Chennai coordinates
        assert detector.detect_off_route(off_route)

        # Edge cases
        edge_case = {'lat': 12.7999, 'lon': 77.3999}  # Just outside bounds
        assert detector.detect_off_route(edge_case)

    def test_calculate_ghost_score(self, detector, mock_redis):
        """Test ghost score calculation."""
        vehicle_id = "test_vehicle"

        # Normal vehicle
        normal_data = {
            'vehicle_id': vehicle_id,
            'lat': 12.9716,
            'lon': 77.5946,
            'timestamp': time.time(),
            'speed': 25
        }
        score = detector.calculate_ghost_score(normal_data, vehicle_id)
        assert score == 0

        # Stale vehicle
        stale_data = normal_data.copy()
        stale_data['timestamp'] = time.time() - 400
        score = detector.calculate_ghost_score(stale_data, vehicle_id)
        assert score == 40

        # Stationary vehicle
        # Add stationary history
        base_time = time.time() - 900
        for i in range(5):
            historical_data = {
                'lat': 12.9716,
                'lon': 77.5946,
                'timestamp': base_time + (i * 180)
            }
            detector.update_vehicle_history(vehicle_id, historical_data)

        stationary_data = normal_data.copy()
        score = detector.calculate_ghost_score(stationary_data, vehicle_id)
        assert score == 30

        # Off-route vehicle
        off_route_data = {
            'vehicle_id': vehicle_id,
            'lat': 13.08,  # Outside bounds
            'lon': 80.27,
            'timestamp': time.time(),
            'speed': 20
        }
        score = detector.calculate_ghost_score(off_route_data, vehicle_id)
        assert score == 30

        # High speed anomaly
        speed_anomaly = normal_data.copy()
        speed_anomaly['speed'] = 90  # Too fast
        score = detector.calculate_ghost_score(speed_anomaly, vehicle_id)
        assert score == 20

        # Combined factors (stale + stationary + off-route)
        ghost_data = {
            'vehicle_id': vehicle_id,
            'lat': 13.08,
            'lon': 80.27,
            'timestamp': time.time() - 400,
            'speed': 0
        }
        score = detector.calculate_ghost_score(ghost_data, vehicle_id)
        assert score == 100  # Should be capped at 100

    def test_analyze_vehicle(self, detector, mock_redis):
        """Test full vehicle analysis."""
        vehicle_data = {
            'vehicle_id': 'test_bus',
            'trip_id': 'trip_001',
            'route_id': 'route_42',
            'lat': 12.9716,
            'lon': 77.5946,
            'timestamp': time.time(),
            'speed': 25,
            'bearing': 90
        }

        result = detector.analyze_vehicle(vehicle_data)

        # Check that all expected fields are present
        assert 'ghost_score' in result
        assert 'is_ghost' in result
        assert 'detection_timestamp' in result
        assert 'detection_rules' in result

        # Check detection rules structure
        rules = result['detection_rules']
        assert 'stale' in rules
        assert 'stationary' in rules
        assert 'off_route' in rules

        # For normal vehicle, should not be ghost
        assert result['is_ghost'] == False
        assert result['ghost_score'] == 0

    def test_edge_cases(self, detector, mock_redis):
        """Test edge cases and error handling."""
        # Empty vehicle data
        empty_data = {}
        with pytest.raises(KeyError):
            detector.analyze_vehicle(empty_data)

        # Missing required fields
        incomplete_data = {'vehicle_id': 'test'}
        with pytest.raises(KeyError):
            detector.analyze_vehicle(incomplete_data)

        # Invalid coordinates
        invalid_coords = {
            'vehicle_id': 'test',
            'lat': 'invalid',
            'lon': 77.5946,
            'timestamp': time.time(),
            'speed': 25
        }
        with pytest.raises(TypeError):
            detector.haversine_distance(invalid_coords['lat'], invalid_coords['lon'], 0, 0)

        # Negative speed
        negative_speed = {
            'vehicle_id': 'test',
            'lat': 12.9716,
            'lon': 77.5946,
            'timestamp': time.time(),
            'speed': -5
        }
        score = detector.calculate_ghost_score(negative_speed, 'test')
        assert score == 20  # Speed anomaly

if __name__ == "__main__":
    pytest.main([__file__])
