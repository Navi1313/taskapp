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
