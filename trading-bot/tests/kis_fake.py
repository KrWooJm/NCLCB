"""KIS 응답 형식을 흉내 내는 가짜 서버 (httpx.MockTransport)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import httpx
from pydantic import SecretStr

from core.broker.kis_client import KisClient
from core.timeutil import KST

Handler = Callable[[httpx.Request], httpx.Response]


def ok(body: dict, tr_cont: str = "") -> httpx.Response:
    return httpx.Response(200, json={"rt_cd": "0", "msg_cd": "MCA00000", "msg1": "정상처리", **body}, headers={"tr_cont": tr_cont})


def fail(code: str, msg: str = "error", status: int = 200) -> httpx.Response:
    return httpx.Response(status, json={"rt_cd": "1", "msg_cd": code, "msg1": msg})


class FakeKis:
    """경로별 핸들러를 등록하고 호출 기록을 남긴다. 토큰 발급은 기본 제공."""

    def __init__(self) -> None:
        self.routes: dict[str, Handler] = {}
        self.calls: list[httpx.Request] = []
        self.token_count = 0
        self.token_expires = "2099-01-01 00:00:00"

    def route(self, path: str, handler: Handler) -> None:
        self.routes[path] = handler

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.calls.append(req)
        if req.url.path == "/oauth2/tokenP":
            self.token_count += 1
            return httpx.Response(
                200,
                json={
                    "access_token": f"tok{self.token_count}",
                    "access_token_token_expired": self.token_expires,
                    "token_type": "Bearer",
                    "expires_in": 86400,
                },
            )
        return self.routes[req.url.path](req)

    def api_calls(self, path: str) -> list[httpx.Request]:
        return [c for c in self.calls if c.url.path == path]


def make_client(fake: FakeKis, tmp_path: Path, *, quote_only: bool = True, max_retries: int = 2, **kw) -> KisClient:
    return KisClient(
        "real",
        SecretStr("APPKEY-TEST-1234"),
        SecretStr("APPSECRET-TEST-5678"),
        tmp_path / "token.json",
        quote_only=quote_only,
        requests_per_second=kw.pop("rps", 1000),
        max_retries=max_retries,
        http=httpx.Client(base_url="https://kis.test", transport=httpx.MockTransport(fake)),
        sleep=kw.pop("sleep", lambda s: None),
        now=kw.pop("now", lambda: datetime(2026, 10, 7, 16, 0, tzinfo=KST)),
        **kw,
    )
