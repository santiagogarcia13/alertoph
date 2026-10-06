/**
 * AlertoPH - USGS-Inspired Hazard & Safe Route Advisory Frontend
 */

// Global Application State
const AppState = {
    activeTab: 'route',
    map: null,
    phCenter: [12.8797, 121.7740],
    defaultZoom: 6,
    mapLayers: {
        baseRoute: null,
        safeRoute: null,
        hazardZones: null,
        earthquakesGroup: null,
        weatherGroup: null,
        advisoryMarker: null,
        originMarker: null,
        destMarker: null,
        radarLayer: null
    },
    radarActive: false,
    weatherSearchQuery: '',
    selectedWeatherRegion: 'all',
    earthquakes: [],
    weatherStations: [],
    currentAdvisory: null,
    currentRoute: null,
    mapPickingMode: null
};

// DOM References
const el = {
    // Nav tabs
    tabBtns: document.querySelectorAll('.tab-btn'),
    tabPanels: document.querySelectorAll('.tab-panel'),
    quakeBadge: document.getElementById('quake-badge'),

    // Chips
    chipUsgs: document.getElementById('chip-usgs'),
    chipWeather: document.getElementById('chip-weather'),
    chipRouting: document.getElementById('chip-routing'),

    // Routing Panel
    originInput: document.getElementById('origin-input'),
    destinationInput: document.getElementById('destination-input'),
    useCurrentLocationBtn: document.getElementById('use-current-location'),
    pickOriginBtn: document.getElementById('pick-origin'),
    pickDestinationBtn: document.getElementById('pick-destination'),
    clearPointsBtn: document.getElementById('clear-points'),
    calculateRouteBtn: document.getElementById('calculate-route-btn'),
    routeSummaryCard: document.getElementById('route-summary-card'),
    routeStatusTitle: document.getElementById('route-status-title'),
    routeSafetyBadge: document.getElementById('route-safety-badge'),
    routeDist: document.getElementById('route-dist'),
    routeTime: document.getElementById('route-time'),
    routeHazardsCount: document.getElementById('route-hazards-count'),
    routeAdviceBox: document.getElementById('route-advice-box'),
    routeAdviceText: document.getElementById('route-advice-text'),

    // Earthquake Panel
    earthquakeFeed: document.getElementById('earthquake-feed'),
    refreshQuakesBtn: document.getElementById('refresh-quakes-btn'),
    quakeFilterPills: document.querySelectorAll('.earthquake-feed-filters .filter-pill, #panel-earthquake .filter-pill'),

    // Weather Panel
    weatherStationList: document.getElementById('weather-station-list'),
    refreshWeatherBtn: document.getElementById('refresh-weather-btn'),
    weatherSearchInput: document.getElementById('weather-search-input'),
    weatherClearSearchBtn: document.getElementById('weather-clear-search-btn'),
    weatherFilterPills: document.querySelectorAll('.weather-filter-pills .filter-pill'),
    weatherStationCount: document.getElementById('weather-station-count'),
    weatherAlertCount: document.getElementById('weather-alert-count'),

    // Advisory Panel
    locationInput: document.getElementById('location-input'),
    searchBtn: document.getElementById('search-btn'),
    toggleCoordBtn: document.getElementById('toggle-coord-btn'),
    coordInputsDrawer: document.getElementById('coord-inputs-drawer'),
    latInput: document.getElementById('lat-input'),
    lngInput: document.getElementById('lng-input'),
    coordSearchBtn: document.getElementById('coord-search-btn'),
    pickAdvisoryBtn: document.getElementById('pick-advisory-location'),
    advisoryResults: document.getElementById('advisory-results'),
    advisoryLocation: document.getElementById('advisory-location'),
    advisoryTimestamp: document.getElementById('advisory-timestamp'),
    safetyAlertBox: document.getElementById('safety-alert-box'),
    safetySeverityTitle: document.getElementById('safety-severity-title'),
    safetySeverityDesc: document.getElementById('safety-severity-desc'),
    earthquakeData: document.getElementById('earthquake-data'),
    weatherData: document.getElementById('weather-data'),
    safetyAdvice: document.getElementById('safety-advice'),

    // Map UI
    mapModeIndicator: document.getElementById('map-mode-indicator'),
    mapRadarToggle: document.getElementById('map-radar-toggle'),
    mapRecenterBtn: document.getElementById('map-recenter-btn'),
    mapLegendToggle: document.getElementById('map-legend-toggle'),
    mapLegendCard: document.getElementById('map-legend-card'),
    legendCloseBtn: document.getElementById('legend-close-btn'),
    mobileToggleBtn: document.getElementById('mobile-toggle-btn'),
    mobileToggleLabel: document.getElementById('mobile-toggle-label'),
    sidebar: document.getElementById('sidebar')
};

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    setupEventListeners();
    setupTabSwitching();
    setupGeocodingAutocomplete();

    // Initial background data fetch
    loadEarthquakes(2.0);
    loadRegionalWeather();
    checkSystemHealth();

    // Mobile map fix: Force multiple invalidations on mobile devices
    if (window.innerWidth <= 900) {
        const mobileMapFix = () => {
            if (AppState.map) {
                AppState.map.invalidateSize();
            }
        };
        setTimeout(mobileMapFix, 100);
        setTimeout(mobileMapFix, 300);
        setTimeout(mobileMapFix, 600);
        setTimeout(mobileMapFix, 1000);
    }
});

/* -------------------------------------------------------------
   Map Initialization
------------------------------------------------------------- */
function initMap() {
    AppState.map = L.map('map', {
        zoomControl: true
    }).setView(AppState.phCenter, AppState.defaultZoom);

    // Free & Open Base Layers (100% Free, Zero API Key required, No Watermarks)
    const osmStandard = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    });

    const esriTopo = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri, USGS, NOAA',
        maxZoom: 18
    });

    const esriStreet = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri',
        maxZoom: 18
    });

    // Add default OpenStreetMap layer
    osmStandard.addTo(AppState.map);

    // Layer groups for dynamic data
    AppState.mapLayers.earthquakesGroup = L.layerGroup().addTo(AppState.map);
    AppState.mapLayers.weatherGroup = L.layerGroup().addTo(AppState.map);

    // Basemap selector
    L.control.layers({
        'OpenStreetMap': osmStandard,
        'Topographic (USGS/Esri)': esriTopo,
        'Street Map': esriStreet
    }, null, { position: 'bottomright' }).addTo(AppState.map);

    AppState.map.on('click', handleMapClick);

    // Mobile map initialization fix: ensure map tiles load correctly on mobile devices
    setTimeout(() => {
        if (AppState.map) {
            AppState.map.invalidateSize();
        }
    }, 100);

    // Additional invalidation after page fully loads (handles mobile layout shifts)
    window.addEventListener('load', () => {
        setTimeout(() => {
            if (AppState.map) {
                AppState.map.invalidateSize();
            }
        }, 250);
    });
}

