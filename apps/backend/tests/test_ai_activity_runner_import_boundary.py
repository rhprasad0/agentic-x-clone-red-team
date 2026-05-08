# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FORBIDDEN = ("app", "apps.backend", "sqlalchemy", "alembic")

def test_runner_import_boundary_excludes_backend_internals():
    paths = [ROOT / "scripts" / "ai_activity_runner.py", *sorted((ROOT / "scripts" / "ai_activity_runner_lib").glob("*.py"))]
    assert paths
    for path in paths:
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            names=[]
            if isinstance(node, ast.Import): names=[alias.name for alias in node.names]
            if isinstance(node, ast.ImportFrom) and node.module: names=[node.module]
            for name in names:
                assert not any(name == f or name.startswith(f + ".") for f in FORBIDDEN), f"{path} imports {name}"

def test_cli_module_import_has_no_side_effects():
    import scripts.ai_activity_runner as runner
    assert callable(runner.main)
