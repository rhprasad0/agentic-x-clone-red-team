#!/usr/bin/env python3
"""Seed the local synthetic fixture world through the backend harness route."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

DEFAULT_API_BASE_URL = "http://localhost:8000"


def post_fixture_route(api_base_url: str, token: str) -> tuple[int, dict[str, Any] | str]:
    url = f"{api_base_url.rstrip('/')}/fixtures/seed"
    request = urllib.request.Request(
        url,
        method="POST",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        return error.code, body
    except urllib.error.URLError as error:
        return 0, f"request failed: {error.reason}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api-base-url",
        default=os.environ.get("XCLONE_API_BASE_URL", DEFAULT_API_BASE_URL),
        help="Backend API base URL. Defaults to XCLONE_API_BASE_URL or http://localhost:8000.",
    )
    args = parser.parse_args()

    token = os.environ.get("XCLONE_HARNESS_TOKEN")
    if not token:
        print("XCLONE_HARNESS_TOKEN is required in the environment.", file=sys.stderr)
        return 2

    status_code, payload = post_fixture_route(args.api_base_url, token)
    print(
        json.dumps({"status_code": status_code, "response": payload}, indent=2, sort_keys=True)
    )
    return 0 if 200 <= status_code < 300 else 1


if __name__ == "__main__":
    raise SystemExit(main())
