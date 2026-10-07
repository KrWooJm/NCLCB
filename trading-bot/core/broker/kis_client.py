"""한국투자증권 Open API 공통 HTTP 클라이언트.

- 접근 토큰 발급·파일 캐시 (발급 횟수 제한이 있어 만료 전까지 재사용)
- 초당 호출 수 제한, 일시 오류 재시도
- quote_only=True면 시세·순위 경로 외 호출을 거부한다 (실전 앱키를 조회 전용으로 묶기 위함)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import SecretStr

from core.timeutil import KST

logger = logging.getLogger(__name__)

Server = Literal["real", "demo"]

BASE_URLS: dict[Server, str] = {
    "real": "https://openapi.koreainvestment.com:9443",
    "demo": "https://openapivts.koreainvestment.com:29443",
}

# 시세·순위 조회 경로만 허용 (주문·잔고 등은 /trading/ 아래에 있다)
QUOTE_PATH_MARKERS = ("/quotations/", "/ranking/")

RATE_LIMIT_CODE = "EGW00201"  # 초당 거래건수 초과
TOKEN_EXPIRED_CODES = {"EGW00123", "EGW00121"}  # 만료·유효하지 않은 토큰
TOKEN_REFRESH_MARGIN = timedelta(minutes=10)


class KisApiError(RuntimeError):
    def __init__(self, code: str, message: str, *, status: int | None = None) -> None:
        super().__init__(f"[{code}] {message}" + (f" (HTTP {status})" if status else ""))
        self.code = code
        self.status = status


class QuoteOnlyViolation(PermissionError):
    """조회 전용 클라이언트로 시세 외 경로를 호출하려 함."""


@dataclass(frozen=True)
class KisResponse:
    body: dict[str, Any]
    tr_cont: str  # "M"/"F": 다음 페이지 있음, "D"/"E"/"": 마지막


class KisClient:
    def __init__(
        self,
        server: Server,
        app_key: SecretStr,
        app_secret: SecretStr,
        token_path: Path,
        *,
        quote_only: bool,
        requests_per_second: float,
        max_retries: int,
        timeout_seconds: float = 10.0,
        http: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(KST),
    ) -> None:
        if not app_key.get_secret_value() or not app_secret.get_secret_value():
            raise ValueError("KIS 앱키/시크릿이 비어 있습니다. .env를 확인하세요.")
        self.server = server
        self.quote_only = quote_only
        self._key = app_key
        self._secret = app_secret
        self._token_path = token_path
        self._min_interval = 1.0 / requests_per_second
        self._max_retries = max_retries
        self._http = http or httpx.Client(base_url=BASE_URLS[server], timeout=timeout_seconds)
        self._sleep = sleep
        self._monotonic = monotonic
        self._now = now
        self._last_call: float | None = None
        self._token: str | None = None
        self._token_expires: datetime | None = None

    # ------------------------------------------------------------ token

    def _fingerprint(self) -> str:
        return hashlib.sha256(self._key.get_secret_value().encode()).hexdigest()[:16]

    def _load_cached_token(self) -> bool:
        try:
            data = json.loads(self._token_path.read_text(encoding="utf-8"))
            expires = datetime.fromisoformat(data["expires_at"])
        except (OSError, ValueError, KeyError):
            return False
        if data.get("server") != self.server or data.get("key") != self._fingerprint():
            return False
        if expires - TOKEN_REFRESH_MARGIN <= self._now():
            return False
        self._token, self._token_expires = data["token"], expires
        return True

    def _issue_token(self) -> None:
        self._throttle()
        res = self._http.post(
            "/oauth2/tokenP",
            json={
                "grant_type": "client_credentials",
                "appkey": self._key.get_secret_value(),
                "appsecret": self._secret.get_secret_value(),
            },
        )
        data = _json(res)
        if res.status_code != 200 or "access_token" not in data:
            raise KisApiError(
                str(data.get("error_code") or data.get("msg_cd") or "TOKEN"),
                str(data.get("error_description") or data.get("msg1") or "토큰 발급 실패"),
                status=res.status_code,
            )
        # 응답의 만료 시각은 KST 기준 "YYYY-MM-DD HH:MM:SS"
        expires = datetime.strptime(data["access_token_token_expired"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=KST)
        self._token, self._token_expires = data["access_token"], expires
        self._token_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._token_path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(
                {"server": self.server, "key": self._fingerprint(), "token": self._token, "expires_at": expires.isoformat()}
            ),
            encoding="utf-8",
        )
        os.replace(tmp, self._token_path)
        logger.info("KIS 접근 토큰 발급 (%s, 만료 %s)", self.server, expires.isoformat())

    def _ensure_token(self) -> str:
        if self._token and self._token_expires and self._token_expires - TOKEN_REFRESH_MARGIN > self._now():
            return self._token
        if not self._load_cached_token():
            self._issue_token()
        assert self._token is not None
        return self._token

    def _invalidate_token(self) -> None:
        self._token = self._token_expires = None
        self._token_path.unlink(missing_ok=True)

    # ------------------------------------------------------------ requests

    def _throttle(self) -> None:
        if self._last_call is not None:
            wait = self._min_interval - (self._monotonic() - self._last_call)
            if wait > 0:
                self._sleep(wait)
        self._last_call = self._monotonic()

    def get(self, path: str, tr_id: str, params: dict[str, str], tr_cont: str = "") -> KisResponse:
        if self.quote_only and not any(m in path for m in QUOTE_PATH_MARKERS):
            raise QuoteOnlyViolation(f"조회 전용 클라이언트는 {path} 를 호출할 수 없습니다")

        refreshed = False
        attempt = 0
        while True:
            headers = {
                "content-type": "application/json; charset=utf-8",
                "authorization": f"Bearer {self._ensure_token()}",
                "appkey": self._key.get_secret_value(),
                "appsecret": self._secret.get_secret_value(),
                "tr_id": tr_id,
                "tr_cont": tr_cont,
                "custtype": "P",
            }
            self._throttle()
            try:
                res = self._http.get(path, params=params, headers=headers)
            except httpx.TransportError as e:
                if attempt < self._max_retries:
                    attempt += 1
                    logger.warning("KIS 연결 오류, 재시도 %d/%d: %s", attempt, self._max_retries, type(e).__name__)
                    self._sleep(2**attempt * 0.5)
                    continue
                raise

            data = _json(res)
            code = str(data.get("msg_cd", ""))
            if res.status_code == 200 and str(data.get("rt_cd")) == "0":
                return KisResponse(body=data, tr_cont=res.headers.get("tr_cont", ""))

            if code in TOKEN_EXPIRED_CODES and not refreshed:
                logger.info("KIS 토큰 만료 응답, 재발급 후 재시도")
                self._invalidate_token()
                refreshed = True
                continue
            retriable = code == RATE_LIMIT_CODE or res.status_code >= 500
            if retriable and attempt < self._max_retries:
                attempt += 1
                logger.warning("KIS 일시 오류 [%s] HTTP %s, 재시도 %d/%d", code, res.status_code, attempt, self._max_retries)
                self._sleep(2**attempt * 0.5)
                continue
            raise KisApiError(code or "HTTP", str(data.get("msg1", res.text[:200])).strip(), status=res.status_code)


def _json(res: httpx.Response) -> dict[str, Any]:
    try:
        data = res.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}
