// RoutePilot AI — Premium Frontend Application Logic

// Application State
let stops = [];
let routeDetails = null;
let map = null;
let routePolyline = null;
let markersGroup = null;

// DOM Elements
const stopsList = document.getElementById("stops-list");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatMessages = document.getElementById("chat-messages");
const thinkingBox = document.getElementById("agent-thinking");
const thinkingLogs = document.getElementById("thinking-logs");
const btnClearLogs = document.getElementById("btn-clear-logs");

const addStopInput = document.getElementById("add-stop-input");
const btnAddStop = document.getElementById("btn-add-stop");
const startStopSelect = document.getElementById("start-stop-select");
const endStopSelect = document.getElementById("end-stop-select");

const btnOptimize = document.getElementById("btn-optimize-itinerary");
const btnSave = document.getElementById("btn-save-itinerary");
const btnClear = document.getElementById("btn-clear-itinerary");

const btnShowSaved = document.getElementById("btn-show-saved");
const btnCloseDrawer = document.getElementById("btn-close-drawer");
const savedDrawer = document.getElementById("saved-drawer");
const savedRoutesList = document.getElementById("saved-routes-list");

const saveModal = document.getElementById("save-modal");
const saveRouteForm = document.getElementById("save-route-form");
const routeNameInput = document.getElementById("route-name-input");
const btnCloseModal = document.getElementById("btn-close-modal");
const btnCancelSave = document.getElementById("btn-cancel-save");

const metricDistance = document.getElementById("metric-distance");
const metricDuration = document.getElementById("metric-duration");
const metricStops = document.getElementById("metric-stops");

// Initialize Application
document.addEventListener("DOMContentLoaded", () => {
    initMap();
    initDragAndDrop();
    setupEventListeners();
    loadSessionMemory();
});

// Initialize Leaflet Map with Dark Mode Theme
function initMap() {
    // Center map on Delhi by default
    map = L.map("map", {
        zoomControl: true,
        fadeAnimation: true
    }).setView([28.6139, 77.2090], 11);

    // Load CartoDB Dark Matter tiles for a high-fidelity dark UI look
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);

    markersGroup = L.layerGroup().addTo(map);
}

// Set up DOM interaction event listeners
function setupEventListeners() {
    // Add manual stop
    btnAddStop.addEventListener("click", addStopFromInput);
    addStopInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            addStopFromInput();
        }
    });

    // Chat submit
    chatForm.addEventListener("submit", handleChatSubmit);
    btnClearLogs.addEventListener("click", () => {
        thinkingLogs.textContent = "";
        thinkingBox.classList.add("hidden");
    });

    // Itinerary actions
    btnOptimize.addEventListener("click", optimizeItinerary);
    btnClear.addEventListener("click", clearItinerary);
    
    // Save modal actions
    btnSave.addEventListener("click", () => {
        if (stops.length < 2) {
            alert("Add at least 2 stops to save a route plan!");
            return;
        }
        saveModal.classList.remove("hidden");
        routeNameInput.value = `Trip with ${stops.length} stops`;
        routeNameInput.focus();
    });
    
    btnCloseModal.addEventListener("click", () => saveModal.classList.add("hidden"));
    btnCancelSave.addEventListener("click", () => saveModal.classList.add("hidden"));
    saveRouteForm.addEventListener("submit", handleSaveRouteSubmit);

    // Saved drawer actions
    btnShowSaved.addEventListener("click", openSavedDrawer);
    btnCloseDrawer.addEventListener("click", () => savedDrawer.classList.add("hidden"));
    
    // Constraint selects
    startStopSelect.addEventListener("change", () => updateConstraintSelections());
    endStopSelect.addEventListener("change", () => updateConstraintSelections());
}

// Load current agent session state (sync map with Agent Memory on page load)
async function loadSessionMemory() {
    try {
        const response = await fetch("/api/memory");
        if (response.ok) {
            const data = await response.json();
            if (data.planned_route && data.planned_route.length > 0) {
                stops = data.planned_route;
                updateStopsUI();
                optimizeItinerary();
            }
        }
    } catch (err) {
        console.warn("Could not sync with session memory:", err);
    }
}

// Add a stop manually using input box
function addStopFromInput() {
    const val = addStopInput.value.trim();
    if (!val) return;
    
    if (stops.includes(val)) {
        alert("This place is already in your stops list!");
        return;
    }
    
    stops.push(val);
    addStopInput.value = "";
    updateStopsUI();
    optimizeItinerary();
}

