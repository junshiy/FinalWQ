"""应用配置。"""
from django.apps import AppConfig


class FaultdiagConfig(AppConfig):
    """Linux 实验故障智能诊断应用。"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "faultdiag"
    verbose_name = "实验故障智能诊断"
