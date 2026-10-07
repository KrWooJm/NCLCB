from __future__ import annotations

from core.broker.base import Broker
from core.config import AppConfig
from core.execution.base import Executor
from core.execution.notify import NotifyExecutor
from core.execution.paper import PaperExecutor


class LiveExecutorNotAvailable(RuntimeError):
    """실계좌 주문은 사용자가 명시적으로 요청하기 전까지 구현·활성화하지 않는다."""


def build_executor(app: AppConfig, broker: Broker | None = None) -> Executor:
    if app.executor == "notify":
        return NotifyExecutor()
    if app.executor == "paper":
        if broker is None:
            raise ValueError("paper 모드에는 모의투자 Broker가 필요합니다")
        return PaperExecutor(broker)
    if app.executor == "live":
        raise LiveExecutorNotAvailable(
            "LiveExecutor는 아직 구현되지 않았습니다. config/app.yaml의 executor를 notify 또는 paper로 설정하세요."
        )
    raise ValueError(f"알 수 없는 executor: {app.executor}")
