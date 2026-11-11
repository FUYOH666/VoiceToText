"""OpenAI-shaped error responses for the STT API.

Body: ``{"error": {"message", "type", "param", "code"}, "detail": message}``.
``detail`` repeats the message for clients written against FastAPI's default
``{"detail": ...}``. Clients branch on status + ``error.code``; the contract
table lives in ``docs/STT_API.md``.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Codes (docs/STT_API.md). Retryable: BUSY (429) and MODEL_LOADING (503) only.
INVALID_AUDIO = "invalid_audio"
UNSUPPORTED_LANGUAGE = "unsupported_language"
INVALID_REQUEST = "invalid_request"
FILE_TOO_LARGE = "file_too_large"
AUDIO_TOO_LONG = "audio_too_long"
BUSY = "busy"
MODEL_LOADING = "model_loading"
MODEL_LOAD_FAILED = "model_load_failed"
TRANSCRIPTION_FAILED = "transcription_failed"
TRANSCRIPTION_TIMEOUT = "transcription_timeout"
INTERNAL_ERROR = "internal_error"
# Model management (/v1/models).
MODEL_NOT_FOUND = "model_not_found"
MODEL_NOT_INSTALLED = "model_not_installed"
MODEL_ACTIVE = "model_active"
MODEL_DOWNLOADING = "model_downloading"
UNSUPPORTED_MODEL = "unsupported_model"

RETRY_AFTER_BUSY_SECONDS = 5
RETRY_AFTER_LOADING_SECONDS = 2


def error_type_for(status: int) -> str:
    if status == 429:
        return "rate_limit_error"
    if status >= 500:
        return "server_error"
    return "invalid_request_error"


def error_body(status: int, code: str, message: str, *, detail: Any = None) -> dict[str, Any]:
    return {
        "error": {
            "message": message,
            "type": error_type_for(status),
            "param": None,
            "code": code,
        },
        "detail": message if detail is None else detail,
    }


class APIError(Exception):
    """An error the API reports with a contract code."""

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        *,
        retry_after: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.retry_after = retry_after

    def headers(self) -> dict[str, str]:
        if self.retry_after is None:
            return {}
        return {"Retry-After": str(int(self.retry_after))}


def error_response(exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        content=error_body(exc.status, exc.code, exc.message),
        headers=exc.headers(),
    )


# Plain HTTPException (FastAPI's own 404/405, anything left over) → shaped body.
_CODE_BY_STATUS = {
    400: INVALID_REQUEST,
    404: "not_found",
    405: "method_not_allowed",
    413: FILE_TOO_LARGE,
    429: BUSY,
    503: MODEL_LOADING,
    504: TRANSCRIPTION_TIMEOUT,
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def _api_error(_request: Request, exc: APIError) -> JSONResponse:
        return error_response(exc)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        code = _CODE_BY_STATUS.get(exc.status_code, INTERNAL_ERROR)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.status_code, code, message),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        parts = []
        for err in errors:
            loc = ".".join(str(p) for p in err.get("loc", ()) if p != "body")
            parts.append(f"{loc}: {err.get('msg', 'invalid')}" if loc else str(err.get("msg")))
        message = "Invalid request: " + "; ".join(parts) if parts else "Invalid request"
        return JSONResponse(
            status_code=400,
            content=error_body(400, INVALID_REQUEST, message, detail=_jsonable(errors)),
        )

    # Starlette re-raises after sending this, so uvicorn still logs the traceback.
    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=error_body(500, INTERNAL_ERROR, "Internal server error"),
        )


def _jsonable(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validation errors can carry raw input/ctx objects; keep the JSON-safe parts."""
    return [
        {k: err[k] for k in ("type", "loc", "msg") if k in err}
        for err in errors
    ]
