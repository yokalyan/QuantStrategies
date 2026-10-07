from __future__ import annotations

from pathlib import Path


def pct(x: float) -> str:
    return f"{x * 100:.2f}%"


def write_report(path: Path, title: str, metrics: dict, assumptions: list[str], gates: list[str]) -> None:
    lines = [f"# {title}", ""]
    lines.append("## Metrics")
    for key, value in metrics.items():
        if key in {"total_return", "cagr", "annual_volatility", "sharpe", "sortino", "calmar", "max_drawdown", "best_day", "worst_day", "beta", "alpha", "correlation"}:
            rendered = pct(value) if key not in {"sharpe", "sortino", "calmar", "beta", "correlation"} else f"{value:.3f}"
        else:
            rendered = f"{value:.2f}"
        lines.append(f"- `{key}`: {rendered}")
    lines.append("")
    lines.append("## Assumptions And Caveats")
    lines.extend(f"- {item}" for item in assumptions)
    lines.append("")
    lines.append("## Gates")
    lines.extend(gates)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

