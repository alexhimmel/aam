"""
FastAPI 应用入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# 创建 FastAPI 应用
app = FastAPI(
    title="AAM - 自动化任务管理",
    description="Automated Task Management API",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 配置（开发环境）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 应用状态
app.state.running = True


@app.on_event("startup")
async def startup_event():
    """启动时初始化"""
    print("=" * 50)
    print("AAM 服务启动")
    print("=" * 50)
    
    # 初始化数据库
    from app.db.engine import init_db
    init_db()
    
    print("服务就绪")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理"""
    from app.core.ssh import SSHConnectionPool
    pool = SSHConnectionPool()
    await pool.close_all()
    print("SSH 连接已关闭")


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "AAM"}


# 测试报告页面
@app.get("/tests/results")
async def test_report_page():
    """测试报告 HTML 页面"""
    return FileResponse("templates/test_report.html", media_type="text/html")


# 根路径 - 命令执行界面
@app.get("/")
async def root():
    """命令执行 HTML 界面"""
    return FileResponse("templates/command_execution.html", media_type="text/html")


# ==================== 路由注册 ====================
from app.api.v1 import tasks, schedules, statistics, test_reports

app.include_router(tasks.router, prefix="/api/v1")
app.include_router(schedules.router, prefix="/api/v1")
app.include_router(statistics.router, prefix="/api/v1")
app.include_router(test_reports.router, prefix="/api/v1")
