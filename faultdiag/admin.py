"""后台管理注册。"""
from django.contrib import admin

from .models import DiagnosisRecord


@admin.register(DiagnosisRecord)
class DiagnosisRecordAdmin(admin.ModelAdmin):
    """诊断记录后台，用于查看命中分布与采纳率。"""

    list_display = ("created_at", "top_rule", "confidence", "elapsed_ms", "need_human", "adopted")
    list_filter = ("need_human", "adopted", "top_rule")
    search_fields = ("raw_text", "top_rule")
    readonly_fields = ("created_at",)
