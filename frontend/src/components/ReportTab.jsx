import { useState } from "react";
import { api, downloadMarkdown } from "../api";
import { Button, Chip, ConfidenceBar, Empty, fmtTime, pct, Spinner } from "./ui";
import { useToast } from "./toast";

const SOURCE = { log: "Build log", diff: "Diff", interview: "Interview" };
const CHECK = { log: "Matches the logs", diff: "Matches the diff", interview: "Matches the transcript" };

export default function ReportTab({ inc, reload }) {
  const toast = useToast();
  const [busy, setBusy] = useState("");
  const r = inc.report;
  const published = inc.status === "published";
  const act = async (key, fn, ok) => {
    setBusy(key);
    try { await fn(); if (ok) toast(ok); reload(); } catch (e) { toast(e.message, "error"); } finally { setBusy(""); }
  };
  const write = () => act("write", () => api(`/incidents/${inc.id}/report`, { method: "POST" }));

  if (inc.status === "compiling" && !r) return <div className="panel"><Empty title="Writing the report"><Spinner /></Empty></div>;
  if (!r) {
    const open = inc.interviews.filter((i) => !["completed", "skipped"].includes(i.status)).length;
    return (
      <div className="panel">
        <Empty title="No report yet">
          {inc.status === "interviewing"
            ? `The report is written automatically when every interview is closed. ${open} still open. You can also write it now from what is known so far; the confidence will reflect the gaps.`
            : "The report is written after the analysis and interviews."}
          {inc.status === "interviewing" && <><br /><br /><Button variant="primary" busy={busy === "write"} onClick={write}>Write report now</Button></>}
        </Empty>
      </div>
    );
  }

  const meta = r.meta;
  const unverified = meta.evidence_total - meta.evidence_verified;
  return (
    <div className="doc-wrap">
      <div className="doc-bar">
        <div className="actions">
          {published ? <Chip kind="published">Published {fmtTime(inc.published_at)}</Chip> : <Chip kind="draft">Draft, not yet approved</Chip>}
          {inc.status === "compiling" && <><Spinner small /><span className="hint">Rewriting</span></>}
        </div>
        <div className="actions">
          <Button onClick={() => act("md", () => downloadMarkdown(inc.id))} busy={busy === "md"}>Download Markdown</Button>
          {!published && <Button onClick={write} busy={busy === "write" || inc.status === "compiling"}>Regenerate</Button>}
          {!published && <Button variant="primary" busy={busy === "pub"} onClick={() => window.confirm("Publish this report? It will be marked as approved.") && act("pub", () => api(`/incidents/${inc.id}/publish`, { method: "POST" }), "Published.")}>Approve and publish</Button>}
        </div>
      </div>

      <article className="doc">
        <h1>{r.title}</h1>
        <div className="doc-meta">{[inc.repo, inc.branch, inc.commit_sha].filter(Boolean).join("  ")}. Based on {meta.interviews_completed} of {meta.interviews_total} interviews, written {fmtTime(meta.generated_at)}.</div>
        <p>{r.summary}</p>

        <h2>Impact</h2><p>{r.impact || "Not stated."}</p>

        <h2>Root cause</h2>
        <div className="root">
          <p>{r.root_cause.statement}</p>
          <div className="conf"><span>Confidence {pct(r.root_cause.confidence)}</span><ConfidenceBar value={r.root_cause.confidence} status="supported" /></div>
        </div>

        {r.timeline.length > 0 && <><h2>Timeline</h2><ul className="timeline">{r.timeline.map((t, i) => <li key={i}><time>{t.when}</time><span>{t.event}</span></li>)}</ul></>}
        {r.contributing_factors.length > 0 && <><h2>Contributing factors</h2><ul>{r.contributing_factors.map((f, i) => <li key={i}>{f}</li>)}</ul></>}

        {r.evidence.length > 0 && (
          <div className="wide" style={{ maxWidth: "70ch", margin: "0 auto" }}>
            <h2 style={{ margin: "30px 0 8px" }}>Evidence</h2>
            <p className="ledger-head">
              {meta.evidence_verified} of {meta.evidence_total} quoted excerpts were found in their source.
              {unverified > 0 && " Excerpts marked as not found may be paraphrased or wrong; check them before approving."}
            </p>
            <div className="scroll-x">
              <table className="ledger">
                <thead><tr><th>Claim</th><th>Source</th><th>Quoted excerpt</th><th>Check</th></tr></thead>
                <tbody>
                  {r.evidence.map((e, i) => (
                    <tr key={i}>
                      <td>{e.claim}</td>
                      <td><span className="src">{SOURCE[e.source]}{e.ref ? `, ${e.ref}` : ""}</span></td>
                      <td><code>{e.excerpt}</code></td>
                      <td><span className={`check ${e.verified ? "ok" : "no"}`}>{e.verified ? CHECK[e.source] : "Not found in source"}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {r.contradictions.length > 0 && <><h2>Where accounts and evidence differ</h2><ul>{r.contradictions.map((c, i) => <li key={i}>{c.statement} <em>{c.conflict}</em></li>)}</ul></>}
        {r.action_items.length > 0 && <><h2>Action items</h2><ul style={{ listStyle: "none", paddingLeft: 0 }}>{r.action_items.map((a, i) => <li key={i} className="action"><Chip kind="draft" plain>{a.type}</Chip><span>{a.action}{a.owner_role ? ` (${a.owner_role})` : ""}</span></li>)}</ul></>}
        {r.open_questions.length > 0 && <><h2>Open questions</h2><ul>{r.open_questions.map((q, i) => <li key={i}>{q}</li>)}</ul></>}
      </article>
    </div>
  );
}
