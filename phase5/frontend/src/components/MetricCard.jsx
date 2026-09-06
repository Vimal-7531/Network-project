function MetricCard({ label, value }) {
    return (
        <div className="metric-card">
            <span className="metric-label">{label}</span>
            <strong className="metric-value">{value}</strong>
        </div>
    )
}

export default MetricCard