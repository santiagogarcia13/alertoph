/**
 * Main JavaScript for AlertoPH frontend functionality.
 */

// Philippine locations for autocomplete and validation
const PhilippineLocations = {
    'manila': { lat: 14.5995, lng: 120.9842, region: 'Metro Manila' },
    'cebu': { lat: 10.3157, lng: 123.8854, region: 'Central Visayas' },
    'davao': { lat: 7.1907, lng: 125.4553, region: 'Davao Region' },
    'quezon city': { lat: 14.6760, lng: 121.0437, region: 'Metro Manila' },
    'makati': { lat: 14.5547, lng: 121.0244, region: 'Metro Manila' },
    'taguig': { lat: 14.5176, lng: 121.0509, region: 'Metro Manila' },
    'pasig': { lat: 14.5764, lng: 121.0851, region: 'Metro Manila' },
    'iloilo': { lat: 10.7202, lng: 122.5621, region: 'Western Visayas' },
    'bacolod': { lat: 10.6760, lng: 122.9509, region: 'Western Visayas' },
    'angeles': { lat: 15.1450, lng: 120.5887, region: 'Central Luzon' },
    'bicol': { lat: 13.4210, lng: 123.4137, region: 'Bicol Region' },
    'mindanao': { lat: 8.1833, lng: 124.1667, region: 'Mindanao' },
    'luzon': { lat: 15.5000, lng: 121.0000, region: 'Luzon' },
    'visayas': { lat: 11.5000, lng: 123.0000, region: 'Visayas' },
    'baguio': { lat: 16.4023, lng: 120.5960, region: 'Cordillera' },
    'cagayan de oro': { lat: 8.4542, lng: 124.6319, region: 'Northern Mindanao' },
    'zamboanga': { lat: 6.9214, lng: 122.0790, region: 'Zamboanga Peninsula' },
    'bataan': { lat: 14.6707, lng: 120.4296, region: 'Central Luzon' },
    'pampanga': { lat: 15.0794, lng: 120.6203, region: 'Central Luzon' },
    'laguna': { lat: 14.1667, lng: 121.3333, region: 'Calabarzon' },
    'cavite': { lat: 14.4791, lng: 120.8970, region: 'Calabarzon' },
    'rizal': { lat: 14.6500, lng: 121.2500, region: 'Calabarzon' },
    'bulacan': { lat: 14.7939, lng: 120.8795, region: 'Central Luzon' },
    'batangas': { lat: 13.7538, lng: 121.0594, region: 'Calabarzon' },
    'puerto princesa': { lat: 9.7392, lng: 118.7353, region: 'Mimaropa' },
    'tacloban': { lat: 11.2444, lng: 125.0039, region: 'Eastern Visayas' },
    'naga': { lat: 13.6218, lng: 123.1948, region: 'Bicol Region' },
    'general santos': { lat: 6.1164, lng: 125.1716, region: 'Soccsksargen' }
};

// Global state
const AppState = {
    currentLanguage: 'english',
    map: null,
    mapMarkers: {
        origin: null,
        destination: null,
        hazards: [],
        advisory: null  // New marker for advisory location
    },
    mapLayers: {
        originRoute: null,
        safeRoute: null,
        hazardZones: null
    },
    currentLocation: null,
    currentAdvisory: null,
    currentRoute: null
};

