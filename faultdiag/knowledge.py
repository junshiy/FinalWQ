"""Linux 实验故障知识库。

每条规则描述一类典型报错：
    patterns  触发该规则的正则（不区分大小写），命中越多置信度越高
    cause     根因说明
    steps     排查/修复步骤（命令可直接复制执行）
    verify    修复后的验证命令
    source    知识来源，用于「引用溯源」展示
    tags      辅助加权关键词
"""

RULES = [
    {
        "id": "disk_full",
        "title": "磁盘空间耗尽：No space left on device",
        "patterns": [
            r"no space left on device",
            r"cannot write.*disk.*full",
            r"write error.*no space",
            r"df:\s*no space",
        ],
        "cause": (
            "目标文件系统 inode 或 block 用尽。常见于 /var/log 日志未轮转、"
            "/tmp 残留、Docker 镜像层堆积，也可能只是 inode 耗尽（df -i 显示 100%）。"
        ),
        "steps": [
            "定位满的是哪个挂载点：df -hT 与 df -i（两者都要看，inode 满时 df -h 仍显示有空间）",
            "从根目录逐层找大头：du -xhd1 / 2>/dev/null | sort -rh | head -20",
            "定位 /var 下大文件：du -xhd2 /var 2>/dev/null | sort -rh | head -20",
            "已删除但仍被进程占用的文件不会释放空间：lsof +L1 | head",
            "确认可清理对象后清日志（不要直接 rm 正在写的日志，用 truncate 更安全）：truncate -s 0 /var/log/<文件>",
            "journald 占用过大时限制体积：journalctl --vacuum-size=200M",
            "清理完成再验证，并给 /var/log 配 logrotate 防复发",
        ],
        "verify": "df -hT && df -i",
        "source": "man df / man du / man lsof，Red Hat 存储排查指南",
        "tags": ["磁盘", "disk", "inode"],
    },
    {
        "id": "port_in_use",
        "title": "端口被占用：Address already in use",
        "patterns": [
            r"address already in use",
            r"bind\(\) to .* failed",
            r"errno 98",
            r"\[emerg\].*bind",
        ],
        "cause": (
            "目标端口已被其他进程监听（旧进程未退出、重复启动、或被 nginx/apache 抢占）。"
            "systemd 服务启动失败时，真实原因往往藏在 journalctl 而不是 systemctl status 的摘要里。"
        ),
        "steps": [
            "查谁占了端口：ss -tlnp | grep -E ':(80|8000|443)\\b'",
            "按 PID 看进程详情：ps -fp <PID>",
            "确认是本项目的旧进程后再处理：systemctl stop <服务名> 优先，其次 kill -TERM <PID>",
            "仍不退出再 kill -9 <PID>（最后手段，可能丢数据）",
            "长期方案：改端口，或用 systemd 的 Restart= 与 ExecStartPre 做端口健康检查",
        ],
        "verify": "ss -tlnp | grep ':8000' ; systemctl status <服务名> --no-pager",
        "source": "man ss / man systemd.service",
        "tags": ["端口", "port", "bind"],
    },
    {
        "id": "nginx_502",
        "title": "Nginx 502 Bad Gateway（反代后端不可用）",
        "patterns": [
            r"502 bad gateway",
            r"connect\(\) failed.*upstream",
            r"upstream.*connection refused.*while connecting to upstream",
            r"no live upstreams",
        ],
        "cause": (
            "Nginx 本身正常，但它转发到的上游（127.0.0.1:8000）没有进程监听、"
            "或监听在 127.0.0.1 之外的地址不匹配、或后端进程崩溃。"
        ),
        "steps": [
            "看 nginx 错误日志确认上游地址：tail -n 50 /var/log/nginx/error.log",
            "确认后端是否在跑：curl -I http://127.0.0.1:8000/ 与 ss -tlnp | grep 8000",
            "后端未启动就拉起：cd /root/FinalWQ && make run（或 systemctl start finalwq）",
            "确认 proxy_pass 与后端监听地址一致（runserver 0.0.0.0:8000 才允许本机以外访问）",
            "检查 SELinux 是否拦截反代：getenforce；临时验证 setsebool -P httpd_can_network_connect 1",
            "改完 reload：nginx -t && systemctl reload nginx",
        ],
        "verify": "curl -I http://127.0.0.1:8000/ ; curl -I http://127.0.0.1/",
        "source": "Nginx 官方文档 ngx_http_proxy_module",
        "tags": ["nginx", "502", "反向代理"],
    },
    {
        "id": "module_not_found",
        "title": "Python 模块缺失：ModuleNotFoundError / No module named",
        "patterns": [
            r"modulenotfounderror",
            r"no module named",
            r"importerror: cannot import name",
            r"django\.core\.exceptions\.improperlyconfigured",
        ],
        "cause": (
            "当前解释器不是虚拟环境里的解释器。典型场景：venv 未激活、用 sudo 执行导致 "
            "PATH 重置到系统 python、或 systemd 的 ExecStart 写了裸 python3。"
        ),
        "steps": [
            "确认当前解释器：which python3 && python3 -V",
            "激活虚拟环境：cd /root/FinalWQ && source .venv/bin/activate",
            "再确认：which python3（应指向 /root/FinalWQ/.venv/bin/python3）",
            "重装依赖：make install 或 .venv/bin/pip install -r requirements.txt",
            "systemd 场景必须写绝对路径：ExecStart=/root/FinalWQ/.venv/bin/gunicorn ...",
            "sudo 场景用 sudo 的绝对路径：sudo /root/FinalWQ/.venv/bin/python3 ...",
        ],
        "verify": ".venv/bin/python3 -c \"import django; print(django.get_version())\"",
        "source": "Python 官方 venv 文档；Django 部署检查清单",
        "tags": ["python", "虚拟环境", "venv"],
    },
    {
        "id": "ssh_permission_denied",
        "title": "SSH 认证失败：Permission denied (publickey)",
        "patterns": [
            r"permission denied \(publickey",
            r"no supported authentication methods available",
            r"too many authentication failures",
            r"host key verification failed",
        ],
        "cause": (
            "服务端不接受密码登录（PasswordAuthentication no）、公钥未写入 "
            "~/.ssh/authorized_keys、或家目录/文件权限过宽导致 sshd 拒绝读取。"
        ),
        "steps": [
            "绕过 VSCode 在本机命令行直接试：ssh -v root@<IP>，看协商停在哪个阶段",
            "看服务端日志（有控制台/VNC 时）：journalctl -u sshd -n 50",
            "检查服务端权限：chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys && chown -R root:root ~/.ssh",
            "确认 sshd 配置：grep -Ei 'PasswordAuthentication|PubkeyAuthentication' /etc/ssh/sshd_config",
            "改过配置要 systemctl reload sshd（Debian 服务名可能是 ssh）",
            "本机多把私钥导致失败时指定身份：ssh -i ~/.ssh/id_ed25519 root@<IP>",
        ],
        "verify": "ssh -o BatchMode=yes root@<IP> 'hostname' ; journalctl -u sshd -n 20",
        "source": "man sshd_config / man ssh",
        "tags": ["ssh", "登录", "公钥"],
    },
    {
        "id": "sudo_unable_resolve_host",
        "title": "sudo 报错：unable to resolve host",
        "patterns": [
            r"unable to resolve host",
            r"sudo:.*unknown host",
            r"no address associated with hostname",
        ],
        "cause": (
            "主机名不在 /etc/hosts 中。Ubuntu 系默认用 127.0.1.1 <hostname> 映射本机名，"
            "改了 hostname 却没同步 /etc/hosts，或删掉了 127.0.1.1 那行，"
            "sudo 做解析时失败（报错但不影响执行）。"
        ),
        "steps": [
            "看当前主机名：hostname && cat /etc/hostname",
            "看解析是否命中：getent hosts \"$(hostname)\"",
            "补映射（Debian 系写在 127.0.1.1，RHEL 系写在 127.0.0.1）：vim /etc/hosts",
            "写入示例：127.0.1.1  wangqi",
            "保存后验证 getent hosts wangqi 能返回 127.0.1.1",
        ],
        "verify": "getent hosts \"$(hostname)\" && sudo -n true && echo sudo-ok",
        "source": "man 5 hosts；Ubuntu 主机名行为说明",
        "tags": ["hostname", "hosts", "sudo"],
    },
    {
        "id": "command_not_found",
        "title": "命令不存在：command not found",
        "patterns": [
            r"command not found",
            r"no such file or directory.*usr/bin",
            r"bash: [a-z0-9_.-]+: not found",
        ],
        "cause": (
            "包未安装、二进制不在 PATH 中，或（最常见）在非交互 shell 里依赖了 "
            "只有 ~/.bashrc 才有的 PATH / alias / conda 环境。"
        ),
        "steps": [
            "确认是否装了：rpm -qf $(command -v git) 或 dpkg -S $(command -v git)",
            "看 PATH：echo $PATH",
            "按发行版安装：apt-get install -y <包名> / dnf install -y <包名>",
            "确认软件实际路径：ls -l /usr/local/bin /usr/bin | grep <命令>",
            "持久化 PATH 写 /etc/profile.d/*.sh，而不是只写 ~/.bashrc（systemd/cron 不加载 bashrc）",
        ],
        "verify": "command -v <命令> && <命令> --version",
        "source": "man bash（PATH 与启动文件加载顺序）",
        "tags": ["path", "安装", "命令"],
    },
    {
        "id": "connection_refused",
        "title": "连接被拒绝：Connection refused / timed out",
        "patterns": [
            r"connection refused",
            r"connection timed out",
            r"failed to connect to .* port",
            r"curl: \(7\)",
            r"could not connect to server",
        ],
        "cause": (
            "服务未启动、只监听 127.0.0.1、或被安全组/本机防火墙拦住。"
            "Alibaba Cloud 需要在控制台安全组放行端口，仅开 firewalld/ufw 是不够的。"
        ),
        "steps": [
            "先在本机自测，排除网络因素：curl -I http://127.0.0.1:<端口>/",
            "看监听地址：ss -tlnp | grep <端口>（0.0.0.0 才对公网可达）",
            "看服务状态与日志：systemctl status nginx --no-pager ; tail -n 50 /var/log/nginx/error.log",
            "查本机防火墙：firewall-cmd --list-ports（RHEL）/ ufw status verbose（Ubuntu）",
            "⚠️ 云厂商安全组必须单独放行 80/443（控制台 → 安全组 → 入方向）",
            "最后用外部视角验证：curl -I http://<公网IP>/",
        ],
        "verify": "ss -tlnp | grep -E ':(80|8000)' ; curl -I http://127.0.0.1/",
        "source": "RFC 793（RST 语义）；Alibaba Cloud 安全组文档",
        "tags": ["防火墙", "安全组", "网络"],
    },
    {
        "id": "dns_resolve",
        "title": "域名解析失败：Could not resolve host",
        "patterns": [
            r"could not resolve host",
            r"temporary failure in name resolution",
            r"name or service not known",
            r"dns.*timeout",
        ],
        "cause": "/etc/resolv.conf 缺失或指向不可用 DNS；容器/云主机重建后 resolv.conf 被覆盖也常见。",
        "steps": [
            "看配置：cat /etc/resolv.conf",
            "直连测试 DNS：dig @223.5.5.5 gitee.com +short（无 dig 用 getent hosts gitee.com）",
            "临时补 DNS：echo 'nameserver 223.5.5.5' > /etc/resolv.conf",
            "systemd-resolved 环境用 resolvectl status 查真实上游",
            "云主机建议在控制台 VPC 侧配置 DNS，避免重启被覆盖",
        ],
        "verify": "getent hosts gitee.com && curl -I https://gitee.com",
        "source": "man 5 resolv.conf",
        "tags": ["dns", "解析", "网络"],
    },
    {
        "id": "readonly_fs",
        "title": "文件系统只读：Read-only file system",
        "patterns": [
            r"read-only file system",
            r"cannot create regular file.*read-only",
            r"input/output error.*ext4",
        ],
        "cause": (
            "ext4/xfs 检测到元数据错误或 IO 异常，自动 remount 为只读以保护数据。"
            "直接 remount rw 只是掩盖问题，磁盘可能已经坏了。"
        ),
        "steps": [
            "确认挂载状态：mount | grep ' ro,' ; dmesg -T | tail -50",
            "查是否有 IO 错误：dmesg -T | grep -iE 'i/o error|ext4-fs error|medium error'",
            "⚠️ 风险提醒：先备份能读的数据，再考虑 fsck（需卸载或进救援模式）",
            "云盘场景优先在控制台做磁盘快照，然后更换/扩容云盘",
            "根分区只读时无法在线修复，需从控制台重启进救援模式：fsck -y /dev/vda1",
        ],
        "verify": "mount | grep -w / ; dmesg -T | tail -20",
        "source": "man ext4 / man fsck.ext4；内核 ext4 文档",
        "tags": ["磁盘", "只读", "io"],
    },
    {
        "id": "too_many_open_files",
        "title": "文件句柄耗尽：Too many open files",
        "patterns": [
            r"too many open files",
            r"emfile",
            r"worker_connections are not enough",
        ],
        "cause": "进程 fd 上限（ulimit -n / systemd LimitNOFILE）过低，或连接未正确关闭导致泄漏。",
        "steps": [
            "看当前限制：ulimit -n ; cat /proc/<PID>/limits | grep 'open files'",
            "统计该进程句柄数：lsof -p <PID> | wc -l",
            "临时提高（仅当前会话）：ulimit -n 65535",
            "持久化：/etc/security/limits.conf 写 * soft nofile 65535 / * hard nofile 65535",
            "systemd 服务在 unit 里写 LimitNOFILE=65535（limits.conf 对它无效）",
            "nginx 还要同步 worker_rlimit_nofile 与 worker_connections",
        ],
        "verify": "ulimit -n ; systemctl show <服务名> -p LimitNOFILE",
        "source": "man limits.conf / man systemd.exec",
        "tags": ["句柄", "ulimit", "性能"],
    },
    {
        "id": "git_push_rejected",
        "title": "Git 推送失败：rejected / authentication failed",
        "patterns": [
            r"failed to push some refs",
            r"\[rejected\].*non-fast-forward",
            r"authentication failed for",
            r"support for password authentication was removed",
            r"remote: .*denied",
        ],
        "cause": (
            "本地与远端历史分叉（远端有 README/initial commit）、或 Gitee 已不支持账号密码推送，"
            "必须使用私人令牌（Private Token）或 SSH key。"
        ),
        "steps": [
            "先拉后推：git pull --rebase origin master",
            "确认分支名一致：git branch -vv ; git remote show origin",
            "Gitee 用私人令牌：设置 → 私人令牌 → 生成，推送时密码处填令牌",
            "或改用 SSH：ssh-keygen -t ed25519 -C 'wangqi' 后把公钥贴到 Gitee → 设置 → SSH 公钥",
            "验证连通：ssh -T git@gitee.com",
            "凭据缓存：git config --global credential.helper store（令牌会明文存本地，注意安全）",
        ],
        "verify": "git remote -v && git log --oneline -3 && ssh -T git@gitee.com",
        "source": "Git 官方文档；Gitee 帮助中心（私人令牌 / SSH 公钥）",
        "tags": ["git", "gitee", "推送"],
    },
]
