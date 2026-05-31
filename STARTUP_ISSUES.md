# AAM 服务启动故障排查文档

## 问题描述

在启动 AAM 服务时遇到导入错误和依赖问题，导致服务无法正常运行。

---

## 错误日志

```
ImportError: cannot import name 'TimeDelta' from 'sqlalchemy'
```

---

## 根本原因

1. **导入错误** - `sqlalchemy` 中不存在 `TimeDelta` 类型
2. **依赖问题** - 部分依赖包需要手动安装
3. **网络问题** - PyPI 源访问受限，需要使用镜像源

---

## 解决方案

### 方案 1：快速修复（推荐）

执行以下命令修复所有导入问题：

```bash
# 1. 修复 base.py 中的导入问题
sed -i 's/, TimeDelta//' app/db/models/base.py
sed -i 's/from datetime import timedelta//' app/db/models/base.py

# 2. 同样修复 execution.py
sed -i 's/, TimeDelta//' app/db/models/execution.py
sed -i 's/from datetime import timedelta//' app/db/models/execution.py

# 3. 同样修复 schedule.py
sed -i 's/, TimeDelta//' app/db/models/schedule.py
sed -i 's/from datetime import timedelta//' app/db/models/schedule.py

# 4. 安装必要依赖
/home/alex/.venv/bin/pip install sqlalchemy paramiko --index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 5. 启动服务
/home/alex/.venv/bin/uvicorn app.api.main:app --host 0.0.0.0 --port 8000
```

---

### 方案 2：临时使用 CLI

如果无法立即修复，可以先使用 CLI 方式管理任务：

```bash
# 查看任务列表
curl http://localhost:8000/api/v1/tasks

# 创建新任务
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "系统监控",
    "command": "uptime, df -h",
    "hosts": "127.0.0.1",
    "task_type": "command"
  }'
```

---

## 访问地址

服务启动后，在 Windows 机器访问：

- **Web 管理界面**: `http://<Ubuntu 服务器 IP>:8000`
- **API 文档**: `http://<Ubuntu 服务器 IP>:8000/docs`
- **测试报告**: `http://<Ubuntu 服务器 IP>:8000/tests/results`

---

## 工具调用限制警告

> ⚠️ Iteration budget reached (90/90)

这是 Hermes Agent 的工具调用次数限制（90 次上限）。

### 原因

启动过程中：
- 依赖问题需要多次重试
- 导入错误需要修改多个文件
- 每次修改后需要重启服务

### 影响

达到限制后无法继续调用工具，需要手动执行修复命令。

---

## 项目状态

### ✅ 已完成
- Web 管理界面（任务管理、通知配置、统计报表）
- 测试报告页面（自动运行单元测试）
- API 接口（任务 CRUD、调度、通知）

### ⚠️ 需要修复
- 数据库模型导入问题（TimeDelta）
- 部分依赖包安装

### 🎯 下一步
1. 执行方案 1 的修复命令
2. 验证服务启动成功
3. 访问 Web 界面测试功能

---

## 相关文档

- [AAM 项目主页](../README.md)
- [API 文档](http://localhost:8000/docs)
- [测试报告](http://localhost:8000/tests/results)

---

**最后更新**: 2026-05-31 21:30
