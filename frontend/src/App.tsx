import { NavLink, Route, Routes } from "react-router-dom";

import { ActionPointDetailPage } from "./pages/ActionPointDetailPage";
import { DashboardPage } from "./pages/DashboardPage";
import { NewActionPointPage } from "./pages/NewActionPointPage";

function navLinkClass({ isActive }: { isActive: boolean }) {
  return isActive ? "nav-link active" : "nav-link";
}

export default function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <h1 className="app-title">Voice-to-Action-Points</h1>
        <nav className="app-nav">
          <NavLink to="/" end className={navLinkClass}>
            Dashboard
          </NavLink>
          <NavLink to="/new" className={navLinkClass}>
            New Action Point
          </NavLink>
        </nav>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/new" element={<NewActionPointPage />} />
          <Route path="/action-points/:id" element={<ActionPointDetailPage />} />
        </Routes>
      </main>
    </div>
  );
}
