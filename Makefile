.PHONY: help all install migrate lint test format run clean distclean

PY      := .venv/bin/python
PIP     := .venv/bin/pip
# 自动优先使用 python3.11（Alibaba Cloud Linux 3 自带 python3 为 3.6，装不了 Django 4.2）
# 需要指定时可覆盖：make install PYTHON=/usr/bin/python3.11
PYTHON  ?= $(shell command -v python3.11 >/dev/null 2>&1 && echo python3.11 || echo python3)
DJANGO  := $(PY) manage.py

.DEFAULT_GOAL := help

help: ## 显示可用目标
	@echo "FinalWQ — 网络操作系统期末实操考核"
	@echo ""
	@echo "用法: make <目标>"
	@echo ""
	@echo "  install   创建 .venv 虚拟环境并安装 requirements.txt"
	@echo "  migrate   生成并执行数据库迁移"
	@echo "  lint      运行 pylint 静态检查"
	@echo "  test      运行 pytest 单元测试"
	@echo "  format    运行 black 代码格式化"
	@echo "  run       启动开发服务器 0.0.0.0:8000"
	@echo "  all       format -> lint -> test 一键全流程"
	@echo "  clean     清理 __pycache__ / .pytest_cache"
	@echo "  distclean 清理缓存并删除 .venv（谨慎）"

all: format lint test ## 全流程：格式化 + 检查 + 测试

.venv/bin/python:
	@echo ">> 创建虚拟环境 .venv"
	$(PYTHON) -m venv .venv

install: .venv/bin/python ## 安装依赖到 .venv
	@echo ">> 升级 pip 并安装依赖"
	$(PIP) install -U pip -q
	$(PIP) install -r requirements.txt
	@echo ">> 完成，当前解释器：$(PY)"

migrate: install ## 数据库迁移
	$(DJANGO) makemigrations faultdiag --noinput
	$(DJANGO) migrate --noinput

lint: ## 静态检查（pylint）
	@echo ">> pylint 检查中"
	$(PY) -m pylint faultdiag FinalWQ --output-format=colorized

test: ## 单元测试（pytest）
	@echo ">> pytest 运行中"
	$(PY) -m pytest -q

format: ## 代码格式化（black）
	@echo ">> black 格式化"
	$(PY) -m black .

run: ## 开发服务器（公网需 0.0.0.0）
	$(DJANGO) runserver 0.0.0.0:8000

clean: ## 清理缓存
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache
	@echo ">> 缓存已清理"

distclean: clean ## 清理缓存 + 删除虚拟环境
	rm -rf .venv
	@echo ">> .venv 已删除，需要重新 make install"
