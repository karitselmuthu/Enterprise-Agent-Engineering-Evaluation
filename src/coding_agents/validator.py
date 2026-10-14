"""Static checks before generated code reaches the container sandbox."""

import ast


class CodeValidationError(ValueError):
    pass


ALLOWED_IMPORTS = {"json", "sys"}
FORBIDDEN_CALLS = {"eval", "exec", "compile", "open", "__import__", "input",
                   "globals", "locals", "getattr", "setattr", "delattr"}


def validate_python(source: str) -> None:
    if not source.strip() or len(source.encode("utf-8")) > 32_768:
        raise CodeValidationError("Generated source is empty or exceeds 32 KiB")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise CodeValidationError(f"Syntax error: {exc.msg}") from exc
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in ALLOWED_IMPORTS:
                    raise CodeValidationError(f"Import not permitted: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            raise CodeValidationError("Import-from is not permitted")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                raise CodeValidationError(f"Call not permitted: {node.func.id}")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise CodeValidationError("Dunder attribute access is not permitted")
