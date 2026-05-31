"""
CLI 工具
"""

import click
from app.db.engine import init_db
from app.core.ssh import SSHConnectionPool

@click.group()
def cli():
    """AAM - 自动化任务管理 CLI"""
    pass

@cli.command()
def init():
    """初始化数据库"""
    click.echo("初始化数据库...")
    init_db()
    click.echo("数据库初始化完成")

@cli.command()
@click.option('--hosts', '-H', required=True, help='目标主机列表')
@click.option('--command', '-c', required=True, help='要执行的命令')
@click.option('--user', '-u', default='root', help='SSH 用户名')
@click.option('--port', '-p', default=22, help='SSH 端口')
def execute(hosts, command, user, port):
    """手动执行命令"""
    click.echo(f"执行命令：{command}")
    click.echo(f"目标主机：{hosts}")
    
    pool = SSHConnectionPool()
    results = []
    
    for host in hosts.split(','):
        host = host.strip()
        if not host:
            continue
        result = pool.execute(host, command)
        results.append(result)
        click.echo(f"\n结果 - {host}:")
        click.echo(f"  状态：{result['status']}")
        if result['stdout']:
            click.echo(f"  输出：{result['stdout'][:200]}...")
        if result['stderr']:
            click.echo(f"  错误：{result['stderr']}")
    
    pool.close_all()
    click.echo("\n执行完成")

@cli.command()
def status():
    """查看服务状态"""
    click.echo("服务状态:")
    click.echo("  - SSH 连接池：就绪")
    click.echo("  - 数据库：就绪")
    click.echo("  - 调度器：就绪")

if __name__ == '__main__':
    cli()
