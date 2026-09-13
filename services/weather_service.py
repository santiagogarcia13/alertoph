"""
Weather service for fetching and processing weather data from OpenWeatherMap.
"""
import requests
import logging
from typing import Dict, Any, Optional, Tuple

from config import Config

logger = logging.getLogger(__name__)


def fetch_current_weather(
    lat: float,
    lon: float
) -> Optional[Dict[str, Any]]:
    """
    Fetch current weather data from OpenWeatherMap.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Weather data dictionary or None if API call fails
    """
    try:
        if not Config.OPENWEATHER_API_KEY:
            logger.error("OpenWeatherMap API key not configured")
            return None

        # Build API request
        params = {
            'lat': lat,
            'lon': lon,
            'appid': Config.OPENWEATHER_API_KEY,
            'units': 'metric',  # Use metric units (Celsius, mm, m/s)
            'exclude': 'minutely,hourly,daily'  # We only need current weather
        }

        logger.info(f"Fetching weather for coordinates: {lat}, {lon}")

        response = requests.get(
            f"{Config.OPENWEATHER_API_BASE}/weather",
            params=params,
            timeout=10
        )
        response.raise_for_status()

        data = response.json()

        # Extract relevant weather information
        weather_data = {
            'location': {
                'name': data.get('name', 'Unknown location'),
                'country': data.get('sys', {}).get('country', ''),
                'latitude': data['coord']['lat'],
                'longitude': data['coord']['lon']
            },
            'temperature': data['main']['temp'],
            'feels_like': data['main']['feels_like'],
            'humidity': data['main']['humidity'],
            'pressure': data['main']['pressure'],
            'wind_speed': data['wind']['speed'],  # m/s
            'wind_direction': data['wind'].get('deg', 0),
            'cloudiness': data['clouds']['all'],  # percentage
            'rain_1h': data.get('rain', {}).get('1h', 0),  # mm in last hour
            'rain_3h': data.get('rain', {}).get('3h', 0),  # mm in last 3 hours
            'snow_1h': data.get('snow', {}).get('1h', 0),
            'weather': [],
            'visibility': data.get('visibility', 10000),  # meters
            'timestamp': data['dt']
        }

        # Process weather conditions
        for weather in data['weather']:
            weather_data['weather'].append({
                'main': weather['main'],
                'description': weather['description'],
                'icon': weather['icon']
            })

        # Process alerts if available
        if 'alerts' in data:
            weather_data['alerts'] = data['alerts']

        logger.info(f"Weather fetched: {weather_data['location']['name']}")
        return weather_data

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching weather data: {e}")
        # Return a minimal error response
        return {
            'location': {'name': 'Unknown', 'latitude': lat, 'longitude': lon},
            'temperature': None,
            'humidity': None,
            'wind_speed': None,
            'rain_1h': 0,
            'weather': [{'main': 'Unknown', 'description': 'Data unavailable'}],
            'error': str(e),
            'timestamp': None
        }
    except Exception as e:
        logger.error(f"Unexpected error processing weather data: {e}")
        return None


