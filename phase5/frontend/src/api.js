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
export async function getAlerts(limit = 10, severity = "") {
    const params = new URLSearchParams()

    params.set("limit", limit)

    if (severity) {
        params.set("severity", severity)
    }

    const response = await fetch(
        `${API_BASE_URL}/network/alerts?${params.toString()}`
    )

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