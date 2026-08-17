// Copyright (c) 2026, edwin@upande.com and contributors
// For license information, please see license.txt

// frappe.ui.form.on("DCU", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on('DCU', {
    refresh(frm) {
        setTimeout(() => {
            const field = frm.fields_dict['geolocation_sxfh'];
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

            if (frm.doc.latitude && frm.doc.longitude) {
                if (window.dcuMarker) {
                    map.removeLayer(window.dcuMarker);
                }

                window.dcuMarker = L.marker(
                    [frm.doc.latitude, frm.doc.longitude],
                    { draggable: true }
                ).addTo(map);

                window.dcuMarker.bindPopup(`DCU: ${frm.doc.dcu_id || ''}`);

                window.dcuMarker.on('dragend', function(e) {
                    const newPos = e.target.getLatLng();
                    frm.set_value('latitude', newPos.lat);
                    frm.set_value('longitude', newPos.lng);
                });

                map.setView([frm.doc.latitude, frm.doc.longitude], 13);
            }
        }, 300);
    },

    latitude(frm) {
        update_geojson(frm);
    },

    longitude(frm) {
        update_geojson(frm);
    }
});

function update_geojson(frm) {
    if (frm.doc.latitude && frm.doc.longitude) {
        const geojson = {
            type: "FeatureCollection",
            features: [{
                type: "Feature",
                properties: {},
                geometry: {
                    type: "Point",
                    coordinates: [parseFloat(frm.doc.longitude), parseFloat(frm.doc.latitude)]
                }
            }]
        };
        frm.set_value('geolocation_sxfh', JSON.stringify(geojson));
        frm.refresh_field('geolocation_sxfh');
    }
}