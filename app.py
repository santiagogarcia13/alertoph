"""
Main Flask application for AlertoPH.
"""
import logging
import time
import concurrent.futures
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
    'general santos': (6.1164, 125.1716),
    'siargao': (9.7811, 126.1558),
    'boracay': (11.9674, 121.9248),
    'coron': (11.9986, 120.2043),
    'el nido': (11.1956, 119.4124),
    'batanes': (20.4486, 121.9708),
    'basco': (20.4486, 121.9708),
    'sagada': (17.0833, 120.9000),
    'banaue': (16.9115, 121.0617),
    'baler': (15.7592, 121.5622),
    'pagudpud': (18.5986, 120.7878),
    'la union': (16.6159, 120.3209),
    'san juan la union': (16.6744, 120.3394),
    'vigan': (17.5747, 120.3869),
    'tagaytay': (14.1153, 120.9621),
    'legazpi': (13.1391, 123.7438),
    'sorsogon': (12.9742, 124.0058),
    'panglao': (9.5786, 123.7744),
    'bohol': (9.8500, 124.1435),
    'siquijor': (9.2141, 123.5158),
    'camiguin': (9.1732, 124.7299),
    'bantayan': (11.1719, 123.7258),
    'malapascua': (11.3333, 124.1167),
    'dumaguete': (9.3068, 123.3054),
    'surigao': (9.7869, 125.4950),
    'butuan': (8.9475, 125.5406),
    'iligan': (8.2280, 124.2452),
    'mati': (6.9550, 126.2167),
    'romblon': (12.5786, 122.2708),
    'catanduanes': (13.5853, 124.2378),
    'virac': (13.5853, 124.2378),
    'subic': (14.8781, 120.2842),
    'olongapo': (14.8386, 120.2842),
    'dingalan': (15.3956, 121.3969)
}

