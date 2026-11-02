# FinalWQ · Linux 实验故障智能诊断

> 网络操作系统（Linux）期末实操考核 · 功能点 D
> 作者：wangqi（WQ）｜ 云主机：47.106.85.63

一个把「学生粘贴的终端报错」转换成「根因 + 可执行修复命令 + 验证命令」的 Django 应用。
覆盖 `systemctl`、`nginx`、`ssh`、`pip/venv`、`git`、磁盘、网络、文件句柄等 12 类高频实验故障。

## 一、项目功能

1. **报错诊断**：粘贴一段报错文本，返回按置信度排序的候选根因（默认 Top3）。
2. **置信度门控**：低于 55 分不硬给结论，直接提示"转人工复核"，避免误导。
3. **引用溯源**：每条结论必须携带知识来源与验证命令，结论可被证伪。
4. **JSON API**：`GET /api/diagnose?q=<报错文本>`，方便脚本或前端异步调用。
5. **诊断留痕**：`DiagnosisRecord` 记录每次诊断的命中规则、置信度、耗时，用于统计采纳率与高频问题。

### 为什么加入"智能"之后效果更好

- **没有它**：学生卡在一条报错上，先在班群发截图，平均等 20~40 分钟才有人回；教师反复回答同一批问题。
- **有它之后**：毫秒级给出候选根因和验证命令，把"等答案"变成"自己验"；教师只处理低置信度的长尾问题。
- **可量化**：首次响应时长从分钟级降到毫秒级；同类问题重复答疑量下降；答案采纳率与知识点掌握度可通过留痕表统计。

## 二、技术栈

| 层次 | 选型 | 说明 |
|---|---|---|
| Web 框架 | Django 4.2 LTS | MTV 分层，模板 + 视图 + 服务层解耦 |
| 应用服务器 | Gunicorn 22 | WSGI，2 worker，systemd 托管 |
| 反向代理 | Nginx 1.20+ | 80 端口反代 127.0.0.1:8000，静态文件直出 |
| 运行环境 | Python 3.9+ / venv | 依赖全部装在 `.venv`，不污染全局 |
| 数据存储 | SQLite | 单机实验场景够用，免去额外运维 |
| 质量保障 | pylint / pytest / black | 静态检查、8 条单测、格式化，全部收进 Makefile |

## 三、目录结构

```
FinalWQ/
├── manage.py                 # Django 管理入口
├── requirements.txt          # 依赖清单（venv 内安装）
├── Makefile                  # install/lint/test/format/all/help/run
├── pyproject.toml            # black 与 pytest 配置
├── .pylintrc                 # pylint 配置（加载 pylint-django）
├── .gitignore
├── FinalWQ/                  # 项目配置包
│   ├── settings.py           # 配置（SECRET_KEY/ALLOWED_HOSTS 支持环境变量覆盖）
│   ├── urls.py               # 根路由
│   ├── wsgi.py               # gunicorn 入口
│   └── asgi.py
├── faultdiag/                # 功能点 D 对应的 APP
│   ├── knowledge.py          # 故障知识库（12 条规则，含根因/步骤/验证/来源）
│   ├── services.py           # 诊断引擎（正则匹配 + 置信度打分 + 阈值门控）
│   ├── views.py              # 页面视图与 JSON API
│   ├── urls.py               # / 与 /index 路由
│   ├── models.py             # 诊断留痕表
│   ├── admin.py              # 后台注册
│   └── test_services.py      # 8 条单元测试
├── templates/index.html      # 诊断页面（任务 6.1 的 index.html）
├── static/css/style.css      # 页面样式
├── deploy/
│   ├── nginx-finalwq.conf    # Nginx 站点配置
│   └── finalwq.service       # gunicorn 的 systemd unit
└── docs/                     # 任务一论证、实验报告
```

## 四、本地启动步骤

```bash
# 1. 克隆
git clone https://gitee.com/<你的账号>/FinalWQ.git
cd FinalWQ

# 2. 建虚拟环境并装依赖（等价于 python3 -m venv .venv + pip install -r requirements.txt）
make install

# 3. 初始化数据库（可选，进后台才需要）
make migrate

# 4. 启动开发服务器
make run          # 监听 0.0.0.0:8000
```

浏览器访问 `http://127.0.0.1:8000/index`，点「填入示例」→「开始诊断」即可看到结果。

