# trading-bot

국내(KOSPI/KOSDAQ) + 미국 주식 대상 PC 데스크톱 자동매매 프로그램.
**신호 알림 → 모의투자 → 실매매** 순서로 단계적으로 전환합니다.

> ⚠️ 실계좌 주문(LiveExecutor)은 구현되어 있지 않습니다. 기본 실행 모드는 항상 `notify`(신호 알림)입니다.

전략·리스크 규칙·개발 단계의 전체 설명은 [CLAUDE.md](CLAUDE.md)를 보세요.

## 현재 진행 상황

| 단계 | 내용 | 상태 |
|---|---|---|
| 1 | 프로젝트 뼈대 (설정 로더, 로깅, Broker/Executor 인터페이스) | ✅ 완료 |
| 2 | 데이터 수집 (한국투자증권 시세 API, 1분봉 → Parquet) | 🔧 코드 완료 · PC에서 자동 적재 확인 필요 |
| 3 | 전략 엔진 + 리스크 가드 | ⏳ |
| 4 | 백테스트 | ⏳ |
| 5 | NotifyExecutor (텔레그램 알림) | ⏳ |
| 6 | PaperExecutor (모의투자 자동주문) | ⏳ |
| 7 | 데스크톱 UI | ⏳ |
| 8 | 패키징 | ⏳ |
| 9 | LiveExecutor | 🔒 사용자 요청 시에만 |

## 요구 사항

- Python 3.11 이상

## 설치

```bash
cd trading-bot
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## 비밀 정보 설정

API 키·계좌번호는 `.env`에만 넣습니다. `.env`는 `.gitignore`에 포함되어 커밋되지 않습니다.

```bash
cp .env.example .env               # 그다음 .env에 값 입력
```

| 변수 | 설명 |
|---|---|
| `KIS_QUOTE_APP_KEY`, `KIS_QUOTE_APP_SECRET` | 한국투자증권 **실전** 앱키 — 시세·순위 조회 전용 |
| `KIS_PAPER_APP_KEY`, `KIS_PAPER_APP_SECRET`, `KIS_PAPER_ACCOUNT_NO` | 모의투자 앱키·계좌 (6단계부터) |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | 텔레그램 알림 (5단계부터) |

실전 앱키를 쓰는 이유: 모의 서버는 과거 일자 분봉 조회를 지원하지 않습니다.
실전 앱키는 **조회 전용 클라이언트**에서만 쓰이며, 이 클라이언트는 시세(`/quotations/`)·순위(`/ranking/`)
경로 외의 호출(주문·잔고 등)을 코드에서 거부합니다. 테스트로도 확인합니다.

로그에 비밀값이 찍히더라도 `***`로 가려집니다.

## 설정 파일

| 파일 | 내용 |
|---|---|
| `config/app.yaml` | 실행 모드(`executor`), 대상 시장, 로그, 알림 설정 |
| `config/strategy.yaml` | 전략 파라미터 전부 — 유니버스, 진입·청산, 포지션 크기, 리스크 한도, 비용 |

- 전략 수치는 코드에 하드코딩하지 않고 `strategy.yaml`에서만 읽습니다. 코드 쪽 기본값이 없으므로 **필드가 빠지거나 오타가 있으면 시작할 때 오류**가 납니다.
- 비율은 소수로 씁니다 (`0.02` = 2%).
- 시각은 반드시 따옴표로 감쌉니다 (`"09:15"`). 따옴표가 없으면 YAML이 숫자로 해석합니다.
- `costs`의 수수료·세금 값은 초기 가정치입니다. 실제 증권사·연도 기준으로 확인한 뒤 수정하세요.

### 실행 모드 (`executor`)

| 값 | 동작 |
|---|---|
| `notify` (기본) | 주문 없이 신호만 알림 |
| `paper` | 모의투자 계좌로 주문 (6단계에서 구현) |
| `live` | **거부됨** — 시작 시 `LiveExecutorNotAvailable` 오류 |

## 분봉 수집 (2단계)

장 마감 후 실행하면 그날의 거래대금 상위 종목을 감시목록으로 뽑고, 각 종목의 1분봉을 저장합니다.
처음 실행할 때는 종목마다 최근 `backfill_days`(기본 20) 평일 중 비어 있는 날도 함께 채웁니다.

```bash
# 연결 확인: 2종목만, 저장하지 않음
python scripts/collect.py --market domestic --dry-run --limit 2 --no-backfill
python scripts/collect.py --market us --dry-run --limit 2 --no-backfill

