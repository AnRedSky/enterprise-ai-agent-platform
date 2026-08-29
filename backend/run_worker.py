"""Worker Service 独立启动脚本。

职责：提供本地开发与部署系统统一的 Worker Service 进程入口。
边界：不启动 FastAPI、不启动 Scheduler；Worker 消费 Workflow Execution 与 Webhook Delivery Durable Fact。
"""

import os

from app.entrypoints.worker import main


def print_startup_info() -> None:
    """打印 Worker Service 的关键非敏感启动信息。"""
    print("=" * 64, flush=True)
    print("Enterprise AI Agent Platform - Worker Service", flush=True)
    print("=" * 64, flush=True)
    print("Service       : worker", flush=True)
    print("Transport     : PostgreSQL Durable Facts", flush=True)
    print("Workflow      : pending WorkflowExecution", flush=True)
    print(
        f"Webhook       : concurrency={os.getenv('WEBHOOK_WORKER_CONCURRENCY', '4')}, "
        f"poll={os.getenv('WEBHOOK_WORKER_POLL_INTERVAL', '0.2')}s, "
        f"lease={os.getenv('WEBHOOK_WORKER_LEASE_SECONDS', '60')}s",
        flush=True,
    )
    print("HTTP API      : none (independent background service)", flush=True)
    print("Scheduler     : run_scheduler.py (independent process)", flush=True)
    print("API Service   : run.py (independent process)", flush=True)
    print("=" * 64, flush=True)


if __name__ == "__main__":
    print_startup_info()
    main()
