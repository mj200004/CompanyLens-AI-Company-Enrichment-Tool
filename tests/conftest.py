from __future__ import annotations

from pathlib import Path

import pytest

from app import create_app, db


@pytest.fixture()
def app(tmp_path: Path):
    database_path = tmp_path / "test_companylens.db"

    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
        }
    )

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
