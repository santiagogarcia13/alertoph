"""
Geocoding service for AlertoPH.
Resolves unique place names, landmarks, addresses, and barangays in the Philippines
to precise geographic coordinates.
"""
import logging
import requests
from typing import List, Dict, Any, Optional

from config import Config

logger = logging.getLogger(__name__)

# Known landmark & city coordinates for instant lookup
KNOWN_LOCATIONS = {
    'manila': {'lat': 14.5995, 'lng': 120.9842, 'name': 'Manila', 'region': 'Metro Manila'},
    'quezon city': {'lat': 14.6760, 'lng': 121.0437, 'name': 'Quezon City', 'region': 'Metro Manila'},
    'makati': {'lat': 14.5547, 'lng': 121.0244, 'name': 'Makati', 'region': 'Metro Manila'},
    'taguig': {'lat': 14.5176, 'lng': 121.0509, 'name': 'Taguig', 'region': 'Metro Manila'},
    'pasig': {'lat': 14.5764, 'lng': 121.0851, 'name': 'Pasig', 'region': 'Metro Manila'},
    'bgc': {'lat': 14.5507, 'lng': 121.0465, 'name': 'Bonifacio Global City (BGC)', 'region': 'Taguig, Metro Manila'},
    'bonifacio global city': {'lat': 14.5507, 'lng': 121.0465, 'name': 'Bonifacio Global City', 'region': 'Taguig, Metro Manila'},
    'cebu': {'lat': 10.3157, 'lng': 123.8854, 'name': 'Cebu City', 'region': 'Central Visayas'},
    'cebu city': {'lat': 10.3157, 'lng': 123.8854, 'name': 'Cebu City', 'region': 'Central Visayas'},
    'davao': {'lat': 7.1907, 'lng': 125.4553, 'name': 'Davao City', 'region': 'Davao Region'},
    'davao city': {'lat': 7.1907, 'lng': 125.4553, 'name': 'Davao City', 'region': 'Davao Region'},
    'baguio': {'lat': 16.4023, 'lng': 120.5960, 'name': 'Baguio City', 'region': 'Cordillera'},
    'iloilo': {'lat': 10.7202, 'lng': 122.5621, 'name': 'Iloilo City', 'region': 'Western Visayas'},
    'bacolod': {'lat': 10.6760, 'lng': 122.9509, 'name': 'Bacolod City', 'region': 'Western Visayas'},
    'cagayan de oro': {'lat': 8.4542, 'lng': 124.6319, 'name': 'Cagayan de Oro', 'region': 'Northern Mindanao'},
    'zamboanga': {'lat': 6.9214, 'lng': 122.0790, 'name': 'Zamboanga City', 'region': 'Zamboanga Peninsula'},
    'angeles': {'lat': 15.1450, 'lng': 120.5887, 'name': 'Angeles City', 'region': 'Central Luzon'},
    'pampanga': {'lat': 15.0794, 'lng': 120.6203, 'name': 'Pampanga', 'region': 'Central Luzon'},
    'bataan': {'lat': 14.6707, 'lng': 120.4296, 'name': 'Bataan', 'region': 'Central Luzon'},
    'laguna': {'lat': 14.1667, 'lng': 121.3333, 'name': 'Laguna', 'region': 'Calabarzon'},
    'cavite': {'lat': 14.4791, 'lng': 120.8970, 'name': 'Cavite', 'region': 'Calabarzon'},
    'rizal': {'lat': 14.6500, 'lng': 121.2500, 'name': 'Rizal', 'region': 'Calabarzon'},
    'bulacan': {'lat': 14.7939, 'lng': 120.8795, 'name': 'Bulacan', 'region': 'Central Luzon'},
    'batangas': {'lat': 13.7538, 'lng': 121.0594, 'name': 'Batangas', 'region': 'Calabarzon'},
    'puerto princesa': {'lat': 9.7392, 'lng': 118.7353, 'name': 'Puerto Princesa', 'region': 'Mimaropa'},
    'tacloban': {'lat': 11.2444, 'lng': 125.0039, 'name': 'Tacloban', 'region': 'Eastern Visayas'},
    'naga': {'lat': 13.6218, 'lng': 123.1948, 'name': 'Naga City', 'region': 'Bicol Region'},
    'general santos': {'lat': 6.1164, 'lng': 125.1716, 'name': 'General Santos', 'region': 'Soccsksargen'},
    'bicol': {'lat': 13.4210, 'lng': 123.4137, 'name': 'Bicol', 'region': 'Bicol Region'},
    'mindanao': {'lat': 8.1833, 'lng': 124.1667, 'name': 'Mindanao', 'region': 'Mindanao'},
    'luzon': {'lat': 15.5000, 'lng': 121.0000, 'name': 'Luzon', 'region': 'Luzon'},
    'visayas': {'lat': 11.5000, 'lng': 123.0000, 'name': 'Visayas', 'region': 'Visayas'},
    'sm mall of asia': {'lat': 14.5352, 'lng': 120.9822, 'name': 'SM Mall of Asia', 'region': 'Pasay, Metro Manila'},
    'moa': {'lat': 14.5352, 'lng': 120.9822, 'name': 'SM Mall of Asia', 'region': 'Pasay, Metro Manila'},
    'intramuros': {'lat': 14.5896, 'lng': 120.9747, 'name': 'Intramuros', 'region': 'Manila, Metro Manila'},
    'boracay': {'lat': 11.9674, 'lng': 121.9248, 'name': 'Boracay Island', 'region': 'Malay, Aklan'},
    'mayon volcano': {'lat': 13.2570, 'lng': 123.6850, 'name': 'Mayon Volcano', 'region': 'Albay, Bicol'},
    'taal volcano': {'lat': 14.0093, 'lng': 120.9961, 'name': 'Taal Volcano', 'region': 'Batangas'}
}


