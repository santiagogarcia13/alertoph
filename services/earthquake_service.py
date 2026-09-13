"""
Earthquake service for fetching and processing earthquake data from USGS.
"""
import requests
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from math import radians, cos, sin, asin, sqrt

from config import Config

logger = logging.getLogger(__name__)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees).
    """
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers

    return c * r


def fetch_recent_earthquakes(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: float = 200.0
) -> List[Dict[str, Any]]:
    """
    Fetch recent earthquakes from USGS API.

    Args:
        lat: Latitude of reference point (optional)
        lon: Longitude of reference point (optional)
        radius_km: Search radius in kilometers (default: 200km)

    Returns:
        List of earthquake data dictionaries
    """
    try:
        # Calculate time window
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=Config.EARTHQUAKE_TIME_WINDOW_HOURS)

        # Build USGS API query parameters
        params = {
            'format': 'geojson',
            'starttime': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'endtime': end_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'minmagnitude': 2.0,  # Get all earthquakes, filter later
            'orderby': 'time'
        }

        # If lat/lon provided, use circular search
        if lat and lon:
            params.update({
                'latitude': lat,
                'longitude': lon,
                'maxradiuskm': radius_km
            })
        else:
            # Otherwise, use Philippines bounding box
            params.update({
                'minlatitude': Config.PH_BBOX['minlatitude'],
                'maxlatitude': Config.PH_BBOX['maxlatitude'],
                'minlongitude': Config.PH_BBOX['minlongitude'],
                'maxlongitude': Config.PH_BBOX['maxlongitude']
            })

        logger.info(f"Fetching earthquakes with params: {params}")

        response = requests.get(
            Config.USGS_EARTHQUAKE_API,
            params=params,
            timeout=10
        )
        response.raise_for_status()

        data = response.json()

        if data.get('metadata', {}).get('count', 0) == 0:
            logger.info("No earthquakes found in the specified area/time")
            return []

        earthquakes = []

        for feature in data.get('features', []):
            props = feature.get('properties', {})
            geometry = feature.get('geometry', {})
            coordinates = geometry.get('coordinates', [])

            if not coordinates or len(coordinates) < 3:
                continue

            # USGS coordinates are [longitude, latitude, depth]
            longitude, latitude, depth_km = coordinates

            earthquake = {
                'id': feature.get('id'),
                'magnitude': props.get('mag'),
                'place': props.get('place', 'Unknown location'),
                'time': props.get('time'),  # Unix timestamp in milliseconds
                'updated': props.get('updated'),
                'latitude': latitude,
                'longitude': longitude,
                'depth_km': depth_km,
                'url': props.get('url'),
                'detail': props.get('detail'),
                'distance_km': None
            }

            # Calculate distance if reference point provided
            if lat and lon:
                earthquake['distance_km'] = haversine_distance(
                    lat, lon, latitude, longitude
                )

            earthquakes.append(earthquake)

        # Sort by magnitude (highest first) and filter for significant ones
        significant_earthquakes = [
            eq for eq in earthquakes
            if eq['magnitude'] >= Config.EARTHQUAKE_MAG_THRESHOLD
        ]
        significant_earthquakes.sort(key=lambda x: x['magnitude'], reverse=True)

        logger.info(f"Found {len(significant_earthquakes)} significant earthquakes")
        return significant_earthquakes

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching earthquake data: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing earthquake data: {e}")
        raise


def get_nearest_earthquake(
    lat: float,
    lon: float,
    radius_km: float = 200.0
) -> Optional[Dict[str, Any]]:
    """
    Get the nearest significant earthquake to a location.

    Args:
        lat: Latitude
        lon: Longitude
        radius_km: Search radius in kilometers

    Returns:
        Nearest earthquake data or None
    """
    earthquakes = fetch_recent_earthquakes(lat, lon, radius_km)

    if not earthquakes:
        return None

    # Return the nearest one by distance
    return min(
        earthquakes,
        key=lambda eq: eq.get('distance_km') if eq.get('distance_km') is not None else float('inf')
    )


def is_hazardous_earthquake(earthquake: Dict[str, Any]) -> bool:
    """
    Determine if an earthquake meets hazard criteria.

    Args:
        earthquake: Earthquake data dictionary

    Returns:
        True if earthquake is hazardous
    """
    if not earthquake:
        return False

    magnitude = earthquake.get('magnitude')
    distance_km = earthquake.get('distance_km')

    # Check magnitude threshold
    if magnitude < Config.EARTHQUAKE_MAG_THRESHOLD:
        return False

    # If we have distance information, apply additional criteria
    if distance_km is not None:
        # Stronger earthquakes are hazardous from farther away
        if magnitude >= 6.0:
            hazardous_distance = 100.0  # km
        elif magnitude >= 5.0:
            hazardous_distance = 50.0   # km
        else:
            hazardous_distance = 25.0   # km

        return distance_km <= hazardous_distance

    # If no distance, assume hazardous if above magnitude threshold
    return True


if __name__ == '__main__':
    # Test the earthquake service
    test_lat = 14.5995  # Manila latitude
    test_lon = 120.9842  # Manila longitude

    try:
        print("Testing earthquake service...")
        quakes = fetch_recent_earthquakes(test_lat, test_lon, radius_km=200)
        print(f"Found {len(quakes)} significant earthquakes near Manila:")
        for quake in quakes[:3]:  # Show first 3
            print(f"  Magnitude {quake['magnitude']} at {quake['place']}")
            print(f"  Distance: {quake.get('distance_km', 'N/A')} km")

        nearest = get_nearest_earthquake(test_lat, test_lon)
        if nearest:
            print(f"\nNearest hazardous earthquake: {nearest['place']}")
            print(f"Is hazardous: {is_hazardous_earthquake(nearest)}")
    except Exception as e:
        print(f"Test failed: {e}")