// DOM Elements
const elements = {
    languageBtn: document.getElementById('language-btn'),
    locationInput: document.getElementById('location-input'),
    searchBtn: document.getElementById('search-btn'),
    latInput: document.getElementById('lat-input'),
    lngInput: document.getElementById('lng-input'),
    coordSearchBtn: document.getElementById('coord-search-btn'),
    pickAdvisoryLocationBtn: document.getElementById('pick-advisory-location'),
    advisoryResults: document.getElementById('advisory-results'),
    advisoryLocation: document.getElementById('advisory-location'),
    advisoryTimestamp: document.getElementById('advisory-timestamp'),
    earthquakeData: document.getElementById('earthquake-data'),
    weatherData: document.getElementById('weather-data'),
    safetyAdvice: document.getElementById('safety-advice'),
    originInput: document.getElementById('origin-input'),
    destinationInput: document.getElementById('destination-input'),
    useCurrentLocationBtn: document.getElementById('use-current-location'),
    pickOriginBtn: document.getElementById('pick-origin'),
    pickDestinationBtn: document.getElementById('pick-destination'),
    clearPointsBtn: document.getElementById('clear-points'),
    calculateRouteBtn: document.getElementById('calculate-route-btn'),
    map: document.getElementById('map'),
    routeInfo: document.getElementById('route-info'),
    earthquakeStatus: document.getElementById('earthquake-status'),
    weatherStatus: document.getElementById('weather-status'),
    routingStatus: document.getElementById('routing-status')
};

// Initialize the application
function init() {
    setupEventListeners();
    initializeMap();
    checkApiStatus();
}

// Set up event listeners
function setupEventListeners() {
    // Language toggle
    elements.languageBtn.addEventListener('click', toggleLanguage);

    // Location search
    elements.searchBtn.addEventListener('click', () => searchByLocation(elements.locationInput.value));
    elements.coordSearchBtn.addEventListener('click', searchByCoordinates);
    elements.locationInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchByLocation(elements.locationInput.value);
    });

    // Advisory location picking
    elements.pickAdvisoryLocationBtn.addEventListener('click', () => setMapPickingMode('advisory'));

    // Route planning
    elements.useCurrentLocationBtn.addEventListener('click', useCurrentLocation);
    elements.pickOriginBtn.addEventListener('click', () => setMapPickingMode('origin'));
    elements.pickDestinationBtn.addEventListener('click', () => setMapPickingMode('destination'));
    elements.clearPointsBtn.addEventListener('click', clearMapPoints);
    elements.calculateRouteBtn.addEventListener('click', calculateRoute);

    // Autocomplete for location input
    elements.locationInput.addEventListener('input', handleLocationAutocomplete);
    elements.locationInput.addEventListener('focus', handleLocationAutocomplete);
}

// Initialize Leaflet map
function initializeMap() {
    // Default to Philippines center
    const phCenter = [12.8797, 121.7740]; // Center of Philippines
    const zoomLevel = 6;

    // Create map
    AppState.map = L.map('map').setView(phCenter, zoomLevel);

    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(AppState.map);

    // Add click handler for point picking
    AppState.map.on('click', handleMapClick);
}

// Handle map clicks for point picking
let mapPickingMode = null; // 'origin', 'destination', 'advisory', or null

function setMapPickingMode(mode) {
    mapPickingMode = mode;
    alert(`Click on the map to set ${mode}. Click again to cancel.`);
}

function handleMapClick(e) {
    if (!mapPickingMode) return;

    const lat = e.latlng.lat;
    const lng = e.latlng.lng;

    switch (mapPickingMode) {
        case 'origin':
            setOriginPoint(lat, lng);
            break;
        case 'destination':
            setDestinationPoint(lat, lng);
            break;
        case 'advisory':
            setAdvisoryLocationFromMap(lat, lng);
            break;
    }

    mapPickingMode = null;
}

function setOriginPoint(lat, lng) {
    // Remove existing origin marker
    if (AppState.mapMarkers.origin) {
        AppState.map.removeLayer(AppState.mapMarkers.origin);
    }

    // Create new origin marker
    AppState.mapMarkers.origin = L.marker([lat, lng], {
        icon: L.divIcon({
            className: 'map-marker origin',
            html: '<i class="fas fa-map-marker-alt" style="color: #1e88e5; font-size: 24px;"></i>',
            iconSize: [24, 24]
        })
    }).addTo(AppState.map);

    // Update input field
    elements.originInput.value = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
}

