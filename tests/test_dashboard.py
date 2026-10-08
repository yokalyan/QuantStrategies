from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dashboard.analytics import compute_dashboard_analytics
from dashboard.server import app


def test_dashboard_analytics_computation():
    data = compute_dashboard_analytics("results/midpoint_stop_orb_intraday")
    assert "summary" in data
    assert "equity_curve" in data
    assert "monthly_pnl" in data
    assert "weekly_pnl" in data
    assert "day_of_week" in data
    assert "recent_trades" in data

    summary = data["summary"]
    assert summary["start_capital"] > 0
    assert summary["current_equity"] > 0
    assert summary["cagr_pct"] > 0
    assert summary["total_trades"] > 0

    # Ensure all 5 weekdays are present
    days = [d["day"] for d in data["day_of_week"]]
    assert days == ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def test_dashboard_api_endpoints():
    client = TestClient(app)

    # 1. Config endpoint
    resp = client.get("/api/config")
    assert resp.status_code == 200
    cfg = resp.json()
    assert "strategy" in cfg

    # 2. Stats endpoint
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert "summary" in stats
    assert stats["summary"]["total_trades"] > 0

    # 3. Status endpoint
    resp = client.get("/api/status")
    assert resp.status_code == 200
    status = resp.json()
    assert "is_running" in status
    assert status["is_running"] is False

    # 4. Root HTML endpoint
    resp = client.get("/")
    assert resp.status_code == 200
    assert "TQQQ Midpoint ORB" in resp.text

    # 5. Reset endpoint
    resp = client.post("/api/strategy/reset")
    assert resp.status_code == 200
    assert resp.json()["status"] == "reset"
