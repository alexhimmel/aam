# 🔒 AAM 安全配置指南

## 目录
- [SSH 安全配置](#ssh 安全配置)
- [数据库密码加密](#数据库密码加密)
- [API 认证授权](#api 认证授权)
- [生产环境建议](#生产环境建议)

---

## SSH 安全配置

### 1. 主机密钥验证

**问题**: 默认使用 `AutoAddPolicy()` 会自动接受所有主机密钥，存在中间人攻击风险。

**解决方案**: 创建已知主机密钥文件

```python
# app/core/ssh.py
class SSHConnectionPool:
    def __init__(self, known_hosts_path: Optional[str] = None, ...):
        self.known_hosts_path = known_hosts_path
        # ...
    
    async def _create_connection(self, ...):
        # 使用自定义已知主机文件
        if self.known_hosts_path:
            client.load_host_keys(self.known_hosts_path)
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
```

**创建已知主机密钥**:
```bash
# 首次连接后手动验证
ssh-copy-id user@host
# 或手动添加
ssh -o StrictHostKeyChecking=yes user@host
```

### 2. 使用 SSH 密钥认证（推荐）

**优势**: 比密码更安全可靠

```bash
# 生成密钥对（如果还没有）
ssh-keygen -t ed25519 -C "your_email@example.com"

# 将公钥复制到目标主机
ssh-copy-id root@192.168.1.100

# 配置 AAM 使用密钥
python -m app.cli execute \
  --hosts "192.168.1.100" \
  --command "uptime" \
  --key-file "~/.ssh/id_ed25519"
```

### 3. SSH 配置优化

创建 `~/.ssh/config`:
```bash
Host aam-*
    HostName 192.168.1.100
    User root
    Port 22
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking yes
    ConnectTimeout 10
```

---

## 数据库密码加密

### 1. 使用 bcrypt 加密 SSH 密码

**安装**:
```bash
pip install bcrypt
```

**配置**:
```python
# app/core/ssh.py
import bcrypt

def hash_password(password: str) -> str:
    """加密密码"""
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(
        password.encode('utf-8'),
        hashed.encode('utf-8')
    )
```

**使用**:
```python
# 存储时加密
from app.utils.security import hash_password
task_data['ssh_password'] = hash_password(plain_password)

# 使用时解密
from app.utils.security import verify_password
if verify_password(entered_password, stored_hashed):
    # 使用密码连接
```

### 2. 数据库字段加密

对于 SQLite:
```python
# app/core/database.py
import sqlite3
from cryptography.fernet import Fernet

class EncryptedColumn:
    def __init__(self, key: bytes):
        self.key = key
        self.fernet = Fernet(key)
    
    def encrypt(self, value: str) -> str:
        return self.fernet.encrypt(value.encode()).decode()
    
    def decrypt(self, encrypted: str) -> str:
        return self.fernet.decrypt(encrypted.encode()).decode()

# 初始化
with open('encryption.key', 'rb') as f:
    encryption_key = f.read()
```

---

## API 认证授权

### 1. JWT 令牌认证

**安装**:
```bash
pip install python-jose[cryptography]
```

**配置**:
```python
# app/core/security.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 小时

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
```

**API 路由**:
```python
# app/api/v1/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    user = db.query(User).filter(User.username == token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
```

### 2. 权限控制

```python
# app/api/v1/tasks.py
from fastapi import APIRouter, Depends, HTTPException
from app.api.v1.deps import get_current_user, require_admin

router = APIRouter(prefix="/api/v1/tasks", tags=["任务"])

@router.post("/", response_model=Task)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user)
):
    # 普通用户可以创建任务
    if current_user.role == "user":
        task_data.enabled = False  # 默认禁用
    
    task = TaskService.create_task(task_data.dict())
    return task

@router.get("/statistics", response_model=StatisticsDict)
async def get_statistics(
    days: int = 7,
    current_user: User = Depends(require_admin)  # 只有管理员可以访问
):
    return await TaskService.get_statistics(days)
```

### 3. 登录接口

```python
# app/api/v1/auth.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.security import create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])

class TokenBase(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/login", response_model=TokenResponse)
async def login(token_data: TokenBase):
    # 验证用户名密码
    user = db.query(User).filter(User.username == token_data.username).first()
    if not user or not verify_password(token_data.password, user.password):
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误"
        )
    
    # 创建令牌
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}
    )
    
    return TokenResponse(access_token=access_token)
```

---

## 生产环境建议

### 1. 环境变量

```python
# .env
DATABASE_URL=postgresql://user:password@localhost:5432/aam
SECRET_KEY=your-super-secret-key
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
WEBHOOK_URL=https://hooks.slack.com/services/YOUR_WEBHOOK
```

```python
# app/core/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    SECRET_KEY: str
    DATABASE_URL: str
    # ...
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### 2. 日志配置

```python
# app/utils/logging_config.py
import logging
import sys
from pathlib import Path

def setup_logging(log_dir: str = "logs"):
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    logger = logging.getLogger("aam")
    logger.setLevel(logging.INFO)
    
    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 文件日志
    file_handler = logging.FileHandler(f"{log_dir}/app.log")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger
```

### 3. Gunicorn 部署

```bash
# 安装
pip install gunicorn

# 运行
gunicorn app.api.main:app \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 120 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log
```

### 4. Nginx 反向代理

```nginx
# /etc/nginx/sites-available/aam
server {
    listen 80;
    server_name aam.example.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
    }
    
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
}
```

---

## 快速检查清单

### 开发环境
- [ ] 使用 SQLite 数据库
- [ ] 明文密码（方便调试）
- [ ] 允许 CORS
- [ ] 不启用认证

### 生产环境
- [ ] 使用 PostgreSQL
- [ ] 加密 SSH 密码
- [ ] 启用 JWT 认证
- [ ] 禁用 CORS 或限制域名
- [ ] 配置已知主机密钥
- [ ] 设置日志轮转
- [ ] 配置 SSL/TLS
- [ ] 启用健康检查
- [ ] 设置资源限制

---

## 参考资源

- [Paramiko 文档](https://docs.paramiko.org/)
- [FastAPI 安全](https://fastapi.tiangolo.com/tutorial/security/)
- [bcrypt 文档](https://bcrypt.readthedocs.io/)
- [JWT 规范](https://tools.ietf.org/html/rfc7519)
