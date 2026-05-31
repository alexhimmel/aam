"""
数据库配置文件
"""

# 数据库类型
DATABASE_TYPE = os.getenv('DATABASE_TYPE', 'postgresql')

# PostgreSQL 连接字符串
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://aam:aam@localhost:5432/aam'
)

# SQLite 连接字符串（开发环境）
SQLITE_DB_PATH = os.getenv('SQLITE_DB_PATH', '/tmp/aam.db')

# 连接池配置
POOL_SIZE = int(os.getenv('DATABASE_POOL_SIZE', '10'))
MAX_OVERFLOW = int(os.getenv('DATABASE_MAX_OVERFLOW', '20'))
POOL_RECYCLE = int(os.getenv('DATABASE_POOL_RECYCLE', '3600'))
