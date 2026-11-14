from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Interview
from app.schemas import ReplyIn, respond_view
from app.security import require_admin
from app.services import integrations, interviewer, pipeline
from app.services.llm import LLMError

# Public: reached only through an unguessable per-person token.
public = APIRouter(prefix="/api/respond")
# Operator actions on a single interview.
admin = APIRouter(prefix="/api/interviews", dependencies=[Depends(require_admin)])


def _by_token(db: Session, token: str) -> Interview:
    iv = db.scalar(select(Interview).where(Interview.token == token))
    if iv is None:
        raise HTTPException(404, "This interview link is not valid.")
    return iv


@public.get("/{token}")
def view(token: str, db: Session = Depends(get_db)):
    return respond_view(_by_token(db, token))


@public.post("/{token}/messages")
def reply(token: str, body: ReplyIn, background: BackgroundTasks, db: Session = Depends(get_db)):
    iv = _by_token(db, token)
    if iv.status in ("completed", "skipped"):
        raise HTTPException(409, "This interview is closed.")
    if not iv.messages:
        raise HTTPException(409, "This interview is not ready yet. Try again in a moment.")
    try:
        done = interviewer.process_reply(db, iv, body.content.strip())
    except LLMError:
        raise HTTPException(502, "The interviewer is unavailable right now. Your message was not sent, so please try again.")
    if done and pipeline.finish_check(db, iv.incident):
        background.add_task(pipeline.compile_report_task, iv.incident_id)
    return respond_view(iv)


def _admin_get(db: Session, interview_id: str) -> Interview:
    iv = db.get(Interview, interview_id)
    if iv is None:
        raise HTTPException(404, "Interview not found.")
    return iv


@admin.post("/{interview_id}/skip")
def skip(interview_id: str, background: BackgroundTasks, db: Session = Depends(get_db)):
    iv = _admin_get(db, interview_id)
    if iv.status in ("completed", "skipped"):
        raise HTTPException(409, "This interview is already closed.")
    iv.status = "skipped"
    pipeline.log_event(db, iv.incident_id, "interview", f"Interview with {iv.name} was skipped.")
    db.commit()
    if pipeline.finish_check(db, iv.incident):
        background.add_task(pipeline.compile_report_task, iv.incident_id)
    return {"ok": True}


@admin.post("/{interview_id}/remind")
def remind(interview_id: str, db: Session = Depends(get_db)):
    iv = _admin_get(db, interview_id)
    if not get_settings().slack_webhook_url:
        raise HTTPException(400, "Slack is not configured. Copy the interview link and send it directly.")
    link = f"{get_settings().app_base_url.rstrip('/')}/respond/{iv.token}"
    if not integrations.post_slack(f"Reminder for {iv.handle or iv.name}: a few questions are waiting about {iv.incident.title}. {link}"):
        raise HTTPException(502, "Slack did not accept the message. Check SLACK_WEBHOOK_URL.")
    pipeline.log_event(db, iv.incident_id, "invite", f"Reminder sent to {iv.name} on Slack.")
    db.commit()
    return {"ok": True}
