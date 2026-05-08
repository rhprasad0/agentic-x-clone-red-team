# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any

from .config import _validate_http_url
from .redaction import safe_summary

READ_TIMEOUT = 30

@dataclass
class APIResult:
    ok: bool
    route_class: str
    status_code: int | None = None
    data: Any = None
    issue_class: str | None = None
    safe_summary: str = ""
    client_request_id: str | None = None


class V2APIClient:
    def __init__(self, base_url: str, *, timeout: float = READ_TIMEOUT, per_agent_retry_budget: int = 2) -> None:
        _validate_http_url(base_url, label="API")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.per_agent_retry_budget = per_agent_retry_budget
        self.retry_spent: dict[str, int] = {}

    def _request(self, method: str, path: str, *, bearer: str | None = None, body: dict[str, Any] | None = None, route_class: str, retryable: bool = False, agent_handle: str | None = None) -> APIResult:
        if not path.startswith("/") or any(blocked in path for blocked in ("fixture", "reset", "validation", "finding", "export", "debug", "harness")):
            return APIResult(False, route_class, issue_class="api_route_forbidden", safe_summary="route refused")
        if method == "POST" and retryable and body is not None and "client_request_id" not in body:
            body = {**body, "client_request_id": str(uuid.uuid4())}
        client_request_id = body.get("client_request_id") if isinstance(body, dict) else None
        attempts = 1 + (self.per_agent_retry_budget if retryable or method in {"GET", "DELETE"} else 0)
        last: APIResult | None = None
        for attempt in range(attempts):
            if attempt:
                key = agent_handle or "global"
                self.retry_spent[key] = self.retry_spent.get(key, 0) + 1
                if self.retry_spent[key] > self.per_agent_retry_budget:
                    break
            try:
                req_body = json.dumps(body).encode("utf-8") if body is not None else None
                headers = {"Accept": "application/json"}
                if req_body is not None:
                    headers["Content-Type"] = "application/json"
                if bearer:
                    headers["Authorization"] = f"Bearer {bearer}"
                request = urllib.request.Request(self.base_url + path, data=req_body, headers=headers, method=method)
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read().decode("utf-8")
                    data = json.loads(raw) if raw else None
                    return APIResult(True, route_class, response.status, data, client_request_id=client_request_id, safe_summary="ok")
            except urllib.error.HTTPError as exc:
                retry_after = exc.headers.get("Retry-After")
                body_text = exc.read().decode("utf-8", errors="replace")
                last = APIResult(False, route_class, exc.code, issue_class="api_http_error", safe_summary=safe_summary(body_text), client_request_id=client_request_id)
                if exc.code not in {429, 500, 502, 503, 504} or not (retryable or method in {"GET", "DELETE"}):
                    return last
                if retry_after:
                    try:
                        time.sleep(min(float(retry_after), 1.0))
                    except ValueError:
                        pass
            except (OSError, json.JSONDecodeError) as exc:
                last = APIResult(False, route_class, issue_class="api_contract_mismatch" if isinstance(exc, json.JSONDecodeError) else "api_network_error", safe_summary=safe_summary(str(exc)), client_request_id=client_request_id)
                if not (retryable or method in {"GET", "DELETE"}):
                    return last
        return last or APIResult(False, route_class, issue_class="api_http_error", safe_summary="retry budget exhausted", client_request_id=client_request_id)

    def signup_agent(self, payload: dict[str, Any]) -> APIResult:
        return self._request("POST", "/agents/signup", body=payload, route_class="POST /agents/signup", retryable=False)
    def public_timeline(self, *, limit: int = 20) -> APIResult:
        return self._request("GET", f"/timelines/public?limit={limit}", route_class="GET /timelines/public")
    def home_timeline(self, bearer: str, *, limit: int = 20) -> APIResult:
        return self._request("GET", f"/timelines/home?limit={limit}", bearer=bearer, route_class="GET /timelines/home")
    def list_agents(self) -> APIResult:
        return self._request("GET", "/agents", route_class="GET /agents")
    def get_agent(self, handle: str) -> APIResult:
        return self._request("GET", f"/agents/{urllib.parse.quote(handle)}", route_class="GET /agents/{handle}")
    def agent_posts(self, handle: str, bearer: str | None = None, tab: str = "posts", limit: int = 20) -> APIResult:
        if tab not in {"posts", "replies", "likes", "reposts"}:
            return APIResult(False, f"GET /agents/{{handle}}/{tab}", issue_class="api_route_forbidden", safe_summary="profile tab refused")
        return self._request("GET", f"/agents/{urllib.parse.quote(handle)}/{tab}?limit={limit}", bearer=bearer, route_class=f"GET /agents/{{handle}}/{tab}")
    def thread(self, post_id: str, bearer: str | None = None) -> APIResult:
        return self._request("GET", f"/posts/{urllib.parse.quote(post_id)}/thread", bearer=bearer, route_class="GET /posts/{post_id}/thread")
    def create_post(self, bearer: str, text: str, *, reply_to_post_id: str | None = None, quote_post_id: str | None = None, agent_handle: str | None = None) -> APIResult:
        body: dict[str, Any] = {"text": text}
        if reply_to_post_id: body["reply_to_post_id"] = reply_to_post_id
        if quote_post_id: body["quote_post_id"] = quote_post_id
        return self._request("POST", "/posts", bearer=bearer, body=body, route_class="POST /posts", retryable=True, agent_handle=agent_handle)
    def like_post(self, bearer: str, post_id: str, *, agent_handle: str | None = None) -> APIResult:
        return self._request("POST", f"/posts/{urllib.parse.quote(post_id)}/like", bearer=bearer, body={}, route_class="POST /posts/{post_id}/like", retryable=True, agent_handle=agent_handle)
    def unlike_post(self, bearer: str, post_id: str) -> APIResult:
        return self._request("DELETE", f"/posts/{urllib.parse.quote(post_id)}/like", bearer=bearer, route_class="DELETE /posts/{post_id}/like")
    def repost(self, bearer: str, post_id: str, *, agent_handle: str | None = None) -> APIResult:
        return self._request("POST", f"/posts/{urllib.parse.quote(post_id)}/repost", bearer=bearer, body={}, route_class="POST /posts/{post_id}/repost", retryable=True, agent_handle=agent_handle)
    def unrepost(self, bearer: str, post_id: str) -> APIResult:
        return self._request("DELETE", f"/posts/{urllib.parse.quote(post_id)}/repost", bearer=bearer, route_class="DELETE /posts/{post_id}/repost")
    def follow(self, bearer: str, handle: str, *, agent_handle: str | None = None) -> APIResult:
        return self._request("POST", f"/agents/{urllib.parse.quote(handle)}/follow", bearer=bearer, body={}, route_class="POST /agents/{handle}/follow", retryable=True, agent_handle=agent_handle)
    def unfollow(self, bearer: str, handle: str) -> APIResult:
        return self._request("DELETE", f"/agents/{urllib.parse.quote(handle)}/follow", bearer=bearer, route_class="DELETE /agents/{handle}/follow")
