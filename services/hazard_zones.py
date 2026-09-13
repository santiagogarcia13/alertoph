"""
Hazard zone generation service.
Creates polygons around hazard points for route avoidance.
"""
import math
import logging
from typing import List, Dict, Any, Tuple
from math import radians, cos, sin, asin, sqrt

from config import Config

logger = logging.getLogger(__name__)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points in kilometers.
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


def create_hazard_polygon(
    center_lat: float,
    center_lng: float,
    radius_km: float = None
) -> List[List[float]]:
    """
    Create a square polygon around a hazard point.

    Args:
        center_lat: Latitude of hazard center
        center_lng: Longitude of hazard center
        radius_km: Radius of the hazard zone in kilometers.
                  If None, uses Config.HAZARD_BUFFER_KM

    Returns:
        List of [longitude, latitude] points defining the polygon
    """
    if radius_km is None:
        radius_km = Config.HAZARD_BUFFER_KM

    # Approximate km per degree (rough average for Philippines)
    km_per_degree_lat = 111.0
    km_per_degree_lng = 111.0 * math.cos(math.radians(center_lat))

    # Calculate buffer in degrees
    buffer_lat = radius_km / km_per_degree_lat
    buffer_lng = radius_km / km_per_degree_lng

    # Create a square polygon (4 corners + closing point)
    polygon = [
        [center_lng - buffer_lng, center_lat - buffer_lat],  # SW
        [center_lng + buffer_lng, center_lat - buffer_lat],  # SE
        [center_lng + buffer_lng, center_lat + buffer_lat],  # NE
        [center_lng - buffer_lng, center_lat + buffer_lat],  # NW
        [center_lng - buffer_lng, center_lat - buffer_lat]   # Close polygon
    ]

    logger.debug(f"Created hazard polygon around ({center_lat}, {center_lng})")
    return polygon


def create_hazard_zones(
    hazard_points: List[Dict[str, Any]],
    hazard_type: str = 'earthquake'
) -> Dict[str, Any]:
    """
    Create hazard zones from multiple hazard points.

    Args:
        hazard_points: List of hazard point dictionaries with lat/lng
        hazard_type: Type of hazard ('earthquake', 'flood', etc.)

    Returns:
        Dictionary containing hazard zones information
    """
    if not hazard_points:
        return {
            'type': hazard_type,
            'count': 0,
            'polygons': [],
            'geojson': {
                'type': 'FeatureCollection',
                'features': []
            }
        }

    polygons = []
    geojson_features = []

    for i, point in enumerate(hazard_points):
        lat = point.get('latitude')
        lng = point.get('longitude')

        if lat is None or lng is None:
            continue

        # Adjust buffer size based on hazard type and magnitude
        if hazard_type == 'earthquake':
            magnitude = point.get('magnitude', 0)
            # Larger earthquakes get larger avoidance zones
            if magnitude >= 6.0:
                radius_km = Config.HAZARD_BUFFER_KM * 3
            elif magnitude >= 5.0:
                radius_km = Config.HAZARD_BUFFER_KM * 2
            else:
                radius_km = Config.HAZARD_BUFFER_KM
        elif hazard_type == 'flood':
            rainfall = point.get('rain_1h', 0)
            if rainfall >= 15.0:
                radius_km = Config.HAZARD_BUFFER_KM * 2.5
            elif rainfall >= 7.5:
                radius_km = Config.HAZARD_BUFFER_KM * 2
            else:
                radius_km = Config.HAZARD_BUFFER_KM
        else:
            radius_km = Config.HAZARD_BUFFER_KM

        # Create polygon
        polygon = create_hazard_polygon(lat, lng, radius_km)
        polygons.append(polygon)

        # Create GeoJSON feature
        feature = {
            'type': 'Feature',
            'properties': {
                'hazard_type': hazard_type,
                'magnitude': point.get('magnitude'),
                'rainfall_mm_hr': point.get('rain_1h'),
                'description': point.get('place', 'Unknown location'),
                'radius_km': radius_km
            },
            'geometry': {
                'type': 'Polygon',
                'coordinates': [polygon]
            }
        }
        geojson_features.append(feature)

    logger.info(f"Created {len(polygons)} {hazard_type} hazard zones")

    return {
        'type': hazard_type,
        'count': len(polygons),
        'polygons': polygons,
        'geojson': {
            'type': 'FeatureCollection',
            'features': geojson_features
        }
    }


