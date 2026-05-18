from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TaskViewSet, add_two_numbers, index

router = DefaultRouter()
router.register(r"tasks", TaskViewSet, basename="task")

urlpatterns = [
    path("", index),
    path("admin/", admin.site.urls),
    path("add/", add_two_numbers),
    path("", include(router.urls)),
]
