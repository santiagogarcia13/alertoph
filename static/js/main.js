/**
 * Main JavaScript for AlertoPH frontend functionality.
 */

// Global state
const AppState = {
    currentLanguage: 'english',
    map: null,
    mapMarkers: {
        origin: null,
        destination: null,
        hazards: [],
        advisory: null
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

    // Dynamic Geocoding Autocomplete for location input
    attachGeocodeAutocomplete(elements.locationInput, (item) => {
        elements.locationInput.value = item.display_name || item.name;
        elements.latInput.value = item.latitude.toFixed(4);
        elements.lngInput.value = item.longitude.toFixed(4);
        setAdvisoryLocationMarker(item.latitude, item.longitude, item.name);
        searchByCoordinates();
    });

    // Dynamic Geocoding Autocomplete for route inputs
    attachGeocodeAutocomplete(elements.originInput, (item) => {
        elements.originInput.value = `${item.latitude.toFixed(4)}, ${item.longitude.toFixed(4)}`;
        setOriginPoint(item.latitude, item.longitude);
    });

    attachGeocodeAutocomplete(elements.destinationInput, (item) => {
        elements.destinationInput.value = `${item.latitude.toFixed(4)}, ${item.longitude.toFixed(4)}`;
        setDestinationPoint(item.latitude, item.longitude);
    });

    // Close autocomplete on external click
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.input-group')) {
            clearAllAutocomplete();
        }
    });
}

// Initialize Leaflet map
function initializeMap() {
    const phCenter = [12.8797, 121.7740]; // Center of Philippines
    const zoomLevel = 6;

    AppState.map = L.map('map').setView(phCenter, zoomLevel);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(AppState.map);

    AppState.map.on('click', handleMapClick);
}

// Map point picking
let mapPickingMode = null;

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
    if (AppState.mapMarkers.origin) {
        AppState.map.removeLayer(AppState.mapMarkers.origin);
    }

    AppState.mapMarkers.origin = L.marker([lat, lng], {
        icon: L.divIcon({
            className: 'map-marker origin',
            html: '<i class="fas fa-map-marker-alt" style="color: #1e88e5; font-size: 24px;"></i>',
            iconSize: [24, 24]
        })
    }).addTo(AppState.map);

    elements.originInput.value = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
}

function setDestinationPoint(lat, lng) {
    if (AppState.mapMarkers.destination) {
        AppState.map.removeLayer(AppState.mapMarkers.destination);
    }

    AppState.mapMarkers.destination = L.marker([lat, lng], {
        icon: L.divIcon({
            className: 'map-marker destination',
            html: '<i class="fas fa-flag-checkered" style="color: #ff9800; font-size: 24px;"></i>',
            iconSize: [24, 24]
        })
    }).addTo(AppState.map);

    elements.destinationInput.value = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
}

function setAdvisoryLocationMarker(lat, lng, title) {
    if (AppState.mapMarkers.advisory) {
        AppState.map.removeLayer(AppState.mapMarkers.advisory);
    }

    AppState.mapMarkers.advisory = L.marker([lat, lng], {
        icon: L.divIcon({
            className: 'map-marker advisory',
            html: '<i class="fas fa-exclamation-circle" style="color: #4caf50; font-size: 24px;"></i>',
            iconSize: [24, 24]
        })
    }).addTo(AppState.map);

    if (title) {
        AppState.mapMarkers.advisory.bindPopup(`<b>${title}</b>`).openPopup();
    }

    AppState.map.setView([lat, lng], 10);
}

function clearMapPoints() {
    if (AppState.mapMarkers.origin) {
        AppState.map.removeLayer(AppState.mapMarkers.origin);
        AppState.mapMarkers.origin = null;
    }
    if (AppState.mapMarkers.destination) {
        AppState.map.removeLayer(AppState.mapMarkers.destination);
        AppState.mapMarkers.destination = null;
    }

    elements.originInput.value = '';
    elements.destinationInput.value = '';

    clearRoutes();
}

function setAdvisoryLocationFromMap(lat, lng) {
    setAdvisoryLocationMarker(lat, lng);
    elements.latInput.value = lat.toFixed(4);
    elements.lngInput.value = lng.toFixed(4);
    elements.locationInput.value = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
    setTimeout(() => searchByCoordinates(), 300);
}

// Dynamic Geocoding and Autocomplete Implementation
const debounceTimers = new Map();

