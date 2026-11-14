"""Single entry point for every Groq call: JSON mode, schema validation, retries, usage tracking."""
import json
import logging
import time

from groq import AuthenticationError, Groq, GroqError, RateLimitError
from pydantic import BaseModel, ValidationError

from app.config import get_settings
from app.db import session_scope
from app.models import LlmCall

log = logging.getLogger(__name__)
_client: Groq | None = None


class LLMError(Exception):
    """Raised with a message that is safe to show to an operator."""


def _get_client() -> Groq:
    global _client
    s = get_settings()
    if not s.groq_api_key:
        raise LLMError("GROQ_API_KEY is not set on the server. Add it to the environment and restart.")
    if _client is None:
        _client = Groq(api_key=s.groq_api_key, timeout=s.groq_timeout, max_retries=2)
    return _client


def _record(incident_id, purpose, model, usage, started, ok):
    try:
        with session_scope() as db:
            db.add(LlmCall(
                incident_id=incident_id, purpose=purpose, model=model, ok=ok,
                prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
                latency_ms=int((time.monotonic() - started) * 1000),
            ))
    except Exception:  # metrics must never break the request
        log.exception("could not record llm call")


def complete_json(*, purpose: str, system: str, user: str, schema: type[BaseModel] | None = None,
                  incident_id: str | None = None, temperature: float = 0.2, max_tokens: int = 1500):
    s = get_settings()
    client = _get_client()
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    for _ in range(2):
        started = time.monotonic()
        try:
            resp = client.chat.completions.create(
                model=s.groq_model, messages=messages, temperature=temperature,
                max_tokens=max_tokens, response_format={"type": "json_object"},
            )
        except AuthenticationError as e:
            _record(incident_id, purpose, s.groq_model, None, started, False)
            raise LLMError("Groq rejected the API key. Check GROQ_API_KEY.") from e
        except RateLimitError as e:
            _record(incident_id, purpose, s.groq_model, None, started, False)
            raise LLMError("Groq rate limit reached. Wait a moment and try again.") from e
        except GroqError as e:
            _record(incident_id, purpose, s.groq_model, None, started, False)
            raise LLMError(f"Groq request failed ({e.__class__.__name__}). Check connectivity and the model name.") from e

        text = resp.choices[0].message.content or "{}"
        try:
            data = json.loads(text)
            result = schema.model_validate(data) if schema else data
            _record(incident_id, purpose, s.groq_model, resp.usage, started, True)
            return result
        except (json.JSONDecodeError, ValidationError):
            _record(incident_id, purpose, s.groq_model, resp.usage, started, False)
            messages += [
                {"role": "assistant", "content": text},
                {"role": "user", "content": "That reply did not match the required JSON schema. Return only the corrected JSON object."},
            ]
    raise LLMError("The model returned an unusable response twice. Try again.")
