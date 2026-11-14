"""Demo mode: LLM-played engineers answer interview questions so the full flow can be shown end to end."""
import logging

from app.config import get_settings
from app.db import session_scope
from app.models import Incident, Interview
from app.scenarios import persona_for
from app.services import interviewer, llm, pipeline
from app.services.llm import LLMError

log = logging.getLogger(__name__)

SYSTEM = """You role-play an engineer being interviewed about a failed build. Stay in character.
Reveal only what the latest question asks about, in your own words and as a short chat message of one to three sentences.
If you would not know something, say so. Never mention being an AI or role-playing.
Reply with one JSON object: {"reply": "..."}"""


def simulate_reply(inc: Incident, iv: Interview) -> str:
    knows, persona = persona_for(inc.scenario_key, iv.name)
    transcript = "\n".join(f"{'Interviewer' if m.role == 'agent' else iv.name}: {m.content}" for m in iv.messages)
    user = (f"You are {iv.name}, {iv.role}.\nWhat you know (private): {knows}\nHow you behave: {persona}\n\n"
            f"Conversation so far:\n{transcript}\n\nWrite your next reply to the last question.")
    out = llm.complete_json(purpose="simulation", incident_id=inc.id, system=SYSTEM, user=user, temperature=0.6, max_tokens=250)
    return str(out.get("reply", "")).strip() or "I'm not sure."


def run_simulation_task(incident_id: str) -> None:
    with session_scope() as db:
        ids = [i.id for i in db.get(Incident, incident_id).interviews if i.status in ("invited", "active")]
    for iv_id in ids:
        for _ in range(get_settings().max_questions + 2):
            with session_scope() as db:
                iv = db.get(Interview, iv_id)
                if iv.status in ("completed", "skipped"):
                    break
                try:
                    done = interviewer.process_reply(db, iv, simulate_reply(iv.incident, iv))
                except LLMError as e:
                    pipeline.log_event(db, iv.incident_id, "error", f"Simulation stopped: {e}")
                    return
            if done:
                break
    with session_scope() as db:
        ready = pipeline.finish_check(db, db.get(Incident, incident_id))
    if ready:
        pipeline.compile_report_task(incident_id)
