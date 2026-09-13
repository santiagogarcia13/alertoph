# AlertoPH

Earthquake, Weather & Hazard-Aware Route Advisory System for the Philippines

## Overview

AlertoPH is a web application that provides real-time hazard awareness for safer travel in the Philippines. It integrates earthquake data, weather conditions, and routing information to generate safety advisories and suggest hazard-aware alternative routes.

## Features

- **Location-Based Hazard Advisory**: Get combined earthquake and weather safety advice for any Philippine location
- **Earthquake Monitoring**: Real-time earthquake data from USGS filtered for the Philippines region
- **Weather Monitoring**: Current weather conditions including rainfall, wind speed, and alerts
- **Hazard-Aware Route Planning**: Calculate routes that avoid hazardous areas (earthquake zones, flood-prone areas)
- **Bilingual Interface**: Toggle between English and Filipino languages
- **Interactive Map**: Visualize routes, hazard zones, and locations using Leaflet.js
- **Graceful Degradation**: System continues working even if individual APIs are unavailable

## Tech Stack

- **Backend**: Python 3.x with Flask
- **Frontend**: HTML5, CSS3, Vanilla JavaScript (Fetch API)
- **Mapping**: Leaflet.js (no API key required)
- **External APIs**:
  - USGS Earthquake API (no key required)
  - OpenWeatherMap API (free tier key required)
  - OpenRouteService Directions API (free key required)

## Setup Instructions

### 1. Prerequisites

- Python 3.8 or higher
- Git (optional)

### 2. Clone/Setup

```bash
# Clone or create the project directory
cd alertoph

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. API Keys Setup

1. **OpenWeatherMap API Key**:
   - Visit https://openweathermap.org/api
   - Sign up for a free account
   - Get your API key from the dashboard

2. **OpenRouteService API Key**:
   - Visit https://openrouteservice.org/dev/#/signup
   - Sign up for a free account (no credit card required)
   - Get your API key

3. **Create `.env` file**:
   Copy `.env.example` to `.env` and update with your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your actual API keys:
```
OPENWEATHER_API_KEY=your_actual_openweather_api_key_here
OPENROUTESERVICE_API_KEY=your_actual_openrouteservice_api_key_here
FLASK_ENV=development
FLASK_DEBUG=True
```

### 5. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Project Structure

```
alertoph/
├── app.py                    # Main Flask application
├── config.py                # Configuration and environment variables
├── requirements.txt         # Python dependencies
├── .env.example            # Example environment variables
├── README.md              # This file
├── services/
│   ├── earthquake_service.py  # USGS earthquake data fetching
│   ├── weather_service.py     # OpenWeatherMap integration
│   ├── advisory_engine.py     # Safety advice generation
│   └── (more services to be added)
├── templates/
│   └── index.html            # Main HTML template
├── static/
│   ├── css/
│   │   └── style.css        # Main stylesheet
│   └── js/
│       └── main.js          # Frontend JavaScript
└── tests/
    └── test_advisory_engine.py  # Unit tests
```

## API Endpoints

### `GET /`
Renders the main application page.

### `GET /api/advisory`
Get combined earthquake and weather advisory for a location.

**Query Parameters:**
- `location` (optional): City or province name (e.g., "Manila", "Cebu")
- `lat`, `lng` (optional): Coordinates
- `lang` (optional): Language code ("english" or "filipino", defaults to "english")

**Example Response:**
```json
{
  "location": {
    "name": "Manila",
    "latitude": 14.5995,
    "longitude": 120.9842
  },
  "earthquakes": [...],
  "weather": {...},
  "advisory": {
    "overall_summary": "⚠️ MODERATE ALERT: Hazard conditions present.",
    "overall_severity": "medium",
    "earthquake": {...},
    "weather": {...}
  }
}
```

### `POST /api/route`
Calculate a hazard-aware route between origin and destination.

**Request Body:**
```json
{
  "origin": {"lat": 14.5995, "lng": 120.9842},
  "destination": {"lat": 10.3157, "lng": 123.8854}
}
```

**Response:**
```json
{
  "origin": {...},
  "destination": {...},
  "base_route": {...},
  "adjusted_route": {...},
  "hazards": [...],
  "advice": "Route passes through hazardous area - alternate route suggested."
}
```

### `GET /api/hazards`
Get current hazard zones as GeoJSON.

## Usage Guide

### Getting a Safety Advisory

1. Open the application in your browser
2. Enter a Philippine location (e.g., "Manila", "Cebu", "Davao")
3. Click "Get Advisory"
4. View earthquake activity, weather conditions, and safety recommendations

### Planning a Hazard-Aware Route

1. Enter origin and destination coordinates
2. Optionally, click "Pick Origin" or "Pick Destination" to select points on the map
3. Click "Calculate Safe Route"
4. View the route on the map with hazard zones highlighted

### Switching Languages

Click the "Switch to Filipino" button to toggle between English and Filipino interfaces.

## Testing

Run unit tests for the advisory engine:

```bash
pytest tests/test_advisory_engine.py
```

## Future Enhancements

1. **Complete Routing Service**: Implement full OpenRouteService integration
2. **Hazard Zone Detection**: Create polygons around hazard points
3. **Geocoding Service**: Add address-to-coordinate conversion
4. **Database Integration**: Cache API responses for performance
5. **User Accounts**: Save favorite locations and routes
6. **Mobile App**: Create React Native or Flutter mobile version
7. **Push Notifications**: Alert users about hazards near their location
8. **Historical Data**: Show trends and patterns over time

## API Rate Limits

- **USGS Earthquake API**: No rate limits
- **OpenWeatherMap Free Tier**: 60 calls/minute, 1,000,000 calls/month
- **OpenRouteService Free Tier**: 2,000 requests/day

## Troubleshooting

### API Key Issues
- Ensure your `.env` file is correctly formatted
- Check that API keys are valid and not expired
- Verify internet connectivity

### Module Import Errors
- Make sure virtual environment is activated
- Run `pip install -r requirements.txt` again
- Check Python version compatibility

### Map Not Displaying
- Check browser console for JavaScript errors
- Ensure internet connection for Leaflet CDN
- Verify no browser extensions are blocking the map

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add/update tests
5. Update documentation
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This system provides advisory information only. Always follow official warnings from government agencies like PAGASA (weather), PHIVOLCS (earthquakes), and local disaster management offices. Use caution and common sense when traveling in hazardous conditions.

## Acknowledgments

- USGS for earthquake data
- OpenWeatherMap for weather data
- OpenRouteService for routing data
- Leaflet for mapping library