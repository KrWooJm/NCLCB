#!/usr/bin/env python3
"""로또 6/45 당첨 데이터 수집기.

기존 데이터를 읽어 마지막 저장 회차 다음부터 증분 수집하고,
정적 사이트가 읽는 docs/data/draws.js 와 draws.json 을 갱신한다.

동행복권 공식 API 는 해외 IP 에서 302 로 차단되므로, 국내에서 실행하면
공식 API 가 바로 동작하고, 해외(예: GitHub Actions 러너)에서는 설정된
대체 경유지를 순서대로 시도한다. 어떤 경로로 받든 값의 형식을 검증한다.

  python3 scripts/update_draws.py            # 증분 갱신
  python3 scripts/update_draws.py --rebuild  # 1회차부터 전체 재수집
  python3 scripts/update_draws.py --probe    # 어떤 소스가 살아있는지만 확인
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "docs" / "data"
JSON_PATH = DATA_DIR / "draws.json"
JS_PATH = DATA_DIR / "draws.js"

KST = timezone(timedelta(hours=9))
FIRST_DRAW_DATE = datetime(2002, 12, 7, 20, 45, tzinfo=KST)  # 1회차 추첨일(토)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Referer": "https://dhlottery.co.kr/gameResult.do?method=byWin",
}
OFFICIAL = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={no}"

# 공식 API 는 해외 IP 를 차단한다(홈페이지로 리다이렉트). 국내에서 실행하면 이쪽이 쓰이고,
# 해외(GitHub Actions 러너 등)에서는 아래 공개 미러를 쓴다. 미러 값은 항상 검증한다.
MIRROR = ("https://raw.githubusercontent.com/Dae-Y/lotto-pattern-lab/main/"
          "data/korea-lotto-645.json")

# 미러 무결성 기준점. 잘 알려진 회차 값이 어긋나면 그 미러는 신뢰하지 않는다.
ANCHORS = {
    1: ([10, 23, 29, 33, 37, 40], 16),
    1000: ([2, 8, 19, 22, 32, 42], 39),
}

TIMEOUT = 20
RETRIES = 2


class NotYetDrawn(Exception):
    """해당 회차가 아직 추첨되지 않음."""


class SourceBlocked(Exception):
    """모든 경로가 실패 — 네트워크 차단으로 판단."""


def _sources(no: int) -> list[str]:
    return [OFFICIAL.format(no=no)]


def _get_json(url: str) -> dict | None:
    """응답을 JSON 으로 해석한다. 실패하면 None."""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        if resp.status != 200:
            return None
        raw = resp.read().decode("utf-8", errors="replace").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _validate(payload: dict, no: int) -> dict:
    """받은 값이 실제 로또 회차 형식인지 확인한 뒤 정규화한다.

    경유지를 거칠 수 있으므로, 형식이 맞지 않으면 그 소스를 신뢰하지 않는다.
    """
    if payload.get("returnValue") != "success":
        raise NotYetDrawn(no)
    numbers = sorted(int(payload[f"drwtNo{i}"]) for i in range(1, 7))
    bonus = int(payload["bnusNo"])
    if payload.get("drwNo") != no:
        raise ValueError(f"회차 불일치: 요청 {no}, 응답 {payload.get('drwNo')}")
    if len(set(numbers)) != 6 or not all(1 <= n <= 45 for n in numbers):
        raise ValueError(f"{no}회차 번호 이상: {numbers}")
    if not 1 <= bonus <= 45 or bonus in numbers:
        raise ValueError(f"{no}회차 보너스 번호 이상: {bonus}")
    return {
        "no": no,
        "date": payload["drwNoDate"],
        "numbers": numbers,
        "bonus": bonus,
        # 1등 당첨자 수·총판매액은 '조합 인기도' 분석의 원천 데이터다.
        "firstWinners": int(payload.get("firstPrzwnerCo") or 0),
        "firstPrize": int(payload.get("firstWinamnt") or 0),
        "totalSales": int(payload.get("totSellamnt") or 0),
    }


def fetch_draw(no: int) -> dict:
    """한 회차를 조회한다. 소스를 순서대로 시도하고 검증까지 통과한 값만 돌려준다."""
    errors: list[str] = []
    for attempt in range(RETRIES):
        for url in _sources(no):
            try:
                payload = _get_json(url)
                if payload is None:
                    errors.append(f"{_label(url)}: JSON 아님")
                    continue
                return _validate(payload, no)
            except NotYetDrawn:
                raise
            except Exception as err:
                errors.append(f"{_label(url)}: {err}")
        if attempt + 1 < RETRIES:
            time.sleep(1 + attempt)
    raise SourceBlocked(f"{no}회차 수집 실패 — " + " | ".join(errors[:4]))


def _label(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc
    return "공식" if "dhlottery" in host else host


def _norm_mirror(entry: dict) -> dict:
    """미러 항목을 내부 형식으로 변환하며 값의 타당성을 검증한다."""
    no = int(entry["drawNo"])
    numbers = sorted(int(n) for n in entry["numbers"])
    bonus = int(entry["bonus"])
    if len(set(numbers)) != 6 or not all(1 <= n <= 45 for n in numbers):
        raise ValueError(f"{no}회차 번호 이상: {numbers}")
    if not 1 <= bonus <= 45 or bonus in numbers:
        raise ValueError(f"{no}회차 보너스 이상: {bonus}")
    return {
        "no": no,
        "date": str(entry["date"]),
        "numbers": numbers,
        "bonus": bonus,
        "firstWinners": int(entry.get("firstPrizeWinners") or 0),
        "firstPrize": int(entry.get("firstPrizeAmount") or 0),
        "totalSales": int(entry.get("totalSales") or 0),
    }


def collect_from_mirror(start: int) -> list[dict]:
    """공개 미러에서 한 번에 받아 start 회차 이후만 돌려준다."""
    req = urllib.request.Request(MIRROR, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        entries = json.loads(resp.read().decode("utf-8"))
    if not isinstance(entries, list) or not entries:
        raise SourceBlocked("미러 응답 형식이 올바르지 않습니다.")

    rows = {}
    for entry in entries:
        try:
            row = _norm_mirror(entry)
        except (KeyError, TypeError, ValueError) as err:
            print(f"  [건너뜀] {err}", flush=True)
            continue
        rows[row["no"]] = row

    # 무결성 확인 — 알려진 회차가 어긋나면 이 미러를 신뢰하지 않는다.
    for no, (numbers, bonus) in ANCHORS.items():
        got = rows.get(no)
        if got and (got["numbers"] != numbers or got["bonus"] != bonus):
            raise SourceBlocked(
                f"미러 무결성 검증 실패 — {no}회차가 {got['numbers']}+{got['bonus']}, "
                f"기대값 {numbers}+{bonus}")
    checked = [n for n in ANCHORS if n in rows]
    print(f"  미러 {len(rows)}회차 수신 · 기준점 {checked} 검증 통과", flush=True)
    return [r for no, r in sorted(rows.items()) if no >= start]


def expected_latest_round() -> int:
    """오늘 기준으로 이미 추첨이 끝났을 최대 회차(탐색 상한)."""
    elapsed = datetime.now(KST) - FIRST_DRAW_DATE
    return max(1, int(elapsed.total_seconds() // (7 * 24 * 3600)) + 1)


def load_existing(rebuild: bool) -> list[dict]:
    if rebuild or not JSON_PATH.exists():
        return []
    try:
        return json.loads(JSON_PATH.read_text(encoding="utf-8")).get("draws", [])
    except (json.JSONDecodeError, OSError):
        return []


def _safe_fetch(no: int):
    try:
        return fetch_draw(no)
    except NotYetDrawn:
        return None
    except SourceBlocked as err:
        return err


def collect(start: int, ceiling: int, on_chunk=None) -> list[dict]:
    """구간을 청크 단위로 수집한다. 진행 상황을 출력하고 부분 결과를 저장한다."""
    if start > ceiling:
        return []
    found: list[dict] = []
    CHUNK = 40
    for base in range(start, ceiling + 1, CHUNK):
        block = list(range(base, min(base + CHUNK, ceiling + 1)))
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(_safe_fetch, block))
        done = [r for r in results if isinstance(r, dict)]
        blocked = [r for r in results if isinstance(r, SourceBlocked)]
        found.extend(done)
        print(f"  {block[0]}~{block[-1]}회차: {len(done)}건 수집 "
              f"({time.time() - t0:.1f}s)", flush=True)
        if on_chunk and done:
            on_chunk(found)
        if blocked and not done:
            raise SourceBlocked(str(blocked[0]))
        if any(r is None for r in results):
            break  # 미추첨 회차 도달
    return found


def write(draws: list[dict], source: str = "동행복권 공식 API") -> None:
    draws = sorted({d["no"]: d for d in draws}.values(), key=lambda d: d["no"])
    bundle = {
        "updatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "latestRound": draws[-1]["no"] if draws else 0,
        "count": len(draws),
        "source": source,
        "draws": draws,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    # file:// 로 열어도 동작하도록 JS 전역으로도 내보낸다(fetch/CORS 불필요).
    JS_PATH.write_text(
        "// 자동 생성 파일 — scripts/update_draws.py 가 갱신합니다. 직접 수정하지 마세요.\n"
        f"window.__LOTTO_DATA__ = {json.dumps(bundle, ensure_ascii=False)};\n",
        encoding="utf-8")


def probe() -> int:
    """각 소스가 살아있는지 1회차로 확인만 한다."""
    print(f"1회차로 소스 확인 (정답: 10 23 29 33 37 40 + 보너스 16)\n")
    alive = 0
    for url in _sources(1):
        t0 = time.time()
        try:
            payload = _get_json(url)
            draw = _validate(payload or {}, 1)
            print(f"  [정상] {_label(url):22} {draw['numbers']} + {draw['bonus']} "
                  f"({time.time() - t0:.1f}s)")
            alive += 1
        except Exception as err:
            print(f"  [실패] {_label(url):22} {type(err).__name__}: {err} "
                  f"({time.time() - t0:.1f}s)")
    print(f"\n사용 가능한 소스: {alive}개")
    return 0 if alive else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="로또 6/45 당첨 데이터 수집")
    parser.add_argument("--rebuild", action="store_true", help="1회차부터 전체 재수집")
    parser.add_argument("--probe", action="store_true", help="소스 접근 가능 여부만 확인")
    args = parser.parse_args()

    if args.probe:
        return probe()

    draws = load_existing(args.rebuild)
    have = {d["no"] for d in draws}
    start = (max(have) + 1) if have else 1
    ceiling = expected_latest_round() + 1

    print(f"보유 {len(draws)}회차 · {start}회차부터 최대 {ceiling}회차까지 확인", flush=True)

    def save_partial(found: list[dict]) -> None:
        write(draws + found, used)

    used = "동행복권 공식 API"
    try:
        fresh = collect(start, ceiling, on_chunk=save_partial)
    except SourceBlocked as err:
        print(f"  공식 API 사용 불가 ({err})", flush=True)
        print("  → 공개 미러로 전환합니다.", flush=True)
        used = "공개 미러 (Dae-Y/lotto-pattern-lab, 공식 기록 대조 검증)"
        try:
            fresh = collect_from_mirror(start)
        except Exception as mirror_err:
            print(f"\n[오류] 공식 API 와 미러 모두 실패했습니다.\n  {mirror_err}\n",
                  file=sys.stderr)
            if draws:
                write(draws, used)  # 기존 데이터는 유지
            return 1

    if not fresh:
        print("신규 회차 없음 — 데이터는 이미 최신입니다.")
        if not JS_PATH.exists() and draws:
            write(draws, used)
        return 0

    draws.extend(fresh)
    write(draws, used)
    print(f"신규 {len(fresh)}회차 추가 ({used}) — 최신 {max(d['no'] for d in draws)}회차")
    return 0


if __name__ == "__main__":
    sys.exit(main())
