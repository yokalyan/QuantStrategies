from __future__ import annotations

from pathlib import Path


FORBIDDEN_CODE_PATTERNS = [
    "from " + "QuantConnect",
    "import " + "QuantConnect",
    "Algorithm" + "Imports",
    "QC" + "Algorithm",
    "import " + "clr",
    "lean " + "cloud",
    "lean " + "backtest",
]


def scan_for_forbidden_terms(root: Path) -> list[str]:
    violations: list[str] = []
    for path in root.rglob("*"):
        if path.is_dir() or ".venv" in path.parts or path.suffix in {".parquet", ".png", ".csv"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in FORBIDDEN_CODE_PATTERNS:
            if pattern in text:
                violations.append(f"{path}: {pattern}")
    return violations
