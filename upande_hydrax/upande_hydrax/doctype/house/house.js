frappe.ui.form.on('House', {
    refresh(frm) {
        setTimeout(() => {
            const field = frm.fields_dict['geolocation_dvks'];
            if (!field || !field.map) return;
            const map = field.map;

            map.eachLayer(layer => {
                if (layer instanceof L.TileLayer) {
                    map.removeLayer(layer);
                }
            });

            const osm = L.tileLayer(
                'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '&copy; OpenStreetMap contributors',
                    maxZoom: 19
                }
            ).addTo(map);

            const satellite = L.tileLayer(
                'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
                    attribution: '© Esri',
                    maxZoom: 19
                }
            );

            L.control.layers(
                { "OpenStreetMap": osm, "Satellite": satellite },
                null,
                { position: 'topright' }
            ).addTo(map);

            const lat = parseFloat(String(frm.doc.latitude || '').replace('°', ''));
            const lng = parseFloat(String(frm.doc.longitude || '').replace('°', ''));

            if (!isNaN(lat) && !isNaN(lng)) {
                if (window.houseMarker) {
                    map.removeLayer(window.houseMarker);
                }

                window.houseMarker = L.marker([lat, lng], { draggable: true }).addTo(map);
                window.houseMarker.bindPopup(`House: ${frm.doc.house_number || ''}`);

                window.houseMarker.on('dragend', function(e) {
                    const newPos = e.target.getLatLng();
                    frm.set_value('latitude', newPos.lat);
                    frm.set_value('longitude', newPos.lng);
                });

                map.setView([lat, lng], 13);
            }
        }, 300);
    },

    latitude(frm) { update_geojson(frm); },
    longitude(frm) { update_geojson(frm); }
});

function update_geojson(frm) {
    const lat = parseFloat(String(frm.doc.latitude || '').replace('°', ''));
    const lng = parseFloat(String(frm.doc.longitude || '').replace('°', ''));

    if (!isNaN(lat) && !isNaN(lng)) {
        const geojson = {
            type: "FeatureCollection",
            features: [{
                type: "Feature",
                properties: {},
                geometry: {
                    type: "Point",
                    coordinates: [lng, lat]
                }
            }]
        };
        frm.set_value('geolocation_dvks', JSON.stringify(geojson));
        frm.refresh_field('geolocation_dvks');
    }
}