function attachGeocodeAutocomplete(inputElement, onSelectCallback) {
    if (!inputElement) return;

    inputElement.addEventListener('input', () => {
        const query = inputElement.value.trim();
        if (query.length < 2) {
            clearAutocompleteFor(inputElement);
            return;
        }

        // Debounce API calls (300ms)
        if (debounceTimers.has(inputElement)) {
            clearTimeout(debounceTimers.get(inputElement));
        }

        const timer = setTimeout(() => {
            fetchGeocodeSuggestions(query, inputElement, onSelectCallback);
        }, 300);

        debounceTimers.set(inputElement, timer);
    });
}

function fetchGeocodeSuggestions(query, inputElement, onSelectCallback) {
    fetch(`/api/geocode?q=${encodeURIComponent(query)}&limit=6`)
        .then(response => response.json())
        .then(data => {
            if (data.results && data.results.length > 0) {
                renderAutocompleteDropdown(inputElement, data.results, onSelectCallback);
            } else {
                clearAutocompleteFor(inputElement);
            }
        })
        .catch(err => {
            console.warn('Geocoding autocomplete error:', err);
            clearAutocompleteFor(inputElement);
        });
}

function renderAutocompleteDropdown(inputElement, items, onSelectCallback) {
    clearAutocompleteFor(inputElement);

    const container = document.createElement('div');
    container.className = 'autocomplete-container';
    container.dataset.owner = inputElement.id;

    items.forEach(item => {
        const row = document.createElement('div');
        row.className = 'autocomplete-item';

        const mainLabel = item.name || 'Location';
        const subLabel = item.display_name || item.region || `${item.latitude.toFixed(3)}, ${item.longitude.toFixed(3)}`;

        row.innerHTML = `
            <strong><i class="fas fa-map-pin" style="margin-right: 6px; color: var(--primary-color);"></i>${escapeHtml(mainLabel)}</strong>
            <small>${escapeHtml(subLabel)}</small>
        `;

        row.addEventListener('click', () => {
            clearAutocompleteFor(inputElement);
            onSelectCallback(item);
        });

        container.appendChild(row);
    });

    inputElement.parentNode.appendChild(container);
}

function clearAutocompleteFor(inputElement) {
    const parent = inputElement.parentNode;
    if (parent) {
        const container = parent.querySelector('.autocomplete-container');
        if (container) container.remove();
    }
}