/* -------------------------------------------------------------
   Tab and Mode Switching
------------------------------------------------------------- */
function setupTabSwitching() {
    el.tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            switchMode(tab);
        });
    });
}

function switchMode(tabName) {
    AppState.activeTab = tabName;

    // Update active tab buttons
    el.tabBtns.forEach(btn => {
        const isActive = btn.dataset.tab === tabName;
        btn.classList.toggle('active', isActive);
        btn.setAttribute('aria-selected', isActive);
    });

    // Update active panel
    el.tabPanels.forEach(panel => {
        panel.classList.toggle('active', panel.id === `panel-${tabName}`);
    });

    // Update Map Indicator & Layer visibility
    updateMapForActiveTab(tabName);

    // Invalidate map size on tab switch for responsive rendering
    if (AppState.map) {
        setTimeout(() => AppState.map.invalidateSize(), 150);
    }
}

function updateMapForActiveTab(tab) {
    const indicator = el.mapModeIndicator;

    switch (tab) {
        case 'route':
            indicator.innerHTML = '<i class="fas fa-route text-primary"></i> <span>Safe Route View</span>';
            AppState.mapLayers.earthquakesGroup.clearLayers();
            AppState.mapLayers.weatherGroup.clearLayers();
            if (AppState.currentRoute) {
                drawRouteOnMap(AppState.currentRoute);
            }
            break;

        case 'earthquake':
            indicator.innerHTML = '<i class="fas fa-bolt text-warning"></i> <span>USGS Seismic View</span>';
            renderEarthquakesOnMap(AppState.earthquakes);
            break;

        case 'weather':
            indicator.innerHTML = '<i class="fas fa-cloud-showers-heavy text-info"></i> <span>Weather & Rain Radar</span>';
            renderWeatherStationsOnMap(AppState.weatherStations);
            break;

        case 'advisory':
            indicator.innerHTML = '<i class="fas fa-search-location text-safe"></i> <span>Location Advisory View</span>';
            AppState.mapLayers.earthquakesGroup.clearLayers();
            AppState.mapLayers.weatherGroup.clearLayers();
            break;
    }
}

/* -------------------------------------------------------------
   Event Listeners Setup
------------------------------------------------------------- */
function setupEventListeners() {
    // Routing panel
    el.calculateRouteBtn.addEventListener('click', calculateRoute);
    el.useCurrentLocationBtn.addEventListener('click', useCurrentLocation);
    el.pickOriginBtn.addEventListener('click', () => startMapPicking('origin'));
    el.pickDestinationBtn.addEventListener('click', () => startMapPicking('destination'));
    el.clearPointsBtn.addEventListener('click', clearRoutePoints);

    // Advisory panel
    el.searchBtn.addEventListener('click', () => searchByLocation(el.locationInput.value));
    el.locationInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchByLocation(el.locationInput.value);
    });
    el.toggleCoordBtn.addEventListener('click', () => {
        const isHidden = el.coordInputsDrawer.style.display === 'none';
        el.coordInputsDrawer.style.display = isHidden ? 'flex' : 'none';
    });
    el.coordSearchBtn.addEventListener('click', searchByCoordinates);
    el.pickAdvisoryBtn.addEventListener('click', () => startMapPicking('advisory'));

    // Earthquake feed
    el.refreshQuakesBtn.addEventListener('click', () => loadEarthquakes(2.0));
    el.quakeFilterPills.forEach(pill => {
        pill.addEventListener('click', () => {
            el.quakeFilterPills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            const minMag = parseFloat(pill.dataset.minMag) || 2.0;
            loadEarthquakes(minMag);
        });
    });

    // Weather feed
    el.refreshWeatherBtn.addEventListener('click', loadRegionalWeather);

    // Weather Search & Regional Filter Controls
    if (el.weatherSearchInput) {
        el.weatherSearchInput.addEventListener('input', () => {
            AppState.weatherSearchQuery = el.weatherSearchInput.value.trim();
            if (el.weatherClearSearchBtn) {
                el.weatherClearSearchBtn.style.display = AppState.weatherSearchQuery ? 'inline-flex' : 'none';
            }
            filterAndRenderWeather();
        });
    }

    if (el.weatherClearSearchBtn) {
        el.weatherClearSearchBtn.addEventListener('click', () => {
            el.weatherSearchInput.value = '';
            AppState.weatherSearchQuery = '';
            el.weatherClearSearchBtn.style.display = 'none';
            filterAndRenderWeather();
            el.weatherSearchInput.focus();
        });
    }

    if (el.weatherFilterPills) {
        el.weatherFilterPills.forEach(pill => {
            pill.addEventListener('click', () => {
                el.weatherFilterPills.forEach(p => p.classList.remove('active'));
                pill.classList.add('active');
                AppState.selectedWeatherRegion = pill.dataset.region || 'all';
                filterAndRenderWeather();
            });
        });
    }

    // Map tools
    el.mapRecenterBtn.addEventListener('click', () => {
        AppState.map.setView(AppState.phCenter, AppState.defaultZoom);
    });

    if (el.mapRadarToggle) {
        el.mapRadarToggle.addEventListener('click', toggleRainRadar);
    }

    el.mapLegendToggle.addEventListener('click', () => {
        const isVisible = el.mapLegendCard.style.display !== 'none';
        el.mapLegendCard.style.display = isVisible ? 'none' : 'flex';
        el.mapLegendCard.classList.toggle('mobile-open');
    });

    el.legendCloseBtn.addEventListener('click', () => {
        el.mapLegendCard.style.display = 'none';
        el.mapLegendCard.classList.remove('mobile-open');
    });

    // Mobile drawer toggle - zoom.earth style slide-up panel with swipe support
    if (el.mobileToggleBtn) {
        const expandDrawer = () => {
            el.sidebar.classList.add('expanded');
            el.mobileToggleBtn.innerHTML = '<i class="fas fa-chevron-down"></i> <span>Hide Controls</span>';
            setTimeout(() => {
                if (AppState.map) AppState.map.invalidateSize();
            }, 350);
        };

        const collapseDrawer = () => {
            el.sidebar.classList.remove('expanded');
            el.mobileToggleBtn.innerHTML = '<i class="fas fa-chevron-up"></i> <span>Expand Controls</span>';
            setTimeout(() => {
                if (AppState.map) AppState.map.invalidateSize();
            }, 350);
        };

        const toggleDrawer = () => {
            if (el.sidebar.classList.contains('expanded')) {
                collapseDrawer();
            } else {
                expandDrawer();
            }
        };

        el.mobileToggleBtn.addEventListener('click', toggleDrawer);

        // Touch/swipe interaction for drawer handle
        let touchStartY = 0;
        let touchStartTime = 0;
        let isDragging = false;

        el.sidebar.addEventListener('touchstart', (e) => {
            if (window.innerWidth > 900) return;

            const rect = el.sidebar.getBoundingClientRect();
            const touchY = e.touches[0].clientY - rect.top;

            // Only handle touches on the handle area (top 32px)
            if (touchY < 32 && !el.sidebar.classList.contains('expanded')) {
                touchStartY = e.touches[0].clientY;
                touchStartTime = Date.now();
                isDragging = true;
            }
        }, { passive: true });

        el.sidebar.addEventListener('touchmove', (e) => {
            if (!isDragging) return;

            const touchY = e.touches[0].clientY;
            const deltaY = touchStartY - touchY;

            // Swipe up to expand
            if (deltaY > 50) {
                isDragging = false;
                expandDrawer();
            }
        }, { passive: true });

        el.sidebar.addEventListener('touchend', (e) => {
            if (!isDragging) return;

            const touchEndY = e.changedTouches[0].clientY;
            const deltaY = touchStartY - touchEndY;
            const deltaTime = Date.now() - touchStartTime;

            // Quick swipe up or significant drag
            if ((deltaTime < 300 && deltaY > 20) || deltaY > 50) {
                expandDrawer();
            }

            isDragging = false;
        }, { passive: true });

        // Click outside drawer to close on mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 900 &&
                el.sidebar.classList.contains('expanded') &&
                !el.sidebar.contains(e.target) &&
                !el.mobileToggleBtn.contains(e.target)) {
                collapseDrawer();
            }
        });
    }

    // Responsive window resize & orientation change handler
    window.addEventListener('resize', () => {
        if (AppState.map) {
            AppState.map.invalidateSize();
        }
    });

    window.addEventListener('orientationchange', () => {
        setTimeout(() => {
            if (AppState.map) AppState.map.invalidateSize();
        }, 200);
    });
}

