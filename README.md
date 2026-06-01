# AAM - 自动化任务管理

## 项目简介

AAM (Automated Task Management) 是一个用于管理自动化任务执行的命令行和 Web 工具，支持简单命令、脚本和文件的远程执行。

### 核心功能

- ✅ **SSH 远程命令执行** - 向目标设备发送命令
- ✅ **定时任务调度** - 自动触发任务执行
- ✅ **结果持久化** - 记录执行日志供后续审查
- ✅ **Web 管理界面** - 可视化任务管理
- ✅ **并发执行** - 支持 20 台设备并发执行
- ✅ **任务类型识别** - 自动判断命令/脚本/文件类型
- ✅ **文件上传执行** - 脚本/文件先上传到目标机器再执行

## 技术栈

- **Python 3.10+**
- **FastAPI** - Web API 框架
- **SQLAlchemy** - ORM 数据库
- **Paramiko** - SSH 客户端（异步支持）
- **APScheduler** - 定时任务调度
- **PostgreSQL** / **SQLite** - 数据库
- **asyncio.to_thread** - 异步/同步混用

## ⚠️ 关键修复（重要）

### Bug 修复
- ✅ **SSH 连接方法**：修复 `get_connection()` 调用方式
- ✅ **认证配置**：支持用户名/密钥/密码多方式认证
- ✅ **异步处理**：使用 `asyncio.to_thread()` 包装 Paramiko 同步调用
- ✅ **批量执行**：修复批量任务执行逻辑

### 架构改进
- ✅ **连接池**：实现 SSH 连接复用机制
- ✅ **健康检查**：添加 `/health`、`/ready`、`/live` 端点
- ✅ **Docker 化**：提供 Dockerfile 和 docker-compose.yml
- ✅ **单元测试**：完整的测试覆盖

### 安全建议
- ⚠️ **SSH 主机密钥验证**：生产环境应验证密钥
- ⚠️ **敏感数据加密**：SSH 密码应加密存储
- ⚠️ **API 认证**：建议添加 JWT 用户认证/授权

## 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate      # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 数据库配置

修改 `config.py` 配置数据库：

```python
# PostgreSQL
DATABASE_TYPE = "postgresql"
DATABASE_URL = "postgresql://aam:***@localhost:5432/aam"

# 或 SQLite（开发环境）
DATABASE_TYPE = "sqlite"
SQLITE_DB_PATH = "/tmp/aam.db"
```

### 3. 初始化数据库

```bash
python init_db.py
```

### 4. 启动服务

```bash
# 方式一：直接运行
uvicorn app.api.main:app --host 0.0.0.0 --port 8000

# 方式二：使用 CLI
python -m app.cli

# 方式三：后台运行
nohup uvicorn app.api.main:app --host 0.0.0.0 --port 8000 > logs/server.log 2>&1 &
```

### 5. Docker 部署（可选）

```bash
# 构建镜像
docker build -t aam .

# 或使用 docker-compose
docker-compose up -d

# 查看日志
docker-compose logs -f aam
```

### 6. 访问界面

- **Web 界面**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

### 1. 环境准备

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate      # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 数据库配置

修改 `config.py` 配置数据库：

```python
# PostgreSQL
DATABASE_TYPE = "postgresql"
DATABASE_URL = "postgresql://aam:aam@localhost:5432/aam"

# 或 SQLite（开发环境）
DATABASE_TYPE = "sqlite"
SQLITE_DB_PATH = "/tmp/aam.db"
```

### 3. 初始化数据库

```bash
python init_db.py
```

### 4. 启动服务

```bash
# 方式一：直接运行
uvicorn app.api.main:app --host 0.0.0.0 --port 8000

# 方式二：使用 CLI
python -m app.cli

# 方式三：后台运行
nohup uvicorn app.api.main:app --host 0.0.0.0 --port 8000 > logs/server.log 2>&1 &
```

### 5. 访问界面

- **Web 界面**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs

## API 使用

### 创建任务