# 실제 수집
python scripts/collect.py --market domestic
python scripts/collect.py --market us
python scripts/collect.py --market domestic --date 2026-10-06   # 특정 거래일
python scripts/collect.py --market us --symbols NAS:AAPL,NYS:F    # 순위 조회 없이 지정 종목만
```

순위 결과가 비면(장 시작 전 등) 가장 최근에 저장된 감시목록을 대신 씁니다.

| 항목 | 내용 |
|---|---|
| 감시목록 | 국내: 거래대금 순위(최대 30) → 가격·시가총액·거래대금 필터 (관리·경고·우선주·정지·ETF·ETN·스팩 제외) / 미국: NAS·NYS·AMS 거래대금 순위 합산 상위 40, 가격 $5~$100. ETF·ADR 구분은 3단계에서 거름 |
| 저장 위치 | `data/candles/{domestic,us}/1m/{종목}/{YYYY-MM-DD}.parquet` (시각은 시간대 포함) |
| 감시목록 기록 | `data/watchlists/{market}/{YYYY-MM-DD}.json` |
| 빈 날 | 휴장·거래정지·제공 범위 밖이면 `.empty` 표시 파일을 남겨 다시 조회하지 않음 |
| 5분봉 | 저장은 1분봉 원본. `core.data.resample.resample_minutes(df, 5, 장시작)`으로 변환 |
| 날짜 | `--date` 생략 시 마감된 가장 최근 평일 (국내는 KST, 미국은 뉴욕 현지 날짜) |

수집 설정(후보 수, 항상 수집할 종목, backfill 일수, 초당 호출 수)은 `config/app.yaml`의 `kis`·`data`·`collect`에 있습니다.

### 매일 자동 실행 (Windows 작업 스케줄러)

PC가 켜져 있어야 합니다. 경로는 본인 환경에 맞게 바꾸세요.

```bat
:: 국내 — 평일 15:45 (KST)
schtasks /Create /TN "trading-bot 국내 분봉" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 15:45 ^
  /TR "\"C:\trading-bot\.venv\Scripts\python.exe\" \"C:\trading-bot\scripts\collect.py\" --market domestic"

:: 미국 — 화~토 06:15 (KST). 뉴욕 16:00 마감은 서머타임 05:00 / 표준시 06:00 KST
schtasks /Create /TN "trading-bot 미국 분봉" /SC WEEKLY /D TUE,WED,THU,FRI,SAT /ST 06:15 ^
  /TR "\"C:\trading-bot\.venv\Scripts\python.exe\" \"C:\trading-bot\scripts\collect.py\" --market us"
```

작업 스케줄러 앱에서 각 작업의 속성 → 조건 탭 → **"작업을 실행하기 위해 컴퓨터의 절전 모드 해제"** 를 켜 두면 절전 중에도 실행됩니다.
결과는 `logs/trading-bot.log`에 남습니다.

### 첫 실행 때 확인할 것

API 문서만으로 확정할 수 없어 실제 응답으로 확인해야 하는 항목입니다. 다르면 알려 주세요.

1. 국내 분봉의 첫 시각이 `09:00`인지 (봉 시각 = 1분 구간의 시작이라는 가정)
2. 미국 종목 하루치가 약 390개로 끊김 없이 받아지는지 (페이지 넘김 키를 현지 시각으로 보낸다는 가정)
3. 미국 분봉이 과거 며칠까지 제공되는지 — 제공 범위 밖의 날은 `.empty`로 표시됩니다
4. 장 마감 후 순위 API가 당일 기준 결과를 주는지

## 설정 로드 확인

```bash
python -c "from core.config import load_strategy; s = load_strategy(); print(s.markets.domestic.entry_window); print(s.risk)"
```

## 테스트

```bash
pytest
```

## 폴더 구조

```
trading-bot/
├─ config/            app.yaml, strategy.yaml
├─ core/
│  ├─ config.py       설정 로더 (YAML 검증 + .env)
│  ├─ logging_setup.py  콘솔·회전 파일 로그, 비밀값 마스킹
│  ├─ timeutil.py     KST / America/New_York (서머타임 자동 반영)
│  ├─ models.py       Quote, Balance, Position, Signal 등
│  ├─ broker/         Broker 인터페이스, KIS 클라이언트(토큰·속도 제한·조회 전용), 국내·해외 구현체
│  ├─ data/           Parquet 저장소, 분봉 검증, 5분봉 변환, 감시목록, 수집기
│  ├─ execution/      Executor 인터페이스, Notify / Paper 스텁, 모드 선택
│  ├─ strategy/  risk/  backtest/   (이후 단계)
├─ scripts/           collect.py (분봉 수집 실행)
├─ api/               FastAPI 로컬 서버 (이후 단계)
├─ ui/                데스크톱 프론트엔드 (7단계)
└─ tests/
```

## 운영 원칙

- 모든 시각은 timezone-aware로 처리합니다 (naive datetime은 오류).
- 리스크 가드를 우회하는 주문 경로는 만들지 않으며, 리스크 가드에는 단위 테스트를 반드시 작성합니다.
- 백테스트는 수수료·세금·슬리피지를 반영하고, 신호를 계산한 봉의 종가로 체결시키지 않습니다.
