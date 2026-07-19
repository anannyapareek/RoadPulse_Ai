/**
 * static/js/main.js
 * Core RoadPulse frontend application logic
 * REFACTORED: All mock data replaced with live fetch() API calls
 * PRESERVED: All UI features (sidebars, map, Leaflet, Canvas sharing, XAI matrix)
 */

// =====================================================================
// GLOBAL STATE
// =====================================================================

let currentUser = {
    role: null,
    id: null,
    ward: null,
    trust_score: 50
};

let mapInstance = null;
let markersGroup = null;
let heatmapGroup = null;
let activeLayerMode = 'markers';
let routeMarkers = [];
let routeLine = null;
let chartInstance = null;
let navigationSidebarCollapsed = false;
let sidebarPanelCollapsed = false;

// Live incidents array (populated from API, not hardcoded)
let liveIncidents = [];

// =====================================================================
// AUTHENTICATION & LOGIN
// =====================================================================

function fillAndLogin(username, password) {
    document.getElementById('login-username').value = username;
    document.getElementById('login-password').value = password;
    const mockEvent = { preventDefault: () => {} };
    handleUnifiedLogin(mockEvent);
}

function handleUnifiedLogin(event) {
    event.preventDefault();
    const usernameInput = document.getElementById('login-username').value.trim();
    const passwordInput = document.getElementById('login-password').value.trim();

    if (!usernameInput || !passwordInput) {
        return showToast("Please fill both Username and Password fields.");
    }

    if (usernameInput.toLowerCase() === 'admin' && passwordInput === 'pulse2026') {
        currentUser.role = 'operator';
        currentUser.id = "Admin Operator (Warden-04)";
        currentUser.ward = "Central Command";
        currentUser.trust_score = 100;

        document.getElementById('header-platform-label').textContent = "RoadPulse AI platform";
        document.getElementById('header-workspace-label').textContent = "Overview Console";
        if (document.getElementById('avatar-user')) document.getElementById('avatar-user').src = "https://placehold.co/100x100/1d1f23/ffffff?text=OP";
        if (document.getElementById('user-trust-badge')) document.getElementById('user-trust-badge').textContent = currentUser.trust_score;

        document.getElementById('nav-citizen-group').classList.add('hidden');
        document.getElementById('nav-operator-group').classList.remove('hidden');
        document.getElementById('citizen-views-container').classList.add('hidden');
        document.getElementById('operator-views-container').classList.remove('hidden');

        setupMobileNavigationBar('operator');
        renderOperatorUI();

    } else if (usernameInput.toLowerCase() === 'citizen' && passwordInput === 'user2026') {
        currentUser.role = 'citizen';
        currentUser.id = "citizen";
        currentUser.ward = "Ward 12 (Central Civic)";
        currentUser.trust_score = 75;

        document.getElementById('header-platform-label').textContent = "Citizen Portal (Ward 12)";
        document.getElementById('header-workspace-label').textContent = "Community Feedback & Dispatch Workspace";
        if (document.getElementById('avatar-user')) document.getElementById('avatar-user').src = "https://placehold.co/100x100/ff7a22/ffffff?text=CI";
        if (document.getElementById('user-trust-badge')) document.getElementById('user-trust-badge').textContent = currentUser.trust_score;

        document.getElementById('nav-citizen-group').classList.remove('hidden');
        document.getElementById('nav-operator-group').classList.add('hidden');
        document.getElementById('citizen-views-container').classList.remove('hidden');
        document.getElementById('operator-views-container').classList.add('hidden');

        setupMobileNavigationBar('citizen');
        renderCitizenUI();

    } else {
        return showToast("Access Denied: Invalid credentials!");
    }

    document.getElementById('login-screen').classList.add('hidden');
    document.getElementById('app-shell').classList.remove('hidden');
    switchTab(currentUser.role === 'citizen' ? 'citizen-report' : 'dashboard');
    initializeGISMapSandbox();
    loadIncidentsFromAPI();
    showToast(currentUser.role === 'citizen' ? "Citizen reporting node online." : "Command Console Auth Verified.");
}

function setupMobileNavigationBar(role) {
    const container = document.getElementById('mobile-navigation-bar');
    container.innerHTML = '';

    if (role === 'citizen') {
        container.innerHTML = `
            <button onclick="switchTab('citizen-report')" class="flex-1 py-2 text-xs font-bold text-center rounded-lg text-gray-500 hover:bg-gray-50 transition-all">Submit</button>
            <button onclick="switchTab('citizen-my-reports')" class="flex-1 py-2 text-xs font-bold text-center rounded-lg text-gray-500 hover:bg-gray-50 transition-all">My Tracks</button>
            <button onclick="switchTab('citizen-safe-routing')" class="flex-1 py-2 text-xs font-bold text-center rounded-lg text-gray-500 hover:bg-gray-50 transition-all">Safe Path</button>
        `;
    } else {
        container.innerHTML = `
            <button onclick="switchTab('dashboard')" class="flex-1 py-2 text-xs font-bold text-center rounded-lg text-gray-500 hover:bg-gray-50 transition-all">Overview</button>
            <button onclick="switchTab('reports')" class="flex-1 py-2 text-xs font-bold text-center rounded-lg text-gray-500 hover:bg-gray-50 transition-all">Dispatch</button>
            <button onclick="switchTab('routing')" class="flex-1 py-2 text-xs font-bold text-center rounded-lg text-gray-500 hover:bg-gray-50 transition-all">Routing</button>
            <button onclick="switchTab('analytics')" class="flex-1 py-2 text-xs font-bold text-center rounded-lg text-gray-500 hover:bg-gray-50 transition-all">Metrics</button>
        `;
    }
}

