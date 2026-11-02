"""FinalWQ 路由总表。

任务 5.2 截图「Django 小火箭」时，请先把 urlpatterns 临时改成空列表：

    urlpatterns = []

截图完成后恢复成本文件的完整配置即可（原因见 README「常见问题」）。
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("faultdiag.urls")),
]
