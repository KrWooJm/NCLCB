"""로깅 설정: 콘솔 + 회전 파일, 비밀값 마스킹, timezone-aware 타임스탬프."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from zoneinfo import ZoneInfo

from core.config import PROJECT_ROOT, LogConfig

MASK = "***"
_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


class SecretMaskingFilter(logging.Filter):
    """로그 메시지·인자에 섞인 비밀값을 가린다."""

    def __init__(self, secrets: Iterable[str]) -> None:
        super().__init__()
        # 긴 값부터 치환해야 부분 문자열 충돌이 없다
        self._secrets = sorted({s for s in secrets if s}, key=len, reverse=True)

    def mask(self, text: str) -> str:
        for s in self._secrets:
            text = text.replace(s, MASK)
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        if self._secrets:
            record.msg = self.mask(record.getMessage())
            record.args = None
            if record.exc_info and not record.exc_text:
                record.exc_text = logging.Formatter().formatException(record.exc_info)
            if record.exc_text:
                record.exc_text = self.mask(record.exc_text)
        return True


class TzFormatter(logging.Formatter):
    """ISO 8601 + UTC 오프셋 타임스탬프 (예: 2026-10-07T09:15:00.123+09:00)."""

    def __init__(self, tz: ZoneInfo) -> None:
        super().__init__(_FORMAT)
        self._tz = tz

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        return datetime.fromtimestamp(record.created, self._tz).isoformat(timespec="milliseconds")


def setup_logging(cfg: LogConfig, secrets: Iterable[str] = (), *, log_dir: Path | None = None) -> None:
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
        h.close()
    root.setLevel(cfg.level)

    directory = log_dir or (PROJECT_ROOT / cfg.dir)
    directory.mkdir(parents=True, exist_ok=True)

    formatter = TzFormatter(ZoneInfo(cfg.timezone))
    mask = SecretMaskingFilter(secrets)
    handlers: list[logging.Handler] = [
        logging.StreamHandler(),
        RotatingFileHandler(
            directory / "trading-bot.log",
            maxBytes=cfg.max_bytes,
            backupCount=cfg.backup_count,
            encoding="utf-8",
        ),
    ]
    for h in handlers:
        h.setFormatter(formatter)
        h.addFilter(mask)
        root.addHandler(h)