// Update the stops list interface and dropdown options
function updateStopsUI() {
    // Clear list
    stopsList.innerHTML = "";
    
    if (stops.length === 0) {
        stopsList.innerHTML = `<li class="empty-list-placeholder">No stops added. Add stops manually above or chat with the agent to generate an itinerary!</li>`;
        metricStops.textContent = "0 Stops";
        updateDropdowns();
        return;
    }
    
    metricStops.textContent = `${stops.length} Stop${stops.length > 1 ? 's' : ''}`;
    
    stops.forEach((stop, index) => {
        const li = document.createElement("li");
        li.className = "stop-item";
        li.setAttribute("draggable", "true");
        li.setAttribute("data-index", index);
        
        li.innerHTML = `
            <div class="stop-info">
                <span class="stop-number">${index + 1}</span>
                <span class="stop-name" title="${stop}">${stop}</span>
            </div>
            <div class="stop-actions">
                <span class="stop-drag-handle" title="Drag to reorder"><i class="fa-solid fa-grip-vertical"></i></span>
                <button class="stop-delete-btn" data-index="${index}" title="Remove Stop"><i class="fa-solid fa-xmark"></i></button>
            </div>
        `;
        
        // Remove item button click
        li.querySelector(".stop-delete-btn").addEventListener("click", (e) => {
            const idx = parseInt(e.currentTarget.getAttribute("data-index"));
            stops.splice(idx, 1);
            updateStopsUI();
            optimizeItinerary();
        });
        
        stopsList.appendChild(li);
    });
    
    updateDropdowns();
    initDragAndDrop();
}

// Update Constraint Select Dropdowns
function updateDropdowns() {
    const currentStart = startStopSelect.value;
    const currentEnd = endStopSelect.value;
    
    startStopSelect.innerHTML = `<option value="">None (Auto-pick)</option>`;
    endStopSelect.innerHTML = `<option value="">None (Auto-pick)</option>`;
    
    stops.forEach(stop => {
        const optionStart = document.createElement("option");
        optionStart.value = stop;
        optionStart.textContent = stop;
        if (stop === currentStart) optionStart.selected = true;
        startStopSelect.appendChild(optionStart);
        
        const optionEnd = document.createElement("option");
        optionEnd.value = stop;
        optionEnd.textContent = stop;
        if (stop === currentEnd) optionEnd.selected = true;
        endStopSelect.appendChild(optionEnd);
    });
}

function updateConstraintSelections() {
    optimizeItinerary();
}

// HTML5 Drag and Drop logic for list reordering
let dragSrcEl = null;

function initDragAndDrop() {
    const items = document.querySelectorAll(".stop-item");
    items.forEach(item => {
        item.addEventListener("dragstart", handleDragStart, false);
        item.addEventListener("dragenter", handleDragEnter, false);
        item.addEventListener("dragover", handleDragOver, false);
        item.addEventListener("dragleave", handleDragLeave, false);
        item.addEventListener("drop", handleDrop, false);
        item.addEventListener("dragend", handleDragEnd, false);
    });
}

function handleDragStart(e) {
    this.classList.add("stop-item-drag-active");
    dragSrcEl = this;
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/html", this.innerHTML);
}

function handleDragOver(e) {
    if (e.preventDefault) {
        e.preventDefault();
    }
    e.dataTransfer.dropEffect = "move";
    return false;
}

function handleDragEnter(e) {
    this.classList.add("over");
}

function handleDragLeave(e) {
    this.classList.remove("over");
}

function handleDrop(e) {
    if (e.stopPropagation) {
        e.stopPropagation();
    }
    
    if (dragSrcEl !== this) {
        const srcIdx = parseInt(dragSrcEl.getAttribute("data-index"));
        const targetIdx = parseInt(this.getAttribute("data-index"));
        
        // Reorder internal stops array
        const temp = stops[srcIdx];
        stops.splice(srcIdx, 1);
        stops.splice(targetIdx, 0, temp);
        
        updateStopsUI();
        optimizeItinerary();
    }
    return false;
}

function handleDragEnd(e) {
    const items = document.querySelectorAll(".stop-item");
    items.forEach(item => {
        item.classList.remove("stop-item-drag-active");
        item.classList.remove("over");
    });
}

