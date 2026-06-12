from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TaskViewSet, UserViewSet, add_two_numbers, index, login, signup

router = DefaultRouter()
router.register(r"tasks", TaskViewSet, basename="task")
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [
    path("", index),
    path("admin/", admin.site.urls),
    path("add/", add_two_numbers),
    path("api/auth/login/", login),
    path("api/auth/signup/", signup),
    path("", include(router.urls)),
]