from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.models import Signal


@runtime_checkable
class Executor(Protocol):
    """리스크 가드를 통과한 신호를 실행한다. 구현체는 config/app.yaml의 executor로 선택."""

    def execute(self, signal: Signal) -> None: ...
