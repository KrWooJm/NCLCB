"""설정 로더.

- config/app.yaml      → AppConfig
- config/strategy.yaml → StrategyConfig (전략 파라미터 전부. 코드에 기본값을 두지 않는다)
- .env                 → Secrets (API 키·계좌번호. YAML에 넣지 않는다)
"""

from __future__ import annotations

import os
from datetime import time
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"

Ratio = float  # 0.02 = 2%


class _Strict(BaseModel):
    # 오타·누락 필드를 조용히 넘기지 않는다
    model_config = ConfigDict(extra="forbid", frozen=True)


# ---------------------------------------------------------------- strategy.yaml


class SessionConfig(_Strict):
    open: time
    close: time


class TimeWindow(_Strict):
    start: time
    end: time

    @model_validator(mode="after")
    def _ordered(self) -> TimeWindow:
        if self.start >= self.end:
            raise ValueError(f"start({self.start})는 end({self.end})보다 앞이어야 합니다")
        return self


class UniverseConfig(_Strict):
    min_market_cap: float | None
    min_prev_turnover: float | None
    min_avg_turnover_20d: float | None
    min_price: float = Field(gt=0)
    max_price: float = Field(gt=0)
    min_gap: Ratio | None
    exclude: list[str]
    watchlist_size: int = Field(gt=0)

    @model_validator(mode="after")
    def _price_range(self) -> UniverseConfig:
        if self.min_price >= self.max_price:
            raise ValueError("min_price는 max_price보다 작아야 합니다")
        return self


class CostConfig(_Strict):
    commission_rate: Ratio = Field(ge=0, lt=0.05)
    sell_tax_rate: Ratio = Field(ge=0, lt=0.05)
    fx_spread_rate: Ratio = Field(ge=0, lt=0.05)
    slippage_rate: Ratio = Field(ge=0, lt=0.05)