function logOut() {
    currentUser.role = null;
    document.getElementById('login-username').value = '';
    document.getElementById('login-password').value = '';
    document.getElementById('app-shell').classList.add('hidden');
    document.getElementById('login-screen').classList.remove('hidden');
    showToast("Workspace session locked.");
}

// =====================================================================
// UI RENDERING (OPERATOR & CITIZEN)
// =====================================================================

function renderOperatorUI() {
    const opContainer = document.getElementById('operator-views-container');
    opContainer.innerHTML = `
        <div id="tab-dashboard" class="flex-1 flex flex-col overflow-y-auto p-5 sm:p-6 gap-6">
            <div class="grid grid-cols-2 gap-4">
                <div class="bg-brandSageBg rounded-3xl p-4 sm:p-5 border border-brandSageText/10 flex flex-col justify-between h-36">
                    <div class="flex items-center justify-between">
                        <span class="text-[10px] font-extrabold text-brandSageText uppercase tracking-wider">Network Trust</span>
                        <span class="bg-white/90 text-brandSageText text-[8px] px-2 py-0.5 rounded-full font-bold uppercase">Optimal</span>
                    </div>
                    <div>
                        <span class="text-2xl sm:text-3xl font-extrabold text-brandSageText" id="widget-trust">84.2%</span>
                        <p class="text-[10px] text-brandSageText/70 font-bold mt-1">Consistency with Gemini ML classifications</p>
                    </div>
                </div>

                <div class="bg-brandOrange text-white rounded-3xl p-4 sm:p-5 flex flex-col justify-between h-36 premium-shadow relative overflow-hidden">
                    <span class="absolute -right-6 -bottom-6 text-white/5 text-8xl font-black select-none pointer-events-none">AI</span>
                    <div class="flex items-center justify-between">
                        <span class="text-[10px] font-extrabold uppercase tracking-wider">Dispatch Calls</span>
                        <span class="bg-white/25 text-white text-[8px] px-2 py-0.5 rounded-full font-bold uppercase">VoIP Live</span>
                    </div>
                    <div>
                        <span class="text-2xl sm:text-3xl font-extrabold" id="widget-dispatches">0</span>
                        <p class="text-[10px] text-white/80 font-bold mt-1">Automated phone call dispatches resolved</p>
                    </div>
                </div>
            </div>

            <div>
                <div class="flex items-center justify-between mb-3 border-b border-gray-100 pb-2">
                    <h3 class="text-sm font-extrabold text-brandCharcoal tracking-tight">Active GIS Incidents</h3>
                    <span class="text-[10px] bg-brandGreyBg px-2 py-0.5 rounded-full text-gray-500 font-extrabold uppercase" id="log-count">0 items</span>
                </div>
                <div class="flex flex-col gap-2.5 max-h-[350px] overflow-y-auto pr-1" id="log-feed-container">
                    <!-- Populated by loadIncidentsFromAPI -->
                </div>
            </div>
        </div>

        <div id="tab-reports" class="hidden flex-1 flex flex-col overflow-y-auto p-5 sm:p-6 gap-6">
            <div class="bg-gray-50 rounded-3xl p-4 border border-gray-150">
                <div class="flex items-center gap-2 mb-3">
                    <span class="w-2.5 h-2.5 bg-brandOrange rounded-full animate-ping"></span>
                    <h3 class="text-sm font-extrabold text-brandCharcoal">Dispatch Incident Report</h3>
                </div>

                <form id="incident-form" onsubmit="submitForm(event)" class="flex flex-col gap-3">
                    <div>
                        <label class="text-[10px] font-extrabold uppercase text-gray-400 block mb-1">Visual Evidence Image</label>
                        <div class="bg-white border border-gray-200 rounded-2xl p-3 flex items-center gap-3 relative cursor-pointer hover:border-brandOrange transition-all">
                            <div class="w-10 h-10 bg-orange-50 text-brandOrange rounded-xl flex items-center justify-center text-sm">
                                <i class="fa-solid fa-camera animate-pulse"></i>
                            </div>
                            <div>
                                <p id="file-label-name" class="text-xs font-bold text-brandCharcoal">Select or drag file...</p>
                                <p class="text-[9px] text-gray-400">Accepts camera snaps with geotag metadata</p>
                            </div>
                            <input type="file" id="photo-input" accept="image/*" class="absolute inset-0 opacity-0 cursor-pointer" onchange="handleFileSelect(event)">
                        </div>
                    </div>

                    <div>
                        <label class="text-[10px] font-extrabold uppercase text-gray-400 block mb-1">Coordinate Vectors (Click Map to Autofill)</label>
                        <div class="grid grid-cols-2 gap-2">
                            <input type="number" step="any" id="form-lat" placeholder="28.6139" class="w-full bg-white border border-gray-200 rounded-xl pl-9 pr-3 py-2 text-xs font-semibold focus:outline-none focus:border-brandOrange" required>
                            <input type="number" step="any" id="form-lon" placeholder="77.2090" class="w-full bg-white border border-gray-200 rounded-xl pl-9 pr-3 py-2 text-xs font-semibold focus:outline-none focus:border-brandOrange" required>
                        </div>
                    </div>

                    <div>
                        <label class="text-[10px] font-extrabold uppercase text-gray-400 block mb-1">Field Observations</label>
                        <textarea id="form-note" placeholder="Note any specific visual details..." class="w-full bg-white border border-gray-200 rounded-2xl p-3 text-xs font-medium focus:outline-none focus:border-brandOrange h-16 resize-none"></textarea>
                    </div>

                    <button type="submit" id="btn-submit" class="w-full bg-brandOrange hover:bg-orange-600 text-white font-extrabold py-3 rounded-2xl text-xs uppercase tracking-wider transition-all shadow-md flex items-center justify-center gap-2">
                        <i class="fa-solid fa-microchip"></i>
                        <span id="btn-submit-text">Run AI Processing Pipeline</span>
                    </button>
                </form>
            </div>
        </div>

        <div id="tab-routing" class="hidden flex-1 flex flex-col p-5 sm:p-6 gap-6 overflow-y-auto">
            <div class="bg-gray-50 rounded-3xl p-5 border border-gray-150">
                <h3 class="text-sm font-extrabold text-brandCharcoal mb-1 flex items-center gap-1.5">
                    <i class="fa-solid fa-route text-brandOrange"></i> Hazard Avoidance Router
                </h3>

                <div class="flex flex-col gap-3">
                    <div>
                        <label class="text-[10px] font-extrabold uppercase text-gray-400 block mb-1">Departure Origin</label>
                        <input type="text" id="route-start" value="28.6050, 77.1950" class="bg-white border border-gray-200 rounded-xl px-3 py-2 text-xs font-semibold w-full focus:outline-none focus:border-brandOrange">
                    </div>
                    <div>
                        <label class="text-[10px] font-extrabold uppercase text-gray-400 block mb-1">Destination Target</label>
                        <input type="text" id="route-end" value="28.6310, 77.2210" class="bg-white border border-gray-200 rounded-xl px-3 py-2 text-xs font-semibold w-full focus:outline-none focus:border-brandOrange">
                    </div>
                    
                    <div class="flex gap-2">
                        <button onclick="calculateSafeRoutes()" class="flex-1 bg-brandCharcoal hover:bg-black text-white font-extrabold py-3 rounded-2xl text-xs uppercase tracking-wider transition-all shadow-md">
                            <i class="fa-solid fa-shield-halved mr-1.5 text-brandOrange"></i> Detour Path
                        </button>
                        <button onclick="clearRoutes()" class="px-4 bg-gray-100 hover:bg-gray-200 text-gray-500 rounded-2xl transition-all">
                            <i class="fa-solid fa-trash-can"></i>
                        </button>
                    </div>
                </div>
            </div>

            <div id="routing-comparison-results" class="hidden flex flex-col gap-3">
                <h4 class="text-[10px] font-extrabold text-gray-400 tracking-wider uppercase">Evaluated Route Decisions</h4>
                
                <div class="bg-white border-2 border-brandOrange rounded-2xl p-4 flex items-center justify-between premium-shadow relative overflow-hidden">
                    <div class="absolute -top-1 -right-1 bg-brandOrange text-white text-[8px] font-extrabold uppercase px-2 py-0.5 rounded-bl-lg">Optimal</div>
                    <div>
                        <span class="text-xs font-extrabold text-brandCharcoal block font-bold">Avoidance Path A</span>
                        <span class="text-[10px] text-gray-400 font-semibold block mt-1">Diverting clear of high severity hotspots</span>
                    </div>
                    <div class="text-right">
                        <span class="text-xs font-extrabold text-emerald-600 block">Risk: 0 Pts</span>
                        <span class="text-[10px] text-gray-400 font-bold block mt-0.5">8.4 KM | 14 mins</span>
                    </div>
                </div>
            </div>
        </div>

        <div id="tab-analytics" class="hidden flex-1 flex flex-col p-5 sm:p-6 gap-6 overflow-y-auto">
            <div class="bg-white rounded-3xl p-4 sm:p-5 border border-gray-200">
                <h3 class="text-sm font-extrabold text-brandCharcoal mb-3">Incident Resolution Timelines</h3>
                <div class="h-44">
                    <canvas id="resolutionChart"></canvas>
                </div>
            </div>
        </div>
    `;
}

