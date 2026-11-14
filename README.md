# Retrace



When a build or deployment fails, Retrace reads the logs and the diff, forms hypotheses, interviews the people involved while they still remember, checks what they say against the evidence, and drafts a blameless incident report that a human approves.

The interview step is the point. Logs show what broke. The reason it broke (an assumption, a skipped runbook step, a config copied from the wrong place) usually lives only in someone's head and fades within hours.

```
GitHub webhook / manual / sample
          |
   redact + injection scan
          |
   hypotheses from logs + diff           (Groq)
          |
   one private interview link per person
   adaptive questions, hard budget       (Groq)
          |
   report + evidence ledger              (Groq)
   every quoted excerpt is string-matched against the real logs, diff, or transcript
          |
   human approves -> published (+ Slack)
```

## Run it

Requirements: a Groq API key.

```bash
cp backend/.env.example backend/.env      # set GROQ_API_KEY and ADMIN_ACCESS_KEY

# Option A: Docker (single container, UI served by the API)
APP_BASE_URL=http://localhost:8000 docker compose up --build   # http://localhost:8000

# Option B: local dev (two terminals)
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
python -m uvicorn app.main:app --reload                         # API on :8000
cd frontend && npm install && npm run dev                       # UI on :5173 (proxies /api)
```

Open the app, choose **New incident, Sample failure**, then **Run simulated interviews** to watch the whole flow with LLM-played engineers. Or open an interview link yourself and answer as the engineer.

## Connect GitHub Actions

Settings in the app shows your webhook URL. In the repo: Settings, Webhooks, add the URL, content type `application/json`, secret = `GITHUB_WEBHOOK_SECRET`, event **Workflow runs**. Set `GITHUB_TOKEN` (read access to Actions and Contents) so Retrace can pull failed-job logs and the commit diff. GitHub needs a public HTTPS address, so use a tunnel locally and set `APP_BASE_URL` to it.

## Understand
The problem, in simple words

Imagine you work at a company that builds software. Every day, developers change the code and send it live. Sometimes it breaks. The website crashes, or the update fails.

When that happens, the team has to find out why it broke. But there are two problems:

The computer only shows what broke, not why. The error messages say “database connection failed”, but they don’t say why the developer changed that setting.
People forget fast. The reason is usually only in the developer’s head. After a few days they forget or the details get mixed up. Then the company writes a weak report and the same mistake happens again.
What this project does

It is like a robot detective for broken software.

Step 1: Something breaks. The project notices the failure automatically.

Step 2: The robot reads the clues. It reads the error messages and the code that was changed, then makes guesses. For example: “Maybe someone reduced the database size.”

Step 3: The robot asks the people. It sends each person a link to a small chat page. It asks simple, specific questions, like:

“In the file config.yaml, the number changed from 20 to 5. Was that on purpose?”

Step 4: The robot checks the answers. People can be wrong or forget. So the robot compares what they said with the real error messages. If an answer doesn’t match the evidence, it notes the difference.

Step 5: The robot writes a report. The report has what happened, the real cause, a timeline, and what to fix so it doesn’t happen again. A human reads it and clicks Approve before it is final.

A real-life example

It’s like a car accident:

The police arrive quickly, look at the road, and talk to the drivers while everyone still remembers.
Then they write a clear report.

This project does the same thing for broken software, automatically and within minutes.


## Environment

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY`, `GROQ_MODEL` | All AI calls. Server-side only. |
| `ADMIN_ACCESS_KEY` | Protects the dashboard API. If empty, the API is open (local dev only). |
| `APP_BASE_URL` | Public address used in interview links and Slack messages. |
| `GITHUB_WEBHOOK_SECRET`, `GITHUB_TOKEN` | Webhook verification and log/diff fetching. |
| `SLACK_WEBHOOK_URL` | Optional invites, reminders, publish notices. |
| `MAX_QUESTIONS` | Question budget per interview (default 5). |
| `DATABASE_URL` | SQLite by default; any SQLAlchemy URL works. |

## How trust is handled

- **Evidence ledger.** The model must quote excerpts; the server then checks each one against the source text. Excerpts that are not found are flagged in the UI and the Markdown export.
- **Humans are claims, not facts.** Conflicts between a statement and the logs go under "Where accounts and evidence differ".
- **Prompt injection.** Logs, diffs, commit messages and participant text are fenced as untrusted data, scanned for instruction-like text, and the model is told never to follow them.
- **Redaction.** Tokens, keys, passwords and emails are scrubbed on ingest.
- **Honest confidence.** With no interview answers, root-cause confidence is capped at 60%.
- **Blameless, budgeted, human-approved.** Questions are limited, participants are told an AI is asking, and nothing is published without approval.
- **Failure handling.** If Groq fails mid-interview the participant's message is not stored, so nothing is lost or half-applied.

## Layout

```
backend/app/
  routers/    incidents, interviews (public token + admin), webhooks, system
  services/   llm (Groq wrapper), analysis, interviewer, pipeline, simulator,
              redaction, integrations (GitHub, Slack)
  scenarios.py  sample failures with hidden ground truth for demo mode
backend/tests/  end-to-end flow with the model stubbed
frontend/src/   pages, components, one stylesheet (no UI framework)
```

## Limits and next steps

- Background work runs in-process (FastAPI background tasks). Move to a queue (RQ, Celery) before running multiple workers.
- Delivery is via interview links and a single Slack webhook. Per-user Slack DMs, Teams and email are natural additions, as are GitLab and Jenkins webhooks.
- Simulated engineers are for demos. To measure quality, build a benchmark of scenarios with known root causes and track root-cause accuracy, questions asked, and unsupported claims, with and without interviews.
- Voice interviews are deliberately not included: consent rules vary by jurisdiction and latency makes them fragile.
