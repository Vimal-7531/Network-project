import { useEffect, useState } from "react"
import { getNetworkSummary } from "../api"
import MetricCard from "../components/MetricCard"
import GridExplorer from "../components/GridExplorer"

function Overview() {
    const [summary, setSummary] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        async function loadSummary() {
            try {
                const data = await getNetworkSummary()
                setSummary(data)
            } catch (err) {
                setError(err.message)
            } finally {
                setLoading(false)
            }
        }

        loadSummary()
    }, [])

    if (loading) {
        return (
            <div className="page">
                <div className="page-state">
                    Loading network data...
                </div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="page">
                <div className="api-error">
                    <strong>Network API unavailable</strong>
                    <span>{error}</span>
                </div>
            </div>
        )
    }

    return (
        <div className="page">
            <header className="page-header">
                <div>
                    <div className="eyebrow">NETWORK OPERATIONS CENTER</div>
                    <h1>Network Overview</h1>
                    <p>Operational activity across the network.</p>
                </div>

                <div className="as-of">
                    <span>Reporting AS_OF</span>
                    <strong>{summary.as_of}</strong>
                </div>
            </header>

            <section className="metrics">
                <MetricCard
                    label="Total Activity"
                    value={summary.total_activity}
                />

                <MetricCard
                    label="Active Grids"
                    value={summary.active_grids}
                />

                <MetricCard
                    label="Peak Hour"
                    value={summary.peak_hour}
                />

                <MetricCard
                    label="Top Grid"
                    value={summary.top_grid}
                />
            </section>

            <GridExplorer />
        </div>
    )
}

export default Overview