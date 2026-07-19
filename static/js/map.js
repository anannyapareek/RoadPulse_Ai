/**
 * RoadPulse AI - Map Module
 * Handles Leaflet map initialization and real-time incident display
 */

// Map Configuration
const MAP_CONFIG = {
    DEFAULT_LAT: 25.2048,
    DEFAULT_LON: 55.2708,
    DEFAULT_ZOOM: 12,
    TILE_LAYER: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    TILE_ATTRIBUTION: '&copy; OpenStreetMap contributors'
};

// Global state
let map = null;
let markers = [];
let heatmapLayer = null;
let currentIncidents = [];
let pollingInterval = null;

/**
 * Initialize the map
 */
function initMap() {
    // Create map centered on default city
    map = L.map('map').setView(
        [MAP_CONFIG.DEFAULT_LAT, MAP_CONFIG.DEFAULT_LON],
        MAP_CONFIG.DEFAULT_ZOOM
    );

    // Add OSM tile layer
    L.tileLayer(MAP_CONFIG.TILE_LAYER, {
        attribution: MAP_CONFIG.TILE_ATTRIBUTION,
        maxZoom: 19
    }).addTo(map);

    // Initialize heatmap layer (empty for now)
    heatmapLayer = L.heatLayer([], {
        radius: 25,
        blur: 15,
        maxZoom: 17,
        gradient: {
            0.0: '#27ae60',  // green (low)
            0.3: '#f39c12',  // yellow (medium)
            0.6: '#e67e22',  // orange (high)
            1.0: '#c0392b'   // red (critical)
        }
    }).addTo(map);

    // Start polling for incidents
    startPolling();

    // Load incidents immediately
    loadIncidents();
}

/**
 * Convert severity level to map color
 */
function getSeverityColor(severity) {
    const colors = {
        'low': '#27ae60',      // green
        'medium': '#f39c12',   // yellow
        'high': '#e67e22',     // orange
        'critical': '#c0392b'  // red
    };
    return colors[severity] || '#95a5a6';
}

/**
 * Create a custom marker icon for an incident
 */
function createMarkerIcon(severity) {
    const color = getSeverityColor(severity);
    return L.divIcon({
        className: 'incident-marker',
        html: `<div style="background: ${color}; width: 28px; height: 28px; border-radius: 50%; border: 3px solid white; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">!</div>`,
        iconSize: [28, 28],
        popupAnchor: [0, -14]
    });
}

/**
 * Clear all markers from the map
 */
function clearMarkers() {
    markers.forEach(marker => marker.remove());
    markers = [];
}

/**
 * Clear heatmap data
 */
function clearHeatmap() {
    if (heatmapLayer) {
        heatmapLayer.setLatLngs([]);
    }
}

/**
 * Add a single incident to the map
 */
function addIncidentMarker(incident) {
    const { id, latitude, longitude, incident_type, severity_level, confidence_score } = incident;

    // Create marker
    const marker = L.marker([latitude, longitude], {
        icon: createMarkerIcon(severity_level)
    }).addTo(map);

    // Create popup content
    const severityBadge = `<span class="badge badge-${severity_level}">${severity_level}</span>`;
    const confidencePercent = (confidence_score * 100).toFixed(0);
    
    let photoHtml = '';
    if (incident.image_filename) {
        const photoUrl = `/uploads/${incident.image_filename}`;
        photoHtml = `<img src="${photoUrl}" alt="Incident photo" style="width: 100%; max-height: 150px; border-radius: 4px; margin: 8px 0; object-fit: cover;" />`;
    }

    const popupContent = `
        <div style="min-width: 280px;">
            <h4 style="margin: 0 0 8px 0;">${capitalizeWords(incident_type)}</h4>
            ${photoHtml}
            <div style="margin: 8px 0;">
                ${severityBadge}
                <span style="margin-left: 8px; font-size: 12px; color: #95a5a6;">
                    ${id}
                </span>
            </div>
            <div style="font-size: 12px; color: #7f8c8d; margin: 8px 0;">
                <div><strong>Confidence:</strong> ${confidencePercent}%</div>
                <div><strong>Location:</strong> ${latitude.toFixed(4)}, ${longitude.toFixed(4)}</div>
                <div><strong>Time:</strong> ${formatTime(incident.created_at)}</div>
                <div><strong>Device:</strong> ${incident.device_id.substring(0, 8)}</div>
            </div>
            <div style="font-size: 12px; padding: 8px; background: #f8f9fa; border-radius: 4px; margin-top: 8px;">
                <strong>AI Summary:</strong> ${incident.raw_gemini_response ? truncateText(incident.raw_gemini_response, 100) : 'Analyzing...'}
            </div>
        </div>
    `;

    marker.bindPopup(popupContent);
    markers.push(marker);

    return marker;
}