function setDestinationPoint(lat, lng) {
    // Remove existing destination marker
    if (AppState.mapMarkers.destination) {
        AppState.map.removeLayer(AppState.mapMarkers.destination);
    }

    // Create new destination marker
    AppState.mapMarkers.destination = L.marker([lat, lng], {
        icon: L.divIcon({
            className: 'map-marker destination',
            html: '<i class="fas fa-flag-checkered" style="color: #ff9800; font-size: 24px;"></i>',
            iconSize: [24, 24]
        })
    }).addTo(AppState.map);

    // Update input field
    elements.destinationInput.value = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
}

function clearMapPoints() {
    // Clear markers
    if (AppState.mapMarkers.origin) {
        AppState.map.removeLayer(AppState.mapMarkers.origin);
        AppState.mapMarkers.origin = null;
    }
    if (AppState.mapMarkers.destination) {
        AppState.map.removeLayer(AppState.mapMarkers.destination);
        AppState.mapMarkers.destination = null;
    }

    // Clear input fields
    elements.originInput.value = '';
    elements.destinationInput.value = '';

    // Clear routes
    clearRoutes();
}

// Set advisory location from map click
function setAdvisoryLocationFromMap(lat, lng) {
    // Remove existing advisory marker
    if (AppState.mapMarkers.advisory) {
        AppState.map.removeLayer(AppState.mapMarkers.advisory);
    }

    // Create new advisory marker
    AppState.mapMarkers.advisory = L.marker([lat, lng], {
        icon: L.divIcon({
            className: 'map-marker advisory',
            html: '<i class="fas fa-exclamation-circle" style="color: #4caf50; font-size: 24px;"></i>',
            iconSize: [24, 24]
        })
    }).addTo(AppState.map);

    // Update coordinate input fields
    elements.latInput.value = lat.toFixed(4);
    elements.lngInput.value = lng.toFixed(4);

    // Try to find the nearest named location
    const nearestLocation = findNearestLocation(lat, lng);
    if (nearestLocation) {
        elements.locationInput.value = nearestLocation.name;
        // Auto-search for advisory
        setTimeout(() => searchByLocation(nearestLocation.name), 500);
    } else {
        // If no named location found, search by coordinates
        setTimeout(() => searchByCoordinates(), 500);
    }
}

// Find nearest named location to coordinates
function findNearestLocation(lat, lng) {
    let nearest = null;
    let minDistance = Infinity;

    for (const [name, data] of Object.entries(PhilippineLocations)) {
        const distance = Math.sqrt(
            Math.pow(lat - data.lat, 2) + Math.pow(lng - data.lng, 2)
        );

        if (distance < minDistance) {
            minDistance = distance;
            nearest = { name, ...data };
        }
    }

    // If within reasonable distance (approx 0.5 degrees ~ 55km)
    return minDistance < 0.5 ? nearest : null;
}

// Autocomplete functionality for location input
function handleLocationAutocomplete() {
    const input = elements.locationInput;
    const value = input.value.toLowerCase().trim();

    if (!value) {
        clearAutocomplete();
        return;
    }

    // Find matching locations
    const matches = [];
    for (const [name, data] of Object.entries(PhilippineLocations)) {
        if (name.toLowerCase().includes(value)) {
            matches.push({ name, region: data.region });
        }
    }

    // Show autocomplete suggestions
    showAutocompleteSuggestions(matches);
}

// Show autocomplete suggestions
function showAutocompleteSuggestions(matches) {
    clearAutocomplete();

    if (matches.length === 0) {
        return;
    }

    const container = document.createElement('div');
    container.className = 'autocomplete-container';
    container.id = 'autocomplete-container';

    matches.slice(0, 5).forEach(match => {
        const item = document.createElement('div');
        item.className = 'autocomplete-item';
        item.innerHTML = `
            <strong>${match.name.charAt(0).toUpperCase() + match.name.slice(1)}</strong>
            <small>${match.region}</small>
        `;
        item.addEventListener('click', () => {
            elements.locationInput.value = match.name;
            clearAutocomplete();
            searchByLocation(match.name);
        });
        container.appendChild(item);
    });

    elements.locationInput.parentNode.appendChild(container);
}