/* -------------------------------------------------------------
   Map Interaction & Waypoints
------------------------------------------------------------- */
function startMapPicking(mode) {
    AppState.mapPickingMode = mode;
    const labels = {
        origin: 'Origin point',
        destination: 'Destination point',
        advisory: 'Location to check'
    };
    alert(`Click anywhere on the map to set ${labels[mode]}.`);
}

function handleMapClick(e) {
    if (!AppState.mapPickingMode) return;

    const lat = e.latlng.lat;
    const lng = e.latlng.lng;

    switch (AppState.mapPickingMode) {
        case 'origin':
            setOriginPoint(lat, lng, `${lat.toFixed(4)}, ${lng.toFixed(4)}`);
            break;
        case 'destination':
            setDestinationPoint(lat, lng, `${lat.toFixed(4)}, ${lng.toFixed(4)}`);
            break;
        case 'advisory':
            el.latInput.value = lat.toFixed(4);
            el.lngInput.value = lng.toFixed(4);
            el.locationInput.value = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
            setAdvisoryMarker(lat, lng, 'Selected Location');
            searchByCoordinates();
            break;
    }

    AppState.mapPickingMode = null;
}

function setOriginPoint(lat, lng, label) {
    if (AppState.mapLayers.originMarker) {
        AppState.map.removeLayer(AppState.mapLayers.originMarker);
    }

    AppState.mapLayers.originMarker = L.marker([lat, lng], {
        icon: L.divIcon({
            className: 'custom-pin origin-pin',
            html: '<div style="background:#2563eb;color:#fff;width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;box-shadow:0 3px 8px rgba(0,0,0,0.3);border:2px solid #fff;"><i class="fas fa-map-marker-alt"></i></div>',
            iconSize: [30, 30],
            iconAnchor: [15, 30]
        })
    }).addTo(AppState.map);

    el.originInput.value = label || `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
}

function setDestinationPoint(lat, lng, label) {
    if (AppState.mapLayers.destMarker) {
        AppState.map.removeLayer(AppState.mapLayers.destMarker);
    }

    AppState.mapLayers.destMarker = L.marker([lat, lng], {
        icon: L.divIcon({
            className: 'custom-pin dest-pin',
            html: '<div style="background:#f59e0b;color:#fff;width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;box-shadow:0 3px 8px rgba(0,0,0,0.3);border:2px solid #fff;"><i class="fas fa-flag-checkered"></i></div>',
            iconSize: [30, 30],
            iconAnchor: [15, 30]
        })
    }).addTo(AppState.map);

    el.destinationInput.value = label || `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
}

function setAdvisoryMarker(lat, lng, title) {
    if (AppState.mapLayers.advisoryMarker) {
        AppState.map.removeLayer(AppState.mapLayers.advisoryMarker);
    }

    AppState.mapLayers.advisoryMarker = L.marker([lat, lng], {
        icon: L.divIcon({
            className: 'custom-pin advisory-pin',
            html: '<div style="background:#10b981;color:#fff;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;box-shadow:0 3px 8px rgba(0,0,0,0.3);border:2px solid #fff;"><i class="fas fa-search-location"></i></div>',
            iconSize: [32, 32],
            iconAnchor: [16, 32]
        })
    }).addTo(AppState.map);

    if (title) {
        AppState.mapLayers.advisoryMarker.bindPopup(`<strong>${escapeHtml(title)}</strong>`).openPopup();
    }

    AppState.map.setView([lat, lng], 11);
}

