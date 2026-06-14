import logging
import re
import time
import uuid
from django.http import JsonResponse
from task_app.models import Task

logger = logging.getLogger(__name__)

TASK_ID_PATH = re.compile(
    r"^/tasks?/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/?$",
    re.IGNORECASE,
)

# Routes that do NOT require a JWT token
_PUBLIC_PATHS = frozenset({
    "/",
    "/add/",
    "/api/auth/login/",
    "/api/auth/signup/",
})


class ValidateTaskIdMiddleware:
    """
    For paths matching /tasks/<uuid>/ (or /task/<uuid>/), validates the UUID and ensures the task
    exists in the database. Attaches ``request.task_id`` before the view runs.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        match = TASK_ID_PATH.match(request.path)
        if not match:
            return self.get_response(request)

        raw_id = match.group(1)
        try:
            task_id = uuid.UUID(raw_id)
        except ValueError:
            return JsonResponse(
                {"error": "task_id must be a valid UUID", "task_id": raw_id},
                status=400,
            )

        if not Task.objects.filter(pk=task_id).exists():
            return JsonResponse(
                {"error": "task not found", "task_id": str(task_id)},
                status=404,
            )

        request.task_id = task_id
        return self.get_response(request)


class RequestLoggingMiddleware:
    """
    Logs each incoming request and adds X-Process-Time-Ms to the response
    with the total wall time for the request (including all downstream middleware
    and the view).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        path = request.get_full_path()
        logger.info("%s %s", request.method, path)

        response = self.get_response(request)

        duration_ms = (time.perf_counter() - start) * 1000
        response["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
        return response


class JWTAuthenticationMiddleware:
    """
    Middleware that enforces JWT authentication on all non-public routes.

    For every request:
      1. If the path is in _PUBLIC_PATHS or starts with /admin/, skip auth and pass through.
      2. Otherwise, expect an ``Authorization: Bearer <token>`` header.
      3. Missing header           → 401 Unauthorized.
      4. Invalid / expired token  → 401 Unauthorized.
      5. Valid token              → attach ``request.user_id`` (str UUID) and continue.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ── 1. Skip public routes ──────────────────────────────────────────────
        if request.path in _PUBLIC_PATHS or request.path.startswith("/admin/"):
            return self.get_response(request)

        # ── 2. Extract Bearer token from Authorization header ─────────────────
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return JsonResponse(
                {
                    "error": "Authorization header missing or invalid.",
                    "hint": "Set header as: Authorization: Bearer <token>",
                },
                status=401,
            )

        token = auth_header[len("Bearer "):].strip()

        # ── 3. Verify the token ───────────────────────────────────────────────
        # Lazy import avoids circular dependency at module load time
        from task_app.utils import JWTUtil
        try:
            payload = JWTUtil.verify_token(token)
        except Exception as exc:
            return JsonResponse(
                {"error": "Invalid or expired token.", "detail": str(exc)},
                status=401,
            )

        # ── 4. Attach user_id to request and continue ─────────────────────────
        request.user_id = payload.get("sub")  # UUID string of the authenticated user
        return self.get_response(request)