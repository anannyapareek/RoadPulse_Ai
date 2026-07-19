// Pre-seeded database items for high realism and validation scenarios
        
        // Current runtime application state database
        let databaseIncidents = [];

        async function fetchLiveIncidents() {
            const response = await API.getIncidents();
            if(response.success) {
                // Ensure field mappings match if backend uses different keys
                databaseIncidents = response.incidents.map(inc => ({
                    ...inc,
                    lat: inc.latitude,
                    lon: inc.longitude
                }));
                if (typeof syncDataAndUI === "function") syncDataAndUI();
            }
        }

        let currentUser = {
            role: null, // 'citizen' or 'operator'
            id: null,   // username
            ward: null, // citizen's active ward
            trust_score: 50 // starting hackathon base trust
        };

        let mapInstance = null;
        let markersGroup = null;
        let heatmapGroup = null;
        let activeLayerMode = 'markers'; // 'markers' or 'heat'
        let routeMarkers = [];
        let routeLine = null;
        let chartInstance = null;
        let navigationSidebarCollapsed = false;
        let sidebarPanelCollapsed = false;

        // UNIFIED AUTHENTICATION AND ROLE SELECTION CONTROLLER
        function fillAndLogin(username, password) {
            document.getElementById('login-username').value = username;
            document.getElementById('login-password').value = password;
            
            // Auto submit form directly
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

            // Route user depending on credentials (Simplified single gateway flow)
            if (usernameInput.toLowerCase() === 'admin' && passwordInput === 'pulse2026') {
                // Initialize Operator Command Hub
                currentUser.role = 'operator';
                currentUser.id = "Admin Operator (Warden-04)";
                currentUser.ward = "Central Command";
                currentUser.trust_score = 100; // Perfect system administrative trust

                document.getElementById('header-platform-label').textContent = "RoadPulse AI platform";
                document.getElementById('header-workspace-label').textContent = "Overview Console";
                document.getElementById('workspace-badge').textContent = "2026 Command v4.5";
                document.getElementById('avatar-user').src = "https://placehold.co/100x100/1d1f23/ffffff?text=OP";
                document.getElementById('user-trust-badge').textContent = currentUser.trust_score;

                document.getElementById('nav-citizen-group').classList.add('hidden');
                document.getElementById('nav-operator-group').classList.remove('hidden');

                document.getElementById('citizen-views-container').classList.add('hidden');
                document.getElementById('operator-views-container').classList.remove('hidden');

                setupMobileNavigationBar('operator');

                document.getElementById('login-screen').classList.add('hidden');
                document.getElementById('app-shell').classList.remove('hidden');

                switchTab('dashboard');
                initializeGISMapSandbox();
                initResolutionTimelineChart();
                fetchLiveIncidents();
                showToast("Command Console Auth Verified.");

            } else if (usernameInput.toLowerCase() === 'citizen' && passwordInput === 'user2026') {
                // Initialize Citizen / Customer Portal
                currentUser.role = 'citizen';
                currentUser.id = "citizen";
                currentUser.ward = "Ward 12 (Central Civic)";
                currentUser.trust_score = 75; // Pre-validated civilian user trust

                // Configure header display values
                document.getElementById('header-platform-label').textContent = "Citizen Portal (Ward 12)";
                document.getElementById('header-workspace-label').textContent = "Community Feedback & Dispatch Workspace";
                document.getElementById('workspace-badge').textContent = "Citizen Token Approved";
                document.getElementById('avatar-user').src = "https://placehold.co/100x100/ff7a22/ffffff?text=CI";
                document.getElementById('user-trust-badge').textContent = currentUser.trust_score;

                // Configure sidebar element filters
                document.getElementById('nav-citizen-group').classList.remove('hidden');
                document.getElementById('nav-operator-group').classList.add('hidden');

                document.getElementById('citizen-views-container').classList.remove('hidden');
                document.getElementById('operator-views-container').classList.add('hidden');

                // Set mobile responsive controls
                setupMobileNavigationBar('citizen');
                
                // Show App Interface
                document.getElementById('login-screen').classList.add('hidden');
                document.getElementById('app-shell').classList.remove('hidden');

                // Initial Tab Switch
                switchTab('citizen-report');
                initializeGISMapSandbox();
                fetchLiveIncidents();
                showToast("Citizen reporting node online.");

            } else {
                // Fallback / Validation Warning
                showToast("Access Denied: Invalid credentials! Check demo credentials below.");
            }
        }

        function setupMobileNavigationBar(role) {
            const container = document.getElementById('mobile-navigation-bar');
            container.innerHTML = '';

            if (role === 'citizen') {
                container.innerHTML = `
                    <button onclick="switchTab('citizen-report')" id="mob-nav-citizen-report" class="flex-1 py-2 text-xs font-bold text-center rounded-lg text-gray-500 hover:bg-gray-50 transition-all">Submit</button>
                    <button onclick="switchTab('citizen-my-reports')" id="mob-nav-citizen-my-reports" class="flex-1 py-2 text-xs font-bold text-center rounded-lg text-gray-500 hover:bg-gray-50 transition-all">My Tracks</button>
                    <button onclick="switchTab('citizen-safe-routing')" id="mob-nav-citizen-safe-routing" class="flex-1 py-2 text-xs font-bold text-center rounded-lg text-gray-500 hover:bg-gray-50 transition-all">Safe Path</button>
                `;
            } else {
                container.innerHTML = `
                    <button onclick="switchTab('dashboard')" id="mob-nav-dashboard" class="flex-1 py-2 text-xs font-bold text-center rounded-lg text-gray-500 hover:bg-gray-50 transition-all">Overview</button>
                    <button onclick="switchTab('reports')" id="mob-nav-reports" class="flex-1 py-2 text-xs font-bold text-center rounded-lg text-gray-500 hover:bg-gray-50 transition-all">Dispatch</button>
                    <button onclick="switchTab('routing')" id="mob-nav-routing" class="flex-1 py-2 text-xs font-bold text-center rounded-lg text-gray-500 hover:bg-gray-50 transition-all">Routing</button>
                    <button onclick="switchTab('analytics')" id="mob-nav-analytics" class="flex-1 py-2 text-xs font-bold text-center rounded-lg text-gray-500 hover:bg-gray-50 transition-all">Metrics</button>
                `;
            }
        }

        function logOut() {
            currentUser.role = null;
            currentUser.id = null;
            currentUser.ward = null;
            currentUser.trust_score = 50;

            // Clear credentials values
            document.getElementById('login-username').value = '';
            document.getElementById('login-password').value = '';

            document.getElementById('app-shell').classList.add('hidden');
            document.getElementById('login-screen').classList.remove('hidden');
            showToast("Workspace session locked.");
        }

        // Dynamic map loader
        function initializeGISMapSandbox() {
            if (mapInstance !== null) {
                setTimeout(() => {
                    mapInstance.invalidateSize();
                }, 100);
                return;
            }

            if (typeof L !== 'undefined') {
                try {
                    // Centralize on New Delhi area coordinates for demonstration realism
                    mapInstance = L.map('map', {
                        zoomControl: false,
                        scrollWheelZoom: true
                    }).setView([28.6180, 77.2090], 13);

                    // Tile mapping matching dark/neutral minimal modern aesthetic
                    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
                        attribution: '&copy; OpenStreetMap &copy; CARTO',
                        subdomains: 'abcd',
                        maxZoom: 20
                    }).addTo(mapInstance);

                    markersGroup = L.layerGroup().addTo(mapInstance);
                    heatmapGroup = L.layerGroup().addTo(mapInstance);

                    // Bind dynamic map clicks to latitude and longitude fields
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

        // Expand/Collapse the navigation left sidebar capsule
        function toggleNavigationSidebar() {
            const navSidebar = document.getElementById('main-navigation-sidebar');
            const icon = document.getElementById('nav-collapse-icon');
            const labels = document.querySelectorAll('.sidebar-label');

            if (navigationSidebarCollapsed) {
                // Expand
                navSidebar.classList.replace('w-16', 'w-20');
                labels.forEach(lbl => lbl.classList.add('hidden'));
                icon.className = "fa-solid fa-angles-left text-[10px]";
                navigationSidebarCollapsed = false;
            } else {
                // Collapse further
                navSidebar.classList.replace('w-20', 'w-16');
                labels.forEach(lbl => lbl.classList.add('hidden'));
                icon.className = "fa-solid fa-angles-right text-[10px]";
                navigationSidebarCollapsed = true;
            }
            setTimeout(() => {
                if (mapInstance) mapInstance.invalidateSize();
            }, 300);
        }

        // Collapse/Expand the right-hand panel sidebar containing fields and telemetry
        function toggleSidebarPanel() {
            const panel = document.getElementById('sidebar-panel');
            const icon = document.getElementById('sidebar-toggle-icon');
            
            if (sidebarPanelCollapsed) {
                // Expand
                panel.classList.replace('lg:w-0', 'lg:w-[450px]');
                panel.classList.remove('opacity-0', 'pointer-events-none');
                icon.className = "fa-solid fa-chevron-right text-xs";
                sidebarPanelCollapsed = false;
            } else {
                // Collapse
                panel.classList.replace('lg:w-[450px]', 'lg:w-0');
                panel.classList.add('opacity-0', 'pointer-events-none');
                icon.className = "fa-solid fa-chevron-left text-xs";
                sidebarPanelCollapsed = true;
            }
            setTimeout(() => {
                if (mapInstance) mapInstance.invalidateSize();
            }, 310);
        }

        function switchTab(tabId) {
            // Hide all tab screens
            const panels = [
                'tab-dashboard', 'tab-reports', 'tab-routing', 'tab-analytics',
                'tab-citizen-report', 'tab-citizen-my-reports', 'tab-citizen-safe-routing'
            ];
            panels.forEach(p => {
                const el = document.getElementById(p);
                if (el) el.classList.add('hidden');
            });

            // Deactivate all Left Sidebar Nav highlights
            const navs = [
                'nav-dashboard', 'nav-reports', 'nav-routing', 'nav-analytics',
                'nav-citizen-report', 'nav-citizen-my-reports', 'nav-citizen-safe-routing'
            ];
            navs.forEach(n => {
                const btn = document.getElementById(n);
                if (btn) btn.className = "w-full h-12 flex items-center justify-center text-gray-400 hover:text-brandCharcoal hover:bg-gray-100 rounded-2xl transition-all duration-300";
            });

            // Deactivate mobile nav buttons
            const mobBtns = [
                'mob-nav-dashboard', 'mob-nav-reports', 'mob-nav-routing', 'mob-nav-analytics',
                'mob-nav-citizen-report', 'mob-nav-citizen-my-reports', 'mob-nav-citizen-safe-routing'
            ];
            mobBtns.forEach(mbId => {
                const btn = document.getElementById(mbId);
                if (btn) btn.className = "flex-1 py-2 text-xs font-bold text-center rounded-lg text-gray-500 hover:bg-gray-50 transition-all";
            });

            // Activate Tab visually
            const targetPanel = document.getElementById('tab-' + tabId);
            if (targetPanel) targetPanel.classList.remove('hidden');

            const targetNav = document.getElementById('nav-' + tabId);
            if (targetNav) {
                targetNav.className = "w-full h-12 flex items-center justify-center rounded-2xl transition-all duration-300 active-nav-item";
            }

            const targetMob = document.getElementById('mob-nav-' + tabId);
            if (targetMob) {
                targetMob.className = "flex-1 py-2 text-xs font-bold text-center rounded-lg bg-brandOrange text-white transition-all";
            }

            // Sync breadcrumbs
            const labels = {
                'dashboard': 'Overview Dashboard',
                'reports': 'Manual Dispatches',
                'routing': 'Avoidance Routing',
                'analytics': 'Ward Metrics Tracker',
                'citizen-report': 'Anomaly Submission Form',
                'citizen-my-reports': 'My Filed Reports',
                'citizen-safe-routing': 'Commuter Safety Path'
            };
            document.getElementById('breadcrumb-current').textContent = labels[tabId] || 'Workspace';

            if (mapInstance) {
                setTimeout(() => { mapInstance.invalidateSize(); }, 150);
            }
        }

        function injectPreset(type) {
            const data = incidentPresets[type];
            if (!data) return;

            if (currentUser.role === 'citizen') {
                document.getElementById('cit-form-lat').value = data.lat;
                document.getElementById('cit-form-lon').value = data.lon;
                document.getElementById('cit-form-note').value = data.description_user;
                document.getElementById('cit-file-label').textContent = `${type.toUpperCase()}_Evidence.jpg`;
            } else {
                document.getElementById('form-lat').value = data.lat;
                document.getElementById('form-lon').value = data.lon;
                document.getElementById('form-note').value = data.description_user;
                document.getElementById('file-label-name').textContent = `${type.toUpperCase()}_Evidence.jpg`;
            }
            showToast(`Preset parameters matching ${type} seeded.`);
        }

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

        function showToast(message) {
            const toast = document.getElementById('toast-notif');
            const label = document.getElementById('toast-message');
            label.textContent = message;
            toast.classList.remove('hidden');
            setTimeout(() => {
                toast.classList.add('hidden');
            }, 4000);
        }

        // Distance formula logic
        function haversineDistanceMeters(lat1, lon1, lat2, lon2) {
            const R = 6371e3; // Earth radius in meters
            const phi1 = lat1 * Math.PI/180;
            const phi2 = lat2 * Math.PI/180;
            const dphi = (lat2-lat1) * Math.PI/180;
            const dlambda = (lon2-lon1) * Math.PI/180;

            const a = Math.sin(dphi/2) * Math.sin(dphi/2) +
                    Math.cos(phi1) * Math.cos(phi2) *
                    Math.sin(dlambda/2) * Math.sin(dlambda/2);
            const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));

            return R * c;
        }

        // Transparent scoring system exact report implementation (§4.3)
        // Formula: 50% gemini_confidence + 25% confirmations + 15% gps_quality + 10% reporter_trust
        function computeConfidenceScore(geminiConfidence, confirmations, gpsAccuracyM, reporterTrust) {
            const gpsQuality = gpsAccuracyM <= 20 ? 1.0 : (gpsAccuracyM <= 50 ? 0.6 : 0.3);
            const confirmationBoost = Math.min(1.0, confirmations / 3);
            const trustFactor = Math.min(1.0, reporterTrust / 100);

            const mlComponent = 0.50 * geminiConfidence;
            const votesComponent = 0.25 * confirmationBoost;
            const gpsComponent = 0.15 * gpsQuality;
            const trustComponent = 0.10 * trustFactor;

            const finalScore = mlComponent + votesComponent + gpsComponent + trustComponent;
            return {
                total: parseFloat(Math.min(finalScore, 1.0).toFixed(3)),
                ml: parseFloat(mlComponent.toFixed(3)),
                votes: parseFloat(votesComponent.toFixed(3)),
                gps: parseFloat(gpsComponent.toFixed(3)),
                trust: parseFloat(trustComponent.toFixed(3))
            };
        }

        // Form processing workflow
        function submitForm(event) {
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

            // Anomaly classification keywords map (§4.4)
            let detectedType = "pothole";
            let severity = "medium";
            let dept = "Municipal Road Department";

            const lowNote = note.toLowerCase();
            if (lowNote.includes('flood') || lowNote.includes('water') || lowNote.includes('drain')) {
                detectedType = "flooding";
                severity = "critical";
                dept = "Drainage Department";
            } else if (lowNote.includes('signal') || lowNote.includes('traffic light') || lowNote.includes('power')) {
                detectedType = "broken_signal";
                severity = "medium";
                dept = "Traffic Department";
            } else if (lowNote.includes('accident') || lowNote.includes('crash') || lowNote.includes('collision')) {
                detectedType = "accident";
                severity = "critical";
                dept = "Traffic Police";
            }

            // DUPLICATE SPATIAL DETECTOR CHECK (Exact §4.2 Report Limit Radius = 50 meters)
            let duplicateFound = null;
            for (let i = 0; i < databaseIncidents.length; i++) {
                const existing = databaseIncidents[i];
                if (existing.incident_type === detectedType) {
                    const dist = haversineDistanceMeters(lat, lon, existing.lat, existing.lon);
                    if (dist <= 50) {
                        duplicateFound = existing;
                        break;
                    }
                }
            }

            // UI submission button anim state
            const targetBtnId = isCitizen ? 'cit-btn-submit' : 'btn-submit';
            const targetTxtId = isCitizen ? 'cit-btn-submit-text' : 'btn-submit-text';
            const submitBtn = document.getElementById(targetBtnId);
            const submitTxt = document.getElementById(targetTxtId);

            submitBtn.disabled = true;
            submitTxt.innerHTML = "Processing Gemini Vision Pipeline <i class='fa-solid fa-spinner animate-spin ml-1.5'></i>";

            setTimeout(() => {
                submitBtn.disabled = false;
                submitTxt.textContent = isCitizen ? "Submit Urgent Report" : "Run AI Processing Pipeline";

                if (duplicateFound) {
                    duplicateFound.confirmations++;
                    
                    // Recalculate transparent score with new confirmation boost
                    const scoreObj = computeConfidenceScore(
                        duplicateFound.gemini_core_confidence || 0.85, 
                        duplicateFound.confirmations, 
                        duplicateFound.gps_accuracy_m || 15.0, 
                        duplicateFound.reporter_trust || 75
                    );
                    duplicateFound.confidence_score = scoreObj.total;
                    
                    showToast("Spatial Overlap (Within 50m limit): Dynamic data cluster merged.");
                    syncDataAndUI();
                    inspectIncident(duplicateFound.id);
                    if (isCitizen) {
                        switchTab('citizen-my-reports');
                    } else {
                        switchTab('dashboard');
                    }
                    return;
                }

                // Add to database
                const newId = "INC-" + (100 + databaseIncidents.length + 1);
                
                // Simulate standard Gemini Vision confidence core
                const simulatedGeminiConf = 0.82; 
                const simulatedGpsAccuracy = 15.0; // Simulated mobile cell accuracy in meters
                
                // Calculate formula score
                const scoreObj = computeConfidenceScore(
                    simulatedGeminiConf, 
                    1, 
                    simulatedGpsAccuracy, 
                    currentUser.trust_score
                );

                const newIncident = {
                    id: newId,
                    incident_type: detectedType,
                    severity: severity,
                    confidence_score: scoreObj.total,
                    gemini_core_confidence: simulatedGeminiConf,
                    status: "verified",
                    lat: lat,
                    lon: lon,
                    description_user: note || "Field report submitted with telemetry parameters.",
                    ai_reasoning: `Visual checks align with normal patterns for ${detectedType.replace('_', ' ')}. Automated priority dispatch activated.`,
                    ai_summary: `Newly registered ${detectedType.replace('_', ' ')} verified near coordinate sector.`,
                    department: dept,
                    image_path: `https://placehold.co/600x400/ffe4e6/991b1b?text=${detectedType.toUpperCase()}`,
                    confirmations: 1,
                    filed_by: isCitizen ? currentUser.id : 'system',
                    gps_accuracy_m: simulatedGpsAccuracy,
                    reporter_trust: currentUser.trust_score
                };

                databaseIncidents.push(newIncident);
                showToast("Telemetry successfully classified by Gemini Vision AI.");
                
                syncDataAndUI();
                inspectIncident(newId);

                // Increment citizen trust on successful verification report submission
                if (isCitizen) {
                    currentUser.trust_score = Math.min(100, currentUser.trust_score + 5);
                    document.getElementById('user-trust-badge').textContent = currentUser.trust_score;
                }

                if (isCitizen) {
                    switchTab('citizen-my-reports');
                } else {
                    switchTab('dashboard');
                }

                // Twilio escalation trigger check
                if (severity === "critical" && scoreObj.total >= 0.55) {
                    triggerSimulatedTwilioCall(newIncident);
                }

            }, 1800);
        }

        // Simulated emergency telephone dial action
        function triggerSimulatedTwilioCall(incident) {
            const twilioLog = document.getElementById('twilio-voice-log');
            twilioLog.innerHTML += `<div class="text-brandOrange font-bold">[CALLING] Alert dispatch queued to ${incident.department}...</div>`;
            twilioLog.scrollTop = twilioLog.scrollHeight;

            // Increment widget counter dynamically
            const callWidget = document.getElementById('widget-dispatches');
            if (callWidget) {
                callWidget.textContent = parseInt(callWidget.textContent) + 1;
            }

            setTimeout(() => {
                twilioLog.innerHTML += `<div class="text-emerald-400">[CONNECTED] Auto-assistant streaming dispatch voice payload...</div>`;
                twilioLog.innerHTML += `<div class="text-slate-300">"Urgent alert: Confirmed ${incident.incident_type.replace('_',' ')} detected at [${incident.lat.toFixed(4)}, ${incident.lon.toFixed(4)}]. Conf: ${(incident.confidence_score*100).toFixed(0)}%"</div>`;
                twilioLog.scrollTop = twilioLog.scrollHeight;
            }, 2500);
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

        function syncDataAndUI() {
            if (!mapInstance) return;

            // Clear old layers
            markersGroup.clearLayers();
            heatmapGroup.clearLayers();

            const heatCoords = [];
            const colorsMap = {
                low: "#10b981",
                medium: "#f59e0b",
                high: "#ff7a22",
                critical: "#ef4444"
            };

            databaseIncidents.forEach(inc => {
                const color = colorsMap[inc.severity] || "#64748b";

                const marker = L.circleMarker([inc.lat, inc.lon], {
                    radius: inc.severity === 'critical' ? 12 : 9,
                    color: color,
                    fillColor: color,
                    fillOpacity: 0.85,
                    weight: 2
                });

                marker.bindPopup(`
                    <div class="p-1 font-sans" style="width: 170px;">
                        <div class="flex items-center justify-between mb-2">
                            <span class="font-extrabold uppercase text-[10px] text-brandCharcoal">${inc.incident_type.replace('_',' ')}</span>
                            <span class="text-[8px] border px-2 py-0.5 rounded-full font-bold uppercase" style="color: ${color}; border-color: ${color}50; background-color: ${color}10">${inc.severity}</span>
                        </div>
                        <img src="${inc.image_path}" class="w-full h-20 object-cover rounded-lg mb-2 border border-gray-150">
                        <button onclick="inspectIncident('${inc.id}')" class="w-full bg-brandCharcoal hover:bg-black text-white font-bold py-1 rounded-lg text-[9px] uppercase transition-all shadow-sm">Inspect</button>
                    </div>
                `);

                markersGroup.addLayer(marker);

                const intensity = { low: 0.3, medium: 0.5, high: 0.8, critical: 1.0 }[inc.severity] || 0.5;
                heatCoords.push([inc.lat, inc.lon, intensity]);
            });

            // Re-render heatmap layer if coordinates are loaded
            if (heatCoords.length > 0 && typeof L.heatLayer === 'function') {
                try {
                    const heatLayer = L.heatLayer(heatCoords, { radius: 25, blur: 15 });
                    heatmapGroup.addLayer(heatLayer);
                } catch(e) {
                    console.warn("Heat layering skipped safely during rendering.");
                }
            }

            updateMapLayerVisibility();

            // Populate Operator & Citizen Triage Lists
            renderTriageFeeds();

            if (currentUser.role === 'admin') {
                loadAnalytics();
            }
        }

        async function loadAnalytics() {
            const res = await API.fetchAnalytics();
            if (!res.success || !res.metrics) return;
            
            const m = res.metrics;
            document.getElementById('kpi-resolution-time').innerText = m.resolution_timeline_hours;
            document.getElementById('kpi-response-perf').innerHTML = `${m.response_performance_pct}% <i class="fa-solid fa-arrow-trend-up"></i>`;
            document.getElementById('kpi-pending-60').innerText = m.pending_over_60_days;

            if (m.pending_over_60_days > 0) {
                document.getElementById('overdue-alert-container').classList.remove('hidden');
                document.getElementById('overdue-alert-title').innerText = `${m.pending_over_60_days} Statutory Review Targets Overdue`;
                document.getElementById('overdue-alert-desc').innerText = `Action deadline exceeded for ${m.pending_over_60_days} complaints. Immediate attention required.`;
            } else {
                document.getElementById('overdue-alert-container').classList.add('hidden');
            }

            const wardContainer = document.getElementById('ward-metrics-container');
            wardContainer.innerHTML = '';
            m.ward_quality.forEach(w => {
                let statusClass, statusText;
                if (w.quality_score >= 80) {
                    statusClass = "bg-emerald-50 border-emerald-100 text-emerald-600";
                    statusText = "Optimal";
                } else if (w.quality_score >= 50) {
                    statusClass = "bg-amber-50 border-amber-100 text-amber-600";
                    statusText = "Warning";
                } else {
                    statusClass = "bg-rose-50 border-rose-100 text-rose-600";
                    statusText = "Poor";
                }

                wardContainer.innerHTML += `
                    <div class="flex justify-between items-center bg-white p-3 rounded-2xl border border-gray-200">
                        <div>
                            <span class="text-xs font-extrabold text-brandCharcoal block">${w.ward}</span>
                            <span class="text-[10px] text-gray-400 font-bold">${w.pending} Active Infrastructure Issues</span>
                        </div>
                        <span class="${statusClass} border text-[10px] font-extrabold px-3 py-1 rounded-full uppercase">${statusText}</span>
                    </div>
                `;
            });
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
            // Operator Panel Populator
            const opFeedContainer = document.getElementById('log-feed-container');
            // Citizen Panel Populator
            const citFeedContainer = document.getElementById('citizen-submissions-list');

            if (opFeedContainer) opFeedContainer.innerHTML = '';
            if (citFeedContainer) citFeedContainer.innerHTML = '';

            const statusColors = {
                low: 'bg-emerald-50 text-emerald-600 border-emerald-100',
                medium: 'bg-amber-50 text-amber-600 border-amber-100',
                high: 'bg-orange-50 text-orange-600 border-orange-100',
                critical: 'bg-red-50 text-red-600 border-red-100'
            };

            const sorted = [...databaseIncidents].sort((a,b) => b.confidence_score - a.confidence_score);
            let citizenOwnCount = 0;

            sorted.forEach(inc => {
                const badgeStyle = statusColors[inc.severity] || 'bg-gray-50 text-gray-600';
                
                // Card Template Structure
                const cardHTML = `
                    <div class="w-12 h-12 bg-gray-50 rounded-xl overflow-hidden shrink-0 border border-gray-100 relative">
                        <img src="${inc.image_path}" class="w-full h-full object-cover">
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center justify-between">
                            <span class="text-xs font-extrabold text-brandCharcoal truncate uppercase tracking-wide">${inc.incident_type.replace('_',' ')}</span>
                            <span class="text-[8px] font-extrabold uppercase px-1.5 py-0.5 rounded-md border ${badgeStyle}">${inc.severity}</span>
                        </div>
                        <p class="text-[9px] text-gray-400 font-bold mt-0.5 truncate"><i class="fa-solid fa-building-shield text-brandOrange mr-1"></i> ${inc.department}</p>
                        <p class="text-[10px] text-gray-500 font-semibold mt-1 leading-tight line-clamp-2">${inc.description_user}</p>
                        <div class="flex items-center justify-between mt-2 text-[9px] font-extrabold text-gray-400">
                            <span><i class="fa-solid fa-square-poll-horizontal text-brandOrange mr-0.5"></i> ${inc.confirmations} votes</span>
                            <span class="text-brandCharcoal font-mono bg-slate-100 px-1 py-0.5 rounded">Conf: ${(inc.confidence_score*100).toFixed(0)}%</span>
                        </div>
                    </div>
                `;

                // Render into admin panel
                if (opFeedContainer) {
                    const card = document.createElement('div');
                    card.className = "bg-white p-3 rounded-2xl border border-gray-150 flex items-start gap-3 hover:border-brandOrange cursor-pointer transition-all premium-shadow";
                    card.onclick = () => inspectIncident(inc.id);
                    card.innerHTML = cardHTML;
                    opFeedContainer.appendChild(card);
                }

                // Render into citizen reports list if match
                if (citFeedContainer && inc.filed_by === currentUser.id) {
                    citizenOwnCount++;
                    const card = document.createElement('div');
                    card.className = "bg-white p-3 rounded-2xl border border-gray-150 flex items-start gap-3 hover:border-brandOrange cursor-pointer transition-all premium-shadow";
                    card.onclick = () => inspectIncident(inc.id);
                    card.innerHTML = cardHTML;
                    citFeedContainer.appendChild(card);
                }
            });

            // Update log indicators
            if (document.getElementById('log-count')) {
                document.getElementById('log-count').textContent = `${databaseIncidents.length} active items`;
            }
            if (document.getElementById('cit-report-count')) {
                document.getElementById('cit-report-count').textContent = `${citizenOwnCount} filed by you`;
            }
        }

        function inspectIncident(id) {
            const inc = databaseIncidents.find(x => x.id === id);
            if (!inc) return;

            document.getElementById('drawer-type').textContent = inc.incident_type.replace('_',' ');
            document.getElementById('drawer-severity').textContent = inc.severity;
            document.getElementById('drawer-id').textContent = inc.id;

            const severityBadgeColors = {
                low: 'bg-emerald-50 text-emerald-600 border border-emerald-200',
                medium: 'bg-amber-50 text-amber-600 border border-amber-200',
                high: 'bg-orange-50 text-orange-600 border border-orange-200',
                critical: 'bg-red-50 text-red-600 border border-red-200'
            };
            document.getElementById('drawer-severity').className = `text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase ${severityBadgeColors[inc.severity]}`;

            document.getElementById('drawer-location').innerHTML = `<i class="fa-solid fa-location-crosshairs mr-1 text-brandOrange"></i> Coordinate Vector: [${inc.lat.toFixed(5)}, ${inc.lon.toFixed(5)}]`;
            document.getElementById('drawer-image').src = inc.image_path;
            document.getElementById('drawer-ai-reasoning').textContent = inc.ai_reasoning;
            document.getElementById('drawer-routing-target').textContent = inc.department;
            document.getElementById('drawer-confirmations').textContent = inc.confirmations;

            // Generate physical tel: triggers dynamic endpoints
            const phoneAction = document.getElementById('drawer-phone-action');
            if (inc.incident_type === 'accident') {
                phoneAction.href = "tel:100"; // Trigger standard emergency traffic police line
                phoneAction.innerHTML = `<i class="fa-solid fa-phone animate-bounce"></i> Call Highway Traffic Police (Tel: 100)`;
                phoneAction.classList.remove('hidden');
            } else if (inc.incident_type === 'flooding') {
                phoneAction.href = "tel:101"; // Drainage Emergency call link
                phoneAction.innerHTML = `<i class="fa-solid fa-phone animate-bounce"></i> Call Drainage Control Helpdesk (Tel: 101)`;
                phoneAction.classList.remove('hidden');
            } else {
                phoneAction.href = "tel:+15550199";
                phoneAction.innerHTML = `<i class="fa-solid fa-phone"></i> Call Municipal Support Desk`;
                phoneAction.classList.remove('hidden');
            }

            // Use real data from the backend instead of simulated pre-fed mock data
            let realGeminiConf = 0.5;
            if (inc.raw_gemini_response) {
                try {
                    const parsedGemini = JSON.parse(inc.raw_gemini_response);
                    if (parsedGemini.confidence_score !== undefined) {
                        realGeminiConf = parseFloat(parsedGemini.confidence_score);
                    }
                } catch (e) {} // Fallback if response is an error string
            }

            const realGpsAccuracy = inc.gps_accuracy || 15.0;
            const realReporterTrust = currentUser ? currentUser.trust_score : 50;
            const realConfirmations = inc.confirmations || 0;

            const scoreObj = computeConfidenceScore(
                realGeminiConf, 
                realConfirmations, 
                realGpsAccuracy, 
                realReporterTrust
            );

            // Ensure the UI matches the official backend confidence score
            const finalConfidence = inc.confidence_score ? inc.confidence_score.toFixed(3) : scoreObj.total;

            // Dynamically output transparent XAI weights to layout
            document.getElementById('drawer-confidence-total').textContent = `e = ${finalConfidence}`;
            document.getElementById('formula-ml-label').textContent = scoreObj.ml;
            document.getElementById('formula-votes-label').textContent = scoreObj.votes;
            document.getElementById('formula-gps-label').textContent = scoreObj.gps;
            document.getElementById('formula-trust-label').textContent = scoreObj.trust;

            const pct = Math.min(100, (realConfirmations / 4) * 100);
            document.getElementById('drawer-consensus-bar').style.width = `${pct}%`;

            document.getElementById('incident-detail-drawer').classList.remove('hidden');
            if (mapInstance) {
                mapInstance.setView([inc.lat, inc.lon], 15);
            }
        }

        function closeDetailDrawer() {
            document.getElementById('incident-detail-drawer').classList.add('hidden');
        }

        function voteOnDrawerIncident(voteType) {
            const idToSearch = document.getElementById('drawer-id').textContent;
            const match = databaseIncidents.find(x => x.id === idToSearch);

            if (match) {
                if (voteType === 'confirm') {
                    match.confirmations++;
                    showToast("Consensus verification registered.");
                } else {
                    match.confirmations = Math.max(0, match.confirmations - 1);
                    showToast("Negative review registered.");
                }
                syncDataAndUI();
                inspectIncident(match.id);
            }
        }

        async function calculateSafeRoutes() {
            if (!mapInstance) return;

            let originText, destinationText;
            let btnId, resultsBlockId;

            if (currentUser.role === 'citizen') {
                originText = document.getElementById('cit-route-start').value;
                destinationText = document.getElementById('cit-route-end').value;
                btnId = 'cit-btn-calculate-route';
                resultsBlockId = 'cit-routing-comparison';
            } else {
                originText = document.getElementById('route-start').value;
                destinationText = document.getElementById('route-end').value;
                btnId = 'btn-calculate-route';
                resultsBlockId = 'routing-comparison-results';
            }

            if (!originText || !destinationText) {
                return showToast("Provide starting and ending locations.");
            }

            const btn = document.getElementById(btnId);
            const originalBtnHtml = btn.innerHTML;
            btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Calculating Route...</span>`;
            btn.disabled = true;

            try {
                clearRoutes();
                showToast("Requesting smart route via Gemini Geocoder & TomTom...");

                const res = await API.fetchSmartRoute(originText, destinationText);
                
                if (res.error) {
                    showToast("Routing Error: " + res.error);
                    btn.innerHTML = originalBtnHtml;
                    btn.disabled = false;
                    return;
                }

                // Create customized Leaflet divicon waypoints
                const startMarker = L.marker([res.resolved_start.lat, res.resolved_start.lon], {
                    icon: L.divIcon({
                        className: '',
                        html: `<div class="w-8 h-8 bg-brandCharcoal text-white rounded-full flex items-center justify-center font-bold border-2 border-white text-xs shadow-md">A</div>`
                    })
                }).addTo(mapInstance);

                const endMarker = L.marker([res.resolved_end.lat, res.resolved_end.lon], {
                    icon: L.divIcon({
                        className: '',
                        html: `<div class="w-8 h-8 bg-brandOrange text-white rounded-full flex items-center justify-center font-bold border-2 border-white text-xs shadow-md">B</div>`
                    })
                }).addTo(mapInstance);

                routeMarkers.push(startMarker, endMarker);

                routeLine = L.polyline(res.polyline, {
                    color: res.risk_warning ? '#e11d48' : '#ff7a22', // rose-600 if risk, orange if safe
                    weight: 6,
                    opacity: 0.90,
                    dashArray: '10, 6',
                    lineJoin: 'round'
                }).addTo(mapInstance);

                mapInstance.fitBounds(routeLine.getBounds(), { padding: [50, 50] });

                // Update UI metrics
                const riskColor = res.risk_warning ? 'text-rose-600' : 'text-emerald-600';
                const badgeColor = res.risk_warning ? 'bg-rose-500' : 'bg-emerald-500';
                const badgeText = res.risk_warning ? 'Risk Detected' : 'Optimal Path';
                const routeTitle = res.risk_warning ? 'Hazard Avoidance Path' : 'Smart Route';
                
                if (currentUser.role === 'citizen') {
                    document.getElementById('cit-route-status-badge').className = `absolute -top-1 -right-1 text-white text-[8px] font-extrabold uppercase px-2 py-0.5 rounded-bl-lg ${badgeColor}`;
                    document.getElementById('cit-route-status-badge').innerText = badgeText;
                    document.getElementById('cit-route-result-title').innerText = routeTitle;
                    document.getElementById('cit-route-result-subtitle').innerText = `${res.resolved_start.resolved_name} to ${res.resolved_end.resolved_name}`;
                    document.getElementById('cit-route-result-risk').className = `text-xs font-extrabold block ${riskColor}`;
                    document.getElementById('cit-route-result-risk').innerText = `Risk Factor: ${(res.destination_incident_risk * 100).toFixed(0)}%`;
                    document.getElementById('cit-route-result-metrics').innerText = `${res.distance_km} KM | ${res.travel_time_minutes} mins`;
                } else {
                    document.getElementById('route-status-badge').className = `absolute -top-1 -right-1 text-white text-[8px] font-extrabold uppercase px-2 py-0.5 rounded-bl-lg ${badgeColor}`;
                    document.getElementById('route-status-badge').innerText = badgeText;
                    document.getElementById('route-result-title').innerText = routeTitle;
                    document.getElementById('route-result-subtitle').innerText = `${res.resolved_start.resolved_name} to ${res.resolved_end.resolved_name}`;
                    document.getElementById('route-result-risk').className = `text-xs font-extrabold block ${riskColor}`;
                    document.getElementById('route-result-risk').innerText = `Risk Factor: ${(res.destination_incident_risk * 100).toFixed(0)}%`;
                    document.getElementById('route-result-metrics').innerText = `${res.distance_km} KM | ${res.travel_time_minutes} mins`;
                }

                document.getElementById(resultsBlockId).classList.remove('hidden');
                showToast("Real-time route generated.");

            } catch (err) {
                console.error(err);
                showToast("Failed to calculate route.");
            } finally {
                btn.innerHTML = originalBtnHtml;
                btn.disabled = false;
            }
        }

        function clearRoutes() {
            routeMarkers.forEach(m => mapInstance.removeLayer(m));
            if (routeLine) mapInstance.removeLayer(routeLine);
            routeMarkers = [];
            routeLine = null;
            
            document.getElementById('cit-routing-comparison').classList.add('hidden');
            document.getElementById('routing-comparison-results').classList.add('hidden');
        }

        function initResolutionTimelineChart() {
            const canvas = document.getElementById('resolutionChart');
            if (!canvas) return;

            const ctx = canvas.getContext('2d');
            
            if (chartInstance) {
                chartInstance.destroy();
            }

            chartInstance = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['Roads', 'Drainage', 'Traffic Police', 'Municipal'],
                    datasets: [{
                        label: 'Resolution Timelines (Hours)',
                        data: [24, 48, 4, 36],
                        backgroundColor: '#ff7a22',
                        hoverBackgroundColor: '#1d1f23',
                        borderRadius: 8,
                        barThickness: 24
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: '#f1f5f9'
                            },
                            ticks: {
                                color: '#94a3b8',
                                font: {
                                    family: 'Plus Jakarta Sans',
                                    size: 9,
                                    weight: 'bold'
                                }
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                color: '#1d1f23',
                                font: {
                                    family: 'Plus Jakarta Sans',
                                    size: 10,
                                    weight: 'bold'
                                }
                            }
                        }
                    }
                }
            });
        }

        // HTML Canvas watermarked Instagram Share Card generator (§1)
        function generateInstagramCard() {
            const activeId = document.getElementById('drawer-id').textContent;
            const inc = databaseIncidents.find(x => x.id === activeId);
            if (!inc) return;

            const canvas = document.getElementById('instagram-canvas');
            const ctx = canvas.getContext('2d');

            // Draw premium background color
            ctx.fillStyle = "#1d1f23";
            ctx.fillRect(0, 0, 400, 400);

            // Draw branding header bar
            ctx.fillStyle = "#ff7a22";
            ctx.fillRect(0, 0, 400, 50);

            // Text on header
            ctx.fillStyle = "#ffffff";
            ctx.font = "bold 14px 'Plus Jakarta Sans', sans-serif";
            ctx.fillText("RoadPulse AI — CIVIC EVIDENCE DISPATCH", 20, 32);

            // Draw a high-tech vector wireframe layout instead of an external placehold.co image (to guarantee NO CORS errors on download)
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

            // Stylized Hazard Sign in vectors
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

            // Incident details
            ctx.fillStyle = "#ffffff";
            ctx.font = "bold 20px sans-serif";
            ctx.fillText(inc.incident_type.toUpperCase().replace('_',' '), 20, 240);

            ctx.fillStyle = "#a1a1aa";
            ctx.font = "12px sans-serif";
            ctx.fillText(`ID: ${inc.id} | Severity: ${inc.severity.toUpperCase()}`, 20, 265);

            // Coordinates details
            ctx.fillStyle = "#ff7a22";
            ctx.font = "bold 12px monospace";
            ctx.fillText(`GPS COORDINATES: [${inc.lat.toFixed(4)}, ${inc.lon.toFixed(4)}]`, 20, 290);

            // AI summary note
            ctx.fillStyle = "#f4f5f8";
            ctx.font = "11px sans-serif";
            const summaryText = inc.ai_summary || "Verification anomaly parsed in real-time.";
            wrapText(ctx, `Complaint: "${summaryText}"`, 20, 320, 360, 16);

            // Anti-Tamper Security Watermark (§1)
            ctx.save();
            ctx.translate(200, 310);
            ctx.rotate(-Math.PI / 12);
            ctx.fillStyle = "rgba(255, 122, 34, 0.15)";
            ctx.font = "900 24px sans-serif";
            ctx.textAlign = "center";
            ctx.fillText("VERIFIED EVIDENCE", 0, 0);
            ctx.restore();

            // Bottom metadata info
            ctx.fillStyle = "#71717a";
            ctx.font = "9px sans-serif";
            ctx.fillText("Automated export under RoadPulse civic reporting framework v4.5", 20, 380);

            // Show interactive modal popover
            document.getElementById('share-card-modal').classList.remove('hidden');
        }

        function closeShareModal() {
            document.getElementById('share-card-modal').classList.add('hidden');
        }

        function downloadShareCard() {
            const canvas = document.getElementById('instagram-canvas');
            const dataUrl = canvas.toDataURL("image/png");
            
            // Create simulated download anchor element
            const link = document.createElement('a');
            link.download = `RoadPulse_Complaint_${document.getElementById('drawer-id').textContent}.png`;
            link.href = dataUrl;
            link.click();
            showToast("Verified Instagram Evidence card exported to folder.");
            closeShareModal();
        }

        // Helper to handle multiline text rendering inside share card canvas
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