function clearRoutePoints() {
    if (AppState.mapLayers.originMarker) {
        AppState.map.removeLayer(AppState.mapLayers.originMarker);
        AppState.mapLayers.originMarker = null;
    }
    if (AppState.mapLayers.destMarker) {
        AppState.map.removeLayer(AppState.mapLayers.destMarker);
        AppState.mapLayers.destMarker = null;
    }
    clearRouteLayers();
    el.originInput.value = '';
    el.destinationInput.value = '';
    el.routeSummaryCard.style.display = 'none';
}

function clearRouteLayers() {
    if (AppState.mapLayers.baseRoute) {
        AppState.map.removeLayer(AppState.mapLayers.baseRoute);
        AppState.mapLayers.baseRoute = null;
    }
    if (AppState.mapLayers.safeRoute) {
        AppState.map.removeLayer(AppState.mapLayers.safeRoute);
        AppState.mapLayers.safeRoute = null;
    }
    if (AppState.mapLayers.hazardZones) {
        AppState.map.removeLayer(AppState.mapLayers.hazardZones);
        AppState.mapLayers.hazardZones = null;
    }
}

/* -------------------------------------------------------------
   Dynamic Geocoding Autocomplete
------------------------------------------------------------- */
const debounceTimers = new Map();

function setupGeocodingAutocomplete() {
    attachGeocode(el.originInput, (item) => {
        setOriginPoint(item.latitude, item.longitude, item.display_name || item.name);
    });

    attachGeocode(el.destinationInput, (item) => {
        setDestinationPoint(item.latitude, item.longitude, item.display_name || item.name);
    });

    attachGeocode(el.locationInput, (item) => {
        el.locationInput.value = item.display_name || item.name;
        el.latInput.value = item.latitude.toFixed(4);
        el.lngInput.value = item.longitude.toFixed(4);
        setAdvisoryMarker(item.latitude, item.longitude, item.name);
        searchByCoordinates();
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.input-wrapper') && !e.target.closest('.autocomplete-container')) {
            clearAllAutocomplete();
        }
    });
}

function attachGeocode(input, onSelect) {
    if (!input) return;

    input.addEventListener('input', () => {
        const q = input.value.trim();
        if (q.length < 2) {
            clearAutocompleteFor(input);
            return;
        }

        if (debounceTimers.has(input)) clearTimeout(debounceTimers.get(input));

        debounceTimers.set(input, setTimeout(() => {
            fetch(`/api/geocode?q=${encodeURIComponent(q)}&limit=5`)
                .then(r => r.json())
                .then(data => {
                    if (data.results && data.results.length > 0) {
                        renderAutocomplete(input, data.results, onSelect);
                    } else {
                        clearAutocompleteFor(input);
                    }
                })
                .catch(() => clearAutocompleteFor(input));
        }, 300));
    });
}

function renderAutocomplete(input, items, onSelect) {
    clearAutocompleteFor(input);

    const container = document.createElement('div');
    container.className = 'autocomplete-container';

    items.forEach(item => {
        const row = document.createElement('div');
        row.className = 'autocomplete-item';
        row.innerHTML = `
            <strong><i class="fas fa-location-dot" style="color:#2563eb; margin-right:6px;"></i>${escapeHtml(item.name)}</strong>
            <small>${escapeHtml(item.display_name || item.region || `${item.latitude.toFixed(3)}, ${item.longitude.toFixed(3)}`)}</small>
        `;
        row.addEventListener('click', () => {
            clearAutocompleteFor(input);
            onSelect(item);
        });
        container.appendChild(row);
    });

    input.parentNode.appendChild(container);
}

function clearAutocompleteFor(input) {
    const parent = input.parentNode;
    if (parent) {
        const c = parent.querySelector('.autocomplete-container');
        if (c) c.remove();
    }
}

function clearAllAutocomplete() {
    document.querySelectorAll('.autocomplete-container').forEach(c => c.remove());
}

/* -------------------------------------------------------------
   Safe Route Calculation & Visualization
------------------------------------------------------------- */
async function resolveInputCoords(str) {
    const parts = str.split(',').map(s => parseFloat(s.trim()));
    if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
        return { lat: parts[0], lng: parts[1] };
    }

    try {
        const res = await fetch(`/api/geocode?q=${encodeURIComponent(str)}&limit=1`);
        const data = await res.json();
        if (data.results && data.results.length > 0) {
            return { lat: data.results[0].latitude, lng: data.results[0].longitude };
        }
    } catch (e) {
        console.warn('Geocoding resolve failed:', e);
    }
    return null;
}

async function calculateRoute() {
    const origVal = el.originInput.value.trim();
    const destVal = el.destinationInput.value.trim();

    if (!origVal || !destVal) {
        alert('Please provide both Origin and Destination.');
        return;
    }

    el.calculateRouteBtn.disabled = true;
    el.calculateRouteBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Calculating Safe Route...';
    clearAllAutocomplete();

    const originCoords = await resolveInputCoords(origVal);
    const destCoords = await resolveInputCoords(destVal);

    if (!originCoords || !destCoords) {
        el.calculateRouteBtn.disabled = false;
        el.calculateRouteBtn.innerHTML = '<i class="fas fa-shield"></i> Calculate Safe Route';
        alert('Could not pinpoint coordinates for origin or destination. Please choose a suggestion from search.');
        return;
    }

    setOriginPoint(originCoords.lat, originCoords.lng);
    setDestinationPoint(destCoords.lat, destCoords.lng);
    clearRouteLayers();

    try {
        const response = await fetch('/api/route', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                origin: originCoords,
                destination: destCoords,
                lang: 'english'
            })
        });

        const data = await response.json();
        if (!response.ok || data.error) throw new Error(data.error || 'Failed to calculate route');

        AppState.currentRoute = data;
        displayRouteSummary(data);
        drawRouteOnMap(data);
        updateHealthChip(el.chipRouting, true);

    } catch (err) {
        alert(`Routing error: ${err.message}`);
        updateHealthChip(el.chipRouting, false);
    } finally {
        el.calculateRouteBtn.disabled = false;
        el.calculateRouteBtn.innerHTML = '<i class="fas fa-shield"></i> Calculate Safe Route';
    }
}

