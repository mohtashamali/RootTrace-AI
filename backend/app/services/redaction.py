"""Scrubs secrets/PII before text reaches a model, and fences untrusted text inside prompts."""
import re

_PATTERNS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "[private key]"),
    (re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "[aws key]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "[github token]"),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"), "[slack token]"),
    (re.compile(r"\b(?:gsk|sk)[-_][A-Za-z0-9_-]{20,}\b"), "[api key]"),
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{16,}"), r"\1[token]"),
    (re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key|token)(\s*[=:]\s*)(\"[^\"]+\"|'[^']+'|\S+)"), r"\1\2[redacted]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[email]"),
]

_INJECTION = re.compile(
    r"(?i)((ignore|disregard|forget)\b.{0,40}\b(previous|prior|above|earlier|all)\b.{0,30}\b(instructions?|prompts?|rules?))"
    r"|\bsystem prompt\b|\byou are now\b|\bdo not (report|mention|flag)\b"
)


def redact(text: str) -> str:
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text or "")
    return text


def looks_like_injection(text: str) -> bool:
    return bool(_INJECTION.search(text or ""))


def fence(label: str, text: str, limit: int = 8000, tail: bool = False) -> str:
    """Wrap untrusted content so prompts can tell data from instructions."""
    body = redact(text or "")
    body = body[-limit:] if tail else body[:limit]
    body = body.replace("</untrusted", "<\\/untrusted")
    return f'<untrusted source="{label}">\n{body}\n</untrusted>'
