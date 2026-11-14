import { useEffect, useRef, useState } from "react";
import { useToast } from "./toast";

export const STATUS = {
  analyzing: "Analyzing", interviewing: "Interviewing", compiling: "Writing report",
  draft: "Draft ready", published: "Published", error: "Needs attention",
};
export const IV_STATUS = { invited: "Invited", active: "In progress", completed: "Completed", skipped: "Skipped" };

export const Chip = ({ kind, children, plain }) => <span className={`chip chip-${kind}${plain ? " plain" : ""}`}>{children}</span>;
export const StatusChip = ({ status }) => <Chip kind={status}>{STATUS[status] || status}</Chip>;
export const Spinner = ({ small }) => <span className={`spinner${small ? " small" : ""}`} role="status" aria-label="Loading" />;

export function Button({ variant = "secondary", busy, children, className = "", ...rest }) {
  return (
    <button className={`btn btn-${variant} ${className}`} disabled={busy || rest.disabled} {...rest}>
      {busy && <Spinner small />}
      {children}
    </button>
  );
}

export function Modal({ title, onClose, children, footer, wide }) {
  const ref = useRef(null);
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    ref.current?.focus();
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="scrim" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal${wide ? " wide" : ""}`} role="dialog" aria-modal="true" aria-label={title} tabIndex={-1} ref={ref}>
        <header className="modal-head"><h2>{title}</h2><button className="icon-btn" onClick={onClose} aria-label="Close">×</button></header>
        <div className="modal-body">{children}</div>
        {footer && <footer className="modal-foot">{footer}</footer>}
      </div>
    </div>
  );
}

export function CopyButton({ text, label = "Copy link" }) {
  const toast = useToast();
  const [done, setDone] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      setTimeout(() => setDone(false), 1600);
    } catch {
      toast("Copy failed. Select the text and copy it manually.", "error");
    }
  };
  return <Button onClick={copy}>{done ? "Copied" : label}</Button>;
}

export function ConfidenceBar({ value, status }) {
  return (
    <div className={`bar bar-${status || "open"}`} role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(value * 100)}>
      <span style={{ width: `${Math.round(value * 100)}%` }} />
    </div>
  );
}

export const Empty = ({ title, children }) => (
  <div className="empty"><h3>{title}</h3><p>{children}</p></div>
);

export function timeAgo(iso) {
  if (!iso) return "Not yet";
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export const fmtTime = (iso) =>
  iso ? new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "";
export const pct = (v) => `${Math.round(v * 100)}%`;
