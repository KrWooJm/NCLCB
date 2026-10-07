# trading-bot

국내(KOSPI/KOSDAQ) + 미국 주식 대상 PC 데스크톱 자동매매 프로그램.
**신호 알림 → 모의투자 → 실매매** 순서로 단계적으로 전환합니다.

> ⚠️ 실계좌 주문(LiveExecutor)은 구현되어 있지 않습니다. 기본 실행 모드는 항상 `notify`(신호 알림)입니다.

전략·리스크 규칙·개발 단계의 전체 설명은 [CLAUDE.md](CLAUDE.md)를 보세요.

## 현재 진행 상황

| 단계 | 내용 | 상태 |
|---|---|---|
| 1 | 프로젝트 뼈대 (설정 로더, 로깅, Broker/Executor 인터페이스) | ✅ 완료 |
| 2 | 데이터 수집 (한국투자증권 모의 서버, 5분봉 → Parquet) | ⏳ 예정 |
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
| `KIS_APP_KEY`, `KIS_APP_SECRET` | 한국투자증권 Open API 키 |
| `KIS_ACCOUNT_NO_DOMESTIC` / `KIS_ACCOUNT_NO_OVERSEAS` | 국내 / 해외 계좌번호 |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | 텔레그램 알림 |

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
│  ├─ broker/         Broker 인터페이스 (증권사 구현체는 2단계)
│  ├─ execution/      Executor 인터페이스, Notify / Paper 스텁, 모드 선택
│  ├─ data/  strategy/  risk/  backtest/   (이후 단계)
├─ api/               FastAPI 로컬 서버 (이후 단계)
├─ ui/                데스크톱 프론트엔드 (7단계)
└─ tests/
```

## 운영 원칙

- 모든 시각은 timezone-aware로 처리합니다 (naive datetime은 오류).
- 리스크 가드를 우회하는 주문 경로는 만들지 않으며, 리스크 가드에는 단위 테스트를 반드시 작성합니다.
- 백테스트는 수수료·세금·슬리피지를 반영하고, 신호를 계산한 봉의 종가로 체결시키지 않습니다.
