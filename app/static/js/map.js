// Leaflet.js campus map integration (Amrita Vishwa Vidyapeetham, Nagercoil Campus)

function initCampusMap(elementId, centerLat = 8.22901, centerLng = 77.41539, zoom = 17) {
    const mapEl = document.getElementById(elementId);
    if (!mapEl || typeof L === 'undefined') return null;

    const map = L.map(elementId).setView([centerLat, centerLng], zoom);

    // OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | Amrita Vishwa Vidyapeetham, Nagercoil',
        maxZoom: 19
    }).addTo(map);

    // Custom map pin icon with Sage Green & Slate Blue accents
    const campusPinIcon = L.divIcon({
        className: 'custom-campus-pin',
        html: `
            <div style="
                width: 28px;
                height: 28px;
                background-color: #4F7C72;
                border: 2px solid #FFFFFF;
                border-radius: 50%;
                box-shadow: 0 2px 6px rgba(36,59,83,0.35);
                display: flex;
                align-items: center;
                justify-content: center;
                color: #FFFFFF;
                font-size: 13px;
            ">
                <i class="bi bi-geo-alt-fill"></i>
            </div>
        `,
        iconSize: [28, 28],
        iconAnchor: [14, 28],
        popupAnchor: [0, -28]
    });

    // Fetch campus locations and plot pins
    fetch('/api/locations')
        .then(res => res.json())
        .then(data => {
            if (data.locations && data.locations.length > 0) {
                const markers = [];
                data.locations.forEach(loc => {
                    const marker = L.marker([loc.lat, loc.lng], { icon: campusPinIcon }).addTo(map);
                    markers.push(marker);
                    const popupContent = `
                        <div style="min-width: 190px; font-family: 'Lucida Bright', Georgia, serif; padding: 4px 2px;">
                            <div class="d-flex align-items-center gap-1 mb-1">
                                <span class="badge" style="background-color: #4F7C72; color: #FFFFFF; font-size: 0.68rem; font-family: sans-serif;">Amrita Campus</span>
                                <span class="badge" style="background-color: #E8DDD1; color: #39434D; font-size: 0.68rem; font-family: sans-serif;">${loc.category}</span>
                            </div>
                            <h6 class="fw-bold mb-1" style="color: #243B53; font-size: 0.95rem;">${loc.name}</h6>
                            <p class="small text-muted mb-2" style="font-size: 0.82rem; line-height: 1.4;">${loc.description || ''}</p>
                            <div class="d-flex justify-content-between small pt-1 border-top" style="border-color: #E5E0D8 !important; font-size: 0.8rem;">
                                <span style="color: #D98C68;"><i class="bi bi-search me-1"></i>Lost: <strong>${loc.lost_count}</strong></span>
                                <span style="color: #4F7C72;"><i class="bi bi-box-seam me-1"></i>Found: <strong>${loc.found_count}</strong></span>
                            </div>
                        </div>
                    `;
                    marker.bindPopup(popupContent);
                });

                // Auto-center on Amrita Vishwa Vidyapeetham Campus
                map.setView([centerLat, centerLng], zoom);
            }
        })
        .catch(err => console.error('Error loading locations map:', err));

    return map;
}

function initLocationPickerMap(elementId, latInputId, lngInputId, selectDropdownId) {
    const mapEl = document.getElementById(elementId);
    if (!mapEl || typeof L === 'undefined') return null;

    const defaultLat = 8.22901;
    const defaultLng = 77.41539;
    const map = L.map(elementId).setView([defaultLat, defaultLng], 17);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap | Amrita Vishwa Vidyapeetham',
        maxZoom: 19
    }).addTo(map);

    let currentMarker = null;

    map.on('click', (e) => {
        const { lat, lng } = e.latlng;
        if (currentMarker) {
            currentMarker.setLatLng([lat, lng]);
        } else {
            currentMarker = L.marker([lat, lng]).addTo(map);
        }

        const latInput = document.getElementById(latInputId);
        const lngInput = document.getElementById(lngInputId);
        if (latInput) latInput.value = lat.toFixed(6);
        if (lngInput) lngInput.value = lng.toFixed(6);
    });

    return map;
}
