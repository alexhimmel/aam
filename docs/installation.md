# 📦 AAM 项目依赖安装指南

## 使用 uv 安装依赖

### 1. 创建虚拟环境

```bash
# 进入项目目录
cd ~/Project/aam

# 创建虚拟环境
uv venv --python python3

# 激活虚拟环境
source .venv/bin/activate
```

### 2. 安装依赖

```bash
# 方式一：使用 requirements_full.txt（推荐）
uv pip sync requirements_full.txt

# 方式二：直接安装 pyproject.toml 中的依赖
uv pip install -e .

# 方式三：只安装基础依赖（生产环境）
uv pip install fastapi uvicorn sqlalchemy pydantic paramiko python-jose

# 方式四：安装开发依赖
uv pip install pytest pytest-asyncio pytest-cov
```

### 3. 验证安装

```bash
# 检查 Python 版本
python --version

# 检查虚拟环境
which python  # 应该在虚拟环境中

# 检查依赖
uv pip list

# 测试 CLI
python -m app.cli --help
```

### 4. 运行项目

```bash
# 方式一：使用 CLI
python -m app.cli init  # 初始化数据库
python -m app.cli execute --help  # 执行命令

# 方式二：启动 Web 服务
uvicorn app.api.main:app --host 0.0.0.0 --port 8000

# 方式三：后台运行
nohup uvicorn app.api.main:app --host 0.0.0.0 --port 8000 > logs/server.log 2>&1 &
```

## 依赖说明

### 核心依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| **fastapi** | ≥0.104.0 | Web API 框架 |
| **uvicorn** | ≥0.24.0 | ASGI 服务器 |
| **sqlalchemy** | ≥2.0.23 | ORM 数据库 |
| **paramiko** | ≥3.4.0 | SSH 客户端 |
| **pydantic** | ≥2.5.0 | 数据验证 |
| **python-jose** | ≥3.3.0 | JWT 认证 |

### 密码学依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| **cryptography** | ≥41.0.0 | 加密功能 |
| **bcrypt** | ≥4.0.0 | 密码哈希 |
| **pynacl** | ≥1.5.0 | SSH 密钥认证 |

### 可选依赖

| 包名 | 用途 |
|------|------|
| **APScheduler** | 定时任务调度 |
| **redis** | 消息队列缓存 |
| **celery** | 异步任务队列 |

## 常见问题

### 1. 依赖冲突

```bash
# 重新同步依赖
uv pip sync requirements_full.txt

# 或更新特定包
uv pip install --upgrade 包名
```

### 2. 安装失败

```bash
# 清理缓存
uv pip cache purge

# 重新安装
uv pip install -e .
```

### 3. 检查依赖

```bash
# 查看已安装包
uv pip list

# 查看缺失依赖
uv pip install -e . --dry-run
```

## 生产环境部署

### 最小化依赖

```bash
# 只安装运行必需的包
uv pip install fastapi uvicorn sqlalchemy pydantic paramiko python-jose python-dotenv
```

### 使用 Docker

```bash
# 构建镜像
docker build -t aam .

# 或使用 docker-compose
docker-compose up -d
```

## 卸载依赖

```bash
# 删除虚拟环境
rm -rf .venv

# 或卸载所有包
uv pip uninstall -y 包名
```

## 更新依赖

```bash
# 更新所有依赖到最新版本
uv pip install --upgrade -r requirements_full.txt

# 或更新特定包
uv pip install --upgrade 包名
```

## 参考资源

- [uv 官方文档](https://docs.astral.sh/uv/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 文档](https://www.sqlalchemy.org/)
