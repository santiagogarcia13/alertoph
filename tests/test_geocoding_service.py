"""
Unit tests for GeocodingService.
"""
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from services.geocoding_service import GeocodingService, KNOWN_LOCATIONS


class TestGeocodingService:
    """Test geocoding functionality for Philippine locations."""

    def test_geocode_known_location(self):
        """Test exact lookup in known locations."""
        result = GeocodingService.geocode('manila')
        assert result is not None
        assert result['latitude'] == pytest.approx(14.5995, 0.001)
        assert result['longitude'] == pytest.approx(120.9842, 0.001)
        assert 'Manila' in result['name']

    def test_geocode_known_landmark(self):
        """Test landmark lookup (e.g., BGC, MOA, Intramuros)."""
        result = GeocodingService.geocode('bgc')
        assert result is not None
        assert result['latitude'] == pytest.approx(14.5507, 0.001)
        assert result['longitude'] == pytest.approx(121.0465, 0.001)

    def test_geocode_empty_query(self):
        """Test empty or whitespace-only query returns None."""
        assert GeocodingService.geocode('') is None
        assert GeocodingService.geocode('   ') is None

    def test_search_suggestions_known_locations(self):
        """Test suggestions matching known locations."""
        results = GeocodingService.search_suggestions('cebu', limit=5)
        assert len(results) >= 1
        assert any('Cebu' in r['name'] for r in results)

    @patch('requests.get')
    def test_search_nominatim_success(self, mock_get):
        """Test OpenStreetMap Nominatim integration."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'name': 'Barangay Bel-Air',
                'display_name': 'Barangay Bel-Air, Makati, Metro Manila, 1209, Philippines',
                'lat': '14.5614',
                'lon': '121.0289',
                'type': 'administrative'
            }
        ]
        mock_get.return_value = mock_response

        results = GeocodingService._search_nominatim('Barangay Bel-Air', limit=3)
        assert len(results) == 1
        assert results[0]['latitude'] == pytest.approx(14.5614, 0.001)
        assert results[0]['longitude'] == pytest.approx(121.0289, 0.001)
        assert 'Bel-Air' in results[0]['name'] or 'Barangay' in results[0]['name']
