import { useDeferredValue, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useLoad } from "../hooks";
import NewIncidentModal from "../components/NewIncidentModal";
import { Button, Chip, Empty, Spinner, StatusChip, STATUS, timeAgo } from "../components/ui";

const minutes = (m) => (m == null ? "Not yet" : m < 1 ? "Under a minute" : m < 90 ? `${Math.round(m)} min` : `${(m / 60).toFixed(1)} h`);

export default function Incidents() {
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [creating, setCreating] = useState(false);
  const dq = useDeferredValue(q);
  const list = useLoad(
    () => api(`/incidents?${new URLSearchParams({ ...(dq && { q: dq }), ...(status && { status }) })}`),
    [dq, status], { interval: 6000 });
  const stats = useLoad(() => api("/stats"), [], { interval: 6000 });
  const s = stats.data;
  const filtering = !!(dq || status);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Incidents</h1>
          <p className="sub">Failed builds and deployments, investigated while people still remember what happened.</p>
        </div>
        <Button variant="primary" onClick={() => setCreating(true)}>New incident</Button>
      </div>

      <dl className="stats">
        <div><dt>Open incidents</dt><dd>{s ? s.open : "–"}</dd></div>
        <div><dt>Waiting on people</dt><dd>{s ? s.waiting_on_people : "–"}</dd></div>
        <div><dt>Median time to report</dt><dd>{s ? minutes(s.median_minutes_to_report) : "–"}</dd></div>
        <div><dt>Questions per interview</dt><dd>{s ? (s.avg_questions ?? "Not yet") : "–"}</dd></div>
      </dl>

      <div className="filters">
        <input type="search" placeholder="Search title, repository or commit" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search incidents" />
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status">
          <option value="">All statuses</option>
          {Object.entries(STATUS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>

      <div className="panel">
        {list.loading ? <div className="empty"><Spinner /></div>
          : list.error && !list.data ? <Empty title="Could not load incidents">{list.error}</Empty>
          : list.data.length === 0 ? (
            filtering ? <Empty title="No matching incidents">Try a different search or clear the status filter.</Empty> : (
              <Empty title="No incidents yet">
                Connect a GitHub repository in Settings so failed workflow runs open incidents automatically, or start one from a sample failure.
                <br /><br /><Button variant="primary" onClick={() => setCreating(true)}>New incident</Button>
              </Empty>)
          ) : (
            <table className="list">
              <thead><tr><th>Incident</th><th>Status</th><th>Severity</th><th>Interviews</th><th>Opened</th></tr></thead>
              <tbody>
                {list.data.map((i) => (
                  <tr key={i.id} onClick={() => nav(`/incidents/${i.id}`)}>
                    <td>
                      <a className="title" href={`/incidents/${i.id}`} onClick={(e) => e.preventDefault()}>{i.title}</a>
                      <div className="sub">{[i.repo, i.branch, i.commit_sha].filter(Boolean).join("  ")}</div>
                    </td>
                    <td><StatusChip status={i.status} /></td>
                    <td>{i.status === "analyzing" ? <span className="muted">Pending</span> : <Chip kind={i.severity} plain>{i.severity}</Chip>}</td>
                    <td className="num">{i.interviews_done} of {i.interviews_total} done</td>
                    <td className="muted">{timeAgo(i.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
      </div>
      {creating && <NewIncidentModal onClose={() => setCreating(false)} />}
    </>
  );
}
