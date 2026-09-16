"""Python kodu calistirma araci (guvenli sandbox)."""
from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# Guvenlik: bu moduller import edilemez
FORBIDDEN_MODULES = {
    "os",
    "sys",
    "subprocess",
    "shutil",
    "socket",
    "urllib",
    "requests",
    "httpx",
    "pathlib",
    "glob",
    "tempfile",
    "pickle",
    "shelve",
    "ctypes",
    "multiprocessing",
    "threading",
    "asyncio",
    "__import__",
    "eval",
    "exec",
}


def _is_code_safe(code: str) -> tuple[bool, str]:
    """Kodu AST ile analiz eder; yasakli import/cagri var mi kontrol eder."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    for node in ast.walk(tree):
        # Import kontrolu
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in FORBIDDEN_MODULES:
                    return False, f"Yasakli import: {root}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                if root in FORBIDDEN_MODULES:
                    return False, f"Yasakli import: {root}"
        # Yasakli fonksiyon cagrilari
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_MODULES:
                    return False, f"Yasakli cagri: {node.func.id}"

    return True, "OK"


def run_python(code: str, timeout: int = 10) -> dict[str, Any]:
    """Python kodunu guvenli sekilde calistirir.

    Args:
        code: Calistirilacak Python kodu
        timeout: Maksimum saniye

    Returns:
        {"stdout": str, "stderr": str, "returncode": int, "safe": bool, "reason": str}
    """
    safe, reason = _is_code_safe(code)
    if not safe:
        logger.warning("code_runner.unsafe", reason=reason)
        return {
            "stdout": "",
            "stderr": f"Guvenlik reddi: {reason}",
            "returncode": -1,
            "safe": False,
            "reason": reason,
        }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = Path(f.name)

    try:
        result = subprocess.run(
            [sys.executable, str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
        )
        logger.info(
            "code_runner.done",
            returncode=result.returncode,
            stdout_len=len(result.stdout),
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "safe": True,
            "reason": "OK",
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Zaman asimi ({timeout}s)",
            "returncode": -1,
            "safe": True,
            "reason": "timeout",
        }
    finally:
        try:
            tmp_path.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    # Test 1: basit kod
    r1 = run_python("print('Merhaba dunya')\nprint(2+2)")
    print("Test 1:", r1["stdout"].strip(), "| returncode:", r1["returncode"])

    # Test 2: yasakli import
    r2 = run_python("import os\nprint(os.getcwd())")
    print("Test 2:", r2["reason"], "| safe:", r2["safe"])