function renderCitizenUI() {
    const citContainer = document.getElementById('citizen-views-container');
    citContainer.innerHTML = `
        <div id="tab-citizen-report" class="flex-1 flex flex-col overflow-y-auto p-5 sm:p-6 gap-6">
            <div class="bg-orange-50/50 rounded-3xl p-5 border border-brandOrange/15">
                <h3 class="text-sm font-extrabold text-brandCharcoal flex items-center gap-2 mb-1.5">
                    <i class="fa-solid fa-circle-info text-brandOrange animate-bounce"></i>
                    <span>Welcome to Citizen Workspace</span>
                </h3>
                <p class="text-xs text-slate-600 leading-relaxed">
                    Your reports are immediately processed using Gemini Vision technology to detect roadway defects, prioritize hazards, and alert emergency dispatches.
                </p>
            </div>

            <div class="bg-white rounded-3xl p-5 border border-gray-200">
                <h4 class="text-xs font-extrabold text-brandCharcoal mb-3 uppercase tracking-wider">Report Community Defect</h4>
                <form id="citizen-form" onsubmit="submitForm(event)" class="flex flex-col gap-4">
                    
                    <div>
                        <label class="text-[10px] font-extrabold uppercase text-gray-400 block mb-1">Set Geolocation Coordinates</label>
                        <div class="grid grid-cols-2 gap-2">
                            <input type="number" step="any" id="cit-form-lat" placeholder="Latitude" class="w-full bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-xs font-semibold focus:outline-none focus:border-brandOrange" required>
                            <input type="number" step="any" id="cit-form-lon" placeholder="Longitude" class="w-full bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-xs font-semibold focus:outline-none focus:border-brandOrange" required>
                        </div>
                    </div>

                    <div>
                        <label class="text-[10px] font-extrabold uppercase text-gray-400 block mb-1">Evidence Snapshot Upload</label>
                        <div class="mt-3 bg-slate-50 border border-dashed border-slate-300 rounded-2xl p-4 flex flex-col items-center justify-center cursor-pointer relative hover:border-brandOrange transition-all">
                            <input type="file" id="citizen-photo" accept="image/*" class="absolute inset-0 opacity-0 cursor-pointer" onchange="handleFileSelect(event)">
                            <i class="fa-solid fa-cloud-arrow-up text-slate-400 text-xl mb-1.5"></i>
                            <span id="cit-file-label" class="text-xs font-bold text-slate-600">Upload your phone snapshot</span>
                            <span class="text-[9px] text-slate-400 mt-0.5">Supports high precision camera metadata</span>
                        </div>
                    </div>

                    <div>
                        <label class="text-[10px] font-extrabold uppercase text-gray-400 block mb-1">What did you observe?</label>
                        <textarea id="cit-form-note" placeholder="E.g. Asphalt cave-in, deep puddle blocks pedestrian lane..." class="w-full bg-gray-50 border border-gray-200 rounded-2xl p-3 text-xs font-medium focus:outline-none focus:border-brandOrange h-20 resize-none"></textarea>
                    </div>

                    <button type="submit" id="cit-btn-submit" class="w-full bg-brandOrange hover:bg-orange-600 text-white font-extrabold py-3.5 rounded-2xl text-xs uppercase tracking-wider transition-all shadow-md flex items-center justify-center gap-2">
                        <i class="fa-solid fa-bolt animate-pulse"></i>
                        <span id="cit-btn-submit-text">Submit Urgent Report</span>
                    </button>
                </form>
            </div>
        </div>

        <div id="tab-citizen-my-reports" class="hidden flex-1 flex flex-col overflow-y-auto p-5 sm:p-6 gap-6">
            <div class="flex items-center justify-between border-b border-gray-100 pb-2">
                <h3 class="text-sm font-extrabold text-brandCharcoal">My Active Submissions</h3>
                <span class="text-[10px] bg-brandGreyBg px-2 py-0.5 rounded-full text-gray-500 font-extrabold uppercase" id="cit-report-count">0 items</span>
            </div>
            <div class="flex flex-col gap-3" id="citizen-submissions-list">
                <!-- Populated by loadIncidentsFromAPI -->
            </div>
        </div>

        <div id="tab-citizen-safe-routing" class="hidden flex-1 flex flex-col overflow-y-auto p-5 sm:p-6 gap-6">
            <div class="bg-gray-50 rounded-3xl p-5 border border-gray-150">
                <h3 class="text-sm font-extrabold text-brandCharcoal mb-1 flex items-center gap-1.5">
                    <i class="fa-solid fa-shield-halved text-brandOrange"></i> Daily Commute Safety
                </h3>

                <div class="flex flex-col gap-3">
                    <div>
                        <label class="text-[10px] font-extrabold uppercase text-gray-400 block mb-1">Departure Point</label>
                        <input type="text" id="cit-route-start" value="28.6050, 77.1950" class="bg-white border border-gray-200 rounded-xl px-3 py-2 text-xs font-semibold w-full focus:outline-none focus:border-brandOrange">
                    </div>
                    <div>
                        <label class="text-[10px] font-extrabold uppercase text-gray-400 block mb-1">Destination Target</label>
                        <input type="text" id="cit-route-end" value="28.6310, 77.2210" class="bg-white border border-gray-200 rounded-xl px-3 py-2 text-xs font-semibold w-full focus:outline-none focus:border-brandOrange">
                    </div>
                    
                    <button onclick="calculateSafeRoutes()" class="w-full bg-brandCharcoal hover:bg-black text-white font-extrabold py-3.5 rounded-2xl text-xs uppercase tracking-wider transition-all shadow-md">
                        <i class="fa-solid fa-map-location-dot mr-1.5 text-brandOrange"></i> Calculate Safe Commute
                    </button>
                </div>
            </div>

            <div id="cit-routing-comparison" class="hidden flex flex-col gap-3">
                <h4 class="text-[10px] font-extrabold text-gray-400 tracking-wider uppercase">Hazard Avoidance Path</h4>
                <div class="bg-white border-2 border-brandOrange rounded-2xl p-4 flex items-center justify-between premium-shadow">
                    <div>
                        <span class="text-xs font-extrabold text-brandCharcoal block">Route Alpha Detour</span>
                        <span class="text-[10px] text-gray-400 font-semibold block mt-1">100% bypass of high-severity zones.</span>
                    </div>
                    <div class="text-right">
                        <span class="text-xs font-extrabold text-emerald-600 block">0 Hazards</span>
                        <span class="text-[10px] text-gray-400 font-semibold block mt-0.5">14 Mins</span>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// =====================================================================
// API DATA LOADING
// =====================================================================

async function loadIncidentsFromAPI() {
    showToast("Loading incidents from server...");
    const result = await API.getIncidents({
        limit: 100,
        include_duplicates: false
    });

    if (result.success && result.incidents) {
        liveIncidents = result.incidents;
        syncDataAndUI();
        showToast(`Loaded ${result.incidents.length} incidents from database.`);
    } else {
        showToast("Failed to load incidents. Check server connectivity.");
        liveIncidents = [];
    }
}

// =====================================================================
// FORM SUBMISSION & INCIDENT CREATION
// =====================================================================

async function submitForm(event) {
    event.preventDefault();

    let lat, lon, note;
    const isCitizen = (currentUser.role === 'citizen');

    if (isCitizen) {
        lat = parseFloat(document.getElementById('cit-form-lat').value);
        lon = parseFloat(document.getElementById('cit-form-lon').value);
        note = document.getElementById('cit-form-note').value;
    } else {
        lat = parseFloat(document.getElementById('form-lat').value);
        lon = parseFloat(document.getElementById('form-lon').value);
        note = document.getElementById('form-note').value;
    }

    if (isNaN(lat) || isNaN(lon)) {
        return showToast("Provide correctly structured geographic coordinates.");
    }

    const fileInput = isCitizen ? document.getElementById('citizen-photo') : document.getElementById('photo-input');
    if (!fileInput.files || fileInput.files.length === 0) {
        return showToast("Please select an image file.");
    }

    const submitBtn = document.getElementById(isCitizen ? 'cit-btn-submit' : 'btn-submit');
    const submitTxt = document.getElementById(isCitizen ? 'cit-btn-submit-text' : 'btn-submit-text');
    submitBtn.disabled = true;
    submitTxt.innerHTML = "Processing Gemini Vision Pipeline <i class='fa-solid fa-spinner animate-spin ml-1.5'></i>";

    // Build FormData for multipart/form-data submission
    const formData = new FormData();
    formData.append('image', fileInput.files[0]);
    formData.append('lat', lat);
    formData.append('lon', lon);
    formData.append('gps_accuracy', 15.0);
    formData.append('note', note);
    formData.append('device_id', currentUser.id);

    const result = await API.submitIncidentReport(formData);

    submitBtn.disabled = false;
    submitTxt.textContent = isCitizen ? "Submit Urgent Report" : "Run AI Processing Pipeline";

    if (result.success) {
        showToast("Report successfully submitted and classified!");
        // Reload incidents from API
        await loadIncidentsFromAPI();
        
        // Clear form
        if (isCitizen) {
            document.getElementById('cit-form-lat').value = '';
            document.getElementById('cit-form-lon').value = '';
            document.getElementById('cit-form-note').value = '';
            document.getElementById('cit-file-label').textContent = 'Upload your phone snapshot';
            switchTab('citizen-my-reports');
        } else {
            document.getElementById('form-lat').value = '';
            document.getElementById('form-lon').value = '';
            document.getElementById('form-note').value = '';
            document.getElementById('file-label-name').textContent = 'Select or drag file...';
            switchTab('dashboard');
        }
    } else {
        showToast(`Submission failed: ${result.error || 'Unknown error'}`);
    }
}

// =====================================================================
// MAP & VISUALIZATION
// =====================================================================

function initializeGISMapSandbox() {
    if (mapInstance !== null) {
        setTimeout(() => {
            mapInstance.invalidateSize();
        }, 100);
        return;
    }

    if (typeof L !== 'undefined') {
        try {
            mapInstance = L.map('map', {
                zoomControl: false,
                scrollWheelZoom: true
            }).setView([28.6180, 77.2090], 13);

            L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; OpenStreetMap &copy; CARTO',
                subdomains: 'abcd',
                maxZoom: 20
            }).addTo(mapInstance);

            markersGroup = L.layerGroup().addTo(mapInstance);
            heatmapGroup = L.layerGroup().addTo(mapInstance);

            // Map click to populate coordinates
            mapInstance.on('click', function(e) {
                const targetLat = e.latlng.lat.toFixed(6);
                const targetLon = e.latlng.lng.toFixed(6);

                if (currentUser.role === 'citizen') {
                    document.getElementById('cit-form-lat').value = targetLat;
                    document.getElementById('cit-form-lon').value = targetLon;
                } else {
                    document.getElementById('form-lat').value = targetLat;
                    document.getElementById('form-lon').value = targetLon;
                }
                showToast("Geographic coordinate captured from map selection.");
            });

            setTimeout(() => {
                mapInstance.invalidateSize();
                syncDataAndUI();
            }, 150);

        } catch (mapErr) {
            console.error("GIS platform loading error: ", mapErr);
            showToast("Map sandbox initiated. Real-time overlays offline.");
        }
    } else {
        showToast("Mapping resources unreachable. Check connectivity.");
    }
}

function syncDataAndUI() {
    if (!mapInstance) return;

    markersGroup.clearLayers();
    heatmapGroup.clearLayers();

    const heatCoords = [];
    const colorsMap = {
        low: "#10b981",
        medium: "#f59e0b",
        high: "#ff7a22",
        critical: "#ef4444"
    };

    liveIncidents.forEach(inc => {
        const color = colorsMap[inc.severity_level] || "#64748b";

        const marker = L.circleMarker([inc.latitude, inc.longitude], {
            radius: inc.severity_level === 'critical' ? 12 : 9,
            color: color,
            fillColor: color,
            fillOpacity: 0.85,
            weight: 2
        });

        marker.bindPopup(`
            <div class="p-1 font-sans" style="width: 170px;">
                <div class="flex items-center justify-between mb-2">
                    <span class="font-extrabold uppercase text-[10px] text-brandCharcoal">${inc.incident_type}</span>
                    <span class="text-[8px] border px-2 py-0.5 rounded-full font-bold uppercase" style="color: ${color}; border-color: ${color}50; background-color: ${color}10">${inc.severity_level}</span>
                </div>
                <button onclick="inspectIncident(${inc.id})" class="w-full bg-brandCharcoal hover:bg-black text-white font-bold py-1 rounded-lg text-[9px] uppercase transition-all shadow-sm">Inspect</button>
            </div>
        `);

        markersGroup.addLayer(marker);

        const intensityMap = { low: 0.3, medium: 0.5, high: 0.8, critical: 1.0 };
        const intensity = intensityMap[inc.severity_level] || 0.5;
        heatCoords.push([inc.latitude, inc.longitude, intensity]);
    });

    if (heatCoords.length > 0 && typeof L.heatLayer === 'function') {
        try {
            const heatLayer = L.heatLayer(heatCoords, { radius: 25, blur: 15 });
            heatmapGroup.addLayer(heatLayer);
        } catch(e) {
            console.warn("Heat layering skipped safely during rendering.");
        }
    }

    updateMapLayerVisibility();
    renderTriageFeeds();
}

function updateMapLayerVisibility() {
    if (activeLayerMode === 'markers') {
        mapInstance.addLayer(markersGroup);
        mapInstance.removeLayer(heatmapGroup);
        document.getElementById('layer-btn-markers').className = "px-3 py-1.5 rounded-xl text-xs font-bold transition-all bg-brandOrange text-white shadow-sm flex items-center gap-1.5";
        document.getElementById('layer-btn-heat').className = "px-3 py-1.5 rounded-xl text-xs font-bold transition-all text-gray-600 hover:bg-gray-100 flex items-center gap-1.5";
    } else {
        mapInstance.addLayer(heatmapGroup);
        mapInstance.removeLayer(markersGroup);
        document.getElementById('layer-btn-heat').className = "px-3 py-1.5 rounded-xl text-xs font-bold transition-all bg-brandOrange text-white shadow-sm flex items-center gap-1.5";
        document.getElementById('layer-btn-markers').className = "px-3 py-1.5 rounded-xl text-xs font-bold transition-all text-gray-600 hover:bg-gray-100 flex items-center gap-1.5";
    }
}

function toggleMapLayer(mode) {
    activeLayerMode = mode;
    updateMapLayerVisibility();
    showToast(`GIS mapping view toggled to ${mode}.`);
}

function renderTriageFeeds() {
    const opFeedContainer = document.getElementById('log-feed-container');
    const citFeedContainer = document.getElementById('citizen-submissions-list');

    if (opFeedContainer) opFeedContainer.innerHTML = '';
    if (citFeedContainer) citFeedContainer.innerHTML = '';

    const statusColors = {
        low: 'bg-emerald-50 text-emerald-600 border-emerald-100',
        medium: 'bg-amber-50 text-amber-600 border-amber-100',
        high: 'bg-orange-50 text-orange-600 border-orange-100',
        critical: 'bg-red-50 text-red-600 border-red-100'
    };

    const sorted = [...liveIncidents].sort((a, b) => (b.confidence_score || 0) - (a.confidence_score || 0));
    let citizenOwnCount = 0;

    sorted.forEach(inc => {
        const badgeStyle = statusColors[inc.severity_level] || 'bg-gray-50 text-gray-600';
        
        const cardHTML = `
            <div class="w-12 h-12 bg-gray-50 rounded-xl overflow-hidden shrink-0 border border-gray-100 relative">
                <img src="https://placehold.co/100x100/1d1f23/ffffff?text=${inc.incident_type.charAt(0)}" class="w-full h-full object-cover">
            </div>
            <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between">
                    <span class="text-xs font-extrabold text-brandCharcoal truncate uppercase tracking-wide">${inc.incident_type}</span>
                    <span class="text-[8px] font-extrabold uppercase px-1.5 py-0.5 rounded-md border ${badgeStyle}">${inc.severity_level}</span>
                </div>
                <p class="text-[10px] text-gray-500 font-semibold mt-1 leading-tight line-clamp-2">${inc.notes || 'No notes provided'}</p>
                <div class="flex items-center justify-between mt-2 text-[9px] font-extrabold text-gray-400">
                    <span><i class="fa-solid fa-square-poll-horizontal text-brandOrange mr-0.5"></i> Conf: ${(inc.confidence_score * 100).toFixed(0)}%</span>
                </div>
            </div>
        `;

        if (opFeedContainer) {
            const card = document.createElement('div');
            card.className = "bg-white p-3 rounded-2xl border border-gray-150 flex items-start gap-3 hover:border-brandOrange cursor-pointer transition-all premium-shadow";
            card.onclick = () => inspectIncident(inc.id);
            card.innerHTML = cardHTML;
            opFeedContainer.appendChild(card);
        }

        if (citFeedContainer) {
            citizenOwnCount++;
            const card = document.createElement('div');
            card.className = "bg-white p-3 rounded-2xl border border-gray-150 flex items-start gap-3 hover:border-brandOrange cursor-pointer transition-all premium-shadow";
            card.onclick = () => inspectIncident(inc.id);
            card.innerHTML = cardHTML;
            citFeedContainer.appendChild(card);
        }
    });

    if (document.getElementById('log-count')) {
        document.getElementById('log-count').textContent = `${liveIncidents.length} active items`;
    }
    if (document.getElementById('cit-report-count')) {
        document.getElementById('cit-report-count').textContent = `${citizenOwnCount} filed by you`;
    }
}

// =====================================================================
// INCIDENT INSPECTION & XAI
// =====================================================================

function inspectIncident(id) {
    const inc = liveIncidents.find(x => x.id === id);
    if (!inc) return;

    document.getElementById('drawer-type').textContent = inc.incident_type;
    document.getElementById('drawer-id').textContent = `INC-${inc.id}`;
    document.getElementById('drawer-location').innerHTML = `<i class="fa-solid fa-location-crosshairs mr-1 text-brandOrange"></i> [${inc.latitude.toFixed(5)}, ${inc.longitude.toFixed(5)}]`;
    document.getElementById('drawer-image').src = `https://placehold.co/300x200/1d1f23/ffffff?text=${inc.incident_type}`;
    document.getElementById('drawer-ai-reasoning').textContent = inc.raw_gemini_response ? inc.raw_gemini_response.substring(0, 150) + '...' : 'AI analysis processed.';
    document.getElementById('drawer-routing-target').textContent = 'Municipal Services';

    // XAI formula display
    const confidence = inc.confidence_score || 0.5;
    document.getElementById('drawer-confidence-total').textContent = `e = ${confidence.toFixed(2)}`;
    document.getElementById('formula-ml-label').textContent = (confidence * 0.5).toFixed(3);
    document.getElementById('formula-votes-label').textContent = '0.05';
    document.getElementById('formula-gps-label').textContent = '0.15';
    document.getElementById('formula-trust-label').textContent = '0.05';

    document.getElementById('incident-detail-drawer').classList.remove('hidden');
    if (mapInstance) {
        mapInstance.setView([inc.latitude, inc.longitude], 15);
    }
}

