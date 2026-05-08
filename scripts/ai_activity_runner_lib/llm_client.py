# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .config import AIActivityConfig
from .personas import style_prompt
from .redaction import redact_text, safe_summary, validate_generated_social_text


class LLMBridgeError(RuntimeError):
    """Raised when the configured compatible LLM bridge fails."""

ALLOWED_INTENTS = {"root_post", "reply", "quote", "like", "repost", "follow", "reply_continue", "like_end", "quote_end", "follow_end", "silence", "silence_end"}

@dataclass
class ActionProposal:
    intent: str
    candidate_ref: str | None = None
    text: str | None = None
    reason: str | None = None
    issue_class: str | None = None

class LocalCodexBridgeClient:
    """OpenAI-compatible chat-completions client for local Codex bridge mode."""
    def __init__(self, config: AIActivityConfig) -> None:
        config.validate()
        self.config = config
    def complete(self, messages: list[dict[str, str]]) -> str:
        request_blob = json.dumps({"messages": messages})
        if self.config.llm_api_key in request_blob:
            raise LLMBridgeError("LLM request contained credential material")
        payload = {"model": self.config.llm_model, "messages": messages, "temperature": self.config.llm_temperature, "max_tokens": self.config.llm_response_budget}
        endpoint = self.config.llm_base_url.rstrip("/") + "/chat/completions"
        request = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers={"Authorization": f"Bearer {self.config.llm_api_key}", "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.config.llm_timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                raise LLMBridgeError(f"LLM bridge auth failed with HTTP {exc.code}") from exc
            raise LLMBridgeError(f"LLM bridge returned HTTP {exc.code}") from exc
        except TimeoutError as exc:
            raise LLMBridgeError("LLM bridge request timed out") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise LLMBridgeError("LLM bridge request failed") from exc
        choices = response_payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMBridgeError("LLM bridge response did not include choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise LLMBridgeError("LLM bridge response did not include message content")
        return content

    def propose_action(self, *, persona: str, context: dict[str, Any], action_options: list[str]) -> ActionProposal:
        redacted_context = redact_text(json.dumps(context, sort_keys=True)).text
        style_pack = str(context.get("style_pack") or self.config.style_pack)
        spicy = style_prompt(style_pack, silliness_level=self.config.silliness_level, chaos_level=self.config.chaos_level) if self.config.spicy_style else "Keep all content fictional, concise, and public-safe."
        messages = [
            {"role": "system", "content": "You are writing fictional used-car social banter for synthetic agents. Return only JSON with intent, optional candidate_ref, optional text, optional reason. Never include routes or credentials."},
            {"role": "system", "content": spicy + " Choose varied actions; do not dogpile the same candidate when alternatives exist."},
            {"role": "user", "content": json.dumps({"persona": safe_summary(persona, 300), "context": redacted_context, "action_options": action_options})},
        ]
        return parse_action_proposal(self.complete(messages))

def parse_action_proposal(content: str) -> ActionProposal:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return ActionProposal("silence", issue_class="llm_malformed_json")
    intent = data.get("intent") or data.get("action")
    if intent not in ALLOWED_INTENTS:
        return ActionProposal("silence", issue_class="llm_unsupported_intent")
    text = data.get("text")
    if text is not None:
        text_result = validate_generated_social_text(str(text))
        if not text_result.ok:
            return ActionProposal("silence_end" if str(intent).endswith("_end") else "silence", issue_class=text_result.issue_class)
        text = text_result.text
    candidate_ref = data.get("candidate_ref") if isinstance(data.get("candidate_ref"), str) else None
    reason = safe_summary(str(data.get("reason", "")), 120) if data.get("reason") is not None else None
    return ActionProposal(str(intent), candidate_ref, text, reason)
