from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from flask import Flask, send_from_directory
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
migrate = Migrate()


def create_app(config_overrides: Mapping[str, Any] | None = None) -> Flask:
    from app.api.errors import register_error_handlers
    from app.api.routes import api_bp
    from app.config import Settings

    settings = Settings.from_env()
    static_dir = Path(__file__).resolve().parent.parent / "static"

    app = Flask(__name__, static_folder=str(static_dir), static_url_path="/static")
    app.config.update(settings.to_flask_config())

    if config_overrides:
        app.config.update(config_overrides)

    app.extensions["companylens_settings"] = settings

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(api_bp)
    register_error_handlers(app)

    @app.get("/")
    def index() -> Any:
        return send_from_directory(app.static_folder, "index.html")

    return app