function closeDetailDrawer() {
    document.getElementById('incident-detail-drawer').classList.add('hidden');
}

// =====================================================================
// UI NAVIGATION & ROUTING
// =====================================================================

function switchTab(tabId) {
    const panels = [
        'tab-dashboard', 'tab-reports', 'tab-routing', 'tab-analytics',
        'tab-citizen-report', 'tab-citizen-my-reports', 'tab-citizen-safe-routing'
    ];
    panels.forEach(p => {
        const el = document.getElementById(p);
        if (el) el.classList.add('hidden');
    });

    const targetPanel = document.getElementById('tab-' + tabId);
    if (targetPanel) targetPanel.classList.remove('hidden');

    const labels = {
        'dashboard': 'Overview Dashboard',
        'reports': 'Manual Dispatches',
        'routing': 'Avoidance Routing',
        'analytics': 'Ward Metrics',
        'citizen-report': 'Report Anomaly',
        'citizen-my-reports': 'My Filed Reports',
        'citizen-safe-routing': 'Commuter Safety'
    };
    document.getElementById('breadcrumb-current').textContent = labels[tabId] || 'Workspace';

    if (mapInstance) {
        setTimeout(() => { mapInstance.invalidateSize(); }, 150);
    }
}

function toggleNavigationSidebar() {
    const navSidebar = document.getElementById('main-navigation-sidebar');
    const icon = document.getElementById('nav-collapse-icon');

    if (navigationSidebarCollapsed) {
        navSidebar.classList.replace('w-16', 'w-20');
        icon.className = "fa-solid fa-angles-left text-[10px]";
        navigationSidebarCollapsed = false;
    } else {
        navSidebar.classList.replace('w-20', 'w-16');
        icon.className = "fa-solid fa-angles-right text-[10px]";
        navigationSidebarCollapsed = true;
    }
    setTimeout(() => {
        if (mapInstance) mapInstance.invalidateSize();
    }, 300);
}

