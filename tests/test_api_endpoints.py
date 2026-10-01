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

    def test_earthquakes_endpoint(self, client):
        """Test GET /api/earthquakes endpoint with min_mag filtering."""
        mock_quakes = [
            {'latitude': 14.2, 'longitude': 120.8, 'magnitude': 4.5, 'place': 'Batangas'},
            {'latitude': 7.1, 'longitude': 125.4, 'magnitude': 2.3, 'place': 'Davao'}
        ]
        with patch('app.fetch_recent_earthquakes', return_value=mock_quakes):
            response = client.get('/api/earthquakes?min_mag=4.0')
            assert response.status_code == 200
            data = response.get_json()
            assert data['count'] == 1
            assert data['earthquakes'][0]['magnitude'] == 4.5

    def test_regional_weather_endpoint(self, client):
        """Test GET /api/weather/regional endpoint."""
        mock_weather = {
            'temperature': 30.0,
            'rain_1h': 8.0,
            'humidity': 75,
            'wind_speed': 4.0,
            'weather': [{'description': 'thunderstorm', 'icon': '11d'}]
        }
        with patch('app.fetch_current_weather', return_value=mock_weather):
            response = client.get('/api/weather/regional')
            assert response.status_code == 200
            data = response.get_json()
            assert 'stations' in data
            assert data['count'] > 0
            assert data['stations'][0]['is_heavy_rain'] is True
            assert data['stations'][0]['pagasa_level'] == 'yellow'

    def test_regional_weather_search_and_filter(self, client):
        """Test GET /api/weather/regional with search and region parameters."""
        mock_weather = {
            'temperature': 28.0,
            'rain_1h': 16.0,
            'humidity': 80,
            'wind_speed': 5.0,
            'weather': [{'description': 'heavy rain', 'icon': '10d'}]
        }
        with patch('app.fetch_current_weather', return_value=mock_weather):
            # Test search parameter for Siargao
            res_search = client.get('/api/weather/regional?search=Siargao')
            assert res_search.status_code == 200
            data_search = res_search.get_json()
            assert data_search['count'] >= 1
            assert any('Siargao' in s['name'] for s in data_search['stations'])
            assert data_search['stations'][0]['pagasa_level'] == 'orange'

            # Test region parameter for Visayas
            res_reg = client.get('/api/weather/regional?region=Visayas')
            assert res_reg.status_code == 200
            data_reg = res_reg.get_json()
            assert data_reg['count'] >= 1
            assert all(s['region'] == 'Visayas' for s in data_reg['stations'])
            assert any('Boracay' in s['name'] for s in data_reg['stations'])

            # Test region parameter for Islands
            res_islands = client.get('/api/weather/regional?region=Islands')
            assert res_islands.status_code == 200
            data_islands = res_islands.get_json()
            assert data_islands['count'] >= 5
            assert any('Batanes' in s['name'] or 'Basco' in s['name'] for s in data_islands['stations'])
            assert any('El Nido' in s['name'] for s in data_islands['stations'])
            assert any('Siargao' in s['name'] for s in data_islands['stations'])

            # Test alert_only parameter
            res_alert = client.get('/api/weather/regional?alert_only=true')
            assert res_alert.status_code == 200
            data_alert = res_alert.get_json()
            assert data_alert['count'] > 0
            assert all(s['is_heavy_rain'] or s['rain_1h'] >= 7.5 for s in data_alert['stations'])

    def test_regional_weather_small_municipalities(self, client):
        """Test that small municipalities and remote tourist spots exist in stations list."""
        mock_weather = {
            'temperature': 24.0,
            'rain_1h': 1.0,
            'humidity': 70,
            'wind_speed': 2.0,
            'weather': [{'description': 'scattered clouds', 'icon': '03d'}]
        }
        with patch('app.fetch_current_weather', return_value=mock_weather):
            response = client.get('/api/weather/regional')
            assert response.status_code == 200
            data = response.get_json()
            station_names = [s['name'] for s in data['stations']]

            # Check small municipalities / tourist gems
            assert any('Sagada' in name for name in station_names)
            assert any('Baler' in name for name in station_names)
            assert any('Dingalan' in name for name in station_names)
            assert any('Pagudpud' in name for name in station_names)
            assert any('El Nido' in name for name in station_names)
            assert any('Coron' in name for name in station_names)
            assert any('Siquijor' in name for name in station_names)
            assert any('Camiguin' in name for name in station_names)

    def test_pagasa_warning_classification(self):
        """Test PAGASA rainfall warning levels helper."""
        from app import get_pagasa_warning_level
        assert get_pagasa_warning_level(0.5)['level'] == 'light'
        assert get_pagasa_warning_level(4.0)['level'] == 'moderate'
        assert get_pagasa_warning_level(8.0)['level'] == 'yellow'
        assert get_pagasa_warning_level(18.0)['level'] == 'orange'
        assert get_pagasa_warning_level(35.0)['level'] == 'red'

    def test_404_handler(self, client):
        """Test non-existent route returns JSON 404."""
        response = client.get('/nonexistent-path')
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