def detect_hazards_along_route(
    route_coordinates: List[List[float]],
    earthquake_hazards: List[Dict[str, Any]],
    weather_hazards: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Detect hazards that intersect with a route.

    Args:
        route_coordinates: Route coordinates as [[lng, lat], ...]
        earthquake_hazards: Earthquake hazard points
        weather_hazards: Weather hazard points

    Returns:
        Dictionary of detected hazards along route
    """
    hazards_detected = {
        'earthquakes': [],
        'floods': [],
        'total_count': 0,
        'intersection_points': []
    }

    if not route_coordinates:
        return hazards_detected

    # Check earthquake hazards
    for quake in earthquake_hazards:
        quake_lat = quake.get('latitude')
        quake_lng = quake.get('longitude')
        magnitude = quake.get('magnitude', 0)

        if quake_lat is None or quake_lng is None:
            continue

        # Calculate distance from each route point
        min_distance = float('inf')
        closest_point = None

        for route_point in route_coordinates:
            route_lng, route_lat = route_point
            distance = haversine_distance(
                route_lat, route_lng,
                quake_lat, quake_lng
            )

            if distance < min_distance:
                min_distance = distance
                closest_point = route_point

        # Check if within hazard buffer distance
        if magnitude >= 6.0:
            hazardous_distance = Config.HAZARD_BUFFER_KM * 3
        elif magnitude >= 5.0:
            hazardous_distance = Config.HAZARD_BUFFER_KM * 2
        else:
            hazardous_distance = Config.HAZARD_BUFFER_KM

        if min_distance <= hazardous_distance:
            hazards_detected['earthquakes'].append({
                **quake,
                'distance_from_route_km': min_distance,
                'closest_route_point': closest_point
            })
            hazards_detected['total_count'] += 1

    # Check weather hazards (floods)
    for hazard in weather_hazards:
        hazard_lat = hazard.get('latitude')
        hazard_lng = hazard.get('longitude')
        rainfall = hazard.get('rain_1h', 0)

        if hazard_lat is None or hazard_lng is None:
            continue

        # Only consider significant rainfall
        if rainfall < Config.HEAVY_RAINFALL_THRESHOLD:
            continue

        min_distance = float('inf')
        closest_point = None

        for route_point in route_coordinates:
            route_lng, route_lat = route_point
            distance = haversine_distance(
                route_lat, route_lng,
                hazard_lat, hazard_lng
            )

            if distance < min_distance:
                min_distance = distance
                closest_point = route_point

        # Adjust buffer based on rainfall intensity
        if rainfall >= 15.0:
            hazardous_distance = Config.HAZARD_BUFFER_KM * 2.5
        elif rainfall >= 7.5:
            hazardous_distance = Config.HAZARD_BUFFER_KM * 2
        else:
            hazardous_distance = Config.HAZARD_BUFFER_KM

        if min_distance <= hazardous_distance:
            hazards_detected['floods'].append({
                **hazard,
                'distance_from_route_km': min_distance,
                'closest_route_point': closest_point
            })
            hazards_detected['total_count'] += 1

    logger.info(f"Detected {hazards_detected['total_count']} hazards along route")
    return hazards_detected


def merge_hazard_polygons(
    hazard_zones: List[Dict[str, Any]]
) -> List[List[List[float]]]:
    """
    Merge overlapping hazard polygons to avoid redundant avoidance areas.

    Args:
        hazard_zones: List of hazard zone dictionaries with polygons

    Returns:
        List of merged polygons
    """
    if not hazard_zones:
        return []

    all_polygons = []
    for zone in hazard_zones:
        all_polygons.extend(zone.get('polygons', []))

    # Simple merging: for now, just return all polygons
    # In production, you'd use a spatial library to merge overlapping polygons
    merged_polygons = []

    for polygon in all_polygons:
        # Check if this polygon overlaps significantly with any already-added polygon
        should_add = True

        for added_polygon in merged_polygons:
            if polygons_overlap(polygon, added_polygon):
                should_add = False
                break

        if should_add:
            merged_polygons.append(polygon)

    logger.info(f"Merged {len(all_polygons)} polygons to {len(merged_polygons)}")
    return merged_polygons


def polygons_overlap(poly1: List[List[float]], poly2: List[List[float]]) -> bool:
    """
    Simple check if two polygons overlap (approximate).
    For a proper implementation, use a spatial library.

    Args:
        poly1: First polygon coordinates
        poly2: Second polygon coordinates

    Returns:
        True if polygons likely overlap
    """
    # Simple bounding box check
    poly1_bbox = [
        min(p[0] for p in poly1),  # min lng
        min(p[1] for p in poly1),  # min lat
        max(p[0] for p in poly1),  # max lng
        max(p[1] for p in poly1)   # max lat
    ]

    poly2_bbox = [
        min(p[0] for p in poly2),
        min(p[1] for p in poly2),
        max(p[0] for p in poly2),
        max(p[1] for p in poly2)
    ]

    # Check if bounding boxes overlap
    return not (
        poly1_bbox[2] < poly2_bbox[0] or  # poly1 right < poly2 left
        poly1_bbox[0] > poly2_bbox[2] or  # poly1 left > poly2 right
        poly1_bbox[3] < poly2_bbox[1] or  # poly1 top < poly2 bottom
        poly1_bbox[1] > poly2_bbox[3]     # poly1 bottom > poly2 top
    )


if __name__ == '__main__':
    print("Testing hazard zones service...")

    # Test hazard point
    test_hazard = {'latitude': 14.5995, 'longitude': 120.9842, 'magnitude': 5.5}

    print(f"\n1. Creating hazard polygon:")
    polygon = create_hazard_polygon(test_hazard['latitude'], test_hazard['longitude'])
    print(f"   Polygon points: {len(polygon)}")
    print(f"   First point: {polygon[0]}")

    print(f"\n2. Creating hazard zones:")
    hazard_zones = create_hazard_zones([test_hazard], 'earthquake')
    print(f"   Zone count: {hazard_zones['count']}")
    print(f"   Feature count: {len(hazard_zones['geojson']['features'])}")

    # Test route hazard detection
    print(f"\n3. Testing route hazard detection:")
    test_route = [
        [120.0, 14.0],
        [121.0, 14.5],
        [122.0, 15.0]
    ]

    test_quakes = [
        {'latitude': 14.2, 'longitude': 120.5, 'magnitude': 5.0, 'place': 'Test Quake'}
    ]

    test_weather = [
        {'latitude': 14.6, 'longitude': 121.0, 'rain_1h': 8.5}
    ]

    detected = detect_hazards_along_route(test_route, test_quakes, test_weather)
    print(f"   Total hazards detected: {detected['total_count']}")
    print(f"   Earthquakes detected: {len(detected['earthquakes'])}")
    print(f"   Floods detected: {len(detected['floods'])}")

    # Test polygon merging
    print(f"\n4. Testing polygon merging:")
    test_zones = [
        create_hazard_zones([test_hazard], 'earthquake'),
        create_hazard_zones([test_hazard], 'earthquake')  # Same zone
    ]

    merged = merge_hazard_polygons(test_zones)
    print(f"   Merged polygons: {len(merged)}")