/**
 * Update heatmap with incident severity data
 */
function updateHeatmap() {
    if (!heatmapLayer || !currentIncidents.length) return;

    const heatmapData = currentIncidents.map(incident => {
        // Weight by severity level (1-4)
        const severityWeight = {
            'low': 1,
            'medium': 2,
            'high': 3,
            'critical': 4
        }[incident.severity_level] || 1;

        return [
            incident.latitude,
            incident.longitude,
            severityWeight / 4  // normalize to 0-1
        ];
    });

    heatmapLayer.setLatLngs(heatmapData);
}

/**
 * Load incidents from API and update map
 */
function loadIncidents() {
    fetch('/api/incidents?limit=200&include_duplicates=false')
        .then(response => {
            if (!response.ok) throw new Error('Failed to fetch incidents');
            return response.json();
        })
        .then(data => {
            if (!data.success) {
                console.error('API error:', data.error);
                return;
            }

            currentIncidents = data.incidents || [];

            // Clear and redraw
            clearMarkers();
            clearHeatmap();

            // Add markers for each incident
            currentIncidents.forEach(incident => {
                addIncidentMarker(incident);
            });

            // Update heatmap
            updateHeatmap();

            // Update stats badge if present
            const totalElement = document.querySelector('[data-stat="total"]');
            if (totalElement) {
                totalElement.textContent = data.total;
            }
        })
        .catch(error => {
            console.error('Error loading incidents:', error);
            showToast('Failed to load incidents', 'error');
        });
}

/**
 * Start polling for incidents every 15 seconds
 */
function startPolling() {
    if (pollingInterval) clearInterval(pollingInterval);
    
    pollingInterval = setInterval(() => {
        loadIncidents();
    }, 15000);  // 15 seconds
}

/**
 * Stop polling
 */
function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

/**
 * Handle geolocation button
 */
function setupGeolocation() {
    const geoBtn = document.getElementById('geolocateBtn');
    if (!geoBtn) return;

    geoBtn.addEventListener('click', () => {
        if (!navigator.geolocation) {
            showToast('Geolocation not supported', 'error');
            return;
        }

        geoBtn.disabled = true;
        geoBtn.textContent = '⏳';

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const { latitude, longitude } = position.coords;
                map.setView([latitude, longitude], 15);
                
                // Update form fields if on report page
                const latInput = document.getElementById('latitude');
                const lonInput = document.getElementById('longitude');
                const accInput = document.getElementById('gpsAccuracy');
                
                if (latInput && lonInput) {
                    latInput.value = latitude.toFixed(4);
                    lonInput.value = longitude.toFixed(4);
                    if (accInput) {
                        accInput.textContent = Math.round(position.coords.accuracy);
                    }
                }

                geoBtn.disabled = false;
                geoBtn.textContent = '📍';
                showToast('Location updated', 'success');
            },
            (error) => {
                console.error('Geolocation error:', error);
                geoBtn.disabled = false;
                geoBtn.textContent = '📍';
                showToast('Could not get your location: ' + error.message, 'error');
            },
            {
                timeout: 10000,
                maximumAge: 0,
                enableHighAccuracy: true
            }
        );
    });
}

/**
 * Handle refresh button
 */
function setupRefresh() {
    const refreshBtn = document.getElementById('refreshBtn');
    if (!refreshBtn) return;

    refreshBtn.addEventListener('click', () => {
        refreshBtn.disabled = true;
        refreshBtn.style.animation = 'spin 0.8s linear';
        
        loadIncidents().finally(() => {
            refreshBtn.disabled = false;
            refreshBtn.style.animation = '';
        });
    });
}

/**
 * Utility: Capitalize words
 */
function capitalizeWords(text) {
    if (!text) return '';
    return text
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

/**
 * Utility: Format timestamp
 */
function formatTime(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString();
}

/**
 * Utility: Truncate text
 */
function truncateText(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<div class="toast-message">${message}</div>`;
    
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Initialize map when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    setupGeolocation();
    setupRefresh();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    stopPolling();
});