# Comprehensive Philippine Regional Weather & Radar Stations
PH_REGIONAL_STATIONS = [
    # --- Luzon (Major & Regional Centers) ---
    {'name': 'Manila', 'province': 'Metro Manila', 'region': 'Luzon', 'lat': 14.5995, 'lng': 120.9842},
    {'name': 'Quezon City', 'province': 'Metro Manila', 'region': 'Luzon', 'lat': 14.6760, 'lng': 121.0437},
    {'name': 'Baguio City', 'province': 'Benguet', 'region': 'Luzon', 'lat': 16.4023, 'lng': 120.5960},
    {'name': 'Sagada', 'province': 'Mountain Province', 'region': 'Luzon', 'lat': 17.0833, 'lng': 120.9000},
    {'name': 'Banaue', 'province': 'Ifugao', 'region': 'Luzon', 'lat': 16.9115, 'lng': 121.0617},
    {'name': 'Baler', 'province': 'Aurora', 'region': 'Luzon', 'lat': 15.7592, 'lng': 121.5622},
    {'name': 'San Juan (Surf)', 'province': 'La Union', 'region': 'Luzon', 'lat': 16.6744, 'lng': 120.3394},
    {'name': 'Pagudpud', 'province': 'Ilocos Norte', 'region': 'Luzon', 'lat': 18.5986, 'lng': 120.7878},
    {'name': 'Vigan City', 'province': 'Ilocos Sur', 'region': 'Luzon', 'lat': 17.5747, 'lng': 120.3869},
    {'name': 'Tuguegarao', 'province': 'Cagayan', 'region': 'Luzon', 'lat': 17.6132, 'lng': 121.7270},
    {'name': 'Angeles City', 'province': 'Pampanga', 'region': 'Luzon', 'lat': 15.1450, 'lng': 120.5887},
    {'name': 'Subic Bay', 'province': 'Zambales', 'region': 'Luzon', 'lat': 14.8781, 'lng': 120.2842},
    {'name': 'Tagaytay', 'province': 'Cavite', 'region': 'Luzon', 'lat': 14.1153, 'lng': 120.9621},
    {'name': 'Batangas City', 'province': 'Batangas', 'region': 'Luzon', 'lat': 13.7538, 'lng': 121.0594},
    {'name': 'Lucena City', 'province': 'Quezon', 'region': 'Luzon', 'lat': 13.9314, 'lng': 121.6172},
    {'name': 'Naga City', 'province': 'Camarines Sur', 'region': 'Luzon', 'lat': 13.6218, 'lng': 123.1948},
    {'name': 'Legazpi (Mayon)', 'province': 'Albay', 'region': 'Luzon', 'lat': 13.1391, 'lng': 123.7438},
    {'name': 'Daet', 'province': 'Camarines Norte', 'region': 'Luzon', 'lat': 14.1167, 'lng': 122.9500},
    {'name': 'Sorsogon City', 'province': 'Sorsogon', 'region': 'Luzon', 'lat': 12.9742, 'lng': 124.0058},
    {'name': 'Dingalan', 'province': 'Aurora', 'region': 'Luzon', 'lat': 15.3956, 'lng': 121.3969},

    # --- Visayas (Islands & Urban Centers) ---
    {'name': 'Cebu City', 'province': 'Cebu', 'region': 'Visayas', 'lat': 10.3157, 'lng': 123.8854},
    {'name': 'Bantayan Island', 'province': 'Cebu', 'region': 'Visayas', 'lat': 11.1719, 'lng': 123.7258},
    {'name': 'Malapascua', 'province': 'Cebu', 'region': 'Visayas', 'lat': 11.3333, 'lng': 124.1167},
    {'name': 'Boracay Island', 'province': 'Aklan', 'region': 'Visayas', 'lat': 11.9674, 'lng': 121.9248},
    {'name': 'Iloilo City', 'province': 'Iloilo', 'region': 'Visayas', 'lat': 10.7202, 'lng': 122.5621},
    {'name': 'Bacolod City', 'province': 'Negros Occidental', 'region': 'Visayas', 'lat': 10.6760, 'lng': 122.9509},
    {'name': 'Dumaguete', 'province': 'Negros Oriental', 'region': 'Visayas', 'lat': 9.3068, 'lng': 123.3054},
    {'name': 'Panglao (Bohol)', 'province': 'Bohol', 'region': 'Visayas', 'lat': 9.5786, 'lng': 123.7744},
    {'name': 'Siquijor Island', 'province': 'Siquijor', 'region': 'Visayas', 'lat': 9.2141, 'lng': 123.5158},
    {'name': 'Tacloban City', 'province': 'Leyte', 'region': 'Visayas', 'lat': 11.2444, 'lng': 125.0039},
    {'name': 'Ormoc City', 'province': 'Leyte', 'region': 'Visayas', 'lat': 11.0050, 'lng': 124.6075},
    {'name': 'Catbalogan', 'province': 'Samar', 'region': 'Visayas', 'lat': 11.7753, 'lng': 124.8819},
    {'name': 'Guiuan', 'province': 'Eastern Samar', 'region': 'Visayas', 'lat': 11.0333, 'lng': 125.7167},
    {'name': 'Kalibo', 'province': 'Aklan', 'region': 'Visayas', 'lat': 11.7081, 'lng': 122.3644},
    {'name': 'Roxas City', 'province': 'Capiz', 'region': 'Visayas', 'lat': 11.5853, 'lng': 122.7511},

    # --- Mindanao ---
    {'name': 'Davao City', 'province': 'Davao del Sur', 'region': 'Mindanao', 'lat': 7.1907, 'lng': 125.4553},
    {'name': 'Cagayan de Oro', 'province': 'Misamis Oriental', 'region': 'Mindanao', 'lat': 8.4542, 'lng': 124.6319},
    {'name': 'General Santos', 'province': 'South Cotabato', 'region': 'Mindanao', 'lat': 6.1164, 'lng': 125.1716},
    {'name': 'Zamboanga City', 'province': 'Zamboanga del Sur', 'region': 'Mindanao', 'lat': 6.9214, 'lng': 122.0790},
    {'name': 'Butuan City', 'province': 'Agusan del Norte', 'region': 'Mindanao', 'lat': 8.9475, 'lng': 125.5406},
    {'name': 'Iligan City', 'province': 'Lanao del Norte', 'region': 'Mindanao', 'lat': 8.2280, 'lng': 124.2452},
    {'name': 'Cotabato City', 'province': 'Maguindanao', 'region': 'Mindanao', 'lat': 7.2236, 'lng': 124.2464},
    {'name': 'Surigao City', 'province': 'Surigao del Norte', 'region': 'Mindanao', 'lat': 9.7869, 'lng': 125.4950},
    {'name': 'Malaybalay', 'province': 'Bukidnon', 'region': 'Mindanao', 'lat': 8.1575, 'lng': 125.1278},
    {'name': 'Mati City', 'province': 'Davao Oriental', 'region': 'Mindanao', 'lat': 6.9550, 'lng': 126.2167},
    {'name': 'Koronadal City', 'province': 'South Cotabato', 'region': 'Mindanao', 'lat': 6.5028, 'lng': 124.8464},
    {'name': 'Dipolog City', 'province': 'Zamboanga del Norte', 'region': 'Mindanao', 'lat': 8.5878, 'lng': 123.3417},

    # --- Islands, MIMAROPA & Tourism Destinations ---
    {'name': 'Siargao (Gen. Luna)', 'province': 'Surigao del Norte', 'region': 'Islands', 'lat': 9.7811, 'lng': 126.1558},
    {'name': 'El Nido', 'province': 'Palawan', 'region': 'Islands', 'lat': 11.1956, 'lng': 119.4124},
    {'name': 'Coron', 'province': 'Palawan', 'region': 'Islands', 'lat': 11.9986, 'lng': 120.2043},
    {'name': 'Puerto Princesa', 'province': 'Palawan', 'region': 'Islands', 'lat': 9.7392, 'lng': 118.7353},
    {'name': 'San Vicente (Long Beach)', 'province': 'Palawan', 'region': 'Islands', 'lat': 10.5186, 'lng': 119.2789},
    {'name': 'Basco / Batanes', 'province': 'Batanes', 'region': 'Islands', 'lat': 20.4486, 'lng': 121.9708},
    {'name': 'Camiguin Island', 'province': 'Camiguin', 'region': 'Islands', 'lat': 9.1732, 'lng': 124.7299},
    {'name': 'Romblon Island', 'province': 'Romblon', 'region': 'Islands', 'lat': 12.5786, 'lng': 122.2708},
    {'name': 'Virac', 'province': 'Catanduanes', 'region': 'Islands', 'lat': 13.5853, 'lng': 124.2378},
    {'name': 'Puerto Galera', 'province': 'Oriental Mindoro', 'region': 'Islands', 'lat': 13.5014, 'lng': 120.9542},
    {'name': 'San Jose', 'province': 'Occidental Mindoro', 'region': 'Islands', 'lat': 12.3528, 'lng': 121.0675},
    {'name': 'Jordan (Guimaras)', 'province': 'Guimaras', 'region': 'Islands', 'lat': 10.5939, 'lng': 122.5975}
]

