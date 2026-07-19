/**
 * RoadPulse AI - Report Form Module
 * Handles incident report form submission and geolocation
 */

// Global state
let currentLocation = {
    latitude: MAP_CONFIG.DEFAULT_LAT,
    longitude: MAP_CONFIG.DEFAULT_LON,
    accuracy: null
};

let deviceId = null;

/**
 * Initialize report form
 */
function initReportForm() {
    // Get or generate device ID
    deviceId = getOrCreateDeviceId();

    // Setup modal controls
    setupModal();

    // Setup geolocation on page load
    captureInitialGeolocation();

    // Setup file input preview
    setupFilePreview();

    // Setup form submission
    setupFormSubmission();
}

/**
 * Setup modal open/close handlers
 */
function setupModal() {
    const reportBtn = document.getElementById('reportBtn');
    const modal = document.getElementById('reportModal');
    const closeBtn = document.getElementById('modalCloseBtn');
    const cancelBtn = document.getElementById('modalCancelBtn');

    if (reportBtn) {
        reportBtn.addEventListener('click', () => {
            modal.classList.add('active');
            // Capture location when modal opens
            captureCurrentGeolocation();
        });
    }

    const closeModal = () => {
        modal.classList.remove('active');
        resetForm();
    };

    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

    // Close modal on overlay click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });
}

/**
 * Capture initial geolocation on page load
 */
function captureInitialGeolocation() {
    if (!navigator.geolocation) {
        console.log('Geolocation not available');
        return;
    }

    navigator.geolocation.getCurrentPosition(
        (position) => {
            updateLocationData(position.coords);
        },
        (error) => {
            console.warn('Initial geolocation failed:', error);
            // Use defaults
        },
        {
            timeout: 5000,
            maximumAge: 60000,
            enableHighAccuracy: true
        }
    );
}

/**
 * Capture current geolocation (called when opening report modal)
 */
function captureCurrentGeolocation() {
    if (!navigator.geolocation) return;

    const latInput = document.getElementById('latitude');
    const lonInput = document.getElementById('longitude');
    const accInput = document.getElementById('gpsAccuracy');

    // Show loading state
    if (latInput) latInput.placeholder = 'Acquiring GPS...';

    navigator.geolocation.getCurrentPosition(
        (position) => {
            updateLocationData(position.coords);
            
            // Update form fields
            if (latInput) latInput.value = currentLocation.latitude.toFixed(4);
            if (lonInput) lonInput.value = currentLocation.longitude.toFixed(4);
            if (accInput) accInput.textContent = Math.round(currentLocation.accuracy);
        },
        (error) => {
            console.warn('Geolocation error:', error);
            
            // Use last known location or defaults
            const latInput = document.getElementById('latitude');
            const lonInput = document.getElementById('longitude');
            const accInput = document.getElementById('gpsAccuracy');
            
            if (latInput) latInput.value = currentLocation.latitude.toFixed(4);
            if (lonInput) lonInput.value = currentLocation.longitude.toFixed(4);
            if (accInput) accInput.textContent = currentLocation.accuracy ? Math.round(currentLocation.accuracy) : '--';
            
            showToast('Using last known location (GPS unavailable)', 'warning');
        },
        {
            timeout: 10000,
            maximumAge: 30000,
            enableHighAccuracy: true
        }
    );
}

/**
 * Update location data from geolocation result
 */
function updateLocationData(coords) {
    currentLocation = {
        latitude: coords.latitude,
        longitude: coords.longitude,
        accuracy: coords.accuracy
    };
}

/**
 * Setup file input preview
 */
function setupFilePreview() {
    const photoInput = document.getElementById('photoInput');
    const filePreview = document.getElementById('filePreview');
    const previewImage = document.getElementById('previewImage');

    if (!photoInput) return;

    photoInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        
        if (!file) {
            filePreview.classList.add('hidden');
            return;
        }

        // Validate file type
        if (!file.type.match('image.*')) {
            showToast('Please select a valid image file', 'error');
            photoInput.value = '';
            filePreview.classList.add('hidden');
            return;
        }

        // Validate file size (10MB)
        if (file.size > 10 * 1024 * 1024) {
            showToast('Image must be smaller than 10MB', 'error');
            photoInput.value = '';
            filePreview.classList.add('hidden');
            return;
        }

        // Show preview
        const reader = new FileReader();
        reader.onload = (event) => {
            previewImage.src = event.target.result;
            filePreview.classList.remove('hidden');
        };
        reader.readAsDataURL(file);
    });

    // Drag and drop support
    const label = photoInput.nextElementSibling;
    if (label) {
        label.addEventListener('dragover', (e) => {
            e.preventDefault();
            label.style.borderColor = '#3498db';
            label.style.background = 'rgba(52, 152, 219, 0.1)';
        });

        label.addEventListener('dragleave', () => {
            label.style.borderColor = '#bdc3c7';
            label.style.background = '#f8f9fa';
        });

        label.addEventListener('drop', (e) => {
            e.preventDefault();
            label.style.borderColor = '#bdc3c7';
            label.style.background = '#f8f9fa';

            const files = e.dataTransfer.files;
            if (files.length > 0) {
                photoInput.files = files;
                const event = new Event('change', { bubbles: true });
                photoInput.dispatchEvent(event);
            }
        });
    }
}

