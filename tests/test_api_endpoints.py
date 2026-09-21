"""
Integration tests for Flask API endpoints in AlertoPH.
"""
import sys
import os
import json
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestAppEndpoints:
    """Test Flask routes and API responses."""

    def test_index_route(self, client):
        """Test GET / renders HTML successfully."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'AlertoPH' in response.data
        assert b'leaflet' in response.data.lower()

    def test_advisory_missing_params(self, client):
        """Test GET /api/advisory with missing parameters returns 400."""
        response = client.get('/api/advisory')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_advisory_unknown_location(self, client):
        """Test GET /api/advisory with unknown location name returns 400 when geocoding fails."""
        with patch('app.fetch_weather_by_city', return_value=None):
            response = client.get('/api/advisory?location=unknownplace123')
            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data
            assert 'suggested_locations' in data

    def test_advisory_geocoding_fallback(self, client):
        """Test GET /api/advisory with unlisted location resolved by weather geocoding fallback."""
        mock_city_weather = {
            'location': {'name': 'Antipolo', 'latitude': 14.5842, 'longitude': 121.1763},
            'temperature': 27.0,
            'rain_1h': 0,
            'wind_speed': 2.0,
            'visibility': 10000,
            'weather': [{'main': 'Clouds', 'description': 'few clouds', 'icon': '02d'}]
        }
        with patch('app.fetch_weather_by_city', return_value=mock_city_weather), \
             patch('app.get_nearest_earthquake', return_value=None), \
             patch('app.fetch_recent_earthquakes', return_value=[]), \
             patch('app.fetch_current_weather', return_value=mock_city_weather):
            response = client.get('/api/advisory?location=Antipolo')
            assert response.status_code == 200
            data = response.get_json()
            assert data['location']['latitude'] == pytest.approx(14.5842, 0.001)
            assert 'advisory' in data

    def test_advisory_known_location_mocked(self, client):
        """Test GET /api/advisory?location=manila with mocked external services."""
        mock_quake = {
            'id': 'test-1',
            'magnitude': 4.8,
            'place': 'Mindoro, Philippines',
            'latitude': 13.5,
            'longitude': 121.0,
            'distance_km': 120.0,
            'time': 1700000000000,
            'depth_km': 10.0
        }
        mock_weather = {
            'location': {'name': 'Manila', 'latitude': 14.5995, 'longitude': 120.9842},
            'temperature': 29.5,
            'rain_1h': 0,
            'wind_speed': 3.5,
            'visibility': 10000,
            'weather': [{'main': 'Clear', 'description': 'clear sky', 'icon': '01d'}]
        }

        with patch('app.get_nearest_earthquake', return_value=mock_quake), \
             patch('app.fetch_recent_earthquakes', return_value=[mock_quake]), \
             patch('app.fetch_current_weather', return_value=mock_weather):
            response = client.get('/api/advisory?location=manila')
            assert response.status_code == 200
            data = response.get_json()
            assert 'location' in data
            assert 'earthquakes' in data
            assert 'weather' in data
            assert 'advisory' in data
            assert data['location']['latitude'] == pytest.approx(14.5995, 0.001)

    def test_advisory_coordinates(self, client):
        """Test GET /api/advisory with explicit lat and lng."""
        mock_quake = None
        mock_weather = {
            'location': {'name': 'Cebu', 'latitude': 10.3157, 'longitude': 123.8854},
            'temperature': 28.0,
            'rain_1h': 12.0,
            'wind_speed': 8.0,
            'visibility': 8000,
            'weather': [{'main': 'Rain', 'description': 'heavy rain', 'icon': '10d'}]
        }

        with patch('app.get_nearest_earthquake', return_value=mock_quake), \
             patch('app.fetch_recent_earthquakes', return_value=[]), \
             patch('app.fetch_current_weather', return_value=mock_weather):
            response = client.get('/api/advisory?lat=10.3157&lng=123.8854')
            assert response.status_code == 200
            data = response.get_json()
            assert data['advisory']['overall_severity'] in ['medium', 'high']

    def test_hazards_endpoint(self, client):
        """Test GET /api/hazards GeoJSON output."""
        mock_quakes = [
            {'latitude': 14.2, 'longitude': 120.8, 'magnitude': 5.2, 'place': 'Batangas'}
        ]
        mock_weather = {
            'latitude': 14.5995,
            'longitude': 120.9842,
            'rain_1h': 8.5,
            'weather': [{'description': 'heavy rain'}]
        }

        with patch('app.fetch_recent_earthquakes', return_value=mock_quakes), \
             patch('app.fetch_current_weather', return_value=mock_weather), \
             patch('app.is_heavy_rainfall', return_value=True):
            response = client.get('/api/hazards')
            assert response.status_code == 200
            data = response.get_json()
            assert data['type'] == 'FeatureCollection'
            assert 'features' in data
            assert 'metadata' in data
            assert data['metadata']['total_zones'] >= 1

    def test_route_missing_body(self, client):
        """Test POST /api/route with empty body."""
        response = client.post('/api/route', json={})
        assert response.status_code == 400

    def test_route_invalid_coordinates(self, client):
        """Test POST /api/route with invalid coordinate format."""
        response = client.post('/api/route', json={'origin': {'x': 1}, 'destination': {'y': 2}})
        assert response.status_code == 400

    def test_route_calculation_success(self, client):
        """Test POST /api/route with mocked route calculation."""
        mock_base_route = {
            'distance': 15000,
            'duration': 1800,
            'coordinates': [[120.9842, 14.5995], [121.0244, 14.5547]],
            'summary': {'distance': 15.0, 'duration': 1800}
        }

        with patch('services.routing_service.RoutingService.calculate_base_route', return_value=mock_base_route), \
             patch('app.fetch_recent_earthquakes', return_value=[]), \
             patch('app.fetch_current_weather', return_value={'rain_1h': 0}):
            response = client.post('/api/route', json={
                'origin': {'lat': 14.5995, 'lng': 120.9842},
                'destination': {'lat': 14.5547, 'lng': 121.0244}
            })
            assert response.status_code == 200
            data = response.get_json()
            assert 'base_route' in data
            assert data['base_route']['available'] is True
            assert 'hazards' in data
            assert 'advice' in data

    def test_geocode_endpoint_missing_q(self, client):
        """Test GET /api/geocode without q parameter returns 400."""
        response = client.get('/api/geocode')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_geocode_endpoint_valid_query(self, client):
        """Test GET /api/geocode with valid query."""
        response = client.get('/api/geocode?q=bgc')
        assert response.status_code == 200
        data = response.get_json()
        assert 'results' in data
        assert data['count'] >= 1
        assert any('BGC' in r['name'] or 'Bonifacio' in r['name'] for r in data['results'])

    def test_404_handler(self, client):
        """Test non-existent route returns JSON 404."""
        response = client.get('/nonexistent-path')
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