def get_pagasa_warning_level(rain_1h: float) -> dict:
    """Classify 1-hour rainfall according to official PAGASA rainfall advisory levels."""
    if rain_1h >= 30.0:
        return {
            'level': 'red',
            'label': 'Red Warning (Torrential)',
            'color': '#ef4444',
            'badge_class': 'badge-red',
            'advice': 'Torrential rain: Severe flooding expected. Evacuation in low-lying areas advised.'
        }
    elif rain_1h >= 15.0:
        return {
            'level': 'orange',
            'label': 'Orange Warning (Intense)',
            'color': '#f97316',
            'badge_class': 'badge-orange',
            'advice': 'Intense rain: Flooding is threatening. Residents should be alert and prepare.'
        }
    elif rain_1h >= 7.5:
        return {
            'level': 'yellow',
            'label': 'Yellow Warning (Heavy)',
            'color': '#eab308',
            'badge_class': 'badge-yellow',
            'advice': 'Heavy rain: Flooding is possible in low-lying areas. Monitor conditions.'
        }
    elif rain_1h >= 2.5:
        return {
            'level': 'moderate',
            'label': 'Moderate Rain',
            'color': '#3b82f6',
            'badge_class': 'badge-moderate',
            'advice': 'Moderate rain: Wet roads and reduced visibility. Carry rain gear.'
        }
    else:
        return {
            'level': 'light',
            'label': 'Light / No Rain',
            'color': '#10b981',
            'badge_class': 'badge-light',
            'advice': 'Normal weather conditions.'
        }

# In-memory TTL cache for regional weather
_REGIONAL_WEATHER_CACHE = {'timestamp': 0.0, 'data': []}

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


