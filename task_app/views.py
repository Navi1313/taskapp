from datetime import datetime
from uuid import UUID

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Task
from .serialization import TaskSerializer


@api_view(["GET"])
def index(request: Request):
    return Response(
        {
            "endpoints": {
                "add": "/add/?a=1&b=2",
                "create_task": "POST /create_task/",
                "list_user_tasks": "GET /tasks/?owner=<name>&type=upcoming|completed|all",
                "list_completed_tasks": "GET /tasks/?owner=<name>&type=completed&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD",
                "task_detail": "/task/<uuid>/",
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


def _parse_date(value: str, param_name: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ValueError(f"{param_name} must be YYYY-MM-DD")


@api_view(["GET"])
def list_user_tasks(request: Request):
    owner = request.GET.get("owner")
    task_type = request.GET.get("type", "all")

    if not owner:
        return Response(
            {"error": "owner query parameter is required"},
            status=400,
        )

    queryset = Task.objects.filter(owner=owner)
    today = timezone.localdate()

    if task_type == "upcoming":
        tasks = queryset.filter(
            status=Task.TaskStatus.PENDING,
            due_at__gte=today,
        ).order_by("due_at")
    elif task_type == "completed":
        start_date_raw = request.GET.get("start_date")
        end_date_raw = request.GET.get("end_date")
        if not start_date_raw or not end_date_raw:
            return Response(
                {
                    "error": "start_date and end_date are required when type=completed",
                },
                status=400,
            )
        try:
            start_date = _parse_date(start_date_raw, "start_date")
            end_date = _parse_date(end_date_raw, "end_date")
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        if start_date > end_date:
            return Response(
                {"error": "start_date must be on or before end_date"},
                status=400,
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
            status=400,
        )

    return Response(
        {
            "owner": owner,
            "type": task_type,
            "count": tasks.count(),
            "tasks": TaskSerializer(tasks, many=True).data,
        },
        status=200,
    )



@api_view(["POST"])
def create_task_request(request: Request):
    serializer = TaskSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=400)
    try:
        task = serializer.save()
    except ValidationError as exc:
        return Response({"errors": exc.message_dict}, status=400)
    return Response(
        {
        "message": "Task created", 
        "task": serializer.to_representation(task)
        },
        status=201,
    )


@api_view(["GET", "DELETE", "PUT"])
def task_detail(request: Request, task_id: UUID):
    task = get_object_or_404(Task, pk=task_id)

    if request.method == "GET":
        return Response(
            {"task_id": str(task.pk), "task": TaskSerializer(task).data},
            status=200,
        )

    if request.method == "DELETE":
        deleted_id = str(task.pk)
        task.delete()
        return Response(
            {"message": "Task deleted", "task_id": deleted_id},
            status=200,
        )

    serializer = TaskSerializer(task, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=400)
    try:
        task = serializer.save()
    except ValidationError as exc:
        return Response({"errors": exc.message_dict}, status=400)
    return Response(
        {"message": "Task updated", "task": TaskSerializer(task).data},
        status=200,
    )
