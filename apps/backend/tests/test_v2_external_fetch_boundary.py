import re
from pathlib import Path

BACKEND_APP = Path(__file__).resolve().parents[1] / "app"

FORBIDDEN_OUTBOUND_PATTERNS = {
    "requests import": re.compile(r"^\s*(?:import\s+requests|from\s+requests\s+import)\b", re.M),
    "httpx client": re.compile(r"\bhttpx\.(?:AsyncClient|Client)\s*\("),
    "urllib request import": re.compile(
        r"^\s*(?:import\s+urllib\.request|from\s+urllib\s+import\s+request|"
        r"from\s+urllib\.request\s+import)\b",
        re.M,
    ),
    "aiohttp import": re.compile(r"^\s*(?:import\s+aiohttp|from\s+aiohttp\s+import)\b", re.M),
    "socket client": re.compile(
        r"\bsocket\.(?:socket|create_connection)\s*\(|"
        r"^\s*from\s+socket\s+import\s+(?:socket|create_connection)\b",
        re.M,
    ),
}

FORBIDDEN_USER_SUPPLIED_FETCH_BEHAVIOR = re.compile(
    r"\b(?:"
    r"fetch_url|fetch_remote|proxy_url|proxy_request|url_preview|link_preview|"
    r"unfurl|enrichment_url|crawl_url|crawler|remote_import|import_remote"
    r")\b",
    re.I,
)


def production_python_files() -> list[Path]:
    return sorted(BACKEND_APP.rglob("*.py"))


def test_backend_app_has_no_production_outbound_http_or_socket_clients() -> None:
    findings: list[str] = []
    for path in production_python_files():
        text = path.read_text(encoding="utf-8")
        for label, pattern in FORBIDDEN_OUTBOUND_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{path.relative_to(BACKEND_APP)}: {label}")

    assert findings == []


def test_backend_app_has_no_user_supplied_fetch_proxy_preview_or_remote_import_surface() -> None:
    findings: list[str] = []
    for path in production_python_files():
        text = path.read_text(encoding="utf-8")
        for match in FORBIDDEN_USER_SUPPLIED_FETCH_BEHAVIOR.finditer(text):
            findings.append(f"{path.relative_to(BACKEND_APP)}: {match.group(0)}")

    assert findings == []
