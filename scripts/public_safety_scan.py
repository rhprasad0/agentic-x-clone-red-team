#!/usr/bin/env python3
"""Public-safety scanner for publishable repository text files.

Examples are bracket-escaped so this file does not self-match:
- A[KIA]................
- s[k]-........................
- /[h]ome/name/project
- user[@]non-example.test
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


MAX_TEXT_BYTES = 2_000_000

SKIP_DIRS = {
    ".git",
    ".next",
    ".cache",
    ".turbo",
    ".vercel",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
}

TEXT_SUFFIXES = {
    "",
    ".css",
    ".env",
    ".example",
    ".gitignore",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mjs",
    ".py",
    ".sh",
    ".sql",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

PLACEHOLDER_RE = re.compile(
    r"(placeholder|example|fake|dummy|redacted|change[_-]?me|replace[_-]?me|not[_-]?used|local[_-]?dev|disabled|scaffold)",
    re.IGNORECASE,
)

SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"^\s*([A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY|ACCESS_KEY|PRIVATE_KEY|CLIENT_SECRET)[A-Z0-9_]*)\s*[:=]\s*(['\"]?)([^'\"\s#]+)",
)


@dataclass(frozen=True)
class PatternCheck:
    name: str
    regex: re.Pattern[str]


def build_patterns() -> list[PatternCheck]:
    slash = "/"
    openai_prefix = "s" + "k" + "-"
    aws_prefix = "AK" + "IA"
    github_prefix = "gh" + "p_"
    jwt_prefix = "e" + "y" + "J"
    slack_prefix = "xo" + "x"
    private_key_header = "-" * 5 + "BEGIN "
    private_key_footer = " PRIVATE KEY" + "-" * 5

    return [
        PatternCheck(
            "private Unix-style home path",
            re.compile(re.escape(slash) + r"(?:home|Users)" + re.escape(slash) + r"[A-Za-z0-9._-]+(?:/|$)"),
        ),
        PatternCheck(
            "AWS access key-like token",
            re.compile(r"\b" + aws_prefix + r"[A-Z0-9]{16}\b"),
        ),
        PatternCheck(
            "OpenAI key-like token",
            re.compile(r"\b" + re.escape(openai_prefix) + r"[A-Za-z0-9]{20,}\b"),
        ),
        PatternCheck(
            "GitHub token-like value",
            re.compile(r"\b" + re.escape(github_prefix) + r"[A-Za-z0-9_]{20,}\b"),
        ),
        PatternCheck(
            "Slack token-like value",
            re.compile(r"\b" + slack_prefix + r"[A-Za-z]-[A-Za-z0-9-]{20,}\b"),
        ),
        PatternCheck(
            "JWT-like token",
            re.compile(r"\b" + jwt_prefix + r"[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
        ),
        PatternCheck(
            "private key header",
            re.compile(re.escape(private_key_header) + r"[A-Z ]+" + re.escape(private_key_footer)),
        ),
        PatternCheck(
            "non-example email address",
            re.compile(
                r"\b[A-Z0-9._%+-]+@(?!(?:example\.com|example\.org|example\.net|localhost|test\.local)\b)"
                r"[A-Z0-9.-]+\.[A-Z]{2,}\b",
                re.IGNORECASE,
            ),
        ),
        PatternCheck(
            "SSN-like identifier",
            re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        ),
        PatternCheck(
            "phone-number-like value",
            re.compile(r"(?<!\d)(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)"),
        ),
    ]


def repo_files(root: Path) -> list[Path] | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    files: list[Path] = []
    for raw in result.stdout.split(b"\0"):
        if raw:
            files.append(root / raw.decode("utf-8", errors="surrogateescape"))
    return files


def walk_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        base = Path(dirpath)
        for filename in filenames:
            yield base / filename


def discover_files(paths: list[Path]) -> list[Path]:
    discovered: list[Path] = []
    for path in paths:
        if path.is_dir():
            git_files = repo_files(path)
            discovered.extend(git_files if git_files is not None else walk_files(path))
        else:
            discovered.append(path)
    return sorted(set(discovered))


def is_text_candidate(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    if path.suffix not in TEXT_SUFFIXES and path.name not in {".env.example", ".gitignore"}:
        return False
    try:
        if path.stat().st_size > MAX_TEXT_BYTES:
            return False
    except OSError:
        return False
    return True


def read_text(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def safe_snippet(line: str, match_text: str) -> str:
    compact = line.strip()
    if match_text:
        compact = compact.replace(match_text, "[redacted-match]")
    return compact[:180]


def assignment_is_allowed(value: str) -> bool:
    stripped = value.strip().strip("'\"")
    if not stripped:
        return True
    if PLACEHOLDER_RE.search(stripped):
        return True
    if stripped.startswith("${") and PLACEHOLDER_RE.search(stripped):
        return True
    return False


def scan_file(path: Path, checks: list[PatternCheck]) -> list[str]:
    text = read_text(path)
    if text is None:
        return []

    findings: list[str] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        assignment = SENSITIVE_ASSIGNMENT_RE.match(line)
        if assignment and not assignment_is_allowed(assignment.group(3)):
            key = assignment.group(1)
            findings.append(f"{path}:{line_no}: suspicious sensitive assignment: {key}=[redacted-value]")

        for check in checks:
            match = check.regex.search(line)
            if match:
                findings.append(f"{path}:{line_no}: {check.name}: {safe_snippet(line, match.group(0))}")
    return findings


def main(argv: list[str]) -> int:
    roots = [Path(arg).resolve() for arg in (argv or ["."])]
    checks = build_patterns()
    findings: list[str] = []

    for path in discover_files(roots):
        if is_text_candidate(path):
            findings.extend(scan_file(path, checks))

    if findings:
        print("Public safety scan failed:")
        for finding in findings:
            print(finding)
        return 1

    print("Public safety scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

