"""
URL configuration for task_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from .views import add_two_numbers, create_task_request, index, task_detail


urlpatterns = [
    path("", index),
    path("admin/", admin.site.urls),
    path("add/", add_two_numbers),
    path("create_task/", create_task_request),
    path("task/<uuid:task_id>/", task_detail),
]

# www.airtribe.live/add?a=10&b=30  -> a, b are request parameters url is "/add"
# www.airtribe.live1/task/1  ->  1 is path parameter is "/task/1"