function displayRouteSummary(routeData) {
    el.routeSummaryCard.style.display = 'flex';

    const activeRoute = routeData.adjusted_route || routeData.base_route;
    const hasHazard = (routeData.hazards?.total_count || 0) > 0;

    // Safety badge & title
    if (hasHazard) {
        el.routeStatusTitle.textContent = 'Hazard Avoidance Detour Active';
        el.routeSafetyBadge.textContent = 'ADJUSTED (SAFE)';
        el.routeSafetyBadge.className = 'safety-badge';
    } else {
        el.routeStatusTitle.textContent = 'Direct Safe Route';
        el.routeSafetyBadge.textContent = 'CLEAR / SAFE';
        el.routeSafetyBadge.className = 'safety-badge';
    }

    // Distance
    if (activeRoute?.distance_km !== undefined) {
        const km = parseFloat(activeRoute.distance_km);
        el.routeDist.textContent = isNaN(km) ? `${activeRoute.distance_km}` : `${km.toFixed(1)} km`;
    } else {
        el.routeDist.textContent = '-';
    }

    // Duration
    if (activeRoute?.duration_min !== undefined) {
        const mins = parseFloat(activeRoute.duration_min);
        if (!isNaN(mins)) {
            if (mins >= 60) {
                const hrs = Math.floor(mins / 60);
                const rem = Math.round(mins % 60);
                el.routeTime.textContent = `${hrs}h ${rem}m`;
            } else {
                el.routeTime.textContent = `${Math.round(mins)} min`;
            }
        } else {
            el.routeTime.textContent = `${activeRoute.duration_min}`;
        }
    } else {
        el.routeTime.textContent = '-';
    }

    // Hazard Count
    el.routeHazardsCount.textContent = routeData.hazards?.total_count || 0;

    // Advice text
    el.routeAdviceText.textContent = routeData.advice?.summary || 'Route is monitored for active seismic and flood hazards.';
}

function drawRouteOnMap(routeData) {
    clearRouteLayers();

    const boundsPoints = [];

    // 1. Draw Base/Direct Route
    if (routeData.base_route?.coordinates?.length > 0) {
        const basePts = routeData.base_route.coordinates.map(c => [c[1], c[0]]);
        AppState.mapLayers.baseRoute = L.polyline(basePts, {
            color: routeData.adjusted_route ? '#64748b' : '#10b981',
            weight: routeData.adjusted_route ? 4 : 6,
            dashArray: routeData.adjusted_route ? '6, 6' : null,
            opacity: 0.8
        }).addTo(AppState.map);

        basePts.forEach(p => boundsPoints.push(p));
    }

    // 2. Draw Safe / Detoured Route in Vibrant Emerald Green
    if (routeData.adjusted_route?.coordinates?.length > 0) {
        const safePts = routeData.adjusted_route.coordinates.map(c => [c[1], c[0]]);
        AppState.mapLayers.safeRoute = L.polyline(safePts, {
            color: '#10b981',
            weight: 6,
            opacity: 0.95
        }).addTo(AppState.map);

        safePts.forEach(p => boundsPoints.push(p));
    }

    // 3. Draw Flood & Hazard Zones in Semi-Transparent Red
    if (routeData.hazard_zones?.length > 0) {
        const zoneFeatures = [];
        routeData.hazard_zones.forEach(zone => {
            if (zone.geojson?.features) {
                zone.geojson.features.forEach(f => zoneFeatures.push(f));
            }
        });

        if (zoneFeatures.length > 0) {
            AppState.mapLayers.hazardZones = L.geoJSON(zoneFeatures, {
                style: {
                    color: '#ef4444',
                    weight: 2,
                    fillColor: '#ef4444',
                    fillOpacity: 0.3
                }
            }).addTo(AppState.map);
        }
    }

    if (boundsPoints.length > 0) {
        AppState.map.fitBounds(L.latLngBounds(boundsPoints), { padding: [40, 40] });
    }
}

/* -------------------------------------------------------------
   USGS Earthquake Feed & Map Layer
------------------------------------------------------------- */
function loadEarthquakes(minMag = 2.0) {
    el.earthquakeFeed.innerHTML = '<div class="loading-state"><i class="fas fa-spinner fa-spin"></i> Loading USGS feed...</div>';

    fetch(`/api/earthquakes?min_mag=${minMag}`)
        .then(r => r.json())
        .then(data => {
            AppState.earthquakes = data.earthquakes || [];
            el.quakeBadge.textContent = AppState.earthquakes.length;
            renderEarthquakeFeed(AppState.earthquakes);

            if (AppState.activeTab === 'earthquake') {
                renderEarthquakesOnMap(AppState.earthquakes);
            }

            updateHealthChip(el.chipUsgs, true);
        })
        .catch(err => {
            console.error('Earthquake fetch error:', err);
            el.earthquakeFeed.innerHTML = '<div class="error-state">Failed to load earthquake data.</div>';
            updateHealthChip(el.chipUsgs, false);
        });
}

function renderEarthquakeFeed(quakes) {
    if (!quakes || quakes.length === 0) {
        el.earthquakeFeed.innerHTML = '<div class="no-data">No recent earthquakes recorded in this magnitude range.</div>';
        return;
    }

    let html = '';
    quakes.forEach(q => {
        const mag = q.magnitude ? q.magnitude.toFixed(1) : '?';
        const magCategory = getMagCategory(q.magnitude);
        const timeAgo = formatTimeAgo(q.time);

        html += `
            <div class="quake-card mag-${magCategory}" onclick="focusEarthquake(${q.latitude}, ${q.longitude}, ${q.magnitude})">
                <div class="quake-mag-badge ${magCategory}">${mag}</div>
                <div class="quake-info">
                    <span class="quake-place">${escapeHtml(q.place || 'Philippine Region')}</span>
                    <div class="quake-meta">
                        <span><i class="far fa-clock"></i> ${timeAgo}</span>
                        <span><i class="fas fa-arrows-down-to-line"></i> ${q.depth_km ? q.depth_km.toFixed(0) : '10'} km depth</span>
                    </div>
                </div>
            </div>
        `;
    });

    el.earthquakeFeed.innerHTML = html;
}