/**
 * Setup form submission
 */
function setupFormSubmission() {
    const form = document.getElementById('reportForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Validate required fields
        const photoInput = document.getElementById('photoInput');
        const latInput = document.getElementById('latitude');
        const lonInput = document.getElementById('longitude');

        if (!photoInput.files || !photoInput.files[0]) {
            showToast('Please select a photo', 'error');
            return;
        }

        if (!latInput.value || !lonInput.value) {
            showToast('Location is required. Please enable GPS', 'error');
            return;
        }

        // Show loading state
        const submitBtn = document.getElementById('submitBtn');
        const submittingState = document.getElementById('submittingState');
        const formFields = form.querySelectorAll('input, textarea, button');

        submitBtn.classList.add('hidden');
        submittingState.classList.remove('hidden');
        formFields.forEach(f => f.disabled = true);

        try {
            // Build form data
            const formData = new FormData();
            formData.append('image', photoInput.files[0]);
            formData.append('lat', latInput.value);
            formData.append('lon', lonInput.value);
            formData.append('gps_accuracy', currentLocation.accuracy || 25);
            formData.append('note', document.getElementById('note').value);
            formData.append('device_id', deviceId);

            // Submit to API
            const response = await fetch('/api/report', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            // Reset form
            submitBtn.classList.remove('hidden');
            submittingState.classList.add('hidden');
            formFields.forEach(f => f.disabled = false);

            if (result.success) {
                // Show success toast with details
                const statusText = result.is_duplicate ? 'Duplicate Merged' : 'Report Accepted';
                const message = result.is_duplicate 
                    ? `Thank you! This incident was merged with a previous report.`
                    : `Report submitted successfully! (ID: ${result.incident_id})`;
                
                showToast(message, 'success', 6000);

                // Close modal after brief delay
                setTimeout(() => {
                    document.getElementById('reportModal').classList.remove('active');
                    resetForm();
                }, 1500);

                // Refresh map
                if (typeof loadIncidents === 'function') {
                    setTimeout(() => loadIncidents(), 500);
                }
            } else {
                showToast(result.error || 'Report submission failed', 'error');
            }

        } catch (error) {
            console.error('Submission error:', error);
            showToast('Network error: ' + error.message, 'error');
            
            submitBtn.classList.remove('hidden');
            submittingState.classList.add('hidden');
            formFields.forEach(f => f.disabled = false);
        }
    });
}

/**
 * Reset form to initial state
 */
function resetForm() {
    const form = document.getElementById('reportForm');
    const photoInput = document.getElementById('photoInput');
    const filePreview = document.getElementById('filePreview');
    const submitBtn = document.getElementById('submitBtn');
    const submittingState = document.getElementById('submittingState');

    form.reset();
    photoInput.value = '';
    filePreview.classList.add('hidden');
    submitBtn.classList.remove('hidden');
    submittingState.classList.add('hidden');
    
    // Reset location inputs to current values
    const latInput = document.getElementById('latitude');
    const lonInput = document.getElementById('longitude');
    if (latInput && lonInput) {
        latInput.value = currentLocation.latitude.toFixed(4);
        lonInput.value = currentLocation.longitude.toFixed(4);
    }
}

/**
 * Get or create device ID (stored in localStorage)
 */
function getOrCreateDeviceId() {
    let id = localStorage.getItem('roadpulse_device_id');
    
    if (!id) {
        // Generate new device ID
        id = 'RP_' + Math.random().toString(36).substring(2, 15) + '_' + Date.now().toString(36);
        localStorage.setItem('roadpulse_device_id', id);
    }
    
    return id;
}

/**
 * Show toast notification (reuse from map.js if available, or local implementation)
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

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initReportForm();
});
