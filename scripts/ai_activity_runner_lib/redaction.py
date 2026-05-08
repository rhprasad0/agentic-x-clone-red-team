# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

REDACTION = "[REDACTED]"

_SENSITIVE_KEY = r"(?:api[_-]?key|token|bearer[_-]?token|access[_-]?token|refresh[_-]?token|secret|password|credential)"

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("auth_header", re.compile(r"(?i)authorization\s*[:=]\s*bearer\s+[A-Za-z0-9._\-]+")),
    ("bearer", re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{8,}")),
    ("api_key", re.compile(rf"(?i){_SENSITIVE_KEY}\s*[:=]\s*['\"]?[^\s,'\"]+")),
    ("json_secret", re.compile(rf"(?i)(['\"]){_SENSITIVE_KEY}\1\s*:\s*(['\"])[^'\"]+\2")),
    ("private_url", re.compile(r"https?://(?:10\.\d+\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[0-1])\.\d+\.\d+|192\.168\.\d+\.\d+|localhost|127\.0\.0\.1)(?::\d+)?[^\s]*")),
    ("private_path", re.compile(r"(?:/home/[A-Za-z0-9._-]+|/Users/[A-Za-z0-9._-]+|C:\\\\Users\\\\[A-Za-z0-9._-]+)[^\s]*")),
    ("email", re.compile(r"\b(?![^@\s]+@example\.com\b)[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("phone", re.compile(r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)")),
    ("traceback", re.compile(r"Traceback \(most recent call last\):[\s\S]*", re.MULTILINE)),
    ("env_dump", re.compile(r"(?m)^(?:[A-Z][A-Z0-9_]{2,}=.*\n?){2,}")),
]

_LONG_DOTTED_VALUE_SHAPE = re.compile(
    r"\b[A-Za-z0-9_\-]{24,}\.[A-Za-z0-9_\-]{8,}(?:\.[A-Za-z0-9_\-]{8,})?\b"
)

@dataclass
class RedactionResult:
    text: str
    redacted: bool = False
    sensitive_fields_removed: list[str] = field(default_factory=list)


def redact_text(text: str | None) -> RedactionResult:
    if text is None:
        return RedactionResult("")
    result = str(text)
    removed: list[str] = []
    for label, pattern in _PATTERNS:
        result, n = pattern.subn(REDACTION, result)
        if n:
            removed.append(label)
    result, n = _LONG_DOTTED_VALUE_SHAPE.subn(REDACTION, result)
    if n:
        removed.append("token_like")
    return RedactionResult(result, bool(removed), sorted(set(removed)))


def redact_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in mapping.items():
        lowered = key.lower()
        if any(marker in lowered for marker in ("token", "secret", "password", "api_key", "authorization", "credential")):
            redacted[key] = REDACTION
        elif isinstance(value, dict):
            redacted[key] = redact_mapping(value)
        elif isinstance(value, list):
            redacted[key] = [redact_mapping(v) if isinstance(v, dict) else redact_text(str(v)).text for v in value]
        elif isinstance(value, str):
            redacted[key] = redact_text(value).text
        else:
            redacted[key] = value
    return redacted


def safe_summary(text: str | None, max_chars: int = 160) -> str:
    redacted = redact_text(text or "").text.replace("\n", " ").strip()
    if len(redacted) > max_chars:
        return redacted[: max_chars - 1].rstrip() + "…"
    return redacted

@dataclass
class SocialTextResult:
    ok: bool
    text: str
    redaction: RedactionResult
    issue_class: str | None = None


def validate_generated_social_text(text: str | None, *, max_chars: int = 280) -> SocialTextResult:
    raw = (text or "").strip()
    redaction = redact_text(raw)
    if not raw:
        return SocialTextResult(False, "", redaction, "empty_text")
    if redaction.redacted:
        return SocialTextResult(False, safe_summary(raw, max_chars), redaction, "safety_redaction_applied")
    if len(raw) > max_chars:
        raw = raw[:max_chars].rstrip()
    return SocialTextResult(True, raw, redaction)
