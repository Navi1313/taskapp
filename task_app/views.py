from datetime import datetime

from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Task
from .serialization import TaskSerializer


def _parse_date(value: str, param_name: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ValueError(f"{param_name} must be YYYY-MM-DD")


@api_view(["GET"])
def index(request: Request):
    return Response(
        {
            "endpoints": {
                "add": "/add/?a=1&b=2",
                "tasks_list": "GET /tasks/ or /tasks/?owner=<name>&type=upcoming|completed|all",
                "tasks_upcoming": "GET /tasks/upcoming/?owner=<name>",
                "tasks_completed": "GET /tasks/completed/?owner=<name>&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD",
                "tasks_create": "POST /tasks/",
                "tasks_detail": "GET|PUT|PATCH|DELETE /tasks/<uuid>/",
                "admin": "/admin/",
            }
        },
        status=200,
    )


@api_view(["GET"])
def add_two_numbers(request: Request):
    a = int(request.GET.get("a"))
    b = int(request.GET.get("b"))
    return Response({"sum": a + b}, status=200)


class TaskViewSet(viewsets.ModelViewSet):
    """
    CRUD for tasks plus owner-filtered list, upcoming, and completed-by-date-range.

    Standard routes (via router):
      GET    /tasks/              list all tasks (?owner= optional)
      POST   /tasks/              create
      GET    /tasks/<uuid>/       retrieve
      PUT    /tasks/<uuid>/       update
      PATCH  /tasks/<uuid>/       partial_update
      DELETE /tasks/<uuid>/       destroy

    Custom routes:
      GET /tasks/upcoming/?owner=<name>
      GET /tasks/completed/?owner=<name>&start_date=...&end_date=...
    """

    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    lookup_field = "pk"

    def _tasks_for_owner(self, owner: str):
        return Task.objects.filter(owner=owner)

    def _serialize_list(self, owner: str | None, task_type: str, tasks):
        payload = {
            "type": task_type,
            "count": tasks.count(),
            "tasks": TaskSerializer(tasks, many=True).data,
        }
        if owner:
            payload["owner"] = owner
        return Response(payload, status=status.HTTP_200_OK)

    def list(self, request, *args, **kwargs):
        owner = request.query_params.get("owner")
        task_type = request.query_params.get("type", "all")

        queryset = self._tasks_for_owner(owner) if owner else Task.objects.all()
        today = timezone.localdate()

        if task_type == "upcoming":
            tasks = queryset.filter(
                status=Task.TaskStatus.PENDING,
                due_at__gte=today,
            ).order_by("due_at")
        elif task_type == "completed":
            start_date_raw = request.query_params.get("start_date")
            end_date_raw = request.query_params.get("end_date")
            if not start_date_raw or not end_date_raw:
                return Response(
                    {
                        "error": "start_date and end_date are required when type=completed",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                start_date = _parse_date(start_date_raw, "start_date")
                end_date = _parse_date(end_date_raw, "end_date")
            except ValueError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            if start_date > end_date:
                return Response(
                    {"error": "start_date must be on or before end_date"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            tasks = queryset.filter(
                status=Task.TaskStatus.COMPLETED,
                completed_at__range=(start_date, end_date),
            ).order_by("-completed_at")
        elif task_type == "all":
            tasks = queryset
        else:
            return Response(
                {"error": "type must be one of: upcoming, completed, all"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return self._serialize_list(owner, task_type, tasks)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            task = serializer.save()
        except ValidationError as exc:
            return Response({"errors": exc.message_dict}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"message": "Task created", "task": serializer.to_representation(task)},
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        task = self.get_object()
        serializer = self.get_serializer(task)
        return Response(
            {"task_id": str(task.pk), "task": serializer.data},
            status=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        task = self.get_object()
        serializer = self.get_serializer(task, data=request.data, partial=partial)
        if not serializer.is_valid():
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            task = serializer.save()
        except ValidationError as exc:
            return Response({"errors": exc.message_dict}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"message": "Task updated", "task": serializer.to_representation(task)},
            status=status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        task = self.get_object()
        deleted_id = str(task.pk)
        task.delete()
        return Response(
            {"message": "Task deleted", "task_id": deleted_id},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def upcoming(self, request):
        """GET /tasks/upcoming/?owner=<name> — pending tasks due today or later."""
        owner = request.query_params.get("owner")
        if not owner:
            return Response(
                {"error": "owner query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        today = timezone.localdate()
        tasks = self._tasks_for_owner(owner).filter(
            status=Task.TaskStatus.PENDING,
            due_at__gte=today,
        ).order_by("due_at")
        return self._serialize_list(owner, "upcoming", tasks)

    @action(detail=False, methods=["get"])
    def completed(self, request):
        """GET /tasks/completed/?owner=<name>&start_date=...&end_date=..."""
        owner = request.query_params.get("owner")
        if not owner:
            return Response(
                {"error": "owner query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        start_date_raw = request.query_params.get("start_date")
        end_date_raw = request.query_params.get("end_date")
        if not start_date_raw or not end_date_raw:
            return Response(
                {"error": "start_date and end_date are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            start_date = _parse_date(start_date_raw, "start_date")
            end_date = _parse_date(end_date_raw, "end_date")
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if start_date > end_date:
            return Response(
                {"error": "start_date must be on or before end_date"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        tasks = self._tasks_for_owner(owner).filter(
            status=Task.TaskStatus.COMPLETED,
            completed_at__range=(start_date, end_date),
        ).order_by("-completed_at")
        return self._serialize_list(owner, "completed", tasks)