// Clear itinerary list
function clearItinerary() {
    stops = [];
    routeDetails = null;
    updateStopsUI();
    
    // Clear map layers
    markersGroup.clearLayers();
    if (routePolyline) {
        map.removeLayer(routePolyline);
        routePolyline = null;
    }
    
    // Reset metrics
    metricDistance.textContent = "0.00 km";
    metricDuration.textContent = "0 min";
}

// Call direct optimization endpoint (TSP solver)
async function optimizeItinerary() {
    if (stops.length < 2) {
        // Clear map line, keep markers if any
        if (routePolyline) {
            map.removeLayer(routePolyline);
            routePolyline = null;
        }
        drawMarkers();
        return;
    }
    
    const startVal = startStopSelect.value || null;
    const endVal = endStopSelect.value || null;
    
    try {
        const response = await fetch("/api/optimize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                stops: stops,
                start: startVal,
                end: endVal
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Optimization failed");
        }
        
        const data = await response.json();
        routeDetails = data;
        
        // Update metric values
        metricDistance.textContent = `${data.total_distance.toFixed(2)} km`;
        
        // Format duration into hours and minutes
        const minutes = data.total_duration;
        if (minutes < 60) {
            metricDuration.textContent = `${Math.round(minutes)} min`;
        } else {
            const hrs = Math.floor(minutes / 60);
            const mins = Math.round(minutes % 60);
            metricDuration.textContent = `${hrs}h ${mins}m`;
        }
        
        // Re-align stops sequence with the optimized order returned from the server
        stops = data.ordered_route;
        
        // Render stops list and dropdown options without triggering recursive optimizations
        renderStopsListSilently();
        
        // Draw route path on map
        drawRoute(data.geometry, data.segments);
        
    } catch (err) {
        console.error("Route Optimization Error:", err);
        alert("Could not calculate route: " + err.message);
    }
}

// Render list items silently (without triggering re-calculations)
function renderStopsListSilently() {
    stopsList.innerHTML = "";
    metricStops.textContent = `${stops.length} Stop${stops.length > 1 ? 's' : ''}`;
    
    stops.forEach((stop, index) => {
        const li = document.createElement("li");
        li.className = "stop-item";
        li.setAttribute("draggable", "true");
        li.setAttribute("data-index", index);
        
        li.innerHTML = `
            <div class="stop-info">
                <span class="stop-number">${index + 1}</span>
                <span class="stop-name" title="${stop}">${stop}</span>
            </div>
            <div class="stop-actions">
                <span class="stop-drag-handle" title="Drag to reorder"><i class="fa-solid fa-grip-vertical"></i></span>
                <button class="stop-delete-btn" data-index="${index}" title="Remove Stop"><i class="fa-solid fa-xmark"></i></button>
            </div>
        `;
        
        li.querySelector(".stop-delete-btn").addEventListener("click", (e) => {
            const idx = parseInt(e.currentTarget.getAttribute("data-index"));
            stops.splice(idx, 1);
            updateStopsUI();
            optimizeItinerary();
        });
        
        stopsList.appendChild(li);
    });
    
    updateDropdowns();
    initDragAndDrop();
}

// Draw Markers for stops on Leaflet Map
function drawMarkers() {
    markersGroup.clearLayers();
    if (stops.length === 0) return;
    
    stops.forEach(async (stop, idx) => {
        try {
            // Geocode place name (will check cache on server)
            const coords = await geocodePlace(stop);
            if (coords) {
                // Determine marker color
                let markerColor = "#4facfe"; // cyan/blue
                if (idx === 0) markerColor = "#00f2fe"; // start
                else if (idx === stops.length - 1) markerColor = "#6c5ce7"; // end
                
                // Pulse icon HTML
                const customIcon = L.divIcon({
                    html: `
                        <div style="
                            position: relative;
                            width: 14px;
                            height: 14px;
                            background-color: ${markerColor};
                            border: 2px solid #ffffff;
                            border-radius: 50%;
                            box-shadow: 0 0 10px ${markerColor};
                        ">
                            <span style="
                                position: absolute;
                                top: -5px;
                                left: -5px;
                                width: 20px;
                                height: 20px;
                                border-radius: 50%;
                                background-color: ${markerColor};
                                opacity: 0.3;
                                animation: markerRipple 1.5s infinite ease-out;
                                pointer-events: none;
                            "></span>
                        </div>
                    `,
                    className: 'custom-map-marker',
                    iconSize: [14, 14],
                    iconAnchor: [7, 7]
                });
                
                const marker = L.marker(coords, { icon: customIcon })
                    .bindPopup(`<strong>Stop ${idx + 1}:</strong> ${stop}`)
                    .addTo(markersGroup);
            }
        } catch (err) {
            console.error("Geocoding marker plotting failed for stop:", stop, err);
        }
    });
}