// Clear autocomplete suggestions
function clearAutocomplete() {
    const container = document.getElementById('autocomplete-container');
    if (container) {
        container.remove();
    }
}

function clearRoutes() {
    // Clear route layers
    if (AppState.mapLayers.originRoute) {
        AppState.map.removeLayer(AppState.mapLayers.originRoute);
        AppState.mapLayers.originRoute = null;
    }
    if (AppState.mapLayers.safeRoute) {
        AppState.map.removeLayer(AppState.mapLayers.safeRoute);
        AppState.mapLayers.safeRoute = null;
    }
    if (AppState.mapLayers.hazardZones) {
        AppState.map.removeLayer(AppState.mapLayers.hazardZones);
        AppState.mapLayers.hazardZones = null;
    }

    // Clear route info
    updateRouteInfo(null);
}

// Toggle between English and Filipino
function toggleLanguage() {
    AppState.currentLanguage = AppState.currentLanguage === 'english' ? 'filipino' : 'english';
    elements.languageBtn.innerHTML = `
        <i class="fas fa-language"></i>
        Switch to ${AppState.currentLanguage === 'english' ? 'Filipino' : 'English'}
    `;

    // Refresh current advisory if available
    if (AppState.currentAdvisory) {
        displayAdvisory(AppState.currentAdvisory);
    }

    // Refresh current route if available
    if (AppState.currentRoute) {
        displayRouteResults(AppState.currentRoute);
    }
}

// Search by location name
function searchByLocation(location) {
    if (!location.trim()) {
        alert('Please enter a location name.');
        return;
    }

    showLoading('advisory');
    fetch(`/api/advisory?location=${encodeURIComponent(location)}&lang=${AppState.currentLanguage}`)
        .then(async response => {
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.error || `HTTP error! status: ${response.status}`);
            }
            return data;
        })
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            AppState.currentAdvisory = data;
            displayAdvisory(data);
            updateApiStatus('earthquake', data.earthquakes ? 'active' : 'warning');
            updateApiStatus('weather', data.weather && !data.weather.error ? 'active' : 'warning');
        })
        .catch(error => {
            console.error('Error fetching advisory:', error);
            showError('advisory', `Failed to get advisory: ${error.message}`);
        })
        .finally(() => {
            hideLoading('advisory');
        });
}

// Search by coordinates
function searchByCoordinates() {
    const lat = parseFloat(elements.latInput.value);
    const lng = parseFloat(elements.lngInput.value);

    if (isNaN(lat) || isNaN(lng)) {
        alert('Please enter valid latitude and longitude values.');
        return;
    }

    if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
        alert('Please enter valid coordinates (lat: -90 to 90, lng: -180 to 180).');
        return;
    }

    showLoading('advisory');
    fetch(`/api/advisory?lat=${lat}&lng=${lng}&lang=${AppState.currentLanguage}`)
        .then(async response => {
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.error || `HTTP error! status: ${response.status}`);
            }
            return data;
        })
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            AppState.currentAdvisory = data;
            displayAdvisory(data);
            updateApiStatus('earthquake', data.earthquakes ? 'active' : 'warning');
            updateApiStatus('weather', data.weather && !data.weather.error ? 'active' : 'warning');
        })
        .catch(error => {
            console.error('Error fetching advisory:', error);
            showError('advisory', `Failed to get advisory: ${error.message}`);
        })
        .finally(() => {
            hideLoading('advisory');
        });
}