@app.route('/api/earthquakes', methods=['GET'])
def get_earthquakes():
    """Get recent earthquakes with support for Philippine and Global scopes and custom timeframes."""
    try:
        min_mag = request.args.get('min_mag', default=2.0, type=float)
        scope = request.args.get('scope', default='ph', type=str)
        days = request.args.get('days', default=None, type=int)
        hours = request.args.get('hours', default=None, type=int)

        if days is not None:
            time_window_hours = days * 24
        elif hours is not None:
            time_window_hours = hours
        else:
            time_window_hours = Config.EARTHQUAKE_TIME_WINDOW_HOURS

        # For global scope, default to M4.5+ if min_mag is left at 2.0 to prevent payload overload
        effective_min_mag = min_mag
        if scope == 'global' and min_mag <= 2.0:
            effective_min_mag = 4.5

        earthquakes = fetch_recent_earthquakes(
            lat=None,
            lon=None,
            radius_km=None,
            time_window_hours=time_window_hours,
            scope=scope,
            min_magnitude=effective_min_mag
        )

        if min_mag > 2.0 and scope == 'ph':
            earthquakes = [q for q in earthquakes if q.get('magnitude', 0) >= min_mag]

        return jsonify({
            'count': len(earthquakes),
            'scope': scope,
            'time_window_hours': time_window_hours,
            'earthquakes': earthquakes,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching earthquakes: {e}")
        return jsonify({'error': 'Failed to fetch earthquake data', 'earthquakes': [], 'count': 0}), 500


def _fetch_single_station(station: dict) -> dict:
    """Fetch weather for a single station and format with PAGASA alert levels."""
    try:
        w = fetch_current_weather(station['lat'], station['lng'])
        if w and not w.get('error'):
            rain_1h = float(w.get('rain_1h', 0) or 0)
            warning_info = get_pagasa_warning_level(rain_1h)
            condition = 'Clear'
            icon = '01d'
            if w.get('weather') and len(w['weather']) > 0:
                condition = w['weather'][0].get('description', 'Clear')
                icon = w['weather'][0].get('icon', '01d')

            return {
                'name': station['name'],
                'province': station.get('province', ''),
                'region': station.get('region', 'Luzon'),
                'lat': station['lat'],
                'lng': station['lng'],
                'temperature': w.get('temperature'),
                'rain_1h': rain_1h,
                'humidity': w.get('humidity'),
                'wind_speed': w.get('wind_speed'),
                'condition': condition,
                'icon': icon,
                'is_heavy_rain': rain_1h >= Config.HEAVY_RAINFALL_THRESHOLD,
                'pagasa_level': warning_info['level'],
                'pagasa_label': warning_info['label'],
                'pagasa_color': warning_info['color'],
                'pagasa_badge_class': warning_info['badge_class'],
                'pagasa_advice': warning_info['advice']
            }
    except Exception as e:
        logger.warning(f"Failed to fetch weather for {station.get('name')}: {e}")
    return None


@app.route('/api/weather/regional', methods=['GET'])
def get_regional_weather():
    """
    Get current weather across 50+ Philippine regional stations with PAGASA rainfall warning levels.
    Supports optional search, region, and alert_only filters.
    """
    global _REGIONAL_WEATHER_CACHE
    now = time.time()
    cache_ttl = 300.0  # 5 minutes

    is_testing = app.config.get('TESTING', False)
    use_cache = not is_testing and (now - _REGIONAL_WEATHER_CACHE['timestamp'] < cache_ttl) and len(_REGIONAL_WEATHER_CACHE['data']) > 0

    if use_cache:
        all_stations = _REGIONAL_WEATHER_CACHE['data']
    else:
        # Multi-threaded concurrent fetching across all stations
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
            future_to_station = {executor.submit(_fetch_single_station, st): st for st in PH_REGIONAL_STATIONS}
            for future in concurrent.futures.as_completed(future_to_station):
                data = future.result()
                if data:
                    results.append(data)

        # Sort stations: Heavy rain alerts first, then alphabetically by name
        results.sort(key=lambda s: (-s['rain_1h'], s['name']))
        all_stations = results
        if not is_testing and results:
            _REGIONAL_WEATHER_CACHE = {'timestamp': now, 'data': results}

    # Optional server-side query filters
    search_q = request.args.get('search', '').strip().lower()
    region_filter = request.args.get('region', '').strip()
    alert_only = request.args.get('alert_only', '').lower() in ['true', '1', 'yes']

    filtered = all_stations
    if region_filter and region_filter.lower() != 'all':
        filtered = [s for s in filtered if s.get('region', '').lower() == region_filter.lower()]

    if alert_only:
        filtered = [s for s in filtered if s.get('is_heavy_rain') or s.get('rain_1h', 0) >= 2.5]

    if search_q:
        filtered = [
            s for s in filtered
            if search_q in s.get('name', '').lower()
            or search_q in s.get('province', '').lower()
            or search_q in s.get('region', '').lower()
        ]

    # Summary statistics
    alert_count = sum(1 for s in all_stations if s.get('is_heavy_rain'))
    moderate_count = sum(1 for s in all_stations if s.get('pagasa_level') == 'moderate')

    return jsonify({
        'count': len(filtered),
        'total_stations': len(all_stations),
        'alert_count': alert_count,
        'moderate_count': moderate_count,
        'stations': filtered,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


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
