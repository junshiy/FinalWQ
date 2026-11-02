#!/usr/bin/env python
"""Django 命令行管理入口。"""
import os
import sys


def main():
    """运行管理命令。"""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "FinalWQ.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "无法导入 Django，请确认已激活虚拟环境并执行 make install"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