// Display advisory results
function displayAdvisory(data) {
    // Show advisory section
    elements.advisoryResults.style.display = 'block';

    // Update location and timestamp
    elements.advisoryLocation.textContent = data.location.name;
    const timestamp = new Date(data.timestamp).toLocaleString();
    elements.advisoryTimestamp.textContent = `Updated: ${timestamp}`;

    // Display earthquake data
    displayEarthquakeData(data.earthquakes, data.advisory.earthquake);

    // Display weather data
    displayWeatherData(data.weather, data.advisory.weather);

    // Display safety advice
    displaySafetyAdvice(data.advisory);

    // Center map on location if coordinates available
    if (data.location.latitude && data.location.longitude) {
        AppState.map.setView([data.location.latitude, data.location.longitude], 10);
    }
}

function displayEarthquakeData(earthquakes, earthquakeAdvice) {
    let html = '';

    if (earthquakes && earthquakes.length > 0) {
        html += '<div class="hazard-list">';
        earthquakes.slice(0, 3).forEach(quake => {
            const magnitude = quake.magnitude?.toFixed(1) || 'Unknown';
            const distance = quake.distance_km?.toFixed(1) || 'N/A';
            const place = quake.place || 'Unknown location';

            html += `
                <div class="hazard-item earthquake">
                    <strong>Magnitude ${magnitude}</strong>
                    <div>${place}</div>
                    <div class="distance">${distance} km away</div>
                </div>
            `;
        });

        if (earthquakes.length > 3) {
            html += `<div class="more-quakes">+ ${earthquakes.length - 3} more earthquakes</div>`;
        }
        html += '</div>';
    } else {
        html += '<div class="no-hazards">No significant earthquake activity detected.</div>';
    }

    // Add advisory summary
    if (earthquakeAdvice) {
        html += `<div class="advice-summary"><strong>${earthquakeAdvice.summary}</strong></div>`;
    }

    elements.earthquakeData.innerHTML = html;
}

function displayWeatherData(weather, weatherAdvice) {
    let html = '';

    if (weather && !weather.error) {
        html += '<div class="weather-data">';

        if (weather.temperature !== null) {
            html += `
                <div class="weather-item">
                    <span class="weather-label">Temperature:</span>
                    <span class="weather-value">${weather.temperature?.toFixed(1)}°C</span>
                </div>
            `;
        }

        if (weather.rain_1h > 0) {
            const rainClass = weather.rain_1h >= 7.5 ? 'rain-heavy' :
                             weather.rain_1h >= 2.5 ? 'rain-moderate' : 'rain-light';
            html += `
                <div class="weather-item">
                    <span class="weather-label">Rainfall (1h):</span>
                    <span class="weather-value ${rainClass}">${weather.rain_1h?.toFixed(1)} mm</span>
                </div>
            `;
        }

        if (weather.wind_speed > 0) {
            html += `
                <div class="weather-item">
                    <span class="weather-label">Wind Speed:</span>
                    <span class="weather-value">${weather.wind_speed?.toFixed(1)} m/s</span>
                </div>
            `;
        }

        if (weather.weather && weather.weather.length > 0) {
            const condition = weather.weather[0].description;
            html += `
                <div class="weather-item">
                    <span class="weather-label">Conditions:</span>
                    <span class="weather-value">${condition}</span>
                </div>
            `;
        }

        html += '</div>';
    } else {
        html += '<div class="no-weather">Weather data unavailable.</div>';
    }

    // Add advisory summary
    if (weatherAdvice) {
        html += `<div class="advice-summary"><strong>${weatherAdvice.summary}</strong></div>`;
    }

    elements.weatherData.innerHTML = html;
}

function displaySafetyAdvice(advisory) {
    let html = '';

    // Overall summary
    html += `<div class="overall-advice ${advisory.overall_severity}">`;
    html += `<h4>${advisory.overall_summary}</h4>`;
    html += `<p>Severity: <span class="severity-${advisory.overall_severity}">${advisory.overall_severity.toUpperCase()}</span></p>`;
    html += '</div>';

    // Individual advice items
    if (advisory.all_advice && advisory.all_advice.length > 0) {
        html += '<div class="advice-list">';
        advisory.all_advice.forEach(advice => {
            html += `<div class="advice-item"><i class="fas fa-exclamation-circle"></i> ${advice}</div>`;
        });
        html += '</div>';
    } else {
        html += '<div class="no-specific-advice">No specific safety advice needed at this time.</div>';
    }

    elements.safetyAdvice.innerHTML = html;
}

