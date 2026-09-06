import { useEffect, useMemo, useState } from "react"

function MilanMap({
    hotspots = [],
    alerts = [],
    selectedGrid,
    onSelectGrid
}) {

    const [geoJson, setGeoJson] = useState(null)
    const [geoJsonError, setGeoJsonError] = useState(null)

    useEffect(() => {
        let mounted = true

        async function loadGeoJson() {
            try {
                const response = await fetch("/reference/milano-grid.geojson")

                if (!response.ok) {
                    throw new Error(
                        `GeoJSON request failed with status ${response.status}`
                    )
                }

                const data = await response.json()

                if (mounted) {
                    setGeoJson(data)
                }
            } catch (error) {
                if (mounted) {
                    setGeoJsonError(error.message)
                }
            }
        }

        loadGeoJson()

        return () => {
            mounted = false
        }
    }, [])

    const statusByGrid = useMemo(() => {
        const map = new Map()

        alerts.forEach((alert) => {
            const gridId = Number(alert.grid_id)

            if (!map.has(gridId)) {
                map.set(gridId, {
                    status: alert.severity === "HIGH"
                        ? "HIGH"
                        : alert.severity === "MEDIUM"
                            ? "ATTENTION"
                            : "NORMAL",
                    alert
                })
            }
        })

        hotspots.forEach((hotspot) => {
            const gridId = Number(hotspot.grid_id)

            if (!map.has(gridId)) {
                map.set(gridId, {
                    status: hotspot.status || "NORMAL",
                    hotspot
                })
            } else {
                const existing = map.get(gridId)

                map.set(gridId, {
                    ...existing,
                    hotspot
                })
            }
        })

        return map
    }, [hotspots, alerts])

    const visibleFeatures = useMemo(() => {
        if (!geoJson?.features) {
            return []
        }

        const relevantGridIds = new Set(
            hotspots.map((item) => Number(item.grid_id))
        )

        alerts.forEach((item) => {
            relevantGridIds.add(Number(item.grid_id))
        })

        return geoJson.features.filter((feature) => {
            const cellId = Number(feature.properties?.cellId)
            return relevantGridIds.has(cellId)
        })
    }, [geoJson, hotspots, alerts])

    const bounds = useMemo(() => {
        if (!visibleFeatures.length) {
            return {
                minLon: 9,
                maxLon: 9.35,
                minLat: 45.35,
                maxLat: 45.55
            }
        }

        let minLon = Infinity
        let maxLon = -Infinity
        let minLat = Infinity
        let maxLat = -Infinity

        visibleFeatures.forEach((feature) => {
            const coordinates = feature.geometry?.coordinates?.[0] || []

            coordinates.forEach(([lon, lat]) => {
                minLon = Math.min(minLon, lon)
                maxLon = Math.max(maxLon, lon)
                minLat = Math.min(minLat, lat)
                maxLat = Math.max(maxLat, lat)
            })
        })

        return {
            minLon,
            maxLon,
            minLat,
            maxLat
        }
    }, [visibleFeatures])

    function projectPoint(lon, lat) {
        const width = 900
        const height = 560
        const padding = 30

        const lonRange = bounds.maxLon - bounds.minLon || 1
        const latRange = bounds.maxLat - bounds.minLat || 1

        const x =
            padding +
            ((lon - bounds.minLon) / lonRange) *
                (width - padding * 2)

        const y =
            height -
            padding -
            ((lat - bounds.minLat) / latRange) *
                (height - padding * 2)

        return [x, y]
    }

    function polygonPath(feature) {
        const rings = feature.geometry?.coordinates || []

        return rings
            .map((ring) => {
                return ring
                    .map(([lon, lat], index) => {
                        const [x, y] = projectPoint(lon, lat)

                        return `${index === 0 ? "M" : "L"} ${x} ${y}`
                    })
                    .join(" ") + " Z"
            })
            .join(" ")
    }

    function getFeatureStatus(cellId) {
        return statusByGrid.get(cellId)?.status || "NORMAL"
    }

    function handlePolygonClick(cellId) {
        onSelectGrid(cellId)
    }

    if (geoJsonError) {
        return (
            <div className="map-panel">
                <div className="page-state">
                    <strong>Unable to load Milan grid map</strong>
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

    return (
        <div className="map-panel">
            <div className="map-header">
                <div>
                    <div className="eyebrow">
                        GEOGRAPHIC OPERATIONS
                    </div>

                    <h2>Milan Grid Map</h2>

                    <p>
                        Showing operational grids returned by the current
                        hotspot and alert selection.
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
                <svg
                    viewBox="0 0 900 560"
                    role="img"
                    aria-label="Milan network grid operational map"
                >
                    {visibleFeatures.map((feature) => {
                        const cellId = Number(
                            feature.properties?.cellId
                        )

                        const status = getFeatureStatus(cellId)

                        const isSelected =
                            selectedGrid === cellId

                        return (
                            <path
                                key={cellId}
                                d={polygonPath(feature)}
                                className={`grid-polygon grid-${status.toLowerCase()} ${
                                    isSelected
                                        ? "grid-selected"
                                        : ""
                                }`}
                                tabIndex="0"
                                role="button"
                                aria-label={`Grid ${cellId}, status ${status}`}
                                onClick={() =>
                                    handlePolygonClick(cellId)
                                }
                                onKeyDown={(event) => {
                                    if (
                                        event.key === "Enter" ||
                                        event.key === " "
                                    ) {
                                        handlePolygonClick(cellId)
                                    }
                                }}
                            />
                        )
                    })}
                </svg>

                {!visibleFeatures.length && (
                    <div className="map-empty">
                        No grid polygons match the current selection.
                    </div>
                )}
            </div>

            <div className="map-footer">
                <span>
                    Displayed grids: {visibleFeatures.length}
                </span>

                <span>
                    Click a grid to open Grid Explorer.
                </span>
            </div>
        </div>
    )
}

export default MilanMap