class GeocodingService:
    """Service for looking up exact coordinates from location names."""

    @staticmethod
    def geocode(query: str) -> Optional[Dict[str, Any]]:
        """
        Geocode a location query to exact coordinates.

        Args:
            query: Place name, address, landmark, city, etc.

        Returns:
            Dict containing name, display_name, latitude, longitude, region,
            or None if location could not be resolved.
        """
        if not query or not query.strip():
            return None

        clean_query = query.strip()
        query_lower = clean_query.lower()

        # 1. Exact match in known locations dictionary
        if query_lower in KNOWN_LOCATIONS:
            loc = KNOWN_LOCATIONS[query_lower]
            return {
                'name': loc['name'],
                'display_name': f"{loc['name']}, {loc['region']}",
                'latitude': loc['lat'],
                'longitude': loc['lng'],
                'region': loc['region']
            }

        # 2. Try OpenStreetMap Nominatim for highly precise Philippine geocoding
        nominatim_result = GeocodingService._search_nominatim(clean_query, limit=1)
        if nominatim_result:
            return nominatim_result[0]

        # 3. Try OpenWeather Geocoding API
        openweather_result = GeocodingService._search_openweather_geo(clean_query, limit=1)
        if openweather_result:
            return openweather_result[0]

        # 4. Prefix / partial match in known locations
        for key, loc in KNOWN_LOCATIONS.items():
            if query_lower in key or key in query_lower:
                return {
                    'name': loc['name'],
                    'display_name': f"{loc['name']}, {loc['region']}",
                    'latitude': loc['lat'],
                    'longitude': loc['lng'],
                    'region': loc['region']
                }

        return None

    @staticmethod
    def search_suggestions(query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for matching locations and return a list of suggestions.

        Args:
            query: Search query text
            limit: Maximum number of suggestions to return

        Returns:
            List of matching location dictionaries
        """
        if not query or len(query.strip()) < 2:
            return []

        clean_query = query.strip()
        query_lower = clean_query.lower()
        results: List[Dict[str, Any]] = []
        seen_coords = set()

        # Check known locations first
        for key, loc in KNOWN_LOCATIONS.items():
            if query_lower in key:
                coord_key = (round(loc['lat'], 3), round(loc['lng'], 3))
                if coord_key not in seen_coords:
                    seen_coords.add(coord_key)
                    results.append({
                        'name': loc['name'],
                        'display_name': f"{loc['name']}, {loc['region']}",
                        'latitude': loc['lat'],
                        'longitude': loc['lng'],
                        'region': loc['region']
                    })
                    if len(results) >= limit:
                        return results

        # Fetch from Nominatim for rich and precise results
        nominatim_results = GeocodingService._search_nominatim(clean_query, limit=limit)
        for item in nominatim_results:
            coord_key = (round(item['latitude'], 3), round(item['longitude'], 3))
            if coord_key not in seen_coords:
                seen_coords.add(coord_key)
                results.append(item)
                if len(results) >= limit:
                    break

        # Fallback to OpenWeather Geocoding if needed
        if len(results) < limit:
            ow_results = GeocodingService._search_openweather_geo(clean_query, limit=limit - len(results))
            for item in ow_results:
                coord_key = (round(item['latitude'], 3), round(item['longitude'], 3))
                if coord_key not in seen_coords:
                    seen_coords.add(coord_key)
                    results.append(item)

        return results

    @staticmethod
    def _search_nominatim(query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Query OpenStreetMap Nominatim API for locations in the Philippines."""
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': query,
                'format': 'json',
                'countrycodes': 'ph',
                'addressdetails': 1,
                'limit': limit
            }
            headers = {
                'User-Agent': 'AlertoPH-DisasterAdvisorySystem/1.0 (alertoph-app@local)'
            }

            response = requests.get(url, params=params, headers=headers, timeout=6)
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data:
                    display_parts = item.get('display_name', '').split(',')
                    short_name = display_parts[0].strip() if display_parts else item.get('name', query)
                    region = ', '.join([p.strip() for p in display_parts[1:3]]) if len(display_parts) > 1 else 'Philippines'

                    results.append({
                        'name': short_name,
                        'display_name': item.get('display_name', ''),
                        'latitude': float(item['lat']),
                        'longitude': float(item['lon']),
                        'region': region,
                        'type': item.get('type', '')
                    })
                return results
        except Exception as e:
            logger.warning(f"Nominatim geocoding error: {e}")

        return []

    @staticmethod
    def _search_openweather_geo(query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Query OpenWeatherMap Direct Geocoding API."""
        try:
            if not Config.OPENWEATHER_API_KEY:
                return []

            url = "http://api.openweathermap.org/geo/1.0/direct"
            params = {
                'q': f"{query},PH",
                'limit': limit,
                'appid': Config.OPENWEATHER_API_KEY
            }
            response = requests.get(url, params=params, timeout=6)
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data:
                    name = item.get('name', query)
                    state = item.get('state', '')
                    display_name = f"{name}, {state}, Philippines" if state else f"{name}, Philippines"
                    results.append({
                        'name': name,
                        'display_name': display_name,
                        'latitude': float(item['lat']),
                        'longitude': float(item['lon']),
                        'region': state or 'Philippines'
                    })
                return results
        except Exception as e:
            logger.warning(f"OpenWeather geocoding error: {e}")

        return []
