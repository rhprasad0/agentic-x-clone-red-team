#!/usr/bin/env python3
"""Pin x-clone GitOps image references to the current GHCR commit tag."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

_IMAGE_TARGETS = {
    "backend": Path("deploy/gitops/apps/base/backend-deployment.yaml"),
    "frontend": Path("deploy/gitops/apps/base/frontend-deployment.yaml"),
}

_IMAGE_LINE_RE = re.compile(
    r"^(?P<indent>\s*image:\s+)"
    r"(?P<image>ghcr\.io/[^\s#]+/(?:xclone-)?(?P<component>backend|frontend):[^\s#]+)"
    r"(?P<suffix>.*)$",
    re.MULTILINE,
)

_HEX_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")


def _short_sha(commit_sha: str) -> str:
    if not _HEX_SHA_RE.fullmatch(commit_sha):
        raise ValueError("commit_sha must be a 7-40 character hex Git commit SHA")
    return commit_sha[:7].lower()


def _pin_image_line(text: str, *, repository: str, component: str, tag: str) -> tuple[str, bool]:
    wanted = f"ghcr.io/{repository}/{component}:{tag}"

    def replace(match: re.Match[str]) -> str:
        if match.group("component") != component:
            return match.group(0)
        return f'{match.group("indent")}{wanted}{match.group("suffix")}'

    updated = _IMAGE_LINE_RE.sub(replace, text)
    return updated, updated != text


def update_gitops_image_tags(
    *, repo_root: Path, repository: str, commit_sha: str
) -> list[Path]:
    """Update GitOps image refs to `ghcr.io/<repository>/<component>:sha-<short-sha>`."""
    tag = f"sha-{_short_sha(commit_sha)}"
    changed: list[Path] = []

    for component, relative_path in _IMAGE_TARGETS.items():
        path = repo_root / relative_path
        text = path.read_text(encoding="utf-8")
        updated, did_change = _pin_image_line(
            text, repository=repository, component=component, tag=tag
        )
        if did_change:
            path.write_text(updated, encoding="utf-8")
            changed.append(path)

    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--repository", required=True, help="GitHub owner/repo, e.g. rhprasad0/repo")
    parser.add_argument("--commit-sha", required=True)
    args = parser.parse_args()

    changed = update_gitops_image_tags(
        repo_root=args.repo_root,
        repository=args.repository,
        commit_sha=args.commit_sha,
    )
    if changed:
        print("Updated GitOps image refs:")
        for path in changed:
            print(path.relative_to(args.repo_root))
    else:
        print("GitOps image refs already pinned to requested commit tag.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
