#!/usr/bin/env python3
"""동행복권 로또 6/45 당첨 데이터 수집기.

기존 데이터를 읽어 마지막 저장 회차 다음부터 증분 수집하고,
정적 사이트가 읽는 docs/data/draws.js 와 draws.json 을 갱신한다.

  python3 scripts/update_draws.py            # 증분 갱신
  python3 scripts/update_draws.py --rebuild  # 1회차부터 전체 재수집
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 동행복권 공식 API. 해외 IP에서 연결이 차단되는 경우가 있어 대체 경로를 함께 둔다.
SOURCES = [
    "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={}",
    "https://dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={}",
]
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
TIMEOUT = 8       # 차단 시 빠르게 실패해야 전체가 멎지 않는다
RETRIES = 2

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "docs" / "data"
JSON_PATH = DATA_DIR / "draws.json"
JS_PATH = DATA_DIR / "draws.js"

KST = timezone(timedelta(hours=9))
# 1회차 추첨일: 2002-12-07 (토). 이후 매주 토요일 추첨.
FIRST_DRAW_DATE = datetime(2002, 12, 7, 20, 45, tzinfo=KST)


class NotYetDrawn(Exception):
    """해당 회차가 아직 추첨되지 않음."""


def fetch_draw(no: int, retries: int = RETRIES) -> dict:
    """단일 회차를 조회한다. 미추첨 회차는 NotYetDrawn 을 던진다."""
    last_err: Exception | None = None
    for attempt in range(retries):
        for url in SOURCES:
            try:
                req = urllib.request.Request(url.format(no), headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                break
            except NotYetDrawn:
                raise
            except Exception as err:  # 다음 소스로 넘어간다
                last_err = err
                payload = None
        try:
            if payload is None:
                raise last_err or RuntimeError("no response")
            if payload.get("returnValue") != "success":
                raise NotYetDrawn(no)
            return {
                "no": payload["drwNo"],
                "date": payload["drwNoDate"],
                "numbers": sorted(payload[f"drwtNo{i}"] for i in range(1, 7)),
                "bonus": payload["bnusNo"],
                # 1등 당첨자 수와 총판매금액은 '조합 인기도' 분석의 원천 데이터다.
                "firstWinners": payload.get("firstPrzwnerCo", 0),
                "firstPrize": payload.get("firstWinamnt", 0),
                "totalSales": payload.get("totSellamnt", 0),
            }
        except NotYetDrawn:
            raise
        except Exception as err:
            last_err = err
            time.sleep(1 + attempt)
    raise RuntimeError(f"{no}회차 수집 실패: {last_err}")


def expected_latest_round() -> int:
    """오늘 기준으로 이미 추첨이 끝났을 최대 회차를 추정한다(상한 탐색용)."""
    elapsed = datetime.now(KST) - FIRST_DRAW_DATE
    return max(1, int(elapsed.total_seconds() // (7 * 24 * 3600)) + 1)


def load_existing(rebuild: bool) -> list[dict]:
    if rebuild or not JSON_PATH.exists():
        return []
    try:
        stored = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        return stored.get("draws", [])
    except (json.JSONDecodeError, OSError):
        return []


def collect(start: int, ceiling: int, on_chunk=None) -> list[dict]:
    """start..ceiling 구간을 청크 단위로 수집한다.

    청크마다 진행 상황을 출력하고 부분 결과를 저장해, 중간에 중단되더라도
    다음 실행이 이어서 수집할 수 있게 한다.
    """
    if start > ceiling:
        return []
    found: list[dict] = []
    CHUNK = 50
    for base in range(start, ceiling + 1, CHUNK):
        block = list(range(base, min(base + CHUNK, ceiling + 1)))
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(_safe_fetch, block))
        done = [r for r in results if r is not None]
        found.extend(done)
        print(f"  {block[0]}~{block[-1]}회차: {len(done)}/{len(block)}건 "
              f"({time.time() - t0:.1f}s)", flush=True)
        if on_chunk and done:
            on_chunk(found)
        if None in results:
            break  # 미추첨 회차 도달 — 이후 회차도 존재하지 않는다
        if not done:
            raise RuntimeError(
                f"{block[0]}~{block[-1]}회차를 한 건도 가져오지 못했습니다. "
                "데이터 소스 접근이 차단된 것으로 보입니다.")
    return found


def _safe_fetch(no: int) -> dict | None:
    try:
        return fetch_draw(no)
    except NotYetDrawn:
        return None


def write(draws: list[dict]) -> None:
    draws.sort(key=lambda d: d["no"])
    bundle = {
        "updatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "latestRound": draws[-1]["no"] if draws else 0,
        "count": len(draws),
        "source": "동행복권 공식 API (dhlottery.co.kr)",
        "draws": draws,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    # file:// 로 열어도 동작하도록 JS 전역으로도 내보낸다(fetch/CORS 불필요).
    JS_PATH.write_text(
        "// 자동 생성 파일 — scripts/update_draws.py 가 갱신합니다. 직접 수정하지 마세요.\n"
        f"window.__LOTTO_DATA__ = {json.dumps(bundle, ensure_ascii=False)};\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="로또 6/45 당첨 데이터 수집")
    parser.add_argument("--rebuild", action="store_true", help="1회차부터 전체 재수집")
    args = parser.parse_args()

    draws = load_existing(args.rebuild)
    have = {d["no"] for d in draws}
    start = (max(have) + 1) if have else 1
    ceiling = expected_latest_round() + 1  # 추정치가 한 주 어긋나도 커버

    print(f"보유 {len(draws)}회차 · {start}회차부터 최대 {ceiling}회차까지 확인", flush=True)

    def save_partial(found: list[dict]) -> None:
        write(draws + [d for d in found if d["no"] not in have])

    fresh = collect(start, ceiling, on_chunk=save_partial)

    if not fresh:
        print("신규 회차 없음 — 데이터는 이미 최신입니다.")
        if not JS_PATH.exists() and draws:
            write(draws)
        return 0

    draws.extend(d for d in fresh if d["no"] not in have)
    write(draws)
    print(f"신규 {len(fresh)}회차 추가 — 최신 {draws[-1]['no']}회차 ({draws[-1]['date']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
