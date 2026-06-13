import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

request_id_context: ContextVar[str] = ContextVar("request_id", default="")


class RequestIDMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        *,
        header_name: str = "X-Request-ID",
    ) -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(
            self.header_name, str(uuid.uuid4())
        )
        request.state.request_id = request_id
        request_id_context.set(request_id)
        response = await call_next(request)
        response.headers[self.header_name] = request_id
        return response