// Fetch coordinates for marker plotting
async function geocodePlace(placeName) {
    try {
        // Query server to geocode
        // We'll call get_route_details to mock search or fetch via optimize.
        // Actually, let's fetch coordinates from nominatim or an optimize segment
        if (routeDetails && routeDetails.segments) {
            // Try fetching from segments coordinates
            for (let seg of routeDetails.segments) {
                if (seg.from.toLowerCase() === placeName.toLowerCase()) {
                    return seg.geometry[0];
                }
                if (seg.to.toLowerCase() === placeName.toLowerCase()) {
                    return seg.geometry[seg.geometry.length - 1];
                }
            }
        }
        
        // If not found in segments, do a quick optimization run to find it
        // Or call nominatim directly. Let's make a request to server for coordinate.
        // In route_tools we have get_coordinates, we can call a small route test segment
        const response = await fetch("/api/optimize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ stops: [placeName, placeName] })
        });
        if (response.ok) {
            const data = await response.json();
            return data.geometry[0];
        }
    } catch (err) {
        console.warn("Geocoding place failed:", placeName);
    }
    return null;
}

// Draw polyline routes and fit bounds
function drawRoute(geometry, segments) {
    if (routePolyline) {
        map.removeLayer(routePolyline);
    }
    
    // Draw markers
    drawMarkers();
    
    if (!geometry || geometry.length === 0) return;
    
    // Create polyline path with neon color and shadow
    routePolyline = L.polyline(geometry, {
        color: "#00f2fe",
        weight: 4,
        opacity: 0.8,
        lineJoin: 'round',
        shadowColor: '#4facfe',
        shadowBlur: 10
    }).addTo(map);
    
    // Zoom/pan map to fit the full route
    map.fitBounds(routePolyline.getBounds(), { padding: [50, 50] });
}

// Handle Chat Message submission
async function handleChatSubmit(e) {
    e.preventDefault();
    const query = chatInput.value.trim();
    if (!query) return;
    
    // Add user bubble
    appendMessage("user", query);
    chatInput.value = "";
    
    // Show thinking logs
    thinkingBox.classList.remove("hidden");
    thinkingLogs.textContent = "Agent initializing...\n";
    
    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: query })
        });
        
        if (!response.ok) {
            throw new Error("Server error handling request");
        }
        
        const data = await response.json();
        
        // Update thinking logs
        if (data.logs) {
            thinkingLogs.textContent = data.logs;
            thinkingLogs.scrollTop = thinkingLogs.scrollHeight;
        } else {
            thinkingLogs.textContent += "Agent finished reasoning successfully.\n";
        }
        
        // Add assistant bubble
        appendMessage("assistant", formatMarkdown(data.response));
        
        // Sync stops with the agent's new memory route
        loadSessionMemory();
        
    } catch (err) {
        console.error(err);
        appendMessage("system", "Error: RoutePilot could not compute your request. Make sure your API keys are valid.");
        thinkingLogs.textContent += `Error: ${err.message}\n`;
    }
}

