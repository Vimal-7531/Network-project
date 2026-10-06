import { useEffect, useMemo, useState } from "react"
import {
    MapContainer,
    TileLayer,
    GeoJSON,
    useMap
} from "react-leaflet"
import L from "leaflet"
import "leaflet/dist/leaflet.css"

function MapController({ bounds }) {
    const map = useMap()

    useEffect(() => {
        if (bounds && bounds.isValid()) {
            map.fitBounds(bounds, {
                padding: [20, 20]
            })
        }
    }, [map, bounds])

    return null
}

function MilanMap({
    hotspots = [],
    alerts = [],
    selectedGrid,
    onSelectGrid
}) {
    const [geoJson, setGeoJson] = useState(null)
    const [geoJsonError, setGeoJsonError] = useState(null)

    useEffect(() => {
        async function loadGeoJson() {
            try {
                const response = await fetch(
                    "/reference/milano-grid.geojson"
                )

                if (!response.ok) {
                    throw new Error(
                        `GeoJSON request failed with status ${response.status}`
                    )
                }

                const data = await response.json()
                setGeoJson(data)
            } catch (error) {
                setGeoJsonError(error.message)
            }
        }

        loadGeoJson()
    }, [])

    const statusByGrid = useMemo(() => {
        const map = new Map()

        alerts.forEach((alert) => {
            const gridId = Number(alert.grid_id)

            if (!Number.isFinite(gridId)) {
                return
            }

            const severity =
                String(alert.severity || "LOW").toUpperCase()

            const status =
                severity === "HIGH"
                    ? "HIGH"
                    : severity === "MEDIUM"
                        ? "ATTENTION"
                        : "NORMAL"

            map.set(gridId, status)
        })

        hotspots.forEach((hotspot) => {
            const gridId = Number(hotspot.grid_id)

            if (!Number.isFinite(gridId)) {
                return
            }

            if (!map.has(gridId)) {
                map.set(
                    gridId,
                    String(hotspot.status || "NORMAL").toUpperCase()
                )
            }
        })

        return map
    }, [hotspots, alerts])

    const visibleGeoJson = useMemo(() => {
        if (!geoJson?.features?.length) {
            return null
        }

        const visibleGridIds = new Set()

        hotspots.forEach((hotspot) => {
            const gridId = Number(hotspot.grid_id)

            if (Number.isFinite(gridId)) {
                visibleGridIds.add(gridId)
            }
        })

        alerts.forEach((alert) => {
            const gridId = Number(alert.grid_id)

            if (Number.isFinite(gridId)) {
                visibleGridIds.add(gridId)
            }
        })

        return {
            ...geoJson,
            features: geoJson.features.filter((feature) => {
                const cellId = Number(feature.properties?.cellId)

                return visibleGridIds.has(cellId)
            })
        }
    }, [geoJson, hotspots, alerts])

    const mapBounds = useMemo(() => {
        if (!visibleGeoJson?.features?.length) {
            return L.latLngBounds(
                [45.35, 9.00],
                [45.55, 9.35]
            )
        }

        const bounds = L.latLngBounds([])

        visibleGeoJson.features.forEach((feature) => {
            const layer = L.geoJSON(feature)
            const featureBounds = layer.getBounds()

            if (featureBounds.isValid()) {
                bounds.extend(featureBounds)
            }
        })

        return bounds
    }, [visibleGeoJson])

    function getStatus(cellId) {
        return statusByGrid.get(cellId) || "NORMAL"
    }

    function getStyle(feature) {
        const cellId = Number(feature.properties?.cellId)
        const status = getStatus(cellId)

        if (selectedGrid === cellId) {
            return {
                color: "#111827",
                weight: 3,
                opacity: 1,
                fillColor: "#2563eb",
                fillOpacity: 0.65
            }
        }

        if (status === "HIGH") {
            return {
                color: "#dc2626",
                weight: 1.5,
                opacity: 1,
                fillColor: "#ef4444",
                fillOpacity: 0.55
            }
        }

        if (status === "ATTENTION") {
            return {
                color: "#d97706",
                weight: 1.5,
                opacity: 1,
                fillColor: "#facc15",
                fillOpacity: 0.55
            }
        }

        return {
            color: "#000000",
            weight: 2,
            opacity: 1,
            fillColor: "#ffffff",
            fillOpacity: 0.35
        }
    }

    function handleEachFeature(feature, layer) {
        const cellId = Number(feature.properties?.cellId)
        const status = getStatus(cellId)

        layer.bindTooltip(
            `Grid ${cellId}<br>Status: ${status}`,
            {
                sticky: true
            }
        )

        layer.on({
            click: () => {
                if (onSelectGrid) {
                    onSelectGrid(cellId)
                }
            },

            mouseover: () => {
                layer.setStyle({
                    weight: 3,
                    opacity: 1,
                    fillOpacity: 0.5
                })

                layer.bringToFront()
            },

            mouseout: () => {
                layer.setStyle(getStyle(feature))
            }
        })
    }

    if (geoJsonError) {
        return (
            <div className="map-panel">
                <div className="page-state">
                    <strong>
                        Unable to load Milan grid map
                    </strong>
                    <span>{geoJsonError}</span>
                </div>
            </div>
        )
    }

    if (!geoJson) {
        return (
            <div className="map-panel">
                <div className="page-state">
                    Loading Milan grid map...
                </div>
            </div>
        )
    }
    console.log("GeoJSON features:", geoJson.features.length)
    console.log("First grid:", geoJson.features[0])

    return (
        <div className="map-panel">
            <div className="map-header">
                <div>
                    <div className="eyebrow">
                        GEOGRAPHIC OPERATIONS
                    </div>

                    <h2>Milan Grid Map</h2>

                    <p>
                        Interactive network grid map with operational
                        hotspot and alert status.
                    </p>
                </div>

                <div className="map-legend">
                    <span>
                        <i className="legend-marker normal"></i>
                        NORMAL
                    </span>

                    <span>
                        <i className="legend-marker attention"></i>
                        ATTENTION
                    </span>

                    <span>
                        <i className="legend-marker high"></i>
                        HIGH
                    </span>
                </div>
            </div>

            <div className="map-canvas">
                <MapContainer
                    center={[45.4642, 9.1900]}
                    zoom={11}
                    scrollWheelZoom={true}
                    preferCanvas={true}
                    style={{
                        width: "100%",
                        height: "650px"
                    }}
                >
                    <TileLayer
                        attribution="&copy; OpenStreetMap contributors"
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />

                    <MapController
                        bounds={mapBounds}
                    />

                    <GeoJSON
                        key={visibleGeoJson?.features.length || 0}
                        data={visibleGeoJson}
                        style={getStyle}
                        onEachFeature={handleEachFeature}
                    />
                </MapContainer>
            </div>

            <div className="map-footer">
                <span>
                    Displayed operational grids: {visibleGeoJson?.features.length || 0}
                </span>

                <span>
                    Click a hotspot or alert grid to open Grid Explorer.
                </span>
            </div>
        </div>
    )
}

export default MilanMap