def fetch_weather_by_city(
    city: str,
    country_code: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Fetch current weather by city name.

    Args:
        city: City name
        country_code: Optional country code (e.g., 'PH' for Philippines)

    Returns:
        Weather data dictionary or None
    """
    try:
        if not Config.OPENWEATHER_API_KEY:
            logger.error("OpenWeatherMap API key not configured")
            return None

        query = city
        if country_code:
            query = f"{city},{country_code}"

        params = {
            'q': query,
            'appid': Config.OPENWEATHER_API_KEY,
            'units': 'metric'
        }

        logger.info(f"Fetching weather for city: {query}")

        response = requests.get(
            f"{Config.OPENWEATHER_API_BASE}/weather",
            params=params,
            timeout=10
        )
        response.raise_for_status()

        data = response.json()
        return fetch_current_weather(data['coord']['lat'], data['coord']['lon'])

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching weather by city: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None


def is_heavy_rainfall(weather_data: Dict[str, Any]) -> bool:
    """
    Check if current weather indicates heavy rainfall.

    Args:
        weather_data: Weather data dictionary

    Returns:
        True if rainfall exceeds threshold
    """
    if not weather_data:
        return False

    # Check rainfall in last hour
    rainfall_1h = weather_data.get('rain_1h', 0)
    return rainfall_1h >= Config.HEAVY_RAINFALL_THRESHOLD


def get_wind_category(wind_speed_mps: float) -> str:
    """
    Categorize wind speed according to Beaufort scale.

    Args:
        wind_speed_mps: Wind speed in meters per second

    Returns:
        Wind category description
    """
    if wind_speed_mps < 0.5:
        return 'Calm'
    elif wind_speed_mps < 3.3:
        return 'Light breeze'
    elif wind_speed_mps < 5.5:
        return 'Gentle breeze'
    elif wind_speed_mps < 7.9:
        return 'Moderate breeze'
    elif wind_speed_mps < 10.7:
        return 'Fresh breeze'
    elif wind_speed_mps < 13.8:
        return 'Strong breeze'
    elif wind_speed_mps < 17.1:
        return 'Near gale'
    elif wind_speed_mps < 20.7:
        return 'Gale'
    elif wind_speed_mps < 24.4:
        return 'Strong gale'
    elif wind_speed_mps < 28.4:
        return 'Storm'
    elif wind_speed_mps < 32.6:
        return 'Violent storm'
    else:
        return 'Hurricane force'


def get_weather_summary(weather_data: Dict[str, Any]) -> str:
    """
    Generate a human-readable weather summary.

    Args:
        weather_data: Weather data dictionary

    Returns:
        Weather summary string
    """
    if not weather_data or 'error' in weather_data:
        return "Weather data unavailable"

    try:
        weather_conditions = weather_data['weather'][0]['description'].title()
        temp = weather_data['temperature']
        rainfall = weather_data.get('rain_1h', 0)
        wind_speed = weather_data.get('wind_speed', 0)

        summary = f"{weather_conditions}, {temp:.1f}°C"

        if rainfall > 0:
            summary += f", {rainfall:.1f} mm/hr rain"

        wind_category = get_wind_category(wind_speed)
        if wind_category != 'Calm' and wind_category != 'Light breeze':
            summary += f", {wind_category.lower()}"

        return summary
    except Exception:
        return "Weather data format error"


def is_hazardous_weather(weather_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Determine if weather conditions are hazardous.

    Args:
        weather_data: Weather data dictionary

    Returns:
        Tuple of (is_hazardous, hazard_description)
    """
    if not weather_data or 'error' in weather_data:
        return False, "Weather data unavailable"

    hazards = []

    # Check heavy rainfall
    if is_heavy_rainfall(weather_data):
        rainfall = weather_data['rain_1h']
        hazards.append(f"Heavy rainfall: {rainfall:.1f} mm/hr")

    # Check strong winds (above 13.8 m/s is near gale)
    wind_speed = weather_data.get('wind_speed', 0)
    if wind_speed >= 13.8:
        hazards.append(f"Strong winds: {wind_speed:.1f} m/s")

    # Check low visibility (less than 1000 meters)
    visibility = weather_data.get('visibility', 10000)
    if visibility < 1000:
        hazards.append(f"Low visibility: {visibility} meters")

    # Check extreme temperature (optional)
    temp = weather_data.get('temperature')
    if temp and (temp > 35 or temp < 15):  # Adjust for Philippines climate
        hazards.append(f"Extreme temperature: {temp:.1f}°C")

    if hazards:
        return True, "; ".join(hazards)

    return False, "No significant weather hazards detected"


if __name__ == '__main__':
    # Test the weather service
    test_lat = 14.5995  # Manila
    test_lon = 120.9842

    print("Testing weather service...")
    weather = fetch_current_weather(test_lat, test_lon)

    if weather:
        print(f"Weather for {weather['location']['name']}:")
        print(f"  Temperature: {weather['temperature']}°C")
        print(f"  Conditions: {weather['weather'][0]['description']}")
        print(f"  Rainfall (1h): {weather.get('rain_1h', 0)} mm")
        print(f"  Wind speed: {weather.get('wind_speed', 0)} m/s")

        print(f"\nWeather summary: {get_weather_summary(weather)}")

        is_hazardous, hazard_desc = is_hazardous_weather(weather)
        print(f"Hazardous weather: {is_hazardous}")
        if is_hazardous:
            print(f"Hazard description: {hazard_desc}")

        print(f"\nHeavy rainfall check: {is_heavy_rainfall(weather)}")
    else:
        print("Failed to fetch weather data")