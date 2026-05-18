from datetime import datetime

from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Task, User
from .serialization import TaskSerializer, UserSerializer


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
                "tasks_list": "GET /tasks/?owner=<name>&type=...&page=1&page_size=10",
                "tasks_upcoming": "GET /tasks/upcoming/?owner=<name>",
                "tasks_completed": "GET /tasks/completed/?owner=<name>&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD",
                "tasks_create": "POST /tasks/",
                "tasks_detail": "GET|PUT|PATCH|DELETE /tasks/<uuid>/",
                "users_list": "GET /users/",
                "users_create": "POST /users/",
                "users_detail": "GET|PUT|PATCH|DELETE /users/<uuid>/",
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


class TaskPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


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
    pagination_class = TaskPagination

    def _tasks_for_owner(self, owner: str):
        return Task.objects.filter(owner=owner)

    def _paginated_list_response(self, owner: str | None, task_type: str, queryset):
        page = self.paginate_queryset(queryset)
        if page is not None:
            response = self.get_paginated_response(TaskSerializer(page, many=True).data)
            response.data["type"] = task_type
            response.data["tasks"] = response.data.pop("results")
            if owner:
                response.data["owner"] = owner
            return response

        payload = {
            "type": task_type,
            "count": queryset.count(),
            "tasks": TaskSerializer(queryset, many=True).data,
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
                    {"error": "start_date and end_date are required when type=completed"},
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

        return self._paginated_list_response(owner, task_type, tasks)

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
        return self._paginated_list_response(owner, "upcoming", tasks)

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
        return self._paginated_list_response(owner, "completed", tasks)


class UserViewSet(viewsets.ModelViewSet):
    """
    CRUD for users.

    Standard routes (via router):
      GET    /users/           list all users
      POST   /users/           create a user
      GET    /users/<uuid>/    retrieve a user
      PUT    /users/<uuid>/    update a user
      PATCH  /users/<uuid>/    partial update
      DELETE /users/<uuid>/    delete a user
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = "pk"
    pagination_class = TaskPagination

    def list(self, request, *args, **kwargs):
        queryset = User.objects.all()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = UserSerializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data["users"] = response.data.pop("results")
            return response
        return Response(
            {"count": queryset.count(), "users": UserSerializer(queryset, many=True).data},
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        return Response(
            {"message": "User created", "user": serializer.to_representation(user)},
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(user)
        return Response(
            {"userid": str(user.pk), "user": serializer.data},
            status=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data, partial=partial)
        if not serializer.is_valid():
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        return Response(
            {"message": "User updated", "user": serializer.to_representation(user)},
            status=status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        deleted_id = str(user.pk)
        user.delete()
        return Response(
            {"message": "User deleted", "userid": deleted_id},
            status=status.HTTP_200_OK,
        )