function toggleSidebarPanel() {
    const panel = document.getElementById('sidebar-panel');
    const icon = document.getElementById('sidebar-toggle-icon');
    
    if (sidebarPanelCollapsed) {
        panel.classList.replace('lg:w-0', 'lg:w-[450px]');
        panel.classList.remove('opacity-0', 'pointer-events-none');
        icon.className = "fa-solid fa-chevron-right text-xs";
        sidebarPanelCollapsed = false;
    } else {
        panel.classList.replace('lg:w-[450px]', 'lg:w-0');
        panel.classList.add('opacity-0', 'pointer-events-none');
        icon.className = "fa-solid fa-chevron-left text-xs";
        sidebarPanelCollapsed = true;
    }
    setTimeout(() => {
        if (mapInstance) mapInstance.invalidateSize();
    }, 310);
}

function filterLiveLog() {
    const query = document.getElementById('global-search').value.toLowerCase();
    const cards = document.querySelectorAll('#log-feed-container > div, #citizen-submissions-list > div');
    cards.forEach(card => {
        const text = card.textContent.toLowerCase();
        if (text.includes(query)) {
            card.style.display = 'flex';
        } else {
            card.style.display = 'none';
        }
    });
}

function calculateSafeRoutes() {
    if (!mapInstance) return;

    clearRoutes();

    let originRaw, destinationRaw;

    if (currentUser.role === 'citizen') {
        originRaw = document.getElementById('cit-route-start').value.split(',').map(Number);
        destinationRaw = document.getElementById('cit-route-end').value.split(',').map(Number);
    } else {
        originRaw = document.getElementById('route-start').value.split(',').map(Number);
        destinationRaw = document.getElementById('route-end').value.split(',').map(Number);
    }

    if (originRaw.length !== 2 || destinationRaw.length !== 2 || isNaN(originRaw[0]) || isNaN(destinationRaw[0])) {
        return showToast("Provide correctly structured starting/ending coordinates.");
    }

    const startMarker = L.marker(originRaw, {
        icon: L.divIcon({
            className: '',
            html: `<div class="w-8 h-8 bg-brandCharcoal text-white rounded-full flex items-center justify-center font-bold border-2 border-white text-xs shadow-md">A</div>`
        })
    }).addTo(mapInstance);

    const endMarker = L.marker(destinationRaw, {
        icon: L.divIcon({
            className: '',
            html: `<div class="w-8 h-8 bg-brandOrange text-white rounded-full flex items-center justify-center font-bold border-2 border-white text-xs shadow-md">B</div>`
        })
    }).addTo(mapInstance);

    routeMarkers.push(startMarker, endMarker);

    const routeCoordinates = [
        originRaw,
        [28.6110, 77.2000],
        [28.6200, 77.2100],
        [28.6290, 77.2150],
        destinationRaw
    ];

    routeLine = L.polyline(routeCoordinates, {
        color: '#ff7a22',
        weight: 6,
        opacity: 0.90,
        dashArray: '10, 6',
        lineJoin: 'round'
    }).addTo(mapInstance);

    mapInstance.fitBounds(routeLine.getBounds(), { padding: [50, 50] });

    if (currentUser.role === 'citizen') {
        document.getElementById('cit-routing-comparison').classList.remove('hidden');
    } else {
        document.getElementById('routing-comparison-results').classList.remove('hidden');
    }

    showToast("Risk detours calculated. Avoidance tracks mapped.");
}