class MarketConfig(_Strict):
    timezone: str
    currency: str
    capital: float = Field(gt=0)
    session: SessionConfig  # 전략 기준 시간 (시가 범위 시작, 장 마감 청산 기준)
    data_session: SessionConfig  # 분봉 수집 범위 (session을 포함해야 함)
    entry_window: TimeWindow
    max_price_vs_limit_up: Ratio | None = Field(gt=0, le=1)
    universe: UniverseConfig
    costs: CostConfig

    @model_validator(mode="after")
    def _sessions_nested(self) -> MarketConfig:
        if not (self.data_session.open <= self.session.open and self.session.close <= self.data_session.close):
            raise ValueError("data_session은 session을 포함해야 합니다")
        if not (self.session.open <= self.entry_window.start and self.entry_window.end <= self.session.close):
            raise ValueError("entry_window는 session 안에 있어야 합니다")
        return self

    @field_validator("timezone")
    @classmethod
    def _valid_tz(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except ZoneInfoNotFoundError as e:
            raise ValueError(f"알 수 없는 timezone: {v}") from e
        return v

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


class Markets(_Strict):
    domestic: MarketConfig
    us: MarketConfig


class RelativeVolume(_Strict):
    lookback_days: int = Field(gt=0)
    multiplier: float = Field(gt=0)


class GapRange(_Strict):
    min: Ratio
    max: Ratio

    @model_validator(mode="after")
    def _ordered(self) -> GapRange:
        if self.min >= self.max:
            raise ValueError("gap.min은 gap.max보다 작아야 합니다")
        return self


class EntryConfig(_Strict):
    bar_minutes: int = Field(gt=0)
    opening_range_minutes: int = Field(gt=0)
    require_above_vwap: bool
    relative_volume: RelativeVolume
    gap: GapRange


class TakeProfit1(_Strict):
    pct: Ratio = Field(gt=0)
    fraction: Ratio = Field(gt=0, lt=1)
    move_stop_to_breakeven: bool


class TakeProfit2(_Strict):
    pct: Ratio = Field(gt=0)


class ExitConfig(_Strict):
    stop_loss_pct: Ratio = Field(gt=0, lt=1)
    use_or_low_stop: bool
    take_profit_1: TakeProfit1
    take_profit_2: TakeProfit2
    flatten_before_close_minutes: int = Field(ge=0)
    max_holding_days: int = Field(gt=0)

    @model_validator(mode="after")
    def _tp_order(self) -> ExitConfig:
        if self.take_profit_2.pct <= self.take_profit_1.pct:
            raise ValueError("take_profit_2.pct는 take_profit_1.pct보다 커야 합니다")
        return self


class SizingConfig(_Strict):
    risk_per_trade: Ratio = Field(gt=0, lt=1)
    max_position_fraction: Ratio = Field(gt=0, le=1)
    min_qty: int = Field(gt=0)


class RiskConfig(_Strict):
    max_drawdown: Ratio = Field(gt=0, lt=1)
    daily_loss_limit: Ratio = Field(gt=0, lt=1)
    max_consecutive_stop_losses: int = Field(gt=0)
    max_positions: int = Field(gt=0)


class StrategyConfig(_Strict):
    markets: Markets
    entry: EntryConfig
    exit: ExitConfig
    sizing: SizingConfig
    risk: RiskConfig


# ---------------------------------------------------------------- app.yaml


class LogConfig(_Strict):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    dir: str
    timezone: str
    max_bytes: int = Field(gt=0)
    backup_count: int = Field(ge=0)


class NotifyConfig(_Strict):
    telegram_enabled: bool


class KisConfig(_Strict):
    requests_per_second: float = Field(gt=0, le=20)
    max_retries: int = Field(ge=0)
    timeout_seconds: float = Field(gt=0)


class DataConfig(_Strict):
    dir: str
    backfill_days: int = Field(ge=0)


class DomesticCollectConfig(_Strict):
    candidates: int = Field(gt=0, le=30)
    extra_symbols: list[str]


class UsCollectConfig(_Strict):
    # 해외 거래대금 순위 API는 계정에 따라 0건만 돌려줘 기본은 symbols 목록을 쓴다
    use_ranking: bool
    symbols: list[str]  # use_ranking=false일 때 수집 대상
    exchanges: list[Literal["NAS", "NYS", "AMS"]] = Field(min_length=1)
    candidates: int = Field(gt=0)
    extra_symbols: list[str]

    @field_validator("symbols", "extra_symbols")
    @classmethod
    def _has_exchange(cls, v: list[str]) -> list[str]:
        for s in v:
            excd, sep, ticker = s.partition(":")
            if not sep or excd not in ("NAS", "NYS", "AMS") or not ticker:
                raise ValueError(f"미국 종목은 '거래소:티커' 형식이어야 합니다 (거래소 NAS/NYS/AMS): {s}")
        return v

    @model_validator(mode="after")
    def _list_needed(self) -> UsCollectConfig:
        if not self.use_ranking and not self.symbols:
            raise ValueError("use_ranking이 false면 symbols에 종목을 넣어야 합니다")
        return self


class CollectConfig(_Strict):
    domestic: DomesticCollectConfig
    us: UsCollectConfig


class AppConfig(_Strict):
    # "live"는 스키마상 허용하되 factory에서 거부한다 (명시적 오류 메시지를 위해)
    executor: Literal["notify", "paper", "live"]
    markets_enabled: list[Literal["domestic", "us"]]
    log: LogConfig
    notify: NotifyConfig
    kis: KisConfig
    data: DataConfig
    collect: CollectConfig

    @property
    def data_dir(self) -> Path:
        p = Path(self.data.dir)
        return p if p.is_absolute() else PROJECT_ROOT / p


# ---------------------------------------------------------------- .env


class Secrets(BaseModel):
    """비밀값. repr/str에 노출되지 않도록 SecretStr로 감싼다. 1단계에서는 모두 선택값."""

    model_config = ConfigDict(frozen=True)

    # 실전 앱키 — 시세 조회 전용. 주문 경로에서는 절대 쓰지 않는다.
    kis_quote_app_key: SecretStr | None = None
    kis_quote_app_secret: SecretStr | None = None
    # 모의투자 앱키·계좌 — 6단계 PaperExecutor에서 사용
    kis_paper_app_key: SecretStr | None = None
    kis_paper_app_secret: SecretStr | None = None
    kis_paper_account_no: SecretStr | None = None
    telegram_bot_token: SecretStr | None = None
    telegram_chat_id: SecretStr | None = None

    def values(self) -> list[str]:
        """로그 마스킹용 비밀값 목록 (비어 있지 않은 것만)."""
        out = []
        for name in type(self).model_fields:
            v = getattr(self, name)
            if v is not None and v.get_secret_value():
                out.append(v.get_secret_value())
        return out


# ---------------------------------------------------------------- loaders


def _read_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: 최상위가 매핑이어야 합니다")
    return data


def load_strategy(path: Path | str | None = None) -> StrategyConfig:
    return StrategyConfig.model_validate(_read_yaml(Path(path or CONFIG_DIR / "strategy.yaml")))


def load_app_config(path: Path | str | None = None) -> AppConfig:
    return AppConfig.model_validate(_read_yaml(Path(path or CONFIG_DIR / "app.yaml")))


def load_secrets(env_file: Path | str | None = None) -> Secrets:
    load_dotenv(env_file or PROJECT_ROOT / ".env", override=False)
    fields = {name: os.environ.get(name.upper()) or None for name in Secrets.model_fields}
    return Secrets(**fields)
