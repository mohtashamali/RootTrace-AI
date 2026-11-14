from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.db import get_db
from app.models import Incident, LlmCall, utcnow
from app.scenarios import SCENARIOS
from app.schemas import IncidentCreate, ParticipantIn, SampleCreate, incident_detail, incident_summary
from app.security import require_admin
from app.services import analysis, integrations, pipeline, simulator

router = APIRouter(prefix="/api/incidents", dependencies=[Depends(require_admin)])


def _get(db: Session, incident_id: str) -> Incident:
    inc = db.get(Incident, incident_id)
    if inc is None:
        raise HTTPException(404, "Incident not found.")
    return inc


def _detail(db: Session, inc: Incident) -> dict:
    calls, pt, ct, avg = db.execute(
        select(func.count(LlmCall.id), func.coalesce(func.sum(LlmCall.prompt_tokens), 0),
               func.coalesce(func.sum(LlmCall.completion_tokens), 0), func.coalesce(func.avg(LlmCall.latency_ms), 0))
        .where(LlmCall.incident_id == inc.id)
    ).one()
    usage = {"calls": calls, "prompt_tokens": int(pt), "completion_tokens": int(ct), "avg_latency_ms": int(avg)}
    return incident_detail(inc, usage)


@router.get("")
def list_incidents(status: str | None = None, q: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Incident).options(selectinload(Incident.interviews)).order_by(Incident.created_at.desc())
    if status:
        stmt = stmt.where(Incident.status == status)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Incident.title.ilike(like), Incident.repo.ilike(like), Incident.commit_sha.ilike(like)))
    return [incident_summary(i) for i in db.scalars(stmt).all()]


@router.post("", status_code=201)
def create_manual(body: IncidentCreate, background: BackgroundTasks, db: Session = Depends(get_db)):
    inc = pipeline.create_incident(
        db, source="manual", participants=[p.model_dump() for p in body.participants],
        **body.model_dump(exclude={"participants"}),
    )
    background.add_task(pipeline.run_pipeline, inc.id)
    return incident_summary(inc)


@router.post("/sample", status_code=201)
def create_sample(body: SampleCreate, background: BackgroundTasks, db: Session = Depends(get_db)):
    sc = SCENARIOS.get(body.scenario_key)
    if sc is None:
        raise HTTPException(404, "Unknown sample scenario.")
    inc = pipeline.create_incident(
        db, source="sample", scenario_key=body.scenario_key,
        participants=[{k: p[k] for k in ("name", "role", "handle")} for p in sc["participants"]],
        **{k: sc[k] for k in ("title", "repo", "branch", "commit_sha", "commit_message", "workflow", "logs", "diff")},
    )
    background.add_task(pipeline.run_pipeline, inc.id)
    return incident_summary(inc)


@router.get("/{incident_id}")
def detail(incident_id: str, db: Session = Depends(get_db)):
    return _detail(db, _get(db, incident_id))


@router.delete("/{incident_id}", status_code=204)
def delete(incident_id: str, db: Session = Depends(get_db)):
    db.delete(_get(db, incident_id))
    db.commit()


@router.post("/{incident_id}/participants", status_code=201)
def add_participant(incident_id: str, body: ParticipantIn, background: BackgroundTasks, db: Session = Depends(get_db)):
    inc = _get(db, incident_id)
    if inc.status not in ("interviewing", "draft"):
        raise HTTPException(409, "People can be added once the analysis is finished and before the report is published.")
    iv = pipeline._new_interview(body.model_dump())
    inc.interviews.append(iv)
    if inc.status == "draft":
        inc.status = "interviewing"
    pipeline.log_event(db, inc.id, "invite", f"{iv.name} was added to the investigation.")
    db.commit()
    background.add_task(pipeline.open_interview_task, iv.id)
    return _detail(db, inc)


@router.post("/{incident_id}/report")
def write_report(incident_id: str, background: BackgroundTasks, db: Session = Depends(get_db)):
    inc = _get(db, incident_id)
    if inc.status == "published":
        raise HTTPException(409, "A published report cannot be regenerated.")
    if not inc.hypotheses:
        raise HTTPException(409, "The analysis has not finished yet.")
    if inc.status == "compiling":
        raise HTTPException(409, "A report is already being written.")
    inc.status, inc.error = "compiling", None
    db.commit()
    background.add_task(pipeline.compile_report_task, inc.id)
    return _detail(db, inc)


@router.post("/{incident_id}/retry")
def retry(incident_id: str, background: BackgroundTasks, db: Session = Depends(get_db)):
    inc = _get(db, incident_id)
    if inc.status != "error":
        raise HTTPException(409, "Only incidents that need attention can be retried.")
    if inc.hypotheses:
        inc.status, inc.error = "compiling", None
        background.add_task(pipeline.compile_report_task, inc.id)
    else:
        inc.status, inc.error = "analyzing", None
        background.add_task(pipeline.run_pipeline, inc.id)
    db.commit()
    return _detail(db, inc)


@router.post("/{incident_id}/publish")
def publish(incident_id: str, db: Session = Depends(get_db)):
    inc = _get(db, incident_id)
    if inc.status != "draft" or not inc.report:
        raise HTTPException(409, "Only a draft report can be published.")
    inc.status, inc.published_at = "published", utcnow()
    pipeline.log_event(db, inc.id, "publish", "Report approved and published.")
    db.commit()
    base = get_settings().app_base_url.rstrip("/")
    integrations.post_slack(f"Incident report published: {inc.title}\nRoot cause: {inc.report['root_cause']['statement']}\n{base}/incidents/{inc.id}")
    return _detail(db, inc)


@router.get("/{incident_id}/report.md")
def export_markdown(incident_id: str, db: Session = Depends(get_db)):
    inc = _get(db, incident_id)
    if not inc.report:
        raise HTTPException(404, "No report has been written yet.")
    return Response(analysis.report_to_markdown(inc), media_type="text/markdown",
                    headers={"Content-Disposition": f'attachment; filename="incident-{inc.id}.md"'})


@router.post("/{incident_id}/simulate")
def simulate(incident_id: str, background: BackgroundTasks, db: Session = Depends(get_db)):
    inc = _get(db, incident_id)
    if not inc.scenario_key:
        raise HTTPException(409, "Simulated responders are only available for sample scenarios.")
    if inc.status != "interviewing":
        raise HTTPException(409, "Interviews are not open.")
    pipeline.log_event(db, inc.id, "simulation", "Simulated engineers are answering the interviews (demo mode).")
    db.commit()
    background.add_task(simulator.run_simulation_task, inc.id)
    return _detail(db, inc)
