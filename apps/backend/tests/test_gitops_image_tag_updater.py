import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts/update_gitops_image_tags.py"
spec = importlib.util.spec_from_file_location("update_gitops_image_tags", SCRIPT_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
update_gitops_image_tags = module.update_gitops_image_tags

REPOSITORY = "rhprasad0/agentic-x-clone-red-team"


def image_line(component: str, image_component: str | None = None) -> str:
    image_component = image_component or f"xclone-{component}"
    return (
        f"image: ghcr.io/{REPOSITORY}/{image_component}:demo-placeholder "
        f'# {{"$imagepolicy": "flux-system:xclone-{component}:tag"}}'
    )


def test_update_gitops_image_tags_pins_app_images_to_short_commit_sha(tmp_path: Path) -> None:
    repo_root = tmp_path
    backend = repo_root / "deploy/gitops/apps/base/backend-deployment.yaml"
    frontend = repo_root / "deploy/gitops/apps/base/frontend-deployment.yaml"
    backend.parent.mkdir(parents=True)

    backend.write_text(
        f"containers:\n  - name: backend\n    {image_line('backend')}\n",
        encoding="utf-8",
    )
    frontend.write_text(
        f"containers:\n  - name: frontend\n    {image_line('frontend')}\n",
        encoding="utf-8",
    )

    changed = update_gitops_image_tags(
        repo_root=repo_root,
        repository=REPOSITORY,
        commit_sha="357d18f174055ff72c0f8944f5810ce890809919",
    )

    backend_text = backend.read_text(encoding="utf-8")
    frontend_text = frontend.read_text(encoding="utf-8")

    assert changed == [backend, frontend]
    assert (
        f"image: ghcr.io/{REPOSITORY}/backend:sha-357d18f "
        '# {"$imagepolicy": "flux-system:xclone-backend:tag"}'
    ) in backend_text
    assert "xclone-backend:demo-placeholder" not in backend_text
    assert f"image: ghcr.io/{REPOSITORY}/frontend:sha-357d18f " in frontend_text


def test_update_gitops_image_tags_rejects_short_or_non_hex_commit(tmp_path: Path) -> None:
    for bad_sha in ("123456", "not-a-real-sha"):
        try:
            update_gitops_image_tags(
                repo_root=tmp_path,
                repository=REPOSITORY,
                commit_sha=bad_sha,
            )
        except ValueError as exc:
            assert "commit_sha" in str(exc)
        else:
            raise AssertionError(f"accepted invalid sha {bad_sha}")