// Append Chat Bubble to window
function appendMessage(sender, text) {
    const msg = document.createElement("div");
    msg.className = `chat-message ${sender}`;
    
    const avatar = sender === "user" ? "ME" : sender === "system" ? "SYS" : "RP";
    
    msg.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <p>${text}</p>
        </div>
    `;
    
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Primitive markdown formatter to display rich itineraries in chat bubble
function formatMarkdown(text) {
    if (!text) return "";
    
    let formatted = text
        // Bold tags
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // Newlines
        .replace(/\n/g, '<br>')
        // Bullets
        .replace(/^\s*[-*]\s*(.*?)$/gm, '<li>$1</li>');
        
    // Group bullets under lists
    if (formatted.includes("<li>")) {
        // Simple list tagging
        formatted = formatted.replace(/(<li>.*?<\/li>)+/g, '<ul>$&</ul>');
    }
    
    return formatted;
}

// Database Operations: Save Route submit
async function handleSaveRouteSubmit(e) {
    e.preventDefault();
    const name = routeNameInput.value.trim();
    if (!name || !routeDetails) return;
    
    try {
        const response = await fetch("/api/routes", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name: name,
                stops: stops,
                ordered_route: routeDetails.ordered_route,
                total_distance: routeDetails.total_distance,
                total_duration: routeDetails.total_duration,
                geometry: routeDetails.geometry
            })
        });
        
        if (!response.ok) {
            throw new Error("Could not save route to SQLite database");
        }
        
        saveModal.classList.add("hidden");
        alert("Itinerary plan saved successfully!");
        
        // Refresh saved drawer if open
        if (!savedDrawer.classList.contains("hidden")) {
            openSavedDrawer();
        }
        
    } catch (err) {
        alert("Error saving itinerary: " + err.message);
    }
}

// Database Operations: Open Saved Routes panel
async function openSavedDrawer() {
    savedDrawer.classList.remove("hidden");
    savedRoutesList.innerHTML = `<li class="empty-list-placeholder"><i class="fa-solid fa-spinner fa-spin"></i> Loading saved itineraries...</li>`;
    
    try {
        const response = await fetch("/api/routes");
        if (!response.ok) throw new Error("Failed to load saved routes");
        
        const routes = await response.json();
        
        savedRoutesList.innerHTML = "";
        
        if (routes.length === 0) {
            savedRoutesList.innerHTML = `<li class="empty-list-placeholder">No saved itineraries found. Build and save one from the stops manager!</li>`;
            return;
        }
        
        routes.forEach(route => {
            const card = document.createElement("li");
            card.className = "saved-route-card";
            
            // Format stop names
            const stopsSummary = route.ordered_route.join(" → ");
            
            // Format duration
            const hoursText = route.total_duration >= 60 
                ? `${Math.floor(route.total_duration / 60)}h ${Math.round(route.total_duration % 60)}m`
                : `${Math.round(route.total_duration)} min`;
                
            card.innerHTML = `
                <div class="saved-route-info">
                    <div class="saved-route-title">${route.name}</div>
                    <div class="saved-route-date">${route.created_at}</div>
                </div>
                <div class="saved-route-metrics">
                    <span><i class="fa-solid fa-road"></i> ${route.total_distance.toFixed(2)} km</span>
                    <span><i class="fa-solid fa-clock"></i> ${hoursText}</span>
                </div>
                <div class="saved-route-stops" title="${stopsSummary}">${stopsSummary}</div>
                <div class="saved-route-actions">
                    <button class="saved-route-btn delete-route-btn" data-id="${route.id}" title="Delete"><i class="fa-solid fa-trash-can"></i> Delete</button>
                    <button class="saved-route-btn load-route-btn" data-id="${route.id}" title="Load Itinerary"><i class="fa-solid fa-folder-open"></i> Load</button>
                </div>
            `;
            
            // Load button click
            card.querySelector(".load-route-btn").addEventListener("click", () => {
                stops = route.ordered_route;
                routeDetails = {
                    ordered_route: route.ordered_route,
                    total_distance: route.total_distance,
                    total_duration: route.total_duration,
                    geometry: route.geometry,
                    segments: [] // segments will reload on next drag/optimize if needed
                };
                
                // Update metrics
                metricDistance.textContent = `${route.total_distance.toFixed(2)} km`;
                metricDuration.textContent = hoursText;
                
                updateStopsUI();
                drawRoute(route.geometry, []);
                savedDrawer.classList.add("hidden");
            });
            
            // Delete button click
            card.querySelector(".delete-route-btn").addEventListener("click", async (e) => {
                const id = e.currentTarget.getAttribute("data-id");
                if (confirm("Are you sure you want to delete this itinerary?")) {
                    try {
                        const delResponse = await fetch(`/api/routes/${id}`, { method: "DELETE" });
                        if (delResponse.ok) {
                            openSavedDrawer();
                        } else {
                            alert("Failed to delete route.");
                        }
                    } catch (err) {
                        alert("Delete error: " + err.message);
                    }
                }
            });
            
            savedRoutesList.appendChild(card);
        });
        
    } catch (err) {
        savedRoutesList.innerHTML = `<li class="empty-list-placeholder" style="color: var(--color-danger)">Could not load routes: ${err.message}</li>`;
    }
}
