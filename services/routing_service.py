"""
Routing service for calculating routes using OpenRouteService API with automatic OSRM fallback.
"""
import requests
import logging
import math
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
        Tries OpenRouteService first (if key configured), then falls back to OSRM.

        Args:
            origin: {'lat': latitude, 'lng': longitude}
            destination: {'lat': latitude, 'lng': longitude}
            profile: Route profile (driving-car, cycling-regular, foot-walking)

        Returns:
            Route data or None if all providers fail
        """
        # 1. Try OpenRouteService if API key configured
        if Config.OPENROUTESERVICE_API_KEY:
            try:
                headers = {
                    'Authorization': Config.OPENROUTESERVICE_API_KEY,
                    'Content-Type': 'application/json'
                }
                route_data = {
                    'coordinates': [
                        [origin['lng'], origin['lat']],
                        [destination['lng'], destination['lat']]
                    ],
                    'instructions': False,
                    'units': 'km',
                    'language': 'en'
                }

                logger.info(f"Calculating route via OpenRouteService: {origin} -> {destination}")
                response = requests.post(
                    f"{Config.OPENROUTESERVICE_API_BASE}/v2/directions/{profile}",
                    headers=headers,
                    json=route_data,
                    timeout=12
                )
                if response.status_code == 200:
                    data = response.json()
                    route_info = data.get('routes', [{}])[0]
                    segments = route_info.get('segments', [{}])[0]
                    route = {
                        'distance': route_info.get('summary', {}).get('distance', 0),  # km
                        'duration': route_info.get('summary', {}).get('duration', 0),  # seconds
                        'geometry': route_info.get('geometry'),
                        'coordinates': RoutingService.decode_polyline(route_info.get('geometry', '')),
                        'summary': route_info.get('summary', {})
                    }
                    if segments:
                        route['segments'] = segments
                    logger.info(f"ORS Route calculated: {route['distance']:.1f} km, {route['duration']:.0f}s")
                    return route
                else:
                    logger.warning(f"ORS request returned status {response.status_code}, falling back to OSRM")
            except Exception as e:
                logger.warning(f"ORS route error ({e}), falling back to OSRM")

        # 2. Free Public OSRM Fallback (Zero API Key Required)
        return RoutingService._calculate_osrm_route(origin, destination)

    @staticmethod
    def _calculate_osrm_route(
        origin: Dict[str, float],
        destination: Dict[str, float],
        waypoints: Optional[List[List[float]]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate route using Open Source Routing Machine (OSRM) public API.

        Args:
            origin: {'lat': lat, 'lng': lng}
            destination: {'lat': lat, 'lng': lng}
            waypoints: Optional list of [lat, lng] detour points

        Returns:
            Formatted route dictionary
        """
        try:
            if waypoints and len(waypoints) > 0:
                wp_coords = ';'.join([f"{w[1]:.5f},{w[0]:.5f}" for w in waypoints])
                coords_str = f"{origin['lng']:.5f},{origin['lat']:.5f};{wp_coords};{destination['lng']:.5f},{destination['lat']:.5f}"
            else:
                coords_str = f"{origin['lng']:.5f},{origin['lat']:.5f};{destination['lng']:.5f},{destination['lat']:.5f}"

            url = f"https://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
            logger.info(f"Calculating route via OSRM fallback: {url}")

            response = requests.get(url, timeout=12)
            if response.status_code == 200:
                data = response.json()
                if data.get('routes') and len(data['routes']) > 0:
                    primary_route = data['routes'][0]
                    dist_km = primary_route.get('distance', 0) / 1000.0
                    dur_sec = primary_route.get('duration', 0)
                    coords = primary_route.get('geometry', {}).get('coordinates', [])

                    return {
                        'distance': dist_km,
                        'duration': dur_sec,
                        'coordinates': coords,
                        'summary': {
                            'distance': dist_km,
                            'duration': dur_sec
                        }
                    }

            # 3. Geometric direct path fallback if network fails
            return RoutingService._generate_geometric_route(origin, destination, waypoints)

        except Exception as e:
            logger.error(f"OSRM routing failed: {e}")
            return RoutingService._generate_geometric_route(origin, destination, waypoints)

    @staticmethod
    def _generate_geometric_route(
        origin: Dict[str, float],
        destination: Dict[str, float],
        waypoints: Optional[List[List[float]]] = None
    ) -> Dict[str, Any]:
        """
        Generate an interpolated route when external routing services are unreachable.
        """
        all_pts = [[origin['lat'], origin['lng']]]
        if waypoints:
            all_pts.extend(waypoints)
        all_pts.append([destination['lat'], destination['lng']])

        coords = []
        total_dist_km = 0.0

        for i in range(len(all_pts) - 1):
            p1 = all_pts[i]
            p2 = all_pts[i + 1]
            steps = 15
            for s in range(steps):
                t = s / steps
                lat = p1[0] + (p2[0] - p1[0]) * t
                lng = p1[1] + (p2[1] - p1[1]) * t
                coords.append([lng, lat])

            # Great circle approximation
            dlat = math.radians(p2[0] - p1[0])
            dlng = math.radians(p2[1] - p1[1])
            a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(p1[0])) * math.cos(math.radians(p2[0])) * math.sin(dlng / 2) ** 2
            total_dist_km += 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        coords.append([destination['lng'], destination['lat']])
        dur_sec = (total_dist_km / 40.0) * 3600.0  # Approx 40 km/h avg speed

        return {
            'distance': total_dist_km,
            'duration': dur_sec,
            'coordinates': coords,
            'summary': {
                'distance': total_dist_km,
                'duration': dur_sec
            }
        }

    @staticmethod
    def calculate_hazard_aware_route(
        origin: Dict[str, float],
        destination: Dict[str, float],
        hazard_polygons: List[List[List[float]]],
        profile: str = 'driving-car'
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate a route avoiding hazard polygons.
        """
        # 1. Try OpenRouteService with avoid_polygons if API key configured
        if Config.OPENROUTESERVICE_API_KEY:
            try:
                headers = {
                    'Authorization': Config.OPENROUTESERVICE_API_KEY,
                    'Content-Type': 'application/json'
                }
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

                logger.info(f"Calculating hazard-aware route avoiding {len(hazard_polygons)} polygons via ORS")
                response = requests.post(
                    f"{Config.OPENROUTESERVICE_API_BASE}/v2/directions/{profile}",
                    headers=headers,
                    json=route_data,
                    timeout=15
                )

                if response.status_code == 200:
                    data = response.json()
                    route_info = data.get('routes', [{}])[0]
                    return {
                        'distance': route_info.get('summary', {}).get('distance', 0),
                        'duration': route_info.get('summary', {}).get('duration', 0),
                        'geometry': route_info.get('geometry'),
                        'coordinates': RoutingService.decode_polyline(route_info.get('geometry', '')),
                        'summary': route_info.get('summary', {}),
                        'hazards_avoided': len(hazard_polygons)
                    }
            except Exception as e:
                logger.warning(f"Hazard avoidance via ORS failed: {e}")

        # 2. Compute detour waypoint avoiding hazard centroids
        detour_waypoints = RoutingService._compute_detour_waypoints(origin, destination, hazard_polygons)
        adjusted = RoutingService._calculate_osrm_route(origin, destination, waypoints=detour_waypoints)
        if adjusted:
            adjusted['hazards_avoided'] = len(hazard_polygons)
            return adjusted

        # Fallback to base route if detour calculation fails
        return RoutingService.calculate_base_route(origin, destination, profile)

    @staticmethod
    def _compute_detour_waypoints(
        origin: Dict[str, float],
        destination: Dict[str, float],
        hazard_polygons: List[List[List[float]]]
    ) -> List[List[float]]:
        """
        Compute safe waypoint offsets around hazard polygons.
        """
        waypoints = []
        for poly in hazard_polygons:
            if not poly or len(poly) < 3:
                continue
            # Calculate polygon centroid
            avg_lng = sum(pt[0] for pt in poly) / len(poly)
            avg_lat = sum(pt[1] for pt in poly) / len(poly)

            # Calculate perpendicular offset from origin-destination line
            dx = destination['lng'] - origin['lng']
            dy = destination['lat'] - origin['lat']
            length = math.sqrt(dx * dx + dy * dy) or 1.0

            # Unit normal vector
            nx = -dy / length
            ny = dx / length

            # 0.08 deg offset (~8-9 km buffer)
            detour_lat = avg_lat + ny * 0.08
            detour_lng = avg_lng + nx * 0.08
            waypoints.append([detour_lat, detour_lng])

        return waypoints

    @staticmethod
    def decode_polyline(encoded: str) -> List[List[float]]:
        """
        Decode Google polyline format.
        """
        if not encoded:
            return []

        coordinates = []
        index = 0
        lat = 0
        lng = 0

        while index < len(encoded):
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
    def check_route_intersects_hazards(
        route_coordinates: List[List[float]],
        hazard_polygons: List[List[List[float]]]
    ) -> bool:
        """
        Check if a route intersects any hazard polygons.
        """
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
        """
        if not polygon or len(polygon) < 3:
            return False

        inside = False
        n = len(polygon)

        for i in range(n):
            j = (i + 1) % n
            xi, yi = polygon[i]
            xj, yj = polygon[j]

            if ((yi > lat) != (yj > lat)):
                x_intersect = xi + (lat - yi) * (xj - xi) / (yj - yi)
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
        """
        if not route_data:
            return {
                'type': route_type,
                'distance_km': 0,
                'duration_min': 0,
                'coordinates': [],
                'available': False
            }

        distance_km = route_data.get('distance', 0)
        duration_min = route_data.get('duration', 0) / 60

        return {
            'type': route_type,
            'distance_km': round(distance_km, 2),
            'duration_min': round(duration_min, 1),
            'coordinates': route_data.get('coordinates', []),
            'available': True,
            'summary': route_data.get('summary', {})
        }
