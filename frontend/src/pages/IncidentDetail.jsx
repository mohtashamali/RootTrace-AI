import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useLoad } from "../hooks";
import InterviewsTab from "../components/InterviewsTab";
import OverviewTab from "../components/OverviewTab";
import ReportTab from "../components/ReportTab";
import { useToast } from "../components/toast";
import { Button, Chip, Empty, Spinner, StatusChip, timeAgo } from "../components/ui";

const SETTLED = ["draft", "published", "error"];

export default function IncidentDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const toast = useToast();
  const [sp, setSp] = useSearchParams();
  const tab = sp.get("tab") || "overview";
  const [busy, setBusy] = useState("");
  const { data: inc, error, loading, reload } = useLoad(() => api(`/incidents/${id}`), [id], { interval: 3000, until: (d) => SETTLED.includes(d.status) });

  if (loading) return <div className="empty"><Spinner /></div>;
  if (!inc) return <div className="panel"><Empty title="Incident not available">{error}<br /><br /><Link to="/">Back to incidents</Link></Empty></div>;

  const act = async (key, path, ok) => {
    setBusy(key);
    try { await api(path, { method: "POST" }); if (ok) toast(ok); reload(); } catch (e) { toast(e.message, "error"); } finally { setBusy(""); }
  };
  const remove = async () => {
    if (!window.confirm("Delete this incident and its interviews? This cannot be undone.")) return;
    try { await api(`/incidents/${id}`, { method: "DELETE" }); nav("/"); } catch (e) { toast(e.message, "error"); }
  };
  const open = inc.interviews.filter((i) => !["completed", "skipped"].includes(i.status)).length;
  const tabs = [["overview", "Overview"], ["interviews", `Interviews`, inc.interviews.length], ["report", "Report"]];

  return (
    <>
      <Link to="/" className="crumb">Incidents</Link>
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div style={{ minWidth: 0 }}>
          <h1>{inc.title}</h1>
          <div className="meta">
            <span><b>Repository</b>{inc.repo || "Not given"}</span>
            {inc.branch && <span><b>Branch</b>{inc.branch}</span>}
            {inc.commit_sha && <span><b>Commit</b><code>{inc.commit_sha}</code></span>}
            {inc.workflow && <span><b>Workflow</b>{inc.workflow}</span>}
            <span><b>Opened</b>{timeAgo(inc.created_at)}</span>
            {inc.run_url && <a href={inc.run_url} target="_blank" rel="noreferrer">View run on GitHub</a>}
          </div>
        </div>
        <div className="actions">
          <StatusChip status={inc.status} />
          {inc.status !== "analyzing" && <Chip kind={inc.severity} plain>{inc.severity} severity</Chip>}
          <Button variant="quiet" className="btn-danger" onClick={remove}>Delete</Button>
        </div>
      </div>

      {inc.status === "analyzing" && <div className="banner"><Spinner small /><span className="grow">Reading the logs and the diff to form hypotheses.</span></div>}
      {inc.status === "interviewing" && (
        <div className="banner warn">
          <span className="grow">{open === 0 ? "All interviews are closed." : `Waiting on ${open} of ${inc.interviews.length} ${open === 1 ? "person" : "people"}.`} The report is written automatically when the last interview closes.</span>
          {inc.can_simulate && <Button busy={busy === "sim"} onClick={() => act("sim", `/incidents/${id}/simulate`, "Simulated engineers are replying.")}>Run simulated interviews</Button>}
        </div>
      )}
      {inc.status === "compiling" && <div className="banner"><Spinner small /><span className="grow">Writing the report and checking every quoted excerpt against its source.</span></div>}
      {inc.status === "error" && (
        <div className="banner bad" role="alert"><span className="grow">{inc.error}</span><Button busy={busy === "retry"} onClick={() => act("retry", `/incidents/${id}/retry`)}>Retry</Button></div>
      )}

      <div className="tabs" role="tablist">
        {tabs.map(([k, label, n]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setSp(k === "overview" ? {} : { tab: k }, { replace: true })}>
            {label}{n != null && <span className="count">{n}</span>}
          </button>
        ))}
      </div>

      {tab === "overview" && <OverviewTab inc={inc} />}
      {tab === "interviews" && <InterviewsTab inc={inc} reload={reload} />}
      {tab === "report" && <ReportTab inc={inc} reload={reload} />}
    </>
  );
}
