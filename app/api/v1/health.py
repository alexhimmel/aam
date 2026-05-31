"""
健康检查 API
"""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["健康检查"])

@router.get("/")
async def health_check():
    """服务健康检查"""
    return {
        "status": "healthy",
        "service": "AAM",
        "version": "0.1.0"
    }

@router.get("/ready")
async def readiness_check():
    """就绪检查"""
    return {"status": "ready"}

@router.get("/live")
async def liveness_check():
    """存活检查"""
    return {"status": "alive"}
