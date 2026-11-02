"""faultdiag 应用路由。

任务 6.1 要求：通过 http://<公网IP>/index 访问 templates/index.html。
"""
from django.urls import path

from . import views

app_name = "faultdiag"

urlpatterns = [
    path("", views.index, name="home"),
    path("index", views.index, name="index"),
    path("index/", views.index, name="index_slash"),
    path("api/diagnose", views.api_diagnose, name="api_diagnose"),
]