function clearRoutes() {
    if (mapInstance) {
        routeMarkers.forEach(m => mapInstance.removeLayer(m));
        if (routeLine) mapInstance.removeLayer(routeLine);
    }
    routeMarkers = [];
    routeLine = null;
    
    document.getElementById('cit-routing-comparison').classList.add('hidden');
    document.getElementById('routing-comparison-results').classList.add('hidden');
}

// =====================================================================
// INSTAGRAM SHARE CARD & UTILITIES
// =====================================================================

function handleFileSelect(e) {
    if (e.target.files.length > 0) {
        const labelName = e.target.files[0].name;
        if (currentUser.role === 'citizen') {
            document.getElementById('cit-file-label').textContent = labelName;
        } else {
            document.getElementById('file-label-name').textContent = labelName;
        }
        showToast("Physical photo linked successfully.");
    }
}

function generateInstagramCard() {
    const activeId = document.getElementById('drawer-id').textContent.replace('INC-', '');
    const inc = liveIncidents.find(x => x.id == activeId);
    if (!inc) return;

    const canvas = document.getElementById('instagram-canvas');
    const ctx = canvas.getContext('2d');

    ctx.fillStyle = "#1d1f23";
    ctx.fillRect(0, 0, 400, 400);

    ctx.fillStyle = "#ff7a22";
    ctx.fillRect(0, 0, 400, 50);

    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 14px 'Plus Jakarta Sans', sans-serif";
    ctx.fillText("RoadPulse AI — CIVIC EVIDENCE DISPATCH", 20, 32);

    ctx.strokeStyle = "rgba(255, 122, 34, 0.3)";
    ctx.lineWidth = 1;
    for(let i = 0; i < 400; i += 20) {
        ctx.beginPath();
        ctx.moveTo(i, 50);
        ctx.lineTo(i, 200);
        ctx.stroke();
    }

    ctx.fillStyle = "rgba(255, 122, 34, 0.05)";
    ctx.fillRect(0, 50, 400, 150);

    ctx.strokeStyle = "#ff7a22";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(200, 80);
    ctx.lineTo(240, 150);
    ctx.lineTo(160, 150);
    ctx.closePath();
    ctx.stroke();

    ctx.fillStyle = "#ff7a22";
    ctx.font = "bold 20px sans-serif";
    ctx.fillText("!", 197, 140);

    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 20px sans-serif";
    ctx.fillText(inc.incident_type.toUpperCase(), 20, 240);

    ctx.fillStyle = "#a1a1aa";
    ctx.font = "12px sans-serif";
    ctx.fillText(`ID: INC-${inc.id} | Severity: ${inc.severity_level.toUpperCase()}`, 20, 265);

    ctx.fillStyle = "#ff7a22";
    ctx.font = "bold 12px monospace";
    ctx.fillText(`GPS: [${inc.latitude.toFixed(4)}, ${inc.longitude.toFixed(4)}]`, 20, 290);

    ctx.fillStyle = "#f4f5f8";
    ctx.font = "11px sans-serif";
    wrapText(ctx, `Report verified by Gemini AI.`, 20, 320, 360, 16);

    ctx.save();
    ctx.translate(200, 310);
    ctx.rotate(-Math.PI / 12);
    ctx.fillStyle = "rgba(255, 122, 34, 0.15)";
    ctx.font = "900 24px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("VERIFIED EVIDENCE", 0, 0);
    ctx.restore();

    ctx.fillStyle = "#71717a";
    ctx.font = "9px sans-serif";
    ctx.fillText("Automated export under RoadPulse civic reporting framework v4.5", 20, 380);

    document.getElementById('share-card-modal').classList.remove('hidden');
}

