/**
 * RoadPulse AI - Admin Dashboard Module
 * Handles dashboard initialization, stats, charts, and incident management
 */

// Global state
let allIncidents = [];
let filteredIncidents = [];
let currentPage = 1;
let pageSize = 20;
let charts = {};
let adminMap = null;

/**
 * Initialize admin dashboard
 */
function initDashboard() {
    loadStats();
    loadIncidents();
    initCharts();
    initAdminMap();
    setupControls();
    
    // Auto-refresh every 30 seconds
    setInterval(() => {
        loadStats();
        loadIncidents();
    }, 30000);
}

/**
 * Load and display statistics
 */
function loadStats() {
    fetch('/api/stats')
        .then(response => {
            if (!response.ok) throw new Error('Failed to fetch stats');
            return response.json();
        })
        .then(data => {
            if (!data.success) {
                console.error('Stats error:', data.error);
                return;
            }

            const stats = data.stats;

            // Update stat cards
            updateStatCard(0, stats.total_incidents, 'Total Incidents');
            updateStatCard(1, stats.total_devices, 'Active Devices');
            updateStatCard(2, stats.average_confidence.toFixed(2), 'Avg Confidence');
            updateStatCard(3, stats.duplicate_count, 'Duplicates Detected');

            // Update charts with new data
            updateCharts(stats);
        })
        .catch(error => {
            console.error('Error loading stats:', error);
        });
}

/**
 * Update a stat card value
 */
function updateStatCard(index, value, label) {
    const cards = document.querySelectorAll('.stat-card');
    if (cards[index]) {
        const valueEl = cards[index].querySelector('.stat-value');
        const labelEl = cards[index].querySelector('.stat-label');
        
        if (valueEl) valueEl.textContent = value;
        if (labelEl) labelEl.textContent = label;
    }
}

/**
 * Initialize Chart.js charts
 */
