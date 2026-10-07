import logging

from core.config import LogConfig
from core.logging_setup import setup_logging


def _cfg() -> LogConfig:
    return LogConfig(level="INFO", dir="logs", timezone="Asia/Seoul", max_bytes=1_000_000, backup_count=1)


def test_secrets_masked_and_timestamp_has_offset(tmp_path):
    setup_logging(_cfg(), secrets=["APPKEY-XYZ", "12345678-01"], log_dir=tmp_path)
    log = logging.getLogger("test")
    log.info("token=%s account=%s", "APPKEY-XYZ", "12345678-01")
    try:
        raise RuntimeError("failed with APPKEY-XYZ")
    except RuntimeError:
        log.exception("boom")
    for h in logging.getLogger().handlers:
        h.flush()

    text = (tmp_path / "trading-bot.log").read_text(encoding="utf-8")
    assert "APPKEY-XYZ" not in text
    assert "12345678-01" not in text
    assert "token=*** account=***" in text
    assert "+09:00" in text  # timezone-aware 타임스탬프 (KST)