质量检查三连：

```bash
make format   # black 格式化
make lint     # pylint 静态检查（目标 10.00/10）
make test     # pytest（8 passed）
```

## 五、云主机部署步骤

环境：Alibaba Cloud ECS · Ubuntu/Debian 系（RHEL 系的差异见每步备注）

### 1. 系统准备

```bash
# RHEL/Rocky/AlmaLinux/Alibaba Cloud Linux（本次实测环境：alinux 3）
dnf install -y git nginx python3.11 python3.11-pip

# Debian/Ubuntu（差异点：包管理器）
# apt-get update && apt-get install -y python3 python3-venv python3-pip git nginx
```

> 系统自带的 `python3` 若是 3.6/3.7，装不了 Django 4.2。本项目 Makefile 会自动优先使用
> `python3.11` 创建虚拟环境，可用 `make install PYTHON=/usr/bin/python3.11` 手动指定。

### 2. 拉代码并安装依赖

```bash
cd /root
git clone https://gitee.com/<你的账号>/FinalWQ.git
cd FinalWQ
make install          # 自动创建 .venv 并安装 requirements.txt
```

### 3. 数据库与静态文件

```bash
make migrate
```

### 4. 启动应用（二选一）

```bash
# 方式 A：前台调试（任务 5.2 截图阶段用这个）
make run

# 方式 B：gunicorn + systemd 常驻（推荐最终形态）
cp deploy/finalwq.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now finalwq
systemctl status finalwq --no-pager
```

### 5. 配置 Nginx 反向代理

```bash
cp deploy/nginx-finalwq.conf /etc/nginx/sites-available/finalwq.conf
ln -sf /etc/nginx/sites-available/finalwq.conf /etc/nginx/sites-enabled/finalwq.conf
rm -f /etc/nginx/sites-enabled/default       # 避免默认站点抢占 80
nginx -t && systemctl reload nginx
systemctl enable nginx

# RHEL 系没有 sites-available 机制，直接放 conf.d：
# cp deploy/nginx-finalwq.conf /etc/nginx/conf.d/finalwq.conf
```

### 6. 放行端口（两层都要开）

```bash
# 本机防火墙
# Ubuntu: ufw allow 80/tcp && ufw allow 22/tcp
# RHEL:   firewall-cmd --permanent --add-service=http && firewall-cmd --reload
```

⚠️ **Alibaba Cloud 安全组必须单独放行 80 端口**（控制台 → 实例 → 安全组 → 配置规则 → 入方向），只在系统里开防火墙是不够的。

### 7. 验证

```bash
ss -tlnp | grep -E ':(80|8000)'      # 80 由 nginx 监听，8000 由 gunicorn 监听
curl -I http://127.0.0.1/            # 200
```

浏览器访问 `http://47.106.85.63/index`。

## 六、常见问题

**Q1：访问公网 IP 显示 Django 小火箭，访问 /index 却 404？**
小火箭只在 `urlpatterns` 为空时出现。任务 5.2 截图时把 `FinalWQ/urls.py` 的 `urlpatterns` 临时改成 `[]`，截完图恢复即可。

**Q2：502 Bad Gateway？**
上游没起来。`systemctl status finalwq` 看状态，`curl -I http://127.0.0.1:8000/` 直连后端确认；常见原因是 systemd 里写了裸 `python` 而不是 `.venv/bin/gunicorn` 的绝对路径。

**Q3：页面能开但样式丢失？**
`location /static/` 的 alias 指向与实际目录不一致；或 `settings.py` 里 `STATICFILES_DIRS` 没包含 `static` 目录。

**Q4：`sudo: unable to resolve host xxx`？**
改了 hostname 但没同步 `/etc/hosts`。Debian 系补 `127.0.1.1 <hostname>`，RHEL 系补 `127.0.0.1 <hostname>`。

## 七、安全说明

- `SECRET_KEY`、`ALLOWED_HOSTS`、`DEBUG` 全部支持环境变量覆盖，生产环境用 `DJANGO_DEBUG=0`。
- `.venv/`、`db.sqlite3` 不进仓库，避免把环境与数据推到公开仓库。
- 应用本身不接收上传文件、不拼接 shell 命令，诊断规则只做文本匹配，不存在命令注入面。
