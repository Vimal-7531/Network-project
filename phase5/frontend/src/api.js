const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

export async function getNetworkSummary() {
    const response = await fetch(`${API_BASE_URL}/network/summary`)

    if (!response.ok) {
        throw new Error(`API request failed with status ${response.status}`)
    }

    return response.json()
}

export async function getGridActivity(gridId) {
    const response = await fetch(`${API_BASE_URL}/network/grid/${gridId}`)

    if (response.status === 404) {
        throw new Error("Grid not found")
    }

    if (!response.ok) {
        throw new Error(`API request failed with status ${response.status}`)
    }

    return response.json()
}

export async function getHotspots(limit = 10) {
    const response = await fetch(
        `${API_BASE_URL}/network/hotspots?limit=${limit}`
    )

    if (!response.ok) {
        throw new Error(`Hotspots request failed with status ${response.status}`)
    }

    return response.json()
}

export async function getAlerts(severity = "") {
    const url = severity
        ? `${API_BASE_URL}/network/alerts?severity=${encodeURIComponent(severity)}`
        : `${API_BASE_URL}/network/alerts`

    const response = await fetch(url)

    if (!response.ok) {
        throw new Error(`Alerts request failed with status ${response.status}`)
    }

    return response.json()
}

export async function predictRisk(payload) {
    const response = await fetch(
        `${API_BASE_URL}/network/predict-risk`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        }
    )

    if (!response.ok) {
        throw new Error(
            `Risk prediction failed with status ${response.status}`
        )
    }

    return response.json()
}