function clearAllAutocomplete() {
    document.querySelectorAll('.autocomplete-container').forEach(el => el.remove());
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function clearRoutes() {
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
    updateRouteInfo(null);
}

// Search by location name or address
function searchByLocation(location) {
    if (!location.trim()) {
        alert('Please enter a location name.');
        return;
    }

    showLoading('advisory');
    clearAllAutocomplete();

    fetch(`/api/advisory?location=${encodeURIComponent(location)}&lang=english`)
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
    clearAllAutocomplete();

    fetch(`/api/advisory?lat=${lat}&lng=${lng}&lang=english`)
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
    elements.advisoryResults.style.display = 'block';

    elements.advisoryLocation.textContent = data.location.name;
    const timestamp = new Date(data.timestamp).toLocaleString();
    elements.advisoryTimestamp.textContent = `Updated: ${timestamp}`;

    displayEarthquakeData(data.earthquakes, data.advisory.earthquake);
    displayWeatherData(data.weather, data.advisory.weather);
    displaySafetyAdvice(data.advisory);

    if (data.location.latitude && data.location.longitude) {
        setAdvisoryLocationMarker(data.location.latitude, data.location.longitude, data.location.name);
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

    if (weatherAdvice) {
        html += `<div class="advice-summary"><strong>${weatherAdvice.summary}</strong></div>`;
    }

    elements.weatherData.innerHTML = html;
}

function displaySafetyAdvice(advisory) {
    let html = '';

    html += `<div class="overall-advice ${advisory.overall_severity}">`;
    html += `<h4>${advisory.overall_summary}</h4>`;
    html += `<p>Severity: <span class="severity-${advisory.overall_severity}">${advisory.overall_severity.toUpperCase()}</span></p>`;
    html += '</div>';

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

// Resolve location input string to coordinates (supports both "lat, lng" and named places)
async function resolveLocationToCoords(inputStr) {
    const parsed = parseCoordinates(inputStr);
    if (parsed) return parsed;

    try {
        const resp = await fetch(`/api/geocode?q=${encodeURIComponent(inputStr)}&limit=1`);
        const data = await resp.json();
        if (data.results && data.results.length > 0) {
            return {
                lat: data.results[0].latitude,
                lng: data.results[0].longitude
            };
        }
    } catch (e) {
        console.warn('Failed to resolve coordinates for:', inputStr, e);
    }
    return null;
}

// Calculate route
async function calculateRoute() {
    const originText = elements.originInput.value.trim();
    const destinationText = elements.destinationInput.value.trim();

    if (!originText || !destinationText) {
        alert('Please enter both origin and destination.');
        return;
    }

    showLoading('route');
    clearAllAutocomplete();

    // Resolve coordinates for origin and destination
    const originCoords = await resolveLocationToCoords(originText);
    const destinationCoords = await resolveLocationToCoords(destinationText);

    if (!originCoords || !destinationCoords) {
        hideLoading('route');
        alert('Unable to resolve coordinates for the origin or destination. Please provide valid location names or coordinates (lat, lng).');
        return;
    }

    setOriginPoint(originCoords.lat, originCoords.lng);
    setDestinationPoint(destinationCoords.lat, destinationCoords.lng);
    clearRoutes();

    const routeRequest = {
        origin: originCoords,
        destination: destinationCoords,
        lang: 'english'
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
    const linePoints = [
        [origin.lat, origin.lng],
        [destination.lat, destination.lng]
    ];

    AppState.mapLayers.originRoute = L.polyline(linePoints, {
        color: '#666',
        weight: 4,
        opacity: 0.7,
        dashArray: '10, 10'
    }).addTo(AppState.map);

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
        const routePoints = routeData.base_route.coordinates.map(coord => [coord[1], coord[0]]);

        AppState.mapLayers.originRoute = L.polyline(routePoints, {
            color: '#1e88e5',
            weight: 5,
            opacity: 0.8
        }).addTo(AppState.map);
    }

    // Draw safe / adjusted route
    if (routeData.adjusted_route && routeData.adjusted_route.coordinates && routeData.adjusted_route.coordinates.length > 0) {
        const adjustedPoints = routeData.adjusted_route.coordinates.map(coord => [coord[1], coord[0]]);

        AppState.mapLayers.safeRoute = L.polyline(adjustedPoints, {
            color: '#4caf50',
            weight: 5,
            opacity: 0.8,
            dashArray: '10, 5'
        }).addTo(AppState.map);
    }

    // Draw hazard zones
    if (routeData.hazard_zones && routeData.hazard_zones.length > 0) {
        routeData.hazard_zones.forEach(zone => {
            if (zone.geojson && zone.geojson.features) {
                zone.geojson.features.forEach(feature => {
                    if (feature.geometry && feature.geometry.coordinates) {
                        const polygon = L.geoJSON(feature, {
                            style: {
                                color: '#ff5252',
                                weight: 2,
                                opacity: 0.6,
                                fillColor: '#ff5252',
                                fillOpacity: 0.25
                            }
                        }).addTo(AppState.map);

                        AppState.mapLayers.hazardZones = polygon;
                    }
                });
            }
        });
    }

    // Fit map bounds
    if (routeData.base_route && routeData.base_route.coordinates && routeData.base_route.coordinates.length > 0) {
        const routePoints = routeData.base_route.coordinates.map(coord => [coord[1], coord[0]]);
        const bounds = L.latLngBounds(routePoints);
        AppState.map.fitBounds(bounds, { padding: [50, 50] });
    }
}

// API status checking
function checkApiStatus() {
    fetch('/api/advisory?lat=14.5995&lng=120.9842&lang=english')
        .then(response => {
            if (response.ok) return response.json();
            throw new Error('Advisory service check response not ok');
        })
        .then(data => {
            updateApiStatus('earthquake', data.earthquakes !== undefined ? 'active' : 'warning');
            updateApiStatus('weather', data.weather && !data.weather.error ? 'active' : 'warning');
        })
        .catch(err => {
            console.error('API check error:', err);
            updateApiStatus('earthquake', 'error');
            updateApiStatus('weather', 'error');
        });

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
        updateApiStatus('routing', response.ok ? 'active' : 'warning');
    })
    .catch(() => {
        updateApiStatus('routing', 'error');
    });
}

function updateApiStatus(api, status) {
    const element = elements[`${api}Status`];
    if (!element) return;

    element.className = 'status-indicator';
    element.textContent = status.charAt(0).toUpperCase() + status.slice(1);

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

function showLoading(context) {
    console.log(`Loading ${context}...`);
}

function hideLoading(context) {
    console.log(`Finished loading ${context}`);
}

function showError(context, message) {
    alert(`Error (${context}): ${message}`);
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', init);
