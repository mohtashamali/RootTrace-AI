import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import { useLoad } from "../hooks";
import { Mark } from "../components/Layout";
import { Button, Empty, Spinner, fmtTime } from "../components/ui";

export default function Respond() {
  const { token } = useParams();
  const { data, error, loading } = useLoad(() => api(`/respond/${token}`), [token]);
  const [view, setView] = useState(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [sendError, setSendError] = useState("");
  const end = useRef(null);
  const current = view || data;

  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [current?.messages.length, busy]);

  const send = async (content) => {
    const body = (content ?? text).trim();
    if (!body || busy) return;
    setBusy(true);
    setSendError("");
    // show the answer immediately; roll back if the interviewer cannot respond
    setView({ ...current, messages: [...current.messages, { id: "pending", role: "participant", content: body }] });
    try {
      setView(await api(`/respond/${token}/messages`, { method: "POST", body: { content: body } }));
      setText("");
    } catch (e) {
      setView(current);
      setSendError(e.message);
      setText(body);
    } finally {
      setBusy(false);
    }
  };

  const onKey = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } };

  if (loading) return <div className="centered"><Spinner /></div>;
  if (!current) return <div className="centered"><div className="panel"><Empty title="This link does not work">{error}</Empty></div></div>;

  const closed = current.status === "completed" || current.status === "skipped";
  const first = current.participant.name.split(" ")[0];
  const inc = current.incident;

  return (
    <div className="respond">
      <div className="brand dark"><Mark /><span>Retrace</span></div>
      <section className="panel brief">
        <h1>Hi {first}, a few questions about a failed build</h1>
        <p><b>{inc.title}</b></p>
        <p className="hint" style={{ margin: "4px 0 10px" }}>{[inc.repo, inc.branch, inc.commit_sha].filter(Boolean).join("  ")}  Opened {fmtTime(inc.opened_at)}</p>
        {inc.summary && <p>{inc.summary}</p>}
        <p className="hint" style={{ marginTop: 10 }}>
          An AI assistant writes the questions from the logs and the code change. Your answers are saved and used in a blameless incident report that a person reviews before it is published. Short answers are fine, and "I don't know" is a useful answer.
        </p>
      </section>

      <section className="panel" style={{ marginTop: 16 }}>
        <div className="chat" aria-live="polite">
          {current.messages.map((m) => <div key={m.id} className={`bubble ${m.role}`}>{m.content}</div>)}
          {busy && <div className="bubble agent"><Spinner small /></div>}
          <div ref={end} />
        </div>
        {closed ? (
          <div className="composer"><p>Thank you. Your answers are recorded and you can close this page.</p></div>
        ) : (
          <div className="composer">
            {sendError && <p className="form-error" role="alert">{sendError}</p>}
            <div className="quick">
              <Button className="btn-small" disabled={busy} onClick={() => send("I don't know.")}>I don't know</Button>
              <Button className="btn-small" disabled={busy} onClick={() => send("I wasn't involved in this. Someone else would know more.")}>I wasn't involved</Button>
            </div>
            <div className="row">
              <textarea value={text} onChange={(e) => setText(e.target.value)} onKeyDown={onKey} rows={2} maxLength={2000}
                placeholder="Type your answer. Enter sends, Shift+Enter adds a line." aria-label="Your answer" />
              <Button variant="primary" busy={busy} disabled={!text.trim()} onClick={() => send()}>Send</Button>
            </div>
            <span className="progress">Question {Math.min(current.asked, current.max_questions)} of at most {current.max_questions}</span>
          </div>
        )}
      </section>
    </div>
  );
}
