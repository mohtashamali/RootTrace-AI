import json

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Incident
from app.security import verify_github_signature
from app.services import pipeline

router = APIRouter(prefix="/api/webhooks")


@router.post("/github")
async def github(request: Request, background: BackgroundTasks, db: Session = Depends(get_db),
                 x_github_event: str = Header(default=""), x_hub_signature_256: str = Header(default="")):
    secret = get_settings().github_webhook_secret
    if not secret:
        raise HTTPException(503, "GITHUB_WEBHOOK_SECRET is not configured.")
    body = await request.body()
    if not verify_github_signature(body, x_hub_signature_256, secret):
        raise HTTPException(401, "Invalid signature.")
    if x_github_event == "ping":
        return {"ok": True}
    if x_github_event != "workflow_run":
        return {"ignored": x_github_event}

    payload = json.loads(body)
    run = payload.get("workflow_run") or {}
    if payload.get("action") != "completed" or run.get("conclusion") != "failure":
        return {"ignored": "not a failed run"}

    external_id = f"gh-{run.get('id')}-{run.get('run_attempt', 1)}"
    existing = db.scalar(select(Incident).where(Incident.external_id == external_id))
    if existing:
        return {"duplicate": existing.id}

    repo = payload.get("repository", {}).get("full_name", "")
    commit = run.get("head_commit") or {}
    author = (commit.get("author") or {}).get("name") or ""
    actor = (run.get("triggering_actor") or run.get("actor") or {}).get("login") or ""
    people, seen = [], set()
    for name, role, handle in [(author, "Commit author", ""), (actor, "Triggered the run", f"@{actor}")]:
        if name and name.lower() not in seen:
            seen.add(name.lower())
            people.append({"name": name, "role": role, "handle": handle})
    if not people:
        owner = payload.get("repository", {}).get("owner", {}).get("login", "Repository owner")
        people = [{"name": owner, "role": "Repository owner", "handle": f"@{owner}"}]

    inc = pipeline.create_incident(
        db, source="github", external_id=external_id, participants=people, repo=repo,
        title=f"{run.get('name', 'Workflow')} failed on {run.get('head_branch', 'unknown branch')}",
        branch=run.get("head_branch", ""), commit_sha=(run.get("head_sha") or "")[:7],
        commit_message=commit.get("message", ""), workflow=run.get("name", ""), run_url=run.get("html_url", ""),
        meta={"run_id": run.get("id")},
    )
    background.add_task(pipeline.run_pipeline, inc.id)
    return {"incident": inc.id}
