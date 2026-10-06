import { useEffect, useState } from "react"
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
                        getAlerts(limit,severity)
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

    function handleGridSelect(gridId) {
        setSelectedGrid(gridId)

        if (onOpenGrid) {
            onOpenGrid(gridId)
        }
    }

    function getSeverityClass(value) {
        if (!value) {
            return "status-normal"
        }

        return `status-${String(value).toLowerCase()}`
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
                        Ranked high-activity areas and current
                        operational alerts from the network intelligence APIs.
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
                            <strong>{hotspots.length}</strong>
                        </div>

                        <div className="summary-item">
                            <span>Alerts</span>
                            <strong>{alerts.length}</strong>
                        </div>

                        <div className="summary-item">
                            <span>High</span>
                            <strong>
                                {
                                    alerts.filter(
                                        (alert) =>
                                            String(alert.severity).toUpperCase() ===
                                            "HIGH"
                                    ).length
                                }
                            </strong>
                        </div>

                        <div className="summary-item">
                            <span>Attention</span>
                            <strong>
                                {
                                    alerts.filter(
                                        (alert) =>
                                            String(alert.severity).toUpperCase() ===
                                            "MEDIUM"
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
                                        HOTSPOTS
                                    </div>

                                    <h2>Ranked High-Activity Grids</h2>
                                </div>

                                <span className="panel-count">
                                    {hotspots.length} grids
                                </span>
                            </div>

                            {hotspots.length === 0 ? (
                                <div className="page-state compact">
                                    No hotspot records match the selected
                                    filter.
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
                                                <th>Timestamp</th>
                                            </tr>
                                        </thead>

                                        <tbody>
                                            {hotspots.map((hotspot, index) => {
                                                const gridId = Number(
                                                    hotspot.grid_id
                                                )

                                                const status =
                                                    hotspot.status || "NORMAL"

                                                return (
                                                    <tr
                                                        key={`${gridId}-${hotspot.timestamp}`}
                                                        className={
                                                            selectedGrid ===
                                                            gridId
                                                                ? "row-selected"
                                                                : ""
                                                        }
                                                        onClick={() =>
                                                            handleGridSelect(
                                                                gridId
                                                            )
                                                        }
                                                    >
                                                        <td>
                                                            <span className="rank-number">
                                                                {index + 1}
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
                                                                        gridId
                                                                    )
                                                                }}
                                                            >
                                                                {gridId}
                                                            </button>
                                                        </td>

                                                        <td>
                                                            {Number(
                                                                hotspot.total_activity
                                                            ).toFixed(2)}
                                                        </td>

                                                        <td>
                                                            <span
                                                                className={`status-badge ${getSeverityClass(
                                                                    status
                                                                )}`}
                                                            >
                                                                {status}
                                                            </span>
                                                        </td>

                                                        <td>
                                                            {hotspot.timestamp}
                                                        </td>
                                                    </tr>
                                                )
                                            })}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="hotspot-layout">
                        <div className="hotspot-table-panel">
                            <div className="panel-header">
                                <div>
                                    <div className="eyebrow">
                                        ALERTS
                                    </div>

                                    <h2>Current Operational Alerts</h2>
                                </div>

                                <span className="panel-count">
                                    {alerts.length} alerts
                                </span>
                            </div>

                            {alerts.length === 0 ? (
                                <div className="page-state compact">
                                    No alerts match the selected severity.
                                </div>
                            ) : (
                                <div className="table-wrapper">
                                    <table className="hotspot-table">
                                        <thead>
                                            <tr>
                                                <th>Grid</th>
                                                <th>Alert Type</th>
                                                <th>Severity</th>
                                                <th>Current</th>
                                                <th>Baseline</th>
                                                <th>Reason</th>
                                                <th>Timestamp</th>
                                            </tr>
                                        </thead>

                                        <tbody>
                                            {alerts.map((alert) => {
                                                const gridId = Number(
                                                    alert.grid_id
                                                )

                                                const severityValue =
                                                    String(
                                                        alert.severity || "LOW"
                                                    ).toUpperCase()

                                                return (
                                                    <tr
                                                        key={`${gridId}-${alert.timestamp}-${alert.alert_type}`}
                                                        className={
                                                            selectedGrid ===
                                                            gridId
                                                                ? "row-selected"
                                                                : ""
                                                        }
                                                        onClick={() =>
                                                            handleGridSelect(
                                                                gridId
                                                            )
                                                        }
                                                    >
                                                        <td>
                                                            <button
                                                                className="grid-link"
                                                                onClick={(
                                                                    event
                                                                ) => {
                                                                    event.stopPropagation()
                                                                    handleGridSelect(
                                                                        gridId
                                                                    )
                                                                }}
                                                            >
                                                                {gridId}
                                                            </button>
                                                        </td>

                                                        <td>
                                                            {alert.alert_type ||
                                                                "—"}
                                                        </td>

                                                        <td>
                                                            <span
                                                                className={`status-badge ${getSeverityClass(
                                                                    severityValue
                                                                )}`}
                                                            >
                                                                {severityValue}
                                                            </span>
                                                        </td>

                                                        <td>
                                                            {Number(
                                                                alert.current_activity
                                                            ).toFixed(2)}
                                                        </td>

                                                        <td>
                                                            {Number(
                                                                alert.baseline_activity
                                                            ).toFixed(2)}
                                                        </td>

                                                        <td>
                                                            {alert.reason || "—"}
                                                        </td>

                                                        <td>
                                                            {alert.timestamp}
                                                        </td>
                                                    </tr>
                                                )
                                            })}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="hotspot-layout">
                        <MilanMap
                            hotspots={hotspots}
                            alerts={alerts}
                            selectedGrid={selectedGrid}
                            onSelectGrid={onOpenGrid}
                        />
                    </div>
                </>
            )}
        </div>
    )
}

export default Hotspots