import { useEffect, useState } from "react"
import { getGridActivity } from "../api"

function GridExplorer({ initialGrid = 4821 }) {
    const [gridId, setGridId] = useState(String(initialGrid))
    const [gridData, setGridData] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)

    useEffect(() => {
        if (initialGrid) {
            setGridId(String(initialGrid))
        }
    }, [initialGrid])

    async function handleSearch(event) {
        event.preventDefault()

        if (!gridId) {
            setError("Please enter a grid ID")
            setGridData(null)
            return
        }

        setLoading(true)
        setError(null)
        setGridData(null)

        try {
            const data = await getGridActivity(gridId)
            setGridData(data)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (!initialGrid) {
            return
        }

        async function loadInitialGrid() {
            setLoading(true)
            setError(null)

            try {
                const data = await getGridActivity(initialGrid)
                setGridData(data)
            } catch (err) {
                setError(err.message)
                setGridData(null)
            } finally {
                setLoading(false)
            }
        }

        loadInitialGrid()
    }, [initialGrid])

    return (
        <section className="panel">
            <div className="panel-header">
                <div>
                    <h2>Grid Explorer</h2>
                    <p>
                        Inspect recent hourly activity for a network grid.
                    </p>
                </div>
            </div>

            <form className="grid-search" onSubmit={handleSearch}>
                <div className="input-group">
                    <label htmlFor="gridId">Grid ID</label>

                    <input
                        id="gridId"
                        type="number"
                        min="1"
                        value={gridId}
                        onChange={(event) =>
                            setGridId(event.target.value)
                        }
                        placeholder="Enter grid ID"
                    />
                </div>

                <button type="submit" disabled={loading}>
                    {loading ? "Loading..." : "Explore Grid"}
                </button>
            </form>

            {error && (
                <div className="inline-error">
                    <strong>Unable to load grid</strong>
                    <span>{error}</span>
                </div>
            )}

            {gridData && (
                <>
                    <div className="grid-summary">
                        <div>
                            <span>Selected Grid</span>
                            <strong>{gridData.grid_id}</strong>
                        </div>

                        <div>
                            <span>Hourly Points</span>
                            <strong>{gridData.data.length}</strong>
                        </div>

                        <div>
                            <span>Reporting AS_OF</span>
                            <strong>{gridData.as_of}</strong>
                        </div>
                    </div>

                    <div className="table-wrapper">
                        <table className="activity-table">
                            <thead>
                                <tr>
                                    <th>Timestamp</th>
                                    <th>SMS Activity</th>
                                    <th>Call Activity</th>
                                    <th>Internet Activity</th>
                                    <th>Total Activity</th>
                                </tr>
                            </thead>

                            <tbody>
                                {gridData.data.map((point) => (
                                    <tr key={point.timestamp}>
                                        <td>{point.timestamp}</td>
                                        <td>
                                            {point.sms_in + point.sms_out}
                                        </td>
                                        <td>
                                            {point.call_in + point.call_out}
                                        </td>
                                        <td>
                                            {point.internet_activity}
                                        </td>
                                        <td>
                                            {point.total_activity}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </>
            )}
        </section>
    )
}

export default GridExplorer