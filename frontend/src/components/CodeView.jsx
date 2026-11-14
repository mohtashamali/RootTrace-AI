const HIT = /\b(error|fatal|exception|failed|failure|timeout|timed out|denied|unauthorized|503|500|401)\b/i;
const MAX = 500;

function Lines({ lines, cls }) {
  return (
    <pre className="code" tabIndex={0}>
      {lines.slice(0, MAX).map((l, i) => (
        <div key={i} className={`ln ${cls(l)}`}><span className="no">{i + 1}</span><span className="tx">{l || " "}</span></div>
      ))}
      {lines.length > MAX && <div className="ln"><span className="no" /><span className="tx muted">{lines.length - MAX} more lines not shown</span></div>}
    </pre>
  );
}

export const LogView = ({ text }) => <Lines lines={text.split("\n")} cls={(l) => (HIT.test(l) ? "hit" : "")} />;

export const DiffView = ({ text }) => (
  <Lines lines={text.split("\n")} cls={(l) =>
    l.startsWith("diff --git") ? "file" : l.startsWith("@@") ? "hunk" :
    l.startsWith("+") && !l.startsWith("+++") ? "add" : l.startsWith("-") && !l.startsWith("---") ? "del" : ""} />
);