// Use current location
function useCurrentLocation() {
    if (!navigator.geolocation) {
        alert('Geolocation is not supported by your browser.');
        return;
    }

    elements.useCurrentLocationBtn.disabled = true;
    elements.useCurrentLocationBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Getting location...';

    navigator.geolocation.getCurrentPosition(
        position => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;

            elements.originInput.value = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
            setOriginPoint(lat, lng);

            elements.useCurrentLocationBtn.disabled = false;
            elements.useCurrentLocationBtn.innerHTML = '<i class="fas fa-location-arrow"></i> Use Current Location';
        },
        error => {
            console.error('Geolocation error:', error);
            alert('Unable to get your location. Please enter it manually.');
            elements.useCurrentLocationBtn.disabled = false;
            elements.useCurrentLocationBtn.innerHTML = '<i class="fas fa-location-arrow"></i> Use Current Location';
        }
    );
}

// Calculate route
function calculateRoute() {
    const origin = elements.originInput.value;
    const destination = elements.destinationInput.value;

    if (!origin || !destination) {
        alert('Please enter both origin and destination.');
        return;
    }

    // Parse coordinates from input
    const originCoords = parseCoordinates(origin);
    const destinationCoords = parseCoordinates(destination);

    if (!originCoords || !destinationCoords) {
        alert('Please enter valid coordinates in format: latitude, longitude');
        return;
    }

    showLoading('route');
    clearRoutes();

    // Call the backend route API
    const routeRequest = {
        origin: originCoords,
        destination: destinationCoords,
        lang: AppState.currentLanguage
    };

    fetch('/api/route', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(routeRequest)
    })
    .then(async response => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.error || `HTTP error! status: ${response.status}`);
        }
        return data;
    })
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }

        AppState.currentRoute = data;
        displayRouteResults(data);
        drawRouteOnMap(data);
        updateApiStatus('routing', 'active');
    })
    .catch(error => {
        console.error('Error calculating route:', error);
        showError('route', `Failed to calculate route: ${error.message}`);
        updateApiStatus('routing', 'error');

        // Fall back to placeholder route
        drawPlaceholderRoute(originCoords, destinationCoords);
        updateRouteInfo({
            distance_km: null,
            duration_min: null,
            hazards: [],
            advice: `Route calculation failed: ${error.message}`
        });
    })
    .finally(() => {
        hideLoading('route');
    });
}

function parseCoordinates(input) {
    const parts = input.split(',').map(part => part.trim());
    if (parts.length !== 2) return null;

    const lat = parseFloat(parts[0]);
    const lng = parseFloat(parts[1]);

    if (isNaN(lat) || isNaN(lng)) return null;
    if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return null;

    return { lat, lng };
}

function drawPlaceholderRoute(origin, destination) {
    // Create a straight line between points
    const linePoints = [
        [origin.lat, origin.lng],
        [destination.lat, destination.lng]
    ];

    // Draw original route (dashed line)
    AppState.mapLayers.originRoute = L.polyline(linePoints, {
        color: '#666',
        weight: 4,
        opacity: 0.7,
        dashArray: '10, 10'
    }).addTo(AppState.map);

    // Add markers if not already present
    if (!AppState.mapMarkers.origin) {
        setOriginPoint(origin.lat, origin.lng);
    }
    if (!AppState.mapMarkers.destination) {
        setDestinationPoint(destination.lat, destination.lng);
    }

    // Fit map to show both points
    AppState.map.fitBounds([linePoints[0], linePoints[1]], { padding: [50, 50] });
}

