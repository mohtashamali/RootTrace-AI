import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { api, auth } from "../api";

export const Mark = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M2 12h5l3-8 4 16 3-8h5" />
  </svg>
);

export default function Layout({ children }) {
  const { pathname } = useLocation();
  const [info, setInfo] = useState(null);
  useEffect(() => { api("/settings").then(setInfo).catch(() => {}); }, []);
  const inIncidents = pathname === "/" || pathname.startsWith("/incidents");

  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand"><Mark /><span>Retrace</span></div>
        <nav aria-label="Main">
          <NavLink to="/" className={inIncidents ? "active" : ""}>Incidents</NavLink>
          <NavLink to="/settings">Settings</NavLink>
        </nav>
        <div className="rail-foot">
          <div className="conn">
            <span className={`dot ${info ? (info.groq.configured ? "ok" : "bad") : ""}`} />
            {info ? (info.groq.configured ? `Groq: ${info.groq.model}` : "Groq key missing") : "Checking"}
          </div>
          {info?.auth_enabled && (
            <button className="linklike" onClick={() => { auth.clear(); location.assign("/"); }}>Sign out</button>
          )}
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
