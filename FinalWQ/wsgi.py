"""WSGI 入口，供 gunicorn 使用：gunicorn FinalWQ.wsgi:application"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "FinalWQ.settings")

application = get_wsgi_application()
