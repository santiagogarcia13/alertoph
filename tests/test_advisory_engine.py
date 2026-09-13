"""
Unit tests for the advisory engine.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from services.advisory_engine import AdvisoryEngine


class TestAdvisoryEngine:
    """Test advisory engine functionality."""

    def test_earthquake_advice_high_magnitude(self):
        """Test earthquake advice for high magnitude quake."""
        quake_data = {
            'magnitude': 6.5,
            'distance_km': 50,
            'place': 'Test Location'
        }

        advice = AdvisoryEngine.generate_earthquake_advice(quake_data, 'english')
        assert advice['magnitude'] == 6.5
        assert advice['severity'] == 'high'
        assert len(advice['details']) > 0
        assert 'tsunami' in advice['details'][0].lower()

    def test_earthquake_advice_medium_magnitude(self):
        """Test earthquake advice for medium magnitude quake."""
        quake_data = {
            'magnitude': 5.5,
            'distance_km': 30,
            'place': 'Test Location'
        }

        advice = AdvisoryEngine.generate_earthquake_advice(quake_data, 'english')
        assert advice['magnitude'] == 5.5
        assert advice['severity'] in ['medium', 'high']
        assert 'strong shaking' in advice['details'][0].lower()

    def test_earthquake_advice_low_magnitude(self):
        """Test earthquake advice for low magnitude quake."""
        quake_data = {
            'magnitude': 3.5,
            'distance_km': 10,
            'place': 'Test Location'
        }

        advice = AdvisoryEngine.generate_earthquake_advice(quake_data, 'english')
        assert advice['magnitude'] == 3.5
        assert advice['severity'] == 'low'
        assert 'drop' in advice['details'][0].lower()

    def test_earthquake_advice_none(self):
        """Test earthquake advice when no data."""
        advice = AdvisoryEngine.generate_earthquake_advice(None, 'english')
        assert advice['severity'] == 'none'
        assert 'no significant' in advice['summary'].lower()

    def test_weather_advice_heavy_rain(self):
        """Test weather advice for heavy rainfall."""
        weather_data = {
            'temperature': 25.0,
            'rain_1h': 10.0,  # Above threshold
            'wind_speed': 5.0,
            'visibility': 10000,
            'weather': [{'description': 'heavy rain'}]
        }

        advice = AdvisoryEngine.generate_weather_advice(weather_data, 'english')
        assert advice['rainfall_mm_hr'] == 10.0
        assert advice['severity'] in ['medium', 'high']
        assert 'heavy rainfall' in advice['details'][0].lower()

    def test_weather_advice_strong_winds(self):
        """Test weather advice for strong winds."""
        weather_data = {
            'temperature': 25.0,
            'rain_1h': 0,
            'wind_speed': 15.0,  # Gale force
            'visibility': 10000,
            'weather': [{'description': 'windy'}]
        }

        advice = AdvisoryEngine.generate_weather_advice(weather_data, 'english')
        assert advice['wind_speed_mps'] == 15.0
        assert advice['severity'] in ['medium', 'high']
        assert 'strong winds' in advice['details'][0].lower()

    def test_weather_advice_good_weather(self):
        """Test weather advice for good conditions."""
        weather_data = {
            'temperature': 28.0,
            'rain_1h': 0,
            'wind_speed': 2.0,
            'visibility': 10000,
            'weather': [{'description': 'clear sky'}]
        }

        advice = AdvisoryEngine.generate_weather_advice(weather_data, 'english')
        assert advice['severity'] == 'low'
        assert 'safe for travel' in advice['details'][0].lower()

    def test_combined_advisory_multiple_hazards(self):
        """Test combined advisory with multiple hazards."""
        quake_data = {
            'magnitude': 5.5,
            'distance_km': 20,
            'place': 'Test Quake Location'
        }

        weather_data = {
            'temperature': 25.0,
            'rain_1h': 8.5,  # Heavy rain
            'wind_speed': 5.0,
            'visibility': 10000,
            'weather': [{'description': 'heavy rain'}]
        }

        advisory = AdvisoryEngine.generate_combined_advisory(
            quake_data,
            weather_data,
            'english'
        )

        assert advisory['overall_severity'] in ['medium', 'high']
        assert len(advisory['all_advice']) >= 2  # At least earthquake and weather advice
        assert 'earthquake' in advisory
        assert 'weather' in advisory

    def test_filipino_language(self):
        """Test advisory generation in Filipino."""
        quake_data = {
            'magnitude': 5.0,
            'distance_km': 15,
            'place': 'Test Location'
        }

        advice = AdvisoryEngine.generate_earthquake_advice(quake_data, 'filipino')
        assert 'lindol' in advice['summary'].lower() or 'earthquake' in advice['summary'].lower()

    def test_route_advice_no_hazards(self):
        """Test route advice when no hazards."""
        advice = AdvisoryEngine.generate_route_advice(
            hazards_detected=False,
            hazard_count=0,
            hazard_types=[],
            language='english'
        )

        assert advice['recommendation'] == 'proceed'
        assert advice['severity'] == 'none'
        assert 'no hazards' in advice['summary'].lower()

    def test_route_advice_with_hazards(self):
        """Test route advice when hazards detected."""
        advice = AdvisoryEngine.generate_route_advice(
            hazards_detected=True,
            hazard_count=2,
            hazard_types=['earthquake', 'flood'],
            language='english'
        )

        assert advice['recommendation'] in ['avoid', 'proceed_with_caution']
        assert advice['severity'] in ['medium', 'high']
        assert advice['hazard_count'] == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])