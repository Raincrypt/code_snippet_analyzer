import logging
import re
import time
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.logging_config import request_id_var

logger = logging.getLogger("app.request")

# Accept a caller-supplied ID only if it is short and harmless (keeps logs clean).
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class RequestContextMiddleware:
    """Gives each request an ID, echoes it as X-Request-ID, and logs one line per request.

    Written as plain ASGI (not BaseHTTPMiddleware) so it stays correct for streaming responses.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = MutableHeaders(scope=scope).get("x-request-id", "")
        request_id = incoming if _SAFE_REQUEST_ID.match(incoming) else uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000)
            method, path = scope["method"], scope["path"]
            logger.info(
                "%s %s -> %s (%sms)",
                method,
                path,
                status,
                duration_ms,
                extra={
                    "method": method,
                    "path": path,
                    "status": status,
                    "duration_ms": duration_ms,
                },
            )
            request_id_var.reset(token)
