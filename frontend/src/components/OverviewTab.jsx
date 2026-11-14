import { DiffView, LogView } from "./CodeView";
import { ConfidenceBar, Empty, fmtTime, pct } from "./ui";

export default function OverviewTab({ inc }) {
  const { usage } = inc;
  return (
    <div className="split">
      <div className="stack">
        {inc.summary && (
          <section className="panel"><div className="panel-body"><h2 style={{ marginBottom: 6 }}>What failed</h2><p>{inc.summary}</p></div></section>
        )}
        <section className="panel">
          <div className="panel-head"><h2>Build logs</h2><span className="hint">Lines that look like errors are highlighted. Secrets are redacted on ingest.</span></div>
          <LogView text={inc.logs} />
        </section>
        <section className="panel">
          <div className="panel-head"><h2>Code diff</h2></div>
          {inc.diff ? <DiffView text={inc.diff} /> : <div className="panel-body hint">No diff was provided for this incident.</div>}
        </section>
      </div>

      <div className="stack">
        <section className="panel">
          <div className="panel-head"><h2>Hypotheses</h2></div>
          <div className="panel-body">
            {inc.hypotheses.length === 0 ? <p className="hint">Hypotheses appear once the analysis finishes.</p> :
              [...inc.hypotheses].sort((a, b) => b.confidence - a.confidence).map((h) => (
                <div key={h.id} className={`hyp hyp-${h.status}`}>
                  <div className="hyp-top"><span className="muted">{h.status === "open" ? "Open" : h.status === "supported" ? "Supported" : "Refuted"}</span><span className="pct">{pct(h.confidence)}</span></div>
                  <p>{h.statement}</p>
                  <ConfidenceBar value={h.confidence} status={h.status} />
                  {h.to_confirm && <p className="confirm">To confirm: {h.to_confirm}</p>}
                </div>
              ))}
          </div>
        </section>
        <section className="panel">
          <div className="panel-head"><h2>Activity</h2></div>
          <div className="panel-body">
            {inc.events.length === 0 ? <Empty title="No activity">Nothing has happened yet.</Empty> : (
              <ul className="activity">
                {[...inc.events].reverse().map((e) => (
                  <li key={e.id} className={e.kind}><time>{fmtTime(e.created_at).split(", ").pop()}</time><span>{e.text}</span></li>
                ))}
              </ul>
            )}
            <p className="foot-note">
              {usage.calls} model calls, {(usage.prompt_tokens + usage.completion_tokens).toLocaleString()} tokens
              {usage.calls ? `, ${(usage.avg_latency_ms / 1000).toFixed(1)} s average` : ""}.
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
