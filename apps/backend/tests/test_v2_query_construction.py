import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"


def production_python_files() -> list[Path]:
    return sorted(path for path in APP_ROOT.rglob("*.py") if "__pycache__" not in path.parts)


def call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def is_dynamic_sql_arg(node: ast.AST) -> bool:
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        return node.func.attr == "format"
    return False


def test_production_code_does_not_build_raw_sql_with_string_interpolation() -> None:
    violations: list[str] = []

    for path in production_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = call_name(node.func)
            if name not in {"execute", "text"}:
                continue
            for arg in node.args:
                if is_dynamic_sql_arg(arg):
                    violations.append(f"{path.relative_to(APP_ROOT)}:{node.lineno}")

    assert violations == []
