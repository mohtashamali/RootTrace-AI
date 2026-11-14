"""Orchestration: create incident -> analyze -> open interviews -> compile report."""
import logging
import secrets

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import session_scope
from app.models import Event, Incident, Interview, utcnow
from app.services import analysis, integrations, interviewer
from app.services.llm import LLMError
from app.services.redaction import looks_like_injection, redact

log = logging.getLogger(__name__)
SOURCES = {"github": "GitHub Actions", "manual": "manual entry", "sample": "a sample scenario"}
GENERIC_ERROR = "Something went wrong while processing this incident. Check the server logs, then retry."


def log_event(db: Session, incident_id: str, kind: str, text: str) -> None:
    db.add(Event(incident_id=incident_id, kind=kind, text=text))


def _new_interview(p: dict) -> Interview:
    return Interview(name=p["name"], role=p.get("role", ""), handle=p.get("handle", ""),
                     token=secrets.token_urlsafe(18), max_questions=get_settings().max_questions)


def create_incident(db: Session, *, title, participants, source, logs="", diff="", repo="", branch="",
                    commit_sha="", commit_message="", workflow="", run_url="", scenario_key=None,
                    external_id=None, meta=None) -> Incident:
    inc = Incident(
        title=title, repo=repo, branch=branch, commit_sha=commit_sha, workflow=workflow, run_url=run_url,
        commit_message=redact(commit_message), logs=redact(logs), diff=redact(diff),
        source=source, scenario_key=scenario_key, external_id=external_id, meta=meta or {},
        interviews=[_new_interview(p) for p in participants],
    )
    db.add(inc)
    db.flush()
    log_event(db, inc.id, "failure", f"Failure received from {SOURCES.get(source, source)}.")
    db.commit()
    return inc


def open_interview(db: Session, inc: Incident, iv: Interview) -> None:
    step = interviewer.next_step(inc, iv, None)
    interviewer.apply_step(db, inc, iv, None, step)
    sent = integrations.post_slack(
        f"Retrace: {iv.handle or iv.name}, could you answer a few quick questions about the failed "
        f"{inc.workflow or 'build'} in {inc.repo or 'your repo'}? {get_settings().app_base_url.rstrip('/')}/respond/{iv.token}"
    )
    log_event(db, inc.id, "invite", f"Interview opened for {iv.name}" + (" and invite posted to Slack." if sent else "."))
    db.commit()


def run_pipeline(incident_id: str) -> None:
    with session_scope() as db:
        inc = db.get(Incident, incident_id)
        if inc is None:
            return
        try:
            inc.status, inc.error = "analyzing", None
            if inc.source == "github" and not inc.logs:
                logs, diff = integrations.fetch_github_context(inc.repo, str(inc.meta.get("run_id", "")), inc.commit_sha)
                inc.logs = redact(logs) or ("(Build logs could not be retrieved. Set GITHUB_TOKEN with read access to "
                                            "Actions and Contents so Retrace can fetch them.)")
                inc.diff = redact(diff)
            if any(looks_like_injection(t) for t in (inc.logs, inc.diff, inc.commit_message)):
                log_event(db, inc.id, "security", "Instruction-like text was found in build output or commit data. "
                          "It is treated as data and is never followed.")
            result = analysis.analyze_failure(inc)
            inc.summary, inc.severity = result.summary, result.severity
            inc.hypotheses = [h.model_dump() for h in result.hypotheses]
            inc.analyzed_at, inc.status = utcnow(), "interviewing"
            log_event(db, inc.id, "analysis", f"Analysis complete: {len(result.hypotheses)} hypotheses, severity {result.severity}.")
            db.commit()
            for iv in list(inc.interviews):
                if iv.messages:
                    continue
                try:
                    open_interview(db, inc, iv)
                except LLMError as e:
                    db.rollback()
                    log_event(db, inc.id, "error", f"Could not open the interview with {iv.name}: {e}")
                    db.commit()
        except LLMError as e:
            db.rollback()
            inc = db.get(Incident, incident_id)
            inc.status, inc.error = "error", str(e)
            log_event(db, inc.id, "error", str(e))
        except Exception:
            log.exception("pipeline failed for incident %s", incident_id)
            db.rollback()
            inc = db.get(Incident, incident_id)
            inc.status, inc.error = "error", GENERIC_ERROR


def open_interview_task(interview_id: str) -> None:
    with session_scope() as db:
        iv = db.get(Interview, interview_id)
        if iv is None or iv.messages:
            return
        try:
            open_interview(db, iv.incident, iv)
        except LLMError as e:
            db.rollback()
            log_event(db, iv.incident_id, "error", f"Could not open the interview with {iv.name}: {e}")


def finish_check(db: Session, inc: Incident) -> bool:
    """True (and status -> compiling) when every interview is closed and a report should be written."""
    if inc.status == "interviewing" and all(i.status in ("completed", "skipped") for i in inc.interviews):
        inc.status = "compiling"
        db.commit()
        return True
    return False


def compile_report_task(incident_id: str) -> None:
    with session_scope() as db:
        inc = db.get(Incident, incident_id)
        if inc is None:
            return
        inc.status, inc.error = "compiling", None
        db.commit()
        try:
            inc.report = analysis.compile_report(inc)
            inc.report_at, inc.status = utcnow(), "draft"
            meta = inc.report["meta"]
            log_event(db, inc.id, "report", f"Draft report written. {meta['evidence_verified']} of {meta['evidence_total']} excerpts matched their source.")
        except LLMError as e:
            db.rollback()
            inc = db.get(Incident, incident_id)
            inc.status, inc.error = "error", str(e)
            log_event(db, inc.id, "error", str(e))
        except Exception:
            log.exception("report failed for incident %s", incident_id)
            db.rollback()
            inc = db.get(Incident, incident_id)
            inc.status, inc.error = "error", GENERIC_ERROR
