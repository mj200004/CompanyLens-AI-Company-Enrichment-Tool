from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from flask import Blueprint, current_app, jsonify

from app import db
from app.models import EnrichmentResult


api_bp = Blueprint("api", __name__)


@api_bp.get("/health")
def health() -> Any:
    settings = current_app.extensions["companylens_settings"]
    database_ok = True

    try:
        db.session.execute(db.text("SELECT 1"))
    except Exception:  # noqa: BLE001
        current_app.logger.exception("Database health check failed")
        database_ok = False

    status_code = 200 if database_ok else 503
    return (
        jsonify(
            {
                "ok": database_ok,
                "service": "companylens",
                "key_set": bool(current_app.config.get("ANTHROPIC_API_KEY")),
                "database": "ok" if database_ok else "error",
                "environment": settings.environment,
                "time": datetime.now(timezone.utc).isoformat(),
            }
        ),
        status_code,
    )


@api_bp.get("/api/results")
@api_bp.get("/results")
def list_results() -> Any:
    results = db.session.execute(
        db.select(EnrichmentResult).order_by(EnrichmentResult.created_at.desc())
    ).scalars()
    return jsonify([result.to_dict() for result in results])


@api_bp.get("/api/results/<int:result_id>")
def get_result(result_id: int) -> Any:
    result = db.get_or_404(EnrichmentResult, result_id)
    return jsonify(result.to_dict())


@api_bp.post("/api/results/clear")
@api_bp.post("/results/clear")
def clear_results() -> Any:
    deleted = db.session.query(EnrichmentResult).delete()
    db.session.commit()
    return jsonify({"ok": True, "deleted": deleted})
