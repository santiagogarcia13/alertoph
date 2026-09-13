"""
Configuration module for AlertoPH.
Loads API keys and settings from environment variables.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration."""

    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    # API Keys
    OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
    OPENROUTESERVICE_API_KEY = os.getenv('OPENROUTESERVICE_API_KEY')

    # API Endpoints
    USGS_EARTHQUAKE_API = 'https://earthquake.usgs.gov/fdsnws/event/1/query'
    OPENWEATHER_API_BASE = 'https://api.openweathermap.org/data/2.5'
    OPENROUTESERVICE_API_BASE = 'https://api.openrouteservice.org'

    # Philippines bounding box for earthquake filtering
    PH_BBOX = {
        'minlatitude': 4.5,
        'maxlatitude': 21.0,
        'minlongitude': 116.0,
        'maxlongitude': 127.0
    }

    # Hazard thresholds
    EARTHQUAKE_MAG_THRESHOLD = 4.5  # Minimum magnitude to flag as hazard
    HEAVY_RAINFALL_THRESHOLD = 7.5  # mm/hr
    HAZARD_BUFFER_KM = 2.0  # Buffer around hazard point

    # Time window for earthquake data (hours)
    EARTHQUAKE_TIME_WINDOW_HOURS = 24

    @staticmethod
    def validate():
        """Validate that required API keys are set."""
        errors = []
        if not Config.OPENWEATHER_API_KEY:
            errors.append('OPENWEATHER_API_KEY not set in .env file')
        if not Config.OPENROUTESERVICE_API_KEY:
            errors.append('OPENROUTESERVICE_API_KEY not set in .env file')

        if errors:
            raise ValueError(
                'Missing required configuration:\n' + '\n'.join(f'  - {e}' for e in errors)
            )
