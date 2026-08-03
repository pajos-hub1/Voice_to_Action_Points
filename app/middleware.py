import logging
import time

from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("voice_to_action_points.latency")


async def log_request_latency(request: Request, call_next) -> Response:
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
    logger.info(
        "%s %s completed in %.2fms (status=%s)",
        request.method,
        request.url.path,
        duration_ms,
        response.status_code,
    )
    return response