function updateRouteInfo(routeData) {
    if (!routeData) {
        elements.routeInfo.querySelector('.info-content').innerHTML = 'No route calculated yet.';
        return;
    }

    let html = '';

    if (routeData.distance_km !== undefined && routeData.distance_km !== null && routeData.distance_km !== 'N/A') {
        const distNum = parseFloat(routeData.distance_km);
        const distDisplay = isNaN(distNum) ? routeData.distance_km : `${distNum.toFixed(1)} km`;
        html += `<div class="route-info-item">
            <span class="route-info-label">Distance:</span>
            <span class="route-info-value">${distDisplay}</span>
        </div>`;
    }

    if (routeData.duration_min !== undefined && routeData.duration_min !== null && routeData.duration_min !== 'N/A') {
        const mins = parseFloat(routeData.duration_min);
        let timeDisplay = '';
        if (!isNaN(mins)) {
            if (mins >= 60) {
                const hrs = Math.floor(mins / 60);
                const remMins = Math.round(mins % 60);
                timeDisplay = remMins > 0 ? `${hrs} ${hrs === 1 ? 'hr' : 'hrs'} ${remMins} ${remMins === 1 ? 'min' : 'mins'}` : `${hrs} ${hrs === 1 ? 'hr' : 'hrs'}`;
            } else if (mins < 1) {
                timeDisplay = '< 1 min';
            } else {
                const roundedMins = Math.round(mins);
                timeDisplay = `${roundedMins} ${roundedMins === 1 ? 'min' : 'mins'}`;
            }
        } else {
            timeDisplay = `${routeData.duration_min}`;
        }
        html += `<div class="route-info-item">
            <span class="route-info-label">Estimated Time:</span>
            <span class="route-info-value">${timeDisplay}</span>
        </div>`;
    }

    const hazardCount = routeData.hazardCount !== undefined ? routeData.hazardCount : (routeData.hazards ? routeData.hazards.length : 0);
    if (hazardCount > 0) {
        html += `<div class="route-info-item">
            <span class="route-info-label">Hazards:</span>
            <span class="route-info-value">${hazardCount} detected</span>
        </div>`;
    }

    if (routeData.advice) {
        html += `<div class="route-info-item">
            <span class="route-info-label">Advice:</span>
            <span class="route-info-value">${routeData.advice}</span>
        </div>`;
    }

    elements.routeInfo.querySelector('.info-content').innerHTML = html || 'No route information available.';
}

function displayRouteResults(routeData) {
    AppState.currentRoute = routeData;

    let hazardList = [];
    let hazardCount = 0;
    if (routeData.hazards) {
        if (Array.isArray(routeData.hazards)) {
            hazardList = routeData.hazards;
            hazardCount = hazardList.length;
        } else {
            const quakes = routeData.hazards.earthquakes || [];
            const floods = routeData.hazards.floods || [];
            hazardList = [...quakes, ...floods];
            hazardCount = routeData.hazards.total_count !== undefined ? routeData.hazards.total_count : hazardList.length;
        }
    }

    const activeRoute = routeData.adjusted_route || routeData.base_route;

    // Update route info
    const info = {
        distance_km: activeRoute?.distance_km,
        duration_min: activeRoute?.duration_min,
        hazards: hazardList,
        hazardCount: hazardCount,
        advice: routeData.advice?.summary || (typeof routeData.advice === 'string' ? routeData.advice : 'No advice available')
    };

    updateRouteInfo(info);
}

