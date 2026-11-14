import { useEffect, useState } from "react";
import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { api, auth } from "./api";
import Layout, { Mark } from "./components/Layout";
import { Button, Spinner } from "./components/ui";
import Incidents from "./pages/Incidents";
import IncidentDetail from "./pages/IncidentDetail";
import Respond from "./pages/Respond";
import Settings from "./pages/Settings";

function Login({ onDone }) {
  const [key, setKey] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    auth.set(key.trim());
    try {
      await api("/auth/verify", { method: "POST" });
      onDone();
    } catch (err) {
      auth.clear();
      setError(err.status === 401 ? "That access key is not correct." : err.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="centered">
      <form className="login" onSubmit={submit}>
        <div className="brand dark"><Mark /><span>Retrace</span></div>
        <h1>Sign in</h1>
        <label className="field">
          <span>Access key</span>
          <input type="password" value={key} onChange={(e) => setKey(e.target.value)} autoFocus autoComplete="current-password" />
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <Button variant="primary" busy={busy} disabled={!key.trim()} type="submit">Sign in</Button>
        <p className="hint">The key is the ADMIN_ACCESS_KEY value set on the server.</p>
      </form>
    </div>
  );
}

function Protected() {
  const [state, setState] = useState("checking");
  useEffect(() => {
    api("/auth/status")
      .then((s) => setState(!s.required || auth.get() ? "ok" : "login"))
      .catch(() => setState("ok"));
    const out = () => { auth.clear(); setState("login"); };
    window.addEventListener("retrace:unauthorized", out);
    return () => window.removeEventListener("retrace:unauthorized", out);
  }, []);
  if (state === "checking") return <div className="centered"><Spinner /></div>;
  if (state === "login") return <Login onDone={() => setState("ok")} />;
  return <Layout><Outlet /></Layout>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/respond/:token" element={<Respond />} />
      <Route element={<Protected />}>
        <Route path="/" element={<Incidents />} />
        <Route path="/incidents/:id" element={<IncidentDetail />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
