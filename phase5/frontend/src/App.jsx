import { useState } from "react"
import Overview from "./pages/Overview"
import Hotspots from "./pages/Hotspots"
import GridExplorer from "./components/GridExplorer"
import Risk from "./pages/Risk"

function App() {
    const [page, setPage] = useState("overview")
    const [selectedGrid, setSelectedGrid] = useState(4821)

    function openGridExplorer(gridId) {
        setSelectedGrid(Number(gridId))
        setPage("grid")
    }

    return (
        <div className="app">
            <nav className="navbar">
                <div className="brand">
                    Network Intelligence
                </div>

                <div className="nav-links">
                    <button
                        className={`nav-link ${
                            page === "overview" ? "active" : ""
                        }`}
                        onClick={() => setPage("overview")}
                    >
                        Overview
                    </button>

                    <button
                        className={`nav-link ${
                            page === "grid" ? "active" : ""
                        }`}
                        onClick={() => setPage("grid")}
                    >
                        Grid Explorer
                    </button>

                    <button
                        className={`nav-link ${
                            page === "hotspots" ? "active" : ""
                        }`}
                        onClick={() => setPage("hotspots")}
                    >
                        Hotspots
                    </button>

                    <button
                        className={`nav-link ${
                            page === "risk" ? "active" : ""
                        }`}
                        onClick={() => setPage("risk")}
                    >
                        Risk
                    </button>
                </div>
            </nav>

            <main>
                {page === "overview" && (
                    <Overview />
                )}

                {page === "grid" && (
                    <GridExplorer
                        initialGrid={selectedGrid}
                    />
                )}

                {page === "hotspots" && (
                    <Hotspots
                        onOpenGrid={openGridExplorer}
                    />
                )}

                {page === "risk" && (
                     <Risk />
                )}
            </main>
        </div>
    )
}

export default App