function drawRouteOnMap(routeData) {
    // Clear existing routes
    if (AppState.mapLayers.originRoute) {
        AppState.map.removeLayer(AppState.mapLayers.originRoute);
        AppState.mapLayers.originRoute = null;
    }
    if (AppState.mapLayers.safeRoute) {
        AppState.map.removeLayer(AppState.mapLayers.safeRoute);
        AppState.mapLayers.safeRoute = null;
    }

    // Draw base route
    if (routeData.base_route && routeData.base_route.coordinates && routeData.base_route.coordinates.length > 0) {
        const routePoints = routeData.base_route.coordinates.map(coord => [coord[1], coord[0]]); // Convert [lng, lat] to [lat, lng]

        AppState.mapLayers.originRoute = L.polyline(routePoints, {
            color: '#1e88e5',
            weight: 5,
            opacity: 0.8,
            dashArray: null
        }).addTo(AppState.map);
    }

    // Draw adjusted route if available
    if (routeData.adjusted_route && routeData.adjusted_route.coordinates && routeData.adjusted_route.coordinates.length > 0) {
        const adjustedPoints = routeData.adjusted_route.coordinates.map(coord => [coord[1], coord[0]]); // Convert [lng, lat] to [lat, lng]

        AppState.mapLayers.safeRoute = L.polyline(adjustedPoints, {
            color: '#4caf50',
            weight: 5,
            opacity: 0.8,
            dashArray: '10, 5'
        }).addTo(AppState.map);
    }

    // Draw hazard zones if available
    if (routeData.hazard_zones && routeData.hazard_zones.length > 0) {
        routeData.hazard_zones.forEach((zone, index) => {
            if (zone.geojson && zone.geojson.features) {
                zone.geojson.features.forEach(feature => {
                    if (feature.geometry && feature.geometry.coordinates) {
                        const polygon = L.geoJSON(feature, {
                            style: {
                                color: '#ff5252',
                                weight: 2,
                                opacity: 0.6,
                                fillColor: '#ff5252',
                                fillOpacity: 0.2
                            }
                        }).addTo(AppState.map);

                        AppState.mapLayers.hazardZones = polygon;
                    }
                });
            }
        });
    }

    // Fit map to show the route
    if (routeData.base_route && routeData.base_route.coordinates && routeData.base_route.coordinates.length > 0) {
        const routePoints = routeData.base_route.coordinates.map(coord => [coord[1], coord[0]]);
        const bounds = L.latLngBounds(routePoints);
        AppState.map.fitBounds(bounds, { padding: [50, 50] });
    }
}

// API status checking
function checkApiStatus() {
    // Check Earthquake & Weather API via advisory endpoint
    fetch('/api/advisory?lat=14.5995&lng=120.9842&lang=english')
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error('Advisory service response not ok');
        })
        .then(data => {
            if (data.earthquakes !== undefined) {
                updateApiStatus('earthquake', 'active');
            } else {
                updateApiStatus('earthquake', 'warning');
            }

            if (data.weather && !data.weather.error) {
                updateApiStatus('weather', 'active');
            } else if (data.weather && data.weather.error) {
                updateApiStatus('weather', 'warning');
            } else {
                updateApiStatus('weather', 'error');
            }
        })
        .catch(err => {
            console.error('API check error:', err);
            updateApiStatus('earthquake', 'error');
            updateApiStatus('weather', 'error');
        });

    // Check Routing API
    fetch('/api/route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            origin: { lat: 14.5995, lng: 120.9842 },
            destination: { lat: 14.5547, lng: 121.0244 },
            lang: 'english'
        })
    })
    .then(response => {
        if (response.ok) {
            updateApiStatus('routing', 'active');
        } else {
            updateApiStatus('routing', 'warning');
        }
    })
    .catch(() => {
        updateApiStatus('routing', 'error');
    });
}

function updateApiStatus(api, status) {
    const element = elements[`${api}Status`];
    if (!element) return;

    // Clear existing classes
    element.className = 'status-indicator';
    element.textContent = status.charAt(0).toUpperCase() + status.slice(1);

    // Add status-specific class
    switch (status) {
        case 'active':
            element.classList.add('active');
            break;
        case 'warning':
            element.classList.add('warning');
            break;
        case 'error':
            element.classList.add('error');
            break;
        case 'pending':
            element.classList.add('pending');
            break;
    }
}

// Utility functions
function showLoading(context) {
    // Could implement loading spinners for different contexts
    console.log(`Loading ${context}...`);
}

function hideLoading(context) {
    console.log(`Finished loading ${context}`);
}

function showError(context, message) {
    alert(`Error (${context}): ${message}`);
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', init);