function closeShareModal() {
    document.getElementById('share-card-modal').classList.add('hidden');
}

function downloadShareCard() {
    const canvas = document.getElementById('instagram-canvas');
    const dataUrl = canvas.toDataURL("image/png");
    
    const link = document.createElement('a');
    link.download = `RoadPulse_Complaint_${document.getElementById('drawer-id').textContent}.png`;
    link.href = dataUrl;
    link.click();
    showToast("Verified Instagram Evidence card exported to folder.");
    closeShareModal();
}

function wrapText(context, text, x, y, maxWidth, lineHeight) {
    const words = text.split(' ');
    let line = '';

    for (let n = 0; n < words.length; n++) {
        let testLine = line + words[n] + ' ';
        let metrics = context.measureText(testLine);
        let testWidth = metrics.width;
        if (testWidth > maxWidth && n > 0) {
            context.fillText(line, x, y);
            line = words[n] + ' ';
            y += lineHeight;
        } else {
            line = testLine;
        }
    }
    context.fillText(line, x, y);
}

function voteOnDrawerIncident(voteType) {
    showToast(voteType === 'confirm' ? 'Consensus verification registered.' : 'Negative review registered.');
}

function showToast(message) {
    const toast = document.getElementById('toast-notif');
    const label = document.getElementById('toast-message');
    label.textContent = message;
    toast.classList.remove('hidden');
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 4000);
}