function renderEarthquakesOnMap(quakes) {
    AppState.mapLayers.earthquakesGroup.clearLayers();

    quakes.forEach(q => {
        const mag = q.magnitude || 2.0;
        const color = getMagColor(mag);
        const radius = Math.max(5, mag * 3.5);

        const circle = L.circleMarker([q.latitude, q.longitude], {
            radius: radius,
            fillColor: color,
            color: '#ffffff',
            weight: 1.5,
            opacity: 0.9,
            fillOpacity: 0.75
        });

        circle.bindPopup(`
            <div style="font-family: inherit;">
                <h4 style="margin:0 0 4px; color:${color}; font-weight:800;">Magnitude ${mag.toFixed(1)}</h4>
                <p style="margin:0 0 4px; font-weight:600;">${escapeHtml(q.place || 'Philippine Region')}</p>
                <small style="color:#64748b;">Depth: ${q.depth_km?.toFixed(0) || 10} km | ${formatTimeAgo(q.time)}</small>
            </div>
        `);

        AppState.mapLayers.earthquakesGroup.addLayer(circle);
    });
}

function focusEarthquake(lat, lng, mag) {
    switchMode('earthquake');
    if (window.innerWidth <= 900) {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    AppState.map.flyTo([lat, lng], 9, { duration: 1.2 });
}

/* -------------------------------------------------------------
   Weather & Rain Stations Feed, Search, & Radar Map Layer
------------------------------------------------------------- */
function loadRegionalWeather() {
    if (el.weatherStationList) {
        el.weatherStationList.innerHTML = '<div class="loading-state"><i class="fas fa-spinner fa-spin"></i> Fetching Philippine weather stations...</div>';
    }

    fetch('/api/weather/regional')
        .then(r => r.json())
        .then(data => {
            AppState.weatherStations = data.stations || [];
            filterAndRenderWeather();

            if (AppState.activeTab === 'weather') {
                renderWeatherStationsOnMap(AppState.weatherStations);
            }

            updateHealthChip(el.chipWeather, true);
        })
        .catch(err => {
            console.error('Weather stations error:', err);
            if (el.weatherStationList) {
                el.weatherStationList.innerHTML = '<div class="error-state">Failed to load weather stations.</div>';
            }
            updateHealthChip(el.chipWeather, false);
        });
}

function filterAndRenderWeather() {
    let filtered = AppState.weatherStations || [];
    const query = (AppState.weatherSearchQuery || '').toLowerCase().trim();
    const region = AppState.selectedWeatherRegion || 'all';

    // 1. Text Search Filter (name, province, region)
    if (query) {
        filtered = filtered.filter(s => {
            const nameMatch = s.name && s.name.toLowerCase().includes(query);
            const provMatch = s.province && s.province.toLowerCase().includes(query);
            const regMatch = s.region && s.region.toLowerCase().includes(query);
            return nameMatch || provMatch || regMatch;
        });
    }

    // 2. Region / Alert Category Filter
    if (region === 'alert') {
        filtered = filtered.filter(s => {
            const rain = s.rain_1h || 0;
            const pagasaLevel = s.pagasa_level || (rain >= 30 ? 'red' : rain >= 15 ? 'orange' : rain >= 7.5 ? 'yellow' : 'light');
            return s.is_heavy_rain || rain >= 7.5 || pagasaLevel === 'yellow' || pagasaLevel === 'orange' || pagasaLevel === 'red';
        });
    } else if (region !== 'all') {
        filtered = filtered.filter(s => s.region === region);
    }

    renderWeatherStationList(filtered);
    updateWeatherStatusBar(filtered, AppState.weatherStations);

    if (AppState.activeTab === 'weather') {
        renderWeatherStationsOnMap(filtered);
    }
}

function updateWeatherStatusBar(filtered, all) {
    if (!el.weatherStationCount) return;

    const totalCount = all.length;
    const filteredCount = filtered.length;
    const alertCount = all.filter(s => (s.rain_1h || 0) >= 7.5 || s.is_heavy_rain).length;

    if (AppState.weatherSearchQuery || AppState.selectedWeatherRegion !== 'all') {
        el.weatherStationCount.innerHTML = `<i class="fas fa-tower-broadcast"></i> Showing <strong>${filteredCount}</strong> of ${totalCount} stations`;
    } else {
        el.weatherStationCount.innerHTML = `<i class="fas fa-tower-broadcast"></i> Monitoring <strong>${totalCount}</strong> Philippine stations`;
    }

    if (el.weatherAlertCount) {
        if (alertCount > 0) {
            el.weatherAlertCount.style.display = 'inline-flex';
            el.weatherAlertCount.innerHTML = `<i class="fas fa-triangle-exclamation"></i> ${alertCount} Heavy Rain Warning${alertCount > 1 ? 's' : ''}`;
        } else {
            el.weatherAlertCount.style.display = 'none';
        }
    }
}

function renderWeatherStationList(stations) {
    if (!el.weatherStationList) return;

    if (!stations || stations.length === 0) {
        el.weatherStationList.innerHTML = `
            <div class="no-data">
                <i class="fas fa-magnifying-glass" style="font-size:1.5rem; margin-bottom:8px; opacity:0.6;"></i><br>
                No weather stations match your search or filter.
            </div>
        `;
        return;
    }

    let html = '';
    stations.forEach(s => {
        const rain = s.rain_1h || 0;
        const level = s.pagasa_level || (rain >= 30 ? 'red' : rain >= 15 ? 'orange' : rain >= 7.5 ? 'yellow' : rain >= 2.5 ? 'moderate' : 'light');
        const badgeLabel = s.pagasa_badge_label || (
            level === 'red' ? 'Red (Torrential)' :
            level === 'orange' ? 'Orange (Intense)' :
            level === 'yellow' ? 'Yellow (Heavy)' :
            level === 'moderate' ? 'Moderate' : 'Light / Clear'
        );
        const advice = s.pagasa_advice || (
            level === 'red' ? 'Torrential rain: Severe flooding expected. Evacuate low areas.' :
            level === 'orange' ? 'Intense rain: Flooding is threatening. Be alert.' :
            level === 'yellow' ? 'Heavy rain: Flooding possible in low-lying areas.' :
            level === 'moderate' ? 'Moderate rain: Wet roads and reduced visibility.' : 'Normal weather conditions.'
        );

        html += `
            <div class="station-card pagasa-${level}" onclick="focusStation(${s.lat}, ${s.lng})">
                <div class="station-info">
                    <div class="station-title-row">
                        <span class="station-city">${escapeHtml(s.name)}</span>
                        <span class="pagasa-badge ${level}">${escapeHtml(badgeLabel)}</span>
                    </div>
                    <div class="station-sub-meta">
                        <span><i class="fas fa-location-dot"></i> ${escapeHtml(s.province || s.region || 'Philippines')}</span>
                        <span>•</span>
                        <span>${escapeHtml(s.condition || 'Clear')}</span>
                    </div>
                    <div class="station-advice-line">
                        <i class="fas fa-shield-halved"></i> ${escapeHtml(advice)}
                    </div>
                </div>
                <div class="station-metrics">
                    <span class="station-temp">${s.temperature !== undefined ? `${Math.round(s.temperature)}°C` : '-'}</span>
                    <span class="station-rain ${rain >= 7.5 ? 'heavy' : ''}">
                        <i class="fas fa-droplet"></i> ${rain.toFixed(1)} mm/h
                    </span>
                </div>
            </div>
        `;
    });

    el.weatherStationList.innerHTML = html;
}

function renderWeatherStationsOnMap(stations) {
    AppState.mapLayers.weatherGroup.clearLayers();

    stations.forEach(s => {
        const rain = s.rain_1h || 0;
        const level = s.pagasa_level || (rain >= 30 ? 'red' : rain >= 15 ? 'orange' : rain >= 7.5 ? 'yellow' : rain >= 2.5 ? 'moderate' : 'light');
        const isHeavy = rain >= 7.5;
        const badgeLabel = s.pagasa_badge_label || (
            level === 'red' ? 'PAGASA Red Warning' :
            level === 'orange' ? 'PAGASA Orange Warning' :
            level === 'yellow' ? 'PAGASA Yellow Warning' :
            level === 'moderate' ? 'Moderate Rain' : 'Light / Clear'
        );

        const iconHtml = `
            <div class="custom-weather-marker level-${level} ${isHeavy ? 'heavy-rain' : ''}">
                <i class="fas ${isHeavy ? 'fa-cloud-bolt text-danger' : rain >= 2.5 ? 'fa-cloud-showers-heavy' : 'fa-cloud-sun text-info'}"></i>
                <span>${s.temperature !== undefined ? Math.round(s.temperature) : '-'}°C</span>
            </div>
        `;

        const marker = L.marker([s.lat, s.lng], {
            icon: L.divIcon({
                className: 'custom-weather-div',
                html: iconHtml,
                iconSize: [68, 28],
                iconAnchor: [34, 14]
            })
        });

        marker.bindPopup(`
            <div style="font-family: inherit; min-width: 190px;">
                <h4 style="margin:0 0 4px; font-weight:800; font-size:0.95rem;">${escapeHtml(s.name)}</h4>
                <p style="margin:0 0 4px; color:#64748b; font-size:0.8rem;">${escapeHtml(s.province || '')} (${escapeHtml(s.region || 'Philippines')})</p>
                <div style="margin:6px 0; padding:4px 8px; border-radius:4px; font-size:0.75rem; font-weight:700; background:${level === 'red' ? '#ef4444' : level === 'orange' ? '#f97316' : level === 'yellow' ? '#eab308' : level === 'moderate' ? '#3b82f6' : '#10b981'}; color:#ffffff;">
                    ${escapeHtml(badgeLabel)}
                </div>
                <p style="margin:4px 0; font-size:0.85rem;"><strong>${s.temperature?.toFixed(1) || '-'}°C</strong> - ${escapeHtml(s.condition || '')}</p>
                <p style="margin:4px 0; color:${isHeavy ? '#ef4444' : '#0284c7'}; font-weight:700; font-size:0.82rem;">
                    <i class="fas fa-droplet"></i> Rainfall: ${rain.toFixed(1)} mm/h
                </p>
                <p style="margin:6px 0 0; font-size:0.75rem; line-height:1.3; color:#334155;">
                    ${escapeHtml(s.pagasa_advice || 'Standard monitoring.')}
                </p>
            </div>
        `);

        AppState.mapLayers.weatherGroup.addLayer(marker);
    });
}

function focusStation(lat, lng) {
    switchMode('weather');
    if (window.innerWidth <= 900) {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    AppState.map.flyTo([lat, lng], 10, { duration: 1.2 });
}

/* -------------------------------------------------------------
   Precipitation Rain Radar Map Tile Layer
------------------------------------------------------------- */
async function toggleRainRadar() {
    const btn = el.mapRadarToggle;

    if (AppState.radarActive) {
        // Deactivate Radar
        if (AppState.mapLayers.radarLayer) {
            AppState.map.removeLayer(AppState.mapLayers.radarLayer);
            AppState.mapLayers.radarLayer = null;
        }
        AppState.radarActive = false;
        if (btn) btn.classList.remove('active');
        return;
    }

    // Activate Radar
    if (btn) btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Radar...</span>';

    try {
        // Fetch latest RainViewer timestamp for real-time radar satellite overlay
        const resp = await fetch('https://api.rainviewer.com/public/weather-maps.json');
        const data = await resp.json();

        let radarPath = '/v2/radar/nowcast_0';
        if (data && data.radar && data.radar.past && data.radar.past.length > 0) {
            const latest = data.radar.past[data.radar.past.length - 1];
            radarPath = latest.path;
        }

        const tileUrl = `https://tilecache.rainviewer.com${radarPath}/256/{z}/{x}/{y}/2/1_1.png`;

        AppState.mapLayers.radarLayer = L.tileLayer(tileUrl, {
            opacity: 0.72,
            maxZoom: 18,
            attribution: '&copy; <a href="https://www.rainviewer.com/" target="_blank">RainViewer</a> Radar'
        }).addTo(AppState.map);

        AppState.radarActive = true;
        if (btn) {
            btn.classList.add('active');
            btn.innerHTML = '<i class="fas fa-cloud-rain"></i> <span>Radar Active</span>';
        }
    } catch (err) {
        console.warn('RainViewer API fetch failed, falling back to direct tile cache:', err);
        // Fallback tile url
        AppState.mapLayers.radarLayer = L.tileLayer('https://tilecache.rainviewer.com/v2/radar/nowcast_0/256/{z}/{x}/{y}/2/1_1.png', {
            opacity: 0.72,
            maxZoom: 18,
            attribution: '&copy; <a href="https://www.rainviewer.com/" target="_blank">RainViewer</a> Radar'
        }).addTo(AppState.map);

        AppState.radarActive = true;
        if (btn) {
            btn.classList.add('active');
            btn.innerHTML = '<i class="fas fa-cloud-rain"></i> <span>Radar Active</span>';
        }
    }
}

/* -------------------------------------------------------------
   Location Advisory Query
------------------------------------------------------------- */
function searchByLocation(query) {
    if (!query.trim()) {
        alert('Please enter a location or landmark name.');
        return;
    }

    clearAllAutocomplete();
    fetchAdvisory(`/api/advisory?location=${encodeURIComponent(query)}&lang=english`);
}

function searchByCoordinates() {
    const lat = parseFloat(el.latInput.value);
    const lng = parseFloat(el.lngInput.value);

    if (isNaN(lat) || isNaN(lng) || lat < -90 || lat > 90 || lng < -180 || lng > 180) {
        alert('Please enter valid latitude (-90 to 90) and longitude (-180 to 180).');
        return;
    }

    clearAllAutocomplete();
    fetchAdvisory(`/api/advisory?lat=${lat}&lng=${lng}&lang=english`);
}

async function fetchAdvisory(url) {
    el.searchBtn.disabled = true;
    el.searchBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

    try {
        const resp = await fetch(url);
        const data = await resp.json();
        if (!resp.ok || data.error) throw new Error(data.error || 'Advisory request failed');

        AppState.currentAdvisory = data;
        displayAdvisoryReport(data);

        if (data.location?.latitude && data.location?.longitude) {
            setAdvisoryMarker(data.location.latitude, data.location.longitude, data.location.name);
        }

    } catch (e) {
        alert(`Advisory search error: ${e.message}`);
    } finally {
        el.searchBtn.disabled = false;
        el.searchBtn.innerHTML = '<i class="fas fa-search"></i> Check';
    }
}

function displayAdvisoryReport(data) {
    el.advisoryResults.style.display = 'flex';
    el.advisoryLocation.textContent = data.location?.name || 'Philippine Location';
    el.advisoryTimestamp.textContent = `Updated: ${new Date(data.timestamp).toLocaleTimeString()}`;

    const sev = (data.advisory?.overall_severity || 'low').toLowerCase();
    el.safetyAlertBox.className = `overall-alert-box ${sev}`;
    el.safetySeverityTitle.textContent = `${sev.toUpperCase()} RISK LEVEL`;
    el.safetySeverityDesc.textContent = data.advisory?.overall_summary || 'Conditions are stable.';

    // Earthquake Proximity
    if (data.earthquakes && data.earthquakes.length > 0) {
        const nearest = data.earthquakes[0];
        el.earthquakeData.innerHTML = `
            <strong>M${nearest.magnitude?.toFixed(1) || '?'} Earthquake</strong><br>
            <span style="color:#64748b;">${escapeHtml(nearest.place || '')} (${nearest.distance_km?.toFixed(0) || '?'} km away)</span>
        `;
    } else {
        el.earthquakeData.innerHTML = '<span style="color:#10b981; font-weight:600;"><i class="fas fa-check"></i> No active earthquakes within 200 km</span>';
    }

    // Weather Data
    if (data.weather && !data.weather.error) {
        const w = data.weather;
        const rain = w.rain_1h || 0;
        const isHeavy = rain >= 7.5;
        el.weatherData.innerHTML = `
            <strong>${w.temperature?.toFixed(1) || '-'}°C - ${escapeHtml(w.weather?.[0]?.description || '')}</strong><br>
            <span style="color:${isHeavy ? '#ef4444' : '#64748b'}; font-weight:${isHeavy ? '700' : 'normal'}">
                Rainfall: ${rain.toFixed(1)} mm/h ${isHeavy ? '(Heavy Rain Warning)' : ''}
            </span>
        `;
    } else {
        el.weatherData.innerHTML = '<span style="color:#64748b;">Weather data temporarily unavailable</span>';
    }

    // Specific Advice
    if (data.advisory?.all_advice && data.advisory.all_advice.length > 0) {
        el.safetyAdvice.innerHTML = data.advisory.all_advice.map(a => `<div><i class="fas fa-circle-dot" style="font-size:0.65rem; margin-right:6px;"></i> ${escapeHtml(a)}</div>`).join('');
    } else {
        el.safetyAdvice.innerHTML = 'No emergency precautions required. Standard safety awareness advised.';
    }
}

/* -------------------------------------------------------------
   System Health Check & Helpers
------------------------------------------------------------- */
function checkSystemHealth() {
    fetch('/api/advisory?lat=14.5995&lng=120.9842&lang=english')
        .then(r => r.json())
        .then(data => {
            updateHealthChip(el.chipUsgs, !!data.earthquakes);
            updateHealthChip(el.chipWeather, !!data.weather && !data.weather.error);
        })
        .catch(() => {
            updateHealthChip(el.chipUsgs, false);
            updateHealthChip(el.chipWeather, false);
        });
}

function updateHealthChip(chipEl, isHealthy) {
    if (!chipEl) return;
    chipEl.classList.toggle('error', !isHealthy);
}

function useCurrentLocation() {
    if (!navigator.geolocation) {
        alert('Geolocation is not supported by your browser.');
        return;
    }

    el.useCurrentLocationBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

    navigator.geolocation.getCurrentPosition(
        pos => {
            const lat = pos.coords.latitude;
            const lng = pos.coords.longitude;
            setOriginPoint(lat, lng, 'My Location');
            el.useCurrentLocationBtn.innerHTML = '<i class="fas fa-location-crosshairs"></i>';
        },
        () => {
            alert('Could not retrieve GPS location.');
            el.useCurrentLocationBtn.innerHTML = '<i class="fas fa-location-crosshairs"></i>';
        }
    );
}

// Helpers
function getMagCategory(mag) {
    if (mag >= 6.0) return 'severe';
    if (mag >= 5.0) return 'strong';
    if (mag >= 4.0) return 'moderate';
    return 'minor';
}

function getMagColor(mag) {
    if (mag >= 6.0) return '#ef4444';
    if (mag >= 5.0) return '#f97316';
    if (mag >= 4.0) return '#eab308';
    return '#10b981';
}

function formatTimeAgo(timestamp) {
    if (!timestamp) return '';
    const diffMs = Date.now() - timestamp;
    const mins = Math.floor(diffMs / 60000);
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
