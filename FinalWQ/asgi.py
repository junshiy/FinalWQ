"""ASGI 入口，供异步服务器（如 uvicorn/daphne）使用。"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "FinalWQ.settings")

application = get_asgi_application()
