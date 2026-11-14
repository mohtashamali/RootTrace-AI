import time
from statistics import mean, median

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Incident, Interview, LlmCall
from app.scenarios import public_list
from app.security import require_admin
from app.services import llm

router = APIRouter(prefix="/api")
admin = [Depends(require_admin)]


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/auth/status")
def auth_status():
    return {"required": bool(get_settings().admin_access_key)}


@router.post("/auth/verify", dependencies=admin)
def auth_verify():
    return {"ok": True}


@router.get("/scenarios", dependencies=admin)
def scenarios():
    return public_list()


@router.get("/settings", dependencies=admin)
def settings():
    s = get_settings()
    base = s.app_base_url.rstrip("/")
    return {
        "groq": {"configured": bool(s.groq_api_key), "model": s.groq_model},
        "github": {"webhook_configured": bool(s.github_webhook_secret), "token_configured": bool(s.github_token),
                   "webhook_url": f"{base}/api/webhooks/github"},
        "slack": {"configured": bool(s.slack_webhook_url)},
        "auth_enabled": bool(s.admin_access_key),
        "max_questions": s.max_questions,
        "base_url": base,
    }


@router.post("/settings/test-groq", dependencies=admin)
def test_groq():
    started = time.monotonic()
    llm.complete_json(purpose="connection_test", system='Reply with the JSON object {"ok": true}.',
                      user="ping", max_tokens=20, temperature=0)
    return {"ok": True, "model": get_settings().groq_model, "latency_ms": int((time.monotonic() - started) * 1000)}


@router.get("/stats", dependencies=admin)
def stats(db: Session = Depends(get_db)):
    incs = db.scalars(select(Incident)).all()
    ivs = db.scalars(select(Interview)).all()

    def aware(dt):
        return dt.replace(tzinfo=None) if dt.tzinfo else dt

    minutes = [(aware(i.report_at) - aware(i.created_at)).total_seconds() / 60 for i in incs if i.report_at]
    questions = [sum(1 for m in iv.messages if m.kind == "question") for iv in ivs if iv.status == "completed"]
    tokens = db.scalar(select(func.coalesce(func.sum(LlmCall.prompt_tokens + LlmCall.completion_tokens), 0)))
    return {
        "total": len(incs),
        "open": sum(1 for i in incs if i.status != "published"),
        "waiting_on_people": sum(1 for iv in ivs if iv.status in ("invited", "active") and iv.incident.status == "interviewing"),
        "median_minutes_to_report": round(median(minutes), 1) if minutes else None,
        "avg_questions": round(mean(questions), 1) if questions else None,
        "tokens": int(tokens or 0),
    }
