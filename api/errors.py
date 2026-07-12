from __future__ import annotations

from typing import Any

from flask import Flask, jsonify


class APIError(Exception):
    def __init__(self, message: str, *, status_code: int = 400, code: str = "bad_request") -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code

    def to_response(self) -> tuple[Any, int]:
        return jsonify({"error": {"code": self.code, "message": self.message}}), self.status_code


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(APIError)
    def handle_api_error(error: APIError) -> tuple[Any, int]:
        return error.to_response()

    @app.errorhandler(404)
    def handle_not_found(_: Any) -> tuple[Any, int]:
        return jsonify({"error": {"code": "not_found", "message": "The requested resource was not found."}}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(_: Any) -> tuple[Any, int]:
        return (
            jsonify(
                {
                    "error": {
                        "code": "method_not_allowed",
                        "message": "The HTTP method is not allowed for this route.",
                    }
                }
            ),
            405,
        )

    @app.errorhandler(500)
    def handle_internal_error(_: Any) -> tuple[Any, int]:
        return (
            jsonify(
                {
                    "error": {
                        "code": "internal_server_error",
                        "message": "An unexpected server error occurred.",
                    }
                }
            ),
            500,
        )
