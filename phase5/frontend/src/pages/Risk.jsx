import { useState } from "react"
import { predictRisk } from "../api"

function Risk() {
    const [gridId, setGridId] = useState("4857")
    const [timestamp, setTimestamp] = useState("2013-11-07T23:00:00")
    const [totalActivity, setTotalActivity] = useState("8344.6583")

    const [result, setResult] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState("")

    async function handlePredict(event) {
        event.preventDefault()

        setLoading(true)
        setError("")
        setResult(null)

        try {
            const response = await predictRisk({
                grid_id: Number(gridId),
                timestamp,
                total_activity: Number(totalActivity)
            })

            setResult(response)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    function getRiskClass(level) {
        if (level === "HIGH") {
            return "risk-high"
        }

        if (level === "MEDIUM") {
            return "risk-medium"
        }

        return "risk-low"
    }

    return (
        <div className="page-container">
            <div className="page-heading">
                <div>
                    <div className="eyebrow">
                        PREDICTIVE INTELLIGENCE
                    </div>

                    <h1>Predictive Risk</h1>

                    <p>
                        Generate an operational attention signal for a
                        selected network grid and time window.
                    </p>
                </div>
            </div>

            <div className="risk-layout">
                <section className="risk-input-panel">
                    <div className="panel-header">
                        <div>
                            <div className="eyebrow">
                                PREDICTION INPUT
                            </div>

                            <h2>Run Risk Assessment</h2>

                            <p>
                                Submit the current grid activity to the
                                prediction service.
                            </p>
                        </div>
                    </div>

                    <form
                        className="risk-form"
                        onSubmit={handlePredict}
                    >
                        <div className="input-group">
                            <label htmlFor="risk-grid-id">
                                Grid ID
                            </label>

                            <input
                                id="risk-grid-id"
                                type="number"
                                min="1"
                                value={gridId}
                                onChange={(event) =>
                                    setGridId(event.target.value)
                                }
                                required
                            />
                        </div>

                        <div className="input-group">
                            <label htmlFor="risk-timestamp">
                                Timestamp
                            </label>

                            <input
                                id="risk-timestamp"
                                type="text"
                                value={timestamp}
                                onChange={(event) =>
                                    setTimestamp(event.target.value)
                                }
                                required
                            />
                        </div>

                        <div className="input-group">
                            <label htmlFor="risk-activity">
                                Total Activity
                            </label>

                            <input
                                id="risk-activity"
                                type="number"
                                step="any"
                                min="0"
                                value={totalActivity}
                                onChange={(event) =>
                                    setTotalActivity(event.target.value)
                                }
                                required
                            />
                        </div>

                        <button
                            type="submit"
                            className="risk-submit"
                            disabled={loading}
                        >
                            {loading
                                ? "Running Prediction..."
                                : "Run Prediction"}
                        </button>
                    </form>

                    {error && (
                        <div className="status-banner error">
                            <strong>Prediction unavailable</strong>
                            <span>{error}</span>
                        </div>
                    )}
                </section>

                <section className="risk-output-panel">
                    <div className="panel-header">
                        <div>
                            <div className="eyebrow">
                                MODEL OUTPUT
                            </div>

                            <h2>Risk Signal</h2>

                            <p>
                                Model output is shown separately from
                                any future AI explanation.
                            </p>
                        </div>
                    </div>

                    {!result ? (
                        <div className="page-state compact">
                            Run a prediction to view the model output.
                        </div>
                    ) : (
                        <div className="risk-result">
                            <div className="risk-score-card">
                                <span>Risk Score</span>

                                <strong>
                                    {Number(
                                        result.risk_score
                                    ).toFixed(2)}
                                </strong>
                            </div>

                            <div className="risk-level-card">
                                <span>Risk Level</span>

                                <strong
                                    className={getRiskClass(
                                        result.risk_level
                                    )}
                                >
                                    {result.risk_level}
                                </strong>
                            </div>

                            <div className="risk-model-card">
                                <span>Model Version</span>

                                <strong>
                                    {result.model_version}
                                </strong>
                            </div>

                            <div className="risk-explanation">
                                <div>
                                    <div className="eyebrow">
                                        NARRATIVE SPACE
                                    </div>

                                    <h3>Explain with AI</h3>
                                </div>

                                <p>
                                    AI explanation will be available
                                    in a later Network Operations
                                    Assistant phase.
                                </p>

                                <button
                                    type="button"
                                    disabled
                                    className="explain-button"
                                >
                                    Explain with AI
                                </button>
                            </div>

                            <div className="risk-disclaimer">
                                <strong>
                                    Operational attention signal
                                </strong>

                                <span>
                                    This prediction is an attention
                                    signal for investigation. It does
                                    not confirm a network fault,
                                    congestion, capacity issue, or
                                    throughput problem.
                                </span>
                            </div>
                        </div>
                    )}
                </section>
            </div>
        </div>
    )
}

export default Risk