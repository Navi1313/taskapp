from uuid import UUID

from django.core.exceptions import ValidationError
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