```bash
```bash
curl -X POST http://localhost:8000/api/v1/tasks \\\
  -H "Content-Type: application/json" \\\
  -d '{
    "name": "系统监控",
    "command": "uptime",
    "target_hosts": "192.168.1.1,192.168.1.2",
    "schedule": "0 2 * * *",
    "task_type": "command"
  }'
```

```bash
# 执行脚本（需要先上传）
curl -X POST http://localhost:8000/api/v1/tasks \\\
  -H "Content-Type: application/json" \\\
  -d '{
    "name": "部署脚本",
    "command": "deploy.sh",
    "target_hosts": "192.168.1.1",
    "schedule": "0 6 * * *",
    "task_type": "脚本",
    "working_dir": "/opt/deploy",
    "upload_dir": "/opt/deploy"
  }'
```

```bash
# 执行文件（上传并执行）
curl -X POST http://localhost:8000/api/v1/tasks \\\
  -H "Content-Type: application/json" \\\
  -d '{
    "name": "备份脚本",
    "command": "/backup.sh",
    "target_hosts": "192.168.1.1,192.168.1.2,192.168.1.3",
    "task_type": "文件",
    "working_dir": "/var/backup",
    "upload_dir": "/backup"
  }'
```

### 列出任务

```bash
curl http://localhost:8000/api/v1/tasks
```

### 执行命令（CLI）

```bash
python -m app.cli execute \
  --hosts "192.168.1.1,192.168.1.2" \
  --command "uptime"
```

## 项目结构

```
aam/
├── app/
│   ├── api/                 # API 路由
│   │   ├── v1/             # API v1 版本
│   │   ├── main.py         # 应用入口
│   │   └── deps.py         # 依赖注入
│   ├── core/               # 核心模块
│   │   ├── ssh.py          # SSH 客户端
│   │   ├── sftp.py         # SFTP 上传（新增）
│   │   ├── scheduler.py    # 任务调度器
│   │   ├── executor.py     # 任务执行器
│   │   └── config.py       # 核心配置
│   ├── db/                 # 数据库层
│   │   ├── models/         # 数据模型
│   │   ├── engine.py       # 数据库连接
│   │   └── config.py       # 数据库配置
│   ├── services/           # 业务逻辑层
│   ├── utils/              # 工具函数
│   └── cli.py              # CLI 工具
├── templates/              # Web 模板
├── static/                 # 静态资源
├── migrations/             # 数据库迁移
├── logs/                   # 日志目录
├── config.py              # 配置文件
├── requirements.txt       # 依赖列表
└── README.md
```

## 开发计划

- [x] 任务依赖管理
- [x] 执行超时控制
- [x] 自动重试机制
- [x] 邮件/Webhook 通知
- [x] 任务统计报表

## 新增功能（里程碑 2）

### 通知功能
- [x] 邮件通知（SMTP）
- [x] Webhook 通知（Slack/Discord/钉钉）
- [x] 异步通知集成到任务执行流程
- [x] 通知配置界面

### 监控功能
- [x] 任务统计报表（成功率、耗时）
- [x] 按任务类型统计
- [x] 按主机统计
- [x] 按时间维度统计
- [x] 错误分析
- [x] 统计 API 端点
- [x] 统计展示界面

### API 端点
- `/api/v1/tasks/statistics/overview` - 任务概览
- `/api/v1/tasks/statistics/type` - 按类型统计
- `/api/v1/tasks/statistics/hosts/top/{n}` - 主机统计
- `/api/v1/tasks/statistics/time/{days}` - 时间统计
- `/api/v1/tasks/statistics/duration/top/{n}` - 耗时最长的任务
- `/api/v1/tasks/statistics/errors` - 错误分析
- `/api/v1/tasks/statistics/{task_id}` - 任务详情
- `/api/v1/tasks/statistics/json` - 完整统计（JSON 格式）

## 新增功能（里程碑 1）

- [x] 任务类型识别（command/脚本/文件）
- [x] 文件上传执行（SFTP 上传 + 权限设置）
- [x] 混合执行逻辑（上传→执行）
- [x] 执行路径和权限处理
- [x] 单元测试覆盖

## 许可证

MIT
