"""
Routing service for calculating routes using OpenRouteService API.
"""
import requests
import logging
from typing import Dict, List, Any, Optional, Tuple

from config import Config

logger = logging.getLogger(__name__)


class RoutingService:
    """Service for route calculations and hazard avoidance."""

    @staticmethod
    def calculate_base_route(
        origin: Dict[str, float],
        destination: Dict[str, float],
        profile: str = 'driving-car'
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate a basic route between origin and destination.

        Args:
            origin: {'lat': latitude, 'lng': longitude}
            destination: {'lat': latitude, 'lng': longitude}
            profile: Route profile (driving-car, cycling-regular, foot-walking)

        Returns:
            Route data or None if API call fails
        """
        try:
            if not Config.OPENROUTESERVICE_API_KEY:
                logger.error("OpenRouteService API key not configured")
                return None

            headers = {
                'Authorization': Config.OPENROUTESERVICE_API_KEY,
                'Content-Type': 'application/json'
            }

            # Build route request
            route_data = {
                'coordinates': [
                    [origin['lng'], origin['lat']],
                    [destination['lng'], destination['lat']]
                ],
                'instructions': False,  # We don't need turn-by-turn for now
                'units': 'km',
                'language': 'en'
            }

            logger.info(f"Calculating route from {origin} to {destination}")

            response = requests.post(
                f"{Config.OPENROUTESERVICE_API_BASE}/v2/directions/{profile}",
                headers=headers,
                json=route_data,
                timeout=15
            )
            response.raise_for_status()

            data = response.json()

            # Extract route information
            route_info = data.get('routes', [{}])[0]
            segments = route_info.get('segments', [{}])[0]

            route = {
                'distance': route_info.get('summary', {}).get('distance'),  # meters
                'duration': route_info.get('summary', {}).get('duration'),  # seconds
                'geometry': route_info.get('geometry'),  # encoded polyline
                'coordinates': RoutingService.decode_polyline(
                    route_info.get('geometry', '')
                ),
                'summary': route_info.get('summary', {})
            }

            # Add segment details if available
            if segments:
                route['segments'] = segments

            logger.info(f"Route calculated: {route['distance']:.0f}m, {route['duration']:.0f}s")
            return route

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calculating route: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in route calculation: {e}")
            return None

    @staticmethod
    def decode_polyline(encoded: str) -> List[List[float]]:
        """
        Decode Google polyline format.

        Args:
            encoded: Encoded polyline string

        Returns:
            List of [longitude, latitude] coordinates
        """
        if not encoded:
            return []

        coordinates = []
        index = 0
        lat = 0
        lng = 0

        while index < len(encoded):
            # Decode latitude
            b = 0
            shift = 0
            result = 0

            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break

            lat += ~(result >> 1) if result & 1 else result >> 1

            # Decode longitude
            b = 0
            shift = 0
            result = 0

            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break

            lng += ~(result >> 1) if result & 1 else result >> 1

            coordinates.append([lng * 1e-5, lat * 1e-5])

        return coordinates

    @staticmethod
    def calculate_hazard_aware_route(
        origin: Dict[str, float],
        destination: Dict[str, float],
        hazard_polygons: List[List[List[float]]],
        profile: str = 'driving-car'
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate a route avoiding hazard polygons.

        Args:
            origin: {'lat': latitude, 'lng': longitude}
            destination: {'lat': latitude, 'lng': longitude}
            hazard_polygons: List of polygons to avoid
            profile: Route profile

        Returns:
            Hazard-aware route data or None
        """
        try:
            if not Config.OPENROUTESERVICE_API_KEY:
                logger.error("OpenRouteService API key not configured")
                return None

            headers = {
                'Authorization': Config.OPENROUTESERVICE_API_KEY,
                'Content-Type': 'application/json'
            }

            # Build route request with avoid_polygons
            route_data = {
                'coordinates': [
                    [origin['lng'], origin['lat']],
                    [destination['lng'], destination['lat']]
                ],
                'instructions': False,
                'units': 'km',
                'language': 'en',
                'options': {
                    'avoid_polygons': {
                        'type': 'MultiPolygon',
                        'coordinates': hazard_polygons
                    }
                }
            }

            logger.info(f"Calculating hazard-aware route avoiding {len(hazard_polygons)} polygons")

            response = requests.post(
                f"{Config.OPENROUTESERVICE_API_BASE}/v2/directions/{profile}",
                headers=headers,
                json=route_data,
                timeout=15
            )

            if response.status_code == 400:
                # The API might not support avoid_polygons or polygons might be invalid
                logger.warning("Route with avoid_polygons failed, falling back to base route")
                return RoutingService.calculate_base_route(origin, destination, profile)

            response.raise_for_status()

            data = response.json()
            route_info = data.get('routes', [{}])[0]

            route = {
                'distance': route_info.get('summary', {}).get('distance'),
                'duration': route_info.get('summary', {}).get('duration'),
                'geometry': route_info.get('geometry'),
                'coordinates': RoutingService.decode_polyline(
                    route_info.get('geometry', '')
                ),
                'summary': route_info.get('summary', {}),
                'hazards_avoided': len(hazard_polygons)
            }

            logger.info(f"Hazard-aware route calculated: {route['distance']:.0f}m")
            return route

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calculating hazard-aware route: {e}")
            # Fall back to base route
            return RoutingService.calculate_base_route(origin, destination, profile)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None

    @staticmethod
    def check_route_intersects_hazards(
        route_coordinates: List[List[float]],
        hazard_polygons: List[List[List[float]]]
    ) -> bool:
        """
        Check if a route intersects any hazard polygons.

        Args:
            route_coordinates: List of [lng, lat] coordinates along the route
            hazard_polygons: List of polygons to check

        Returns:
            True if route intersects any hazard polygon
        """
        # Simple implementation: check if any route point is inside any polygon
        # In production, you'd use a proper spatial library like Shapely

        for point in route_coordinates:
            lng, lat = point
            for polygon in hazard_polygons:
                if RoutingService.point_in_polygon(lat, lng, polygon):
                    return True

        return False

    @staticmethod
    def point_in_polygon(lat: float, lng: float, polygon: List[List[float]]) -> bool:
        """
        Check if a point is inside a polygon using ray casting algorithm.

        Args:
            lat: Point latitude
            lng: Point longitude
            polygon: List of [lng, lat] points defining the polygon

        Returns:
            True if point is inside polygon
        """
        if not polygon or len(polygon) < 3:
            return False

        inside = False
        n = len(polygon)

        for i in range(n):
            j = (i + 1) % n
            xi, yi = polygon[i]
            xj, yj = polygon[j]

            # Check if point is between the y-values of the edge
            if ((yi > lat) != (yj > lat)):
                # Calculate x-coordinate of intersection
                x_intersect = xi + (lat - yi) * (xj - xi) / (yj - yi)

                # If intersection is to the right of point, toggle inside/outside
                if lng < x_intersect:
                    inside = not inside

        return inside

    @staticmethod
    def format_route_for_frontend(
        route_data: Dict[str, Any],
        route_type: str = 'base'
    ) -> Dict[str, Any]:
        """
        Format route data for frontend consumption.

        Args:
            route_data: Raw route data from API
            route_type: 'base' or 'adjusted'

        Returns:
            Formatted route data
        """
        if not route_data:
            return {
                'type': route_type,
                'distance_km': 0,
                'duration_min': 0,
                'coordinates': [],
                'available': False
            }

        # Distance is already in kilometers (due to 'units': 'km' in API request)
        distance_km = route_data.get('distance', 0)

        # Convert duration from seconds to minutes
        duration_min = route_data.get('duration', 0) / 60

        return {
            'type': route_type,
            'distance_km': round(distance_km, 2),
            'duration_min': round(duration_min, 1),
            'coordinates': route_data.get('coordinates', []),
            'available': True,
            'summary': route_data.get('summary', {})
        }


if __name__ == '__main__':
    # Test the routing service
    print("Testing routing service...")

    # Test coordinates (Manila to Cebu)
    test_origin = {'lat': 14.5995, 'lng': 120.9842}
    test_destination = {'lat': 10.3157, 'lng': 123.8854}

    # Test base route (will fail without API key, but show structure)
    print(f"\n1. Calculating base route:")
    print(f"   From: {test_origin}")
    print(f"   To: {test_destination}")

    # Test point in polygon
    print("\n2. Testing point-in-polygon:")
    test_polygon = [
        [120.0, 14.0],
        [121.0, 14.0],
        [121.0, 15.0],
        [120.0, 15.0],
        [120.0, 14.0]  # Closing point
    ]
    test_point_inside = (14.5, 120.5)
    test_point_outside = (13.5, 119.5)

    inside_result = RoutingService.point_in_polygon(
        test_point_inside[0], test_point_inside[1], test_polygon
    )
    outside_result = RoutingService.point_in_polygon(
        test_point_outside[0], test_point_outside[1], test_polygon
    )

    print(f"   Point {test_point_inside} inside polygon: {inside_result}")
    print(f"   Point {test_point_outside} inside polygon: {outside_result}")

    # Test route formatting
    print("\n3. Testing route formatting:")
    sample_route = {
        'distance': 5000,  # 5km
        'duration': 900,   # 15 minutes
        'coordinates': [[120.0, 14.0], [120.1, 14.1]]
    }

    formatted = RoutingService.format_route_for_frontend(sample_route)
    print(f"   Formatted: {formatted}")