function initCharts() {
    const severityCtx = document.getElementById('severityChart');
    const typeCtx = document.getElementById('typeChart');

    if (severityCtx) {
        charts.severity = new Chart(severityCtx, {
            type: 'doughnut',
            data: {
                labels: ['Low', 'Medium', 'High', 'Critical'],
                datasets: [{
                    data: [0, 0, 0, 0],
                    backgroundColor: [
                        '#27ae60',  // green
                        '#f39c12',  // yellow
                        '#e67e22',  // orange
                        '#c0392b'   // red
                    ],
                    borderColor: 'white',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    if (typeCtx) {
        charts.type = new Chart(typeCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Incidents',
                    data: [],
                    backgroundColor: '#3498db',
                    borderColor: '#2980b9',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }
}

/**
 * Update charts with new data
 */
function updateCharts(stats) {
    // Update severity chart
    if (charts.severity) {
        const severityData = {
            'low': stats.incidents_by_severity['low'] || 0,
            'medium': stats.incidents_by_severity['medium'] || 0,
            'high': stats.incidents_by_severity['high'] || 0,
            'critical': stats.incidents_by_severity['critical'] || 0
        };

        charts.severity.data.datasets[0].data = [
            severityData.low,
            severityData.medium,
            severityData.high,
            severityData.critical
        ];
        charts.severity.update();
    }

    // Update type chart
    if (charts.type) {
        const typeData = stats.incidents_by_type || {};
        const labels = Object.keys(typeData);
        const values = Object.values(typeData);

        charts.type.data.labels = labels.map(l => capitalizeWords(l));
        charts.type.data.datasets[0].data = values;
        charts.type.update();
    }
}

/**
 * Initialize admin map
 */
function initAdminMap() {
    const mapContainer = document.getElementById('adminMap');
    if (!mapContainer) return;

    adminMap = L.map('adminMap').setView([25.2048, 55.2708], 12);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(adminMap);
}

/**
 * Load incidents from API
 */
function loadIncidents() {
    fetch('/api/incidents?limit=500&include_duplicates=false')
        .then(response => {
            if (!response.ok) throw new Error('Failed to fetch incidents');
            return response.json();
        })
        .then(data => {
            if (!data.success) {
                console.error('API error:', data.error);
                return;
            }

            allIncidents = data.incidents || [];
            filteredIncidents = [...allIncidents];

            // Render table with pagination
            renderIncidentTable();

            // Update admin map
            updateAdminMap();
        })
        .catch(error => {
            console.error('Error loading incidents:', error);
            showToast('Failed to load incidents', 'error');
        });
}

/**
 * Render incident table with pagination
 */
function renderIncidentTable() {
    const tbody = document.getElementById('incidentsTableBody');
    if (!tbody) return;

    // Calculate pagination
    const totalPages = Math.ceil(filteredIncidents.length / pageSize);
    const startIdx = (currentPage - 1) * pageSize;
    const endIdx = startIdx + pageSize;
    const pageIncidents = filteredIncidents.slice(startIdx, endIdx);

    // Build table rows
    if (pageIncidents.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 32px;">No incidents found</td></tr>';
    } else {
        tbody.innerHTML = pageIncidents.map(incident => {
            const severityClass = `severity-${incident.severity_level}`;
            const statusBadge = incident.is_duplicate ? 
                '<span class="badge" style="background: #ecf0f1; color: #7f8c8d;">Duplicate</span>' :
                '<span class="badge badge-' + incident.severity_level + '">' + incident.severity_level + '</span>';
            
            return `
                <tr>
                    <td>${incident.id}</td>
                    <td>${capitalizeWords(incident.incident_type)}</td>
                    <td class="${severityClass}" style="font-weight: 600;">${capitalizeWords(incident.severity_level)}</td>
                    <td>${(incident.confidence_score * 100).toFixed(0)}%</td>
                    <td style="font-size: 12px; font-family: monospace;">
                        ${incident.latitude.toFixed(4)}, ${incident.longitude.toFixed(4)}
                    </td>
                    <td style="font-size: 12px; font-family: monospace;">
                        ${incident.device_id.substring(0, 12)}
                    </td>
                    <td style="font-size: 12px;">
                        ${formatTime(incident.created_at)}
                    </td>
                    <td>${statusBadge}</td>
                </tr>
            `;
        }).join('');
    }

    // Update pagination info
    const pageInfo = document.getElementById('pageInfo');
    if (pageInfo) {
        pageInfo.textContent = `Page ${currentPage} of ${Math.max(1, totalPages)} (${filteredIncidents.length} total)`;
    }

    // Update pagination buttons
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    if (prevBtn) prevBtn.disabled = currentPage === 1;
    if (nextBtn) nextBtn.disabled = currentPage >= totalPages;
}

/**
 * Update admin map with incident markers
 */
function updateAdminMap() {
    if (!adminMap) return;

    // Clear existing layers (except tiles)
    adminMap.eachLayer(layer => {
        if (layer instanceof L.Marker || layer instanceof L.Circle) {
            adminMap.removeLayer(layer);
        }
    });

    // Add markers for all incidents
    allIncidents.forEach(incident => {
        const color = getSeverityColor(incident.severity_level);
        
        L.circleMarker([incident.latitude, incident.longitude], {
            radius: 6,
            fillColor: color,
            color: 'white',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.7
        }).bindPopup(`
            <div style="font-size: 12px;">
                <strong>${capitalizeWords(incident.incident_type)}</strong><br>
                Severity: ${incident.severity_level}<br>
                Confidence: ${(incident.confidence_score * 100).toFixed(0)}%<br>
                Time: ${formatTime(incident.created_at)}
            </div>
        `).addTo(adminMap);
    });

    // Fit bounds if there are incidents
    if (allIncidents.length > 0) {
        const bounds = L.latLngBounds(
            allIncidents.map(i => [i.latitude, i.longitude])
        );
        adminMap.fitBounds(bounds, { padding: [50, 50] });
    }
}

/**
 * Setup control event listeners
 */
function setupControls() {
    // Search
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            filteredIncidents = allIncidents.filter(incident => {
                return incident.incident_type.toLowerCase().includes(query) ||
                       incident.device_id.toLowerCase().includes(query) ||
                       incident.id.toString().includes(query);
            });
            currentPage = 1;
            renderIncidentTable();
        });
    }

    // Sort
    const sortSelect = document.getElementById('sortSelect');
    if (sortSelect) {
        sortSelect.addEventListener('change', (e) => {
            const sortBy = e.target.value;
            
            if (sortBy === 'recent') {
                filteredIncidents.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
            } else if (sortBy === 'severity') {
                const severityOrder = { 'critical': 4, 'high': 3, 'medium': 2, 'low': 1 };
                filteredIncidents.sort((a, b) => 
                    (severityOrder[b.severity_level] || 0) - (severityOrder[a.severity_level] || 0)
                );
            } else if (sortBy === 'confidence') {
                filteredIncidents.sort((a, b) => b.confidence_score - a.confidence_score);
            }
            
            currentPage = 1;
            renderIncidentTable();
        });
    }

    // Pagination
    const prevBtn = document.getElementById('prevBtn');
    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage--;
                renderIncidentTable();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    }

    const nextBtn = document.getElementById('nextBtn');
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            const totalPages = Math.ceil(filteredIncidents.length / pageSize);
            if (currentPage < totalPages) {
                currentPage++;
                renderIncidentTable();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    }
}

/**
 * Get severity color
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
 * Capitalize words
 */
function capitalizeWords(text) {
    if (!text) return '';
    return text
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

/**
 * Format time relative to now
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
 * Show toast notification
 */
function showToast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const title = type === 'success' ? '✓ Success' : 
                  type === 'error' ? '✗ Error' :
                  type === 'warning' ? '⚠ Warning' : 'ℹ Info';
    
    toast.innerHTML = `
        <div class="toast-title">${title}</div>
        <div class="toast-message">${message}</div>
    `;
    
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initDashboard();
});
