import { useEffect, useMemo, useState } from "react"
import { getAlerts, getHotspots } from "../api"
import MilanMap from "../components/MilanMap"

function Hotspots({ onOpenGrid }) {
    const [hotspots, setHotspots] = useState([])
    const [alerts, setAlerts] = useState([])
    const [limit, setLimit] = useState(10)
    const [severity, setSeverity] = useState("")
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState("")
    const [selectedGrid, setSelectedGrid] = useState(null)

    useEffect(() => {
        let active = true

        async function loadData() {
            setLoading(true)
            setError("")

            try {
                const [hotspotResponse, alertResponse] =
                    await Promise.all([
                        getHotspots(limit),
                        getAlerts(severity)
                    ])

                if (!active) {
                    return
                }

                setHotspots(hotspotResponse.data || [])
                setAlerts(alertResponse.data || [])
            } catch (err) {
                if (active) {
                    setError(err.message)
                    setHotspots([])
                    setAlerts([])
                }
            } finally {
                if (active) {
                    setLoading(false)
                }
            }
        }

        loadData()

        return () => {
            active = false
        }
    }, [limit, severity])

    const alertByGrid = useMemo(() => {
        const map = new Map()

        alerts.forEach((alert) => {
            const gridId = Number(alert.grid_id)

            if (!map.has(gridId)) {
                map.set(gridId, alert)
            }
        })

        return map
    }, [alerts])

    const rows = useMemo(() => {
        return hotspots.map((hotspot, index) => {
            const gridId = Number(hotspot.grid_id)
            const alert = alertByGrid.get(gridId)

            let status = hotspot.status || "NORMAL"

            if (alert?.severity === "HIGH") {
                status = "HIGH"
            } else if (alert?.severity === "MEDIUM") {
                status = "ATTENTION"
            } else if (alert?.severity === "LOW") {
                status = "NORMAL"
            }

            return {
                ...hotspot,
                gridId,
                rank: index + 1,
                alert,
                status
            }
        })
    }, [hotspots, alertByGrid])

    function handleGridSelect(gridId) {
        setSelectedGrid(gridId)

        if (onOpenGrid) {
            onOpenGrid(gridId)
        }
    }

    return (
        <div className="page-container">
            <div className="page-heading">
                <div>
                    <div className="eyebrow">
                        NETWORK OPERATIONS
                    </div>

                    <h1>Hotspots & Alerts</h1>

                    <p>
                        Ranked operational attention areas from the
                        network intelligence APIs.
                    </p>
                </div>

                <div className="hotspot-controls">
                    <label>
                        <span>Limit</span>

                        <select
                            value={limit}
                            onChange={(event) =>
                                setLimit(Number(event.target.value))
                            }
                        >
                            <option value={5}>5</option>
                            <option value={10}>10</option>
                            <option value={20}>20</option>
                            <option value={50}>50</option>
                        </select>
                    </label>

                    <label>
                        <span>Severity</span>

                        <select
                            value={severity}
                            onChange={(event) =>
                                setSeverity(event.target.value)
                            }
                        >
                            <option value="">All</option>
                            <option value="HIGH">HIGH</option>
                            <option value="MEDIUM">ATTENTION</option>
                            <option value="LOW">NORMAL</option>
                        </select>
                    </label>
                </div>
            </div>

            {error && (
                <div className="status-banner error">
                    <strong>API unavailable</strong>
                    <span>{error}</span>
                </div>
            )}

            {loading ? (
                <div className="page-state">
                    Loading hotspots and alerts...
                </div>
            ) : (
                <>
                    <div className="hotspot-summary">
                        <div className="summary-item">
                            <span>Hotspots</span>
                            <strong>{rows.length}</strong>
                        </div>

                        <div className="summary-item">
                            <span>High</span>
                            <strong>
                                {
                                    rows.filter(
                                        (row) =>
                                            row.status === "HIGH"
                                    ).length
                                }
                            </strong>
                        </div>

                        <div className="summary-item">
                            <span>Attention</span>
                            <strong>
                                {
                                    rows.filter(
                                        (row) =>
                                            row.status ===
                                            "ATTENTION"
                                    ).length
                                }
                            </strong>
                        </div>

                        <div className="summary-item">
                            <span>Normal</span>
                            <strong>
                                {
                                    rows.filter(
                                        (row) =>
                                            row.status === "NORMAL"
                                    ).length
                                }
                            </strong>
                        </div>
                    </div>

                    <div className="hotspot-layout">
                        <div className="hotspot-table-panel">
                            <div className="panel-header">
                                <div>
                                    <div className="eyebrow">
                                        RANKED VIEW
                                    </div>

                                    <h2>Operational Attention</h2>
                                </div>

                                <span className="panel-count">
                                    {rows.length} grids
                                </span>
                            </div>

                            {rows.length === 0 ? (
                                <div className="page-state compact">
                                    No hotspot records match the
                                    selected filter.
                                </div>
                            ) : (
                                <div className="table-wrapper">
                                    <table className="hotspot-table">
                                        <thead>
                                            <tr>
                                                <th>Rank</th>
                                                <th>Grid</th>
                                                <th>Activity</th>
                                                <th>Status</th>
                                                <th>Alert</th>
                                                <th>Timestamp</th>
                                            </tr>
                                        </thead>

                                        <tbody>
                                            {rows.map((row) => (
                                                <tr
                                                    key={`${row.gridId}-${row.timestamp}`}
                                                    className={
                                                        selectedGrid ===
                                                        row.gridId
                                                            ? "row-selected"
                                                            : ""
                                                    }
                                                    onClick={() =>
                                                        handleGridSelect(
                                                            row.gridId
                                                        )
                                                    }
                                                >
                                                    <td>
                                                        <span className="rank-number">
                                                            {row.rank}
                                                        </span>
                                                    </td>

                                                    <td>
                                                        <button
                                                            className="grid-link"
                                                            onClick={(
                                                                event
                                                            ) => {
                                                                event.stopPropagation()
                                                                handleGridSelect(
                                                                    row.gridId
                                                                )
                                                            }}
                                                        >
                                                            {row.gridId}
                                                        </button>
                                                    </td>

                                                    <td>
                                                        {Number(
                                                            row.total_activity
                                                        ).toFixed(2)}
                                                    </td>

                                                    <td>
                                                        <span
                                                            className={`status-badge status-${row.status.toLowerCase()}`}
                                                        >
                                                            {row.status}
                                                        </span>
                                                    </td>

                                                    <td>
                                                        {row.alert
                                                            ?.alert_type ||
                                                            "—"}
                                                    </td>

                                                    <td>
                                                        {row.timestamp}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>

                        <MilanMap
                            hotspots={rows}
                            alerts={alerts}
                            selectedGrid={selectedGrid}
                            onSelectGrid={setSelectedGrid}
                        />
                    </div>
                </>
            )}
        </div>
    )
}

export default Hotspots