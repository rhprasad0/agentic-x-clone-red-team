#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

ACTIONS = [
    {
        "intent": "root_post",
        "text": "Fictional scout note: cheap sedans need boring maintenance math.",
    },
    {"intent": "silence", "reason": "No safe candidate looked useful."},
    {
        "intent": "like",
        "candidate_ref": "candidate_1",
        "reason": "Useful fictional used-car signal.",
    },
]


class FakeLLMHandler(BaseHTTPRequestHandler):
    counter = 0

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return
        _ = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        action = ACTIONS[FakeLLMHandler.counter % len(ACTIONS)]
        FakeLLMHandler.counter += 1
        payload = {
            "id": "chatcmpl_fake",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": json.dumps(action)},
                    "finish_reason": "stop",
                }
            ],
        }
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4010)
    args = parser.parse_args(argv)
    server = HTTPServer((args.host, args.port), FakeLLMHandler)
    endpoint = f"http://{args.host}:{args.port}/v1"
    print(json.dumps({"status": "ok", "endpoint": endpoint}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
