import { useState } from "react";
import { api } from "../api";
import { useLoad } from "../hooks";
import { Button, Chip, CopyButton, Spinner } from "../components/ui";
import { useToast } from "../components/toast";

const State = ({ ok, yes = "Configured", no = "Not configured" }) => <Chip kind={ok ? "published" : "invited"}>{ok ? yes : no}</Chip>;

export default function Settings() {
  const toast = useToast();
  const { data: s, error, loading } = useLoad(() => api("/settings"), []);
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState(null);

  const test = async () => {
    setTesting(true);
    setResult(null);
    try { setResult({ ok: true, ...(await api("/settings/test-groq", { method: "POST" })) }); }
    catch (e) { setResult({ ok: false, message: e.message }); toast(e.message, "error"); }
    finally { setTesting(false); }
  };

  if (loading) return <div className="empty"><Spinner /></div>;
  if (!s) return <p className="form-error">{error}</p>;

  return (
    <>
      <div className="page-head"><div><h1>Settings</h1><p className="sub">Connections are set with environment variables on the server, so secrets never reach the browser.</p></div></div>
      <div className="panel">
        <div className="setting">
          <div><h3>Groq</h3><p className="desc">Powers analysis, interviews and reports.</p></div>
          <div className="stack">
            <div className="kv"><State ok={s.groq.configured} no="GROQ_API_KEY missing" /><code>{s.groq.model}</code></div>
            <div className="kv">
              <Button busy={testing} disabled={!s.groq.configured} onClick={test}>Test connection</Button>
              {result?.ok && <span className="check ok">Connected, {result.latency_ms} ms</span>}
              {result && !result.ok && <span className="check no">{result.message}</span>}
            </div>
          </div>
        </div>

        <div className="setting">
          <div><h3>GitHub Actions</h3><p className="desc">Opens an incident whenever a workflow run fails.</p></div>
          <div className="stack">
            <div className="kv"><State ok={s.github.webhook_configured} yes="Webhook secret set" no="GITHUB_WEBHOOK_SECRET missing" /><State ok={s.github.token_configured} yes="Token set" no="GITHUB_TOKEN missing" /></div>
            <div className="kv"><code>{s.github.webhook_url}</code><CopyButton text={s.github.webhook_url} label="Copy URL" /></div>
            <ol className="steps">
              <li>In the repository, open Settings, then Webhooks, then Add webhook.</li>
              <li>Paste the URL above, choose content type application/json, and enter the same secret as GITHUB_WEBHOOK_SECRET.</li>
              <li>Select individual events and tick Workflow runs.</li>
              <li>Set GITHUB_TOKEN (read access to Actions and Contents) so Retrace can fetch logs and diffs.</li>
            </ol>
            {!s.base_url.startsWith("https") && <p className="hint">GitHub can only reach a public HTTPS address. For local testing, expose this server with a tunnel and set APP_BASE_URL to that address.</p>}
          </div>
        </div>

        <div className="setting">
          <div><h3>Slack</h3><p className="desc">Posts interview invites, reminders and published reports.</p></div>
          <div className="stack">
            <State ok={s.slack.configured} no="SLACK_WEBHOOK_URL missing" />
            <p className="hint">Without Slack, copy each person's interview link from the Interviews tab and send it yourself.</p>
          </div>
        </div>

        <div className="setting">
          <div><h3>Access and limits</h3><p className="desc">Dashboard protection and interview length.</p></div>
          <div className="stack">
            <div className="kv"><State ok={s.auth_enabled} yes="Access key required" no="No access key set" /><span className="num">Up to {s.max_questions} questions per interview</span></div>
            {!s.auth_enabled && <p className="hint">Set ADMIN_ACCESS_KEY before exposing this server to a network.</p>}
          </div>
        </div>
      </div>
    </>
  );
}
