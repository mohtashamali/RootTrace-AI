import { useState } from "react";
import { api } from "../api";
import { Button, Chip, CopyButton, IV_STATUS, Modal } from "./ui";
import { useToast } from "./toast";

function AddPerson({ incidentId, initial, onClose, onDone }) {
  const toast = useToast();
  const [p, setP] = useState({ name: initial || "", role: "", handle: "" });
  const [busy, setBusy] = useState(false);
  const save = async () => {
    setBusy(true);
    try {
      await api(`/incidents/${incidentId}/participants`, { method: "POST", body: p });
      toast(`${p.name} added. Their first question is being prepared.`);
      onDone();
    } catch (e) { toast(e.message, "error"); setBusy(false); }
  };
  return (
    <Modal title="Add person" onClose={onClose} footer={<><Button onClick={onClose}>Cancel</Button><Button variant="primary" busy={busy} disabled={!p.name.trim()} onClick={save}>Add and open interview</Button></>}>
      <label className="field"><span>Name</span><input value={p.name} onChange={(e) => setP({ ...p, name: e.target.value })} autoFocus /></label>
      <label className="field"><span>Role</span><input value={p.role} onChange={(e) => setP({ ...p, role: e.target.value })} placeholder="For example, on-call SRE" /></label>
      <label className="field"><span>Slack handle</span><input value={p.handle} onChange={(e) => setP({ ...p, handle: e.target.value })} placeholder="@handle" /></label>
    </Modal>
  );
}

function Card({ iv, onChange, onInvite, locked }) {
  const toast = useToast();
  const [open, setOpen] = useState(iv.status === "active");
  const [busy, setBusy] = useState("");
  const run = async (key, fn, ok) => {
    setBusy(key);
    try { await fn(); if (ok) toast(ok); onChange(); } catch (e) { toast(e.message, "error"); } finally { setBusy(""); }
  };
  const closed = iv.status === "completed" || iv.status === "skipped";
  return (
    <section className="panel">
      <div className="iv-head">
        <div>
          <div className="who"><b>{iv.name}</b><span>{iv.role}{iv.handle ? `  ${iv.handle}` : ""}</span></div>
          <div className="iv-meta">
            <Chip kind={iv.status}>{IV_STATUS[iv.status]}</Chip>
            <span className="num">{iv.asked} of {iv.max_questions} questions asked</span>
          </div>
        </div>
        <div className="actions">
          {!closed && <CopyButton text={iv.invite_url} />}
          {!closed && <Button busy={busy === "remind"} onClick={() => run("remind", () => api(`/interviews/${iv.id}/remind`, { method: "POST" }), "Reminder sent on Slack.")}>Send Slack reminder</Button>}
          {!closed && !locked && <Button variant="quiet" busy={busy === "skip"} onClick={() => window.confirm(`Skip the interview with ${iv.name}?`) && run("skip", () => api(`/interviews/${iv.id}/skip`, { method: "POST" }))}>Skip</Button>}
          <Button variant="quiet" onClick={() => setOpen(!open)} aria-expanded={open}>{open ? "Hide transcript" : "Show transcript"}</Button>
        </div>
      </div>
      {iv.referral && !locked && (
        <div className="referral"><span>{iv.name} suggested talking to: <b>{iv.referral}</b></span><Button onClick={() => onInvite(iv.referral)}>Invite them</Button></div>
      )}
      {open && (
        <div className="transcript">
          {iv.messages.length === 0 ? <span className="hint">The first question is still being written.</span> : iv.messages.map((m) => (
            <div key={m.id} className={`msg ${m.role}`}><div className="who">{m.role === "agent" ? "Retrace" : iv.name}</div><p>{m.content}</p></div>
          ))}
        </div>
      )}
    </section>
  );
}

export default function InterviewsTab({ inc, reload }) {
  const [adding, setAdding] = useState(null);
  const locked = inc.status === "published";
  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <p className="hint" style={{ maxWidth: "70ch" }}>Each person gets a private link to a short chat. Questions are written from the logs, the diff, and what colleagues have already said.</p>
        {!locked && <Button onClick={() => setAdding("")}>Add person</Button>}
      </div>
      {inc.interviews.map((iv) => <Card key={iv.id} iv={iv} onChange={reload} onInvite={setAdding} locked={locked} />)}
      {adding !== null && <AddPerson incidentId={inc.id} initial={adding} onClose={() => setAdding(null)} onDone={() => { setAdding(null); reload(); }} />}
    </div>
  );
}
