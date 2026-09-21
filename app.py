"""
Main Flask application for AlertoPH.
"""
import logging
from datetime import datetime, timezone
from flask import Flask, render_template, jsonify, request

from config import Config
from services.earthquake_service import fetch_recent_earthquakes, get_nearest_earthquake
from services.weather_service import fetch_current_weather, fetch_weather_by_city, is_heavy_rainfall
from services.advisory_engine import AdvisoryEngine
from services.routing_service import RoutingService
from services.geocoding_service import GeocodingService
from services.hazard_zones import (
    create_hazard_zones,
    detect_hazards_along_route,
    merge_hazard_polygons
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Validate configuration
try:
    Config.validate()
    logger.info("Configuration validated successfully")
except ValueError as e:
    logger.warning(f"Configuration validation: {e}")

# Known Philippine locations coordinates lookup
PH_LOCATIONS = {
    'manila': (14.5995, 120.9842),
    'cebu': (10.3157, 123.8854),
    'davao': (7.1907, 125.4553),
    'quezon city': (14.6760, 121.0437),
    'makati': (14.5547, 121.0244),
    'taguig': (14.5176, 121.0509),
    'pasig': (14.5764, 121.0851),
    'baguio': (16.4023, 120.5960),
    'cagayan de oro': (8.4542, 124.6319),
    'zamboanga': (6.9214, 122.0790),
    'iloilo': (10.7202, 122.5621),
    'bacolod': (10.6760, 122.9509),
    'angeles': (15.1450, 120.5887),
    'bicol': (13.4210, 123.4137),
    'mindanao': (8.1833, 124.1667),
    'luzon': (15.5000, 121.0000),
    'visayas': (11.5000, 123.0000),
    'pampanga': (15.0794, 120.6203),
    'bataan': (14.6707, 120.4296),
    'laguna': (14.1667, 121.3333),
    'cavite': (14.4791, 120.8970),
    'rizal': (14.6500, 121.2500),
    'bulacan': (14.7939, 120.8795),
    'batangas': (13.7538, 121.0594),
    'puerto princesa': (9.7392, 118.7353),
    'tacloban': (11.2444, 125.0039),
    'naga': (13.6218, 123.1948),
    'general santos': (6.1164, 125.1716)
}

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/api/geocode', methods=['GET'])
def geocode():
    """Geocode a location query or return autocomplete suggestions across the Philippines."""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({
            'error': 'Query parameter "q" is required',
            'results': [],
            'count': 0
        }), 400

    limit = request.args.get('limit', default=5, type=int)
    limit = max(1, min(limit, 10))

    try:
        suggestions = GeocodingService.search_suggestions(query, limit=limit)
        return jsonify({
            'query': query,
            'results': suggestions,
            'count': len(suggestions)
        })
    except Exception as e:
        logger.error(f"Error in geocode endpoint: {e}")
        return jsonify({
            'error': 'Error searching location',
            'details': str(e),
            'results': []
        }), 500


@app.route('/api/advisory', methods=['GET'])
def advisory():
    """Get earthquake and weather advisory for a location."""
    location = request.args.get('location')
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    language = request.args.get('lang', 'english')
    resolved_location_name = location

    try:
        # If location name provided, try to get coordinates
        if location and (lat is None or lng is None):
            location_key = location.lower().strip()
            if location_key in PH_LOCATIONS:
                lat, lng = PH_LOCATIONS[location_key]
            else:
                # Try geocoding with GeocodingService
                geo_result = GeocodingService.geocode(location)
                if geo_result:
                    lat = geo_result['latitude']
                    lng = geo_result['longitude']
                    resolved_location_name = geo_result.get('display_name') or geo_result.get('name')
                else:
                    # Fallback to city weather geocoding
                    city_weather = fetch_weather_by_city(location, country_code='PH') or fetch_weather_by_city(location)
                    if city_weather and city_weather.get('location', {}).get('latitude') is not None:
                        lat = city_weather['location']['latitude']
                        lng = city_weather['location']['longitude']
                        resolved_location_name = city_weather['location'].get('name', location)
                    else:
                        # Return error with suggested locations
                        return jsonify({
                            'error': f'Location "{location}" not recognized. Please provide a more specific location, address, landmark, or coordinates.',
                            'suggested_locations': list(PH_LOCATIONS.keys())
                        }), 400

        # Validate coordinates
        if lat is None or lng is None:
            return jsonify({
                'error': 'Invalid location. Please provide valid coordinates or a known Philippine location.',
                'suggested_locations': list(PH_LOCATIONS.keys())
            }), 400

        # Get earthquake data
        try:
            earthquake_data = get_nearest_earthquake(lat, lng, radius_km=200)
            earthquakes = fetch_recent_earthquakes(lat, lng, radius_km=200)
        except Exception as e:
            logger.error(f"Error fetching earthquake data: {e}")
            earthquake_data = None
            earthquakes = []

        # Get weather data
        try:
            weather_data = fetch_current_weather(lat, lng)
            if weather_data and 'error' in weather_data:
                logger.warning(f"Weather API error: {weather_data['error']}")
                # Keep weather_data but mark as error
                weather_data = {'error': 'Weather data unavailable'}
        except Exception as e:
            logger.error(f"Error fetching weather data: {e}")
            weather_data = {'error': 'Weather service unavailable'}

        # Generate advisory
        advisory_data = AdvisoryEngine.generate_combined_advisory(
            earthquake_data,
            weather_data,
            language
        )

        # Prepare response
        response = {
            'location': {
                'name': resolved_location_name or f"{lat:.4f}, {lng:.4f}",
                'latitude': lat,
                'longitude': lng
            },
            'earthquakes': earthquakes[:5],  # Return up to 5 most significant
            'weather': weather_data,
            'advisory': advisory_data,
            'timestamp': advisory_data['timestamp']
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in advisory endpoint: {e}")
        return jsonify({
            'error': 'Internal server error while generating advisory',
            'details': str(e)
        }), 500

@app.route('/api/route', methods=['POST'])
def route():
    """Calculate a route with hazard awareness."""
    data = request.get_json()
    language = data.get('lang', 'english') if data else 'english'

    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    origin = data.get('origin')
    destination = data.get('destination')

    if not origin or not destination:
        return jsonify({'error': 'Origin and destination required'}), 400

    # Validate coordinates
    if not all(key in origin for key in ['lat', 'lng']) or \
       not all(key in destination for key in ['lat', 'lng']):
        return jsonify({'error': 'Invalid coordinate format. Use {"lat": x, "lng": y}'}), 400

    try:
        # Step 1: Calculate base route
        base_route = RoutingService.calculate_base_route(origin, destination)

        if not base_route:
            return jsonify({
                'error': 'Unable to calculate route. Please check API key and coordinates.'
            }), 500

        # Step 2: Get hazard data along the route
        route_coords = base_route.get('coordinates', [])

        # Get earthquake hazards near route
        route_midpoint = route_coords[len(route_coords) // 2] if route_coords else [0, 0]
        route_mid_lat, route_mid_lng = route_midpoint[1], route_midpoint[0]

        earthquake_hazards = fetch_recent_earthquakes(
            route_mid_lat, route_mid_lng, radius_km=100
        )

        # Get weather hazards near route
        weather_data = fetch_current_weather(route_mid_lat, route_mid_lng)
        weather_hazards = []
        if weather_data and not weather_data.get('error'):
            # Check if heavy rainfall at this location
            if is_heavy_rainfall(weather_data):
                weather_hazards.append({
                    'latitude': route_mid_lat,
                    'longitude': route_mid_lng,
                    'rain_1h': weather_data.get('rain_1h', 0),
                    'weather': weather_data.get('weather', [{}])[0]
                })

        # Step 3: Detect hazards along the route
        detected_hazards = detect_hazards_along_route(
            route_coords,
            earthquake_hazards,
            weather_hazards
        )

        # Step 4: Create hazard zones for avoidance
        hazard_zones = []
        if detected_hazards['earthquakes']:
            earthquake_zones = create_hazard_zones(
                detected_hazards['earthquakes'],
                'earthquake'
            )
            hazard_zones.append(earthquake_zones)

        if detected_hazards['floods']:
            flood_zones = create_hazard_zones(
                detected_hazards['floods'],
                'flood'
            )
            hazard_zones.append(flood_zones)

        # Step 5: Calculate hazard-adjusted route if needed
        adjusted_route = None
        if detected_hazards['total_count'] > 0:
            # Merge hazard polygons
            hazard_polygons = merge_hazard_polygons(hazard_zones)

            # Calculate route avoiding hazards
            adjusted_route = RoutingService.calculate_hazard_aware_route(
                origin,
                destination,
                hazard_polygons
            )

        # Step 6: Generate route advice
        hazard_types = []
        if detected_hazards['earthquakes']:
            hazard_types.append('earthquake')
        if detected_hazards['floods']:
            hazard_types.append('flood')

        route_advice = AdvisoryEngine.generate_route_advice(
            hazards_detected=detected_hazards['total_count'] > 0,
            hazard_count=detected_hazards['total_count'],
            hazard_types=hazard_types,
            language=language
        )

        # Step 7: Prepare response
        response = {
            'origin': origin,
            'destination': destination,
            'base_route': RoutingService.format_route_for_frontend(base_route, 'base'),
            'adjusted_route': RoutingService.format_route_for_frontend(adjusted_route, 'adjusted') if adjusted_route else None,
            'hazards': detected_hazards,
            'hazard_zones': hazard_zones,
            'advice': route_advice,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in route calculation: {e}")
        return jsonify({
            'error': 'Internal server error while calculating route',
            'details': str(e)
        }), 500

@app.route('/api/hazards', methods=['GET'])
def hazards():
    """Get current hazard zones as GeoJSON."""
    try:
        # Get recent earthquakes in Philippines
        earthquake_hazards = fetch_recent_earthquakes(
            lat=None, lon=None, radius_km=None  # Use bounding box
        )

        # Get sample weather hazard (in production, you'd fetch multiple locations)
        # For demo, use Manila as reference point
        weather_data = fetch_current_weather(14.5995, 120.9842)
        weather_hazards = []

        if weather_data and not weather_data.get('error') and is_heavy_rainfall(weather_data):
            weather_hazards.append({
                'latitude': 14.5995,
                'longitude': 120.9842,
                'rain_1h': weather_data.get('rain_1h', 0),
                'weather': weather_data.get('weather', [{}])[0],
                'type': 'flood'
            })

        # Create hazard zones
        hazard_zones = []

        if earthquake_hazards:
            earthquake_zones = create_hazard_zones(earthquake_hazards, 'earthquake')
            hazard_zones.append(earthquake_zones)

        if weather_hazards:
            flood_zones = create_hazard_zones(weather_hazards, 'flood')
            hazard_zones.append(flood_zones)

        # Combine all GeoJSON features
        all_features = []
        for zone in hazard_zones:
            all_features.extend(zone.get('geojson', {}).get('features', []))

        response = {
            'type': 'FeatureCollection',
            'features': all_features,
            'metadata': {
                'earthquake_count': len(earthquake_hazards),
                'weather_hazard_count': len(weather_hazards),
                'total_zones': len(all_features),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error fetching hazards: {e}")
        return jsonify({
            'type': 'FeatureCollection',
            'features': [],
            'error': 'Unable to fetch hazard data',
            'metadata': {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    logger.error(f'Server error: {error}')
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=Config.DEBUG)
