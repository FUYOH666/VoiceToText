"""Pure-ASGI request body size limit.

FastAPI parses the whole multipart body before the endpoint runs, so a size
check inside the endpoint comes too late. This middleware:

- rejects a declared ``Content-Length`` over the limit before reading any body
  (with ``Expect: 100-continue`` the client never uploads it);
- counts streamed bytes (chunked uploads have no ``Content-Length``) and stops
  at the limit: it answers 413 itself, tells the app the client disconnected
  and drops whatever the app tries to send afterwards.
"""
from __future__ import annotations

import json
from typing import Any, Awaitable, Callable, Optional

from server.errors import FILE_TOO_LARGE, error_body

Scope = dict[str, Any]
Message = dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


def _declared_length(scope: Scope) -> Optional[int]:
    for name, value in scope.get("headers") or ():
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, *, max_bytes: int, message: str) -> None:
        self.app = app
        self.max_bytes = max_bytes
        self.message = message

    async def _reject(self, send: Send) -> None:
        body = json.dumps(
            error_body(413, FILE_TOO_LARGE, self.message), ensure_ascii=False
        ).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                    (b"connection", b"close"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = _declared_length(scope)
        if declared is not None and declared > self.max_bytes:
            await self._reject(send)
            return

        received = 0
        answered = False
        app_started = False

        async def limited_receive() -> Message:
            nonlocal received, answered
            if answered:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body") or b"")
                if received > self.max_bytes:
                    if not app_started:
                        answered = True
                        await self._reject(send)
                    return {"type": "http.disconnect"}
            return message

        async def guarded_send(message: Message) -> None:
            nonlocal app_started
            if answered:
                return  # 413 already sent; the app's reply to the "disconnect" is dropped
            if message["type"] == "http.response.start":
                app_started = True
            await send(message)

        await self.app(scope, limited_receive, guarded_send)
