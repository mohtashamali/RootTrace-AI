from datetime import timezone

from pydantic import BaseModel, Field

from app.config import get_settings


# ---- request models ---------------------------------------------------------
class ParticipantIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(default="", max_length=120)
    handle: str = Field(default="", max_length=120)


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    repo: str = Field(default="", max_length=200)
    branch: str = Field(default="", max_length=200)
    commit_sha: str = Field(default="", max_length=64)
    commit_message: str = Field(default="", max_length=5000)
    workflow: str = Field(default="", max_length=200)
    logs: str = Field(min_length=10, max_length=200_000)
    diff: str = Field(default="", max_length=200_000)
    participants: list[ParticipantIn] = Field(min_length=1, max_length=8)


class SampleCreate(BaseModel):
    scenario_key: str


class ReplyIn(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


# ---- serializers ------------------------------------------------------------
def iso(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:  # SQLite returns naive datetimes; everything is stored as UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def message_out(m):
    return {"id": m.id, "role": m.role, "kind": m.kind, "content": m.content, "created_at": iso(m.created_at)}


def asked(iv) -> int:
    return sum(1 for m in iv.messages if m.kind == "question")


def interview_out(iv):
    base = get_settings().app_base_url.rstrip("/")
    return {
        "id": iv.id, "name": iv.name, "role": iv.role, "handle": iv.handle, "status": iv.status,
        "max_questions": iv.max_questions, "asked": asked(iv), "referral": iv.referral,
        "invite_url": f"{base}/respond/{iv.token}",
        "created_at": iso(iv.created_at), "completed_at": iso(iv.completed_at),
        "messages": [message_out(m) for m in iv.messages],
    }


def incident_summary(inc):
    return {
        "id": inc.id, "title": inc.title, "repo": inc.repo, "branch": inc.branch, "commit_sha": inc.commit_sha,
        "status": inc.status, "severity": inc.severity, "source": inc.source, "created_at": iso(inc.created_at),
        "interviews_total": len(inc.interviews),
        "interviews_done": sum(1 for i in inc.interviews if i.status in ("completed", "skipped")),
    }


def incident_detail(inc, usage):
    return {
        **incident_summary(inc),
        "commit_message": inc.commit_message, "workflow": inc.workflow, "run_url": inc.run_url,
        "summary": inc.summary, "logs": inc.logs, "diff": inc.diff, "hypotheses": inc.hypotheses,
        "report": inc.report, "error": inc.error,
        "analyzed_at": iso(inc.analyzed_at), "report_at": iso(inc.report_at), "published_at": iso(inc.published_at),
        "interviews": [interview_out(i) for i in inc.interviews],
        "events": [{"id": e.id, "kind": e.kind, "text": e.text, "created_at": iso(e.created_at)} for e in inc.events],
        "usage": usage,
        "can_simulate": bool(inc.scenario_key) and inc.status == "interviewing",
    }


def respond_view(iv):
    inc = iv.incident
    return {
        "participant": {"name": iv.name, "role": iv.role},
        "status": iv.status, "max_questions": iv.max_questions, "asked": asked(iv),
        "messages": [message_out(m) for m in iv.messages],
        "incident": {
            "title": inc.title, "repo": inc.repo, "branch": inc.branch, "commit_sha": inc.commit_sha,
            "workflow": inc.workflow, "summary": inc.summary, "opened_at": iso(inc.created_at),
        },
    }
