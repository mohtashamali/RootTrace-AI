import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useLoad } from "../hooks";
import { Button, Modal, Spinner } from "./ui";

const EMPTY = { title: "", repo: "", branch: "", commit_sha: "", workflow: "", commit_message: "", logs: "", diff: "" };

export default function NewIncidentModal({ onClose }) {
  const nav = useNavigate();
  const [mode, setMode] = useState("sample");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const scenarios = useLoad(() => api("/scenarios"), []);
  const [picked, setPicked] = useState("");
  const [form, setForm] = useState(EMPTY);
  const [people, setPeople] = useState([{ name: "", role: "", handle: "" }]);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const setPerson = (i, k, v) => setPeople((l) => l.map((p, j) => (j === i ? { ...p, [k]: v } : p)));
  const cleaned = people.filter((p) => p.name.trim());
  const manualReady = form.title.trim().length >= 3 && form.logs.trim().length >= 10 && cleaned.length > 0;
  const ready = mode === "sample" ? !!picked : manualReady;

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      const created = mode === "sample"
        ? await api("/incidents/sample", { method: "POST", body: { scenario_key: picked } })
        : await api("/incidents", { method: "POST", body: { ...form, participants: cleaned } });
      nav(`/incidents/${created.id}`);
    } catch (e) {
      setError(e.message);
      setBusy(false);
    }
  };

  return (
    <Modal wide title="New incident" onClose={onClose}
      footer={<>
        {error && <span className="form-error" style={{ marginRight: "auto" }} role="alert">{error}</span>}
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="primary" busy={busy} disabled={!ready} onClick={submit}>Start investigation</Button>
      </>}>
      <div className="seg" role="group" aria-label="Source">
        <button aria-pressed={mode === "sample"} onClick={() => setMode("sample")}>Sample failure</button>
        <button aria-pressed={mode === "manual"} onClick={() => setMode("manual")}>Paste your own</button>
      </div>

      {mode === "sample" ? (
        <div style={{ display: "grid", gap: 10 }}>
          <p className="hint">Pick a realistic failure. Retrace analyzes it, opens interviews, and you can answer them yourself or let simulated engineers respond.</p>
          {scenarios.loading && <Spinner />}
          {scenarios.error && <p className="form-error">{scenarios.error}</p>}
          {scenarios.data?.map((s) => (
            <label key={s.key} className="choice">
              <input type="radio" name="scenario" checked={picked === s.key} onChange={() => setPicked(s.key)} />
              <div><b>{s.title}</b><span>{s.blurb} {s.repo}, {s.people} people to interview.</span></div>
            </label>
          ))}
        </div>
      ) : (
        <>
          <label className="field"><span>Title</span><input value={form.title} onChange={set("title")} placeholder="Deploy failed: checkout-service health check" /></label>
          <div className="grid3">
            <label className="field"><span>Repository</span><input value={form.repo} onChange={set("repo")} placeholder="acme/checkout" /></label>
            <label className="field"><span>Branch</span><input value={form.branch} onChange={set("branch")} placeholder="main" /></label>
            <label className="field"><span>Commit</span><input value={form.commit_sha} onChange={set("commit_sha")} placeholder="a3f9c21" /></label>
          </div>
          <div className="grid2">
            <label className="field"><span>Workflow or pipeline</span><input value={form.workflow} onChange={set("workflow")} placeholder="deploy-production" /></label>
            <label className="field"><span>Commit message</span><input value={form.commit_message} onChange={set("commit_message")} /></label>
          </div>
          <label className="field"><span>Build or deploy logs</span><textarea className="code-in" rows={7} value={form.logs} onChange={set("logs")} placeholder="Paste the failing output" /></label>
          <label className="field"><span>Code diff (optional)</span><textarea className="code-in" rows={5} value={form.diff} onChange={set("diff")} placeholder="Paste git diff output" /></label>
          <div style={{ display: "grid", gap: 8 }}>
            <span className="hint">People to interview. Each gets a private link to a short chat.</span>
            {people.map((p, i) => (
              <div className="person-row" key={i}>
                <input aria-label="Name" placeholder="Name" value={p.name} onChange={(e) => setPerson(i, "name", e.target.value)} />
                <input aria-label="Role" placeholder="Role, for example commit author" value={p.role} onChange={(e) => setPerson(i, "role", e.target.value)} />
                <input aria-label="Slack handle" placeholder="@handle" value={p.handle} onChange={(e) => setPerson(i, "handle", e.target.value)} />
                <Button variant="quiet" disabled={people.length === 1} onClick={() => setPeople((l) => l.filter((_, j) => j !== i))}>Remove</Button>
              </div>
            ))}
            {people.length < 8 && <div><Button onClick={() => setPeople((l) => [...l, { name: "", role: "", handle: "" }])}>Add person</Button></div>}
          </div>
        </>
      )}
    </Modal>
  );
}
