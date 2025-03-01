# 암호화폐 자동투자 프로그램

이 프로젝트는 바이낸스 스팟(현물) 및 선물 시장에서 자동으로 데이터를 수집하고, 기술적 지표를 기반으로 매매 신호를 생성하여 주문을 실행하는 **자동투자 봇**입니다.

---

## 1. 환경 변수 설정

**.env** 파일에 다음 변수를 설정해 주세요:

1. `BINANCE_ACCESS_KEY` = 바이낸스 API Key  
2. `BINANCE_SECRET_KEY` = 바이낸스 Secret Key  
3. `SLACK_API_KEY` = 슬랙 봇 API Token  
4. `SLACK_ASSET_CHANNEL_ID` = 자산 정보를 전송할 슬랙 채널 ID  
5. `SLACK_TRADE_CHANNEL_ID` = 매매 정보를 전송할 슬랙 채널 ID  
6. `SLACK_ERROR_CHANNEL_ID` = 에러 정보를 전송할 슬랙 채널 ID  
7. `SEED_MONEY` = 초기 시드머니 (수익률 계산용)  
8. `COIN_TICKERS` = 매매하고자 하는 코인 티커들 (예: "BTC ETH" 처럼 공백으로 구분)  
9. `FUTURES_USE` = 선물 사용 여부 (예: `"true"` / `"false"`)  
10. `FUTURES_LEVERAGE` = 선물 레버리지 배율 (숫자)  
11. `FUTURES_MARGIN_TYPE` = 선물 마진 타입 (예: CROSS, ISOLATED)  
12. `FUTURES_COIN_TICKERS` = 선물에서 매매할 코인 티커들 (예: "BTC ETH" 공백 구분)

예:  
```
BINANCE_ACCESS_KEY=YOUR_BINANCE_KEY
BINANCE_SECRET_KEY=YOUR_BINANCE_SECRET
SLACK_API_KEY=xoxb-1234567890-...
SLACK_ASSET_CHANNEL_ID=ABC123
SLACK_TRADE_CHANNEL_ID=DEF456
SLACK_ERROR_CHANNEL_ID=GHI789
SEED_MONEY=1000
COIN_TICKERS="BTC ETH"
FUTURES_USE=true
FUTURES_LEVERAGE=10
FUTURES_MARGIN_TYPE="CROSS"
FUTURES_COIN_TICKERS="BTC"
```

---

## 2. 프로젝트 파일 구조

```
├─ main.py                # 프로그램 진입점. 전체 로직을 실행하는 스크립트
├─ src/
│  ├─ config.py           # 환경 변수(.env) 로드 및 검증
│  ├─ data_control.py     # 데이터 수집 및 지표 계산 (SMA, RSI, MACD 등)
│  ├─ notifier.py         # Slack 알림 및 계좌/포지션 정보 조회
│  ├─ strategy.py         # 매매 전략 (signal 함수)
│  ├─ order_executor.py   # 바이낸스 API를 이용한 주문 실행
│  ├─ trade_manager.py    # 스팟/선물 매매 로직(단계별 매수/매도, 포지션 관리)
│  └─ utils.py            # MACD_signal 등 유틸 함수, 글로벌 변수 관리
├─ backtester/
│  ├─ backtester.py       # 백테스트 실행 로직
│  ├─ backtest_engine.py  # 백테스트 엔진 (포지션, 자산, 체결 시뮬레이션)
│  └─ data_loader.py      # 백테스트용 데이터 로더, 지표 계산
├─ README.md              # 현재 문서
├─ requirements.txt       # 설치해야 할 Python 패키지 목록
└─ .env                   # 환경 변수 파일
```

---

## 3. 사용 방법

### (1) 의존성 설치

```bash
pip install -r requirements.txt
```

또는 `requirements.txt`가 없으면 직접 `pip install python-binance slack_sdk pandas ...` 등을 설치해 주세요.

### (2) .env 파일 생성 및 환경 변수 설정

위에 언급된 변수를 모두 `.env` 파일에 기입합니다.

### (3) 프로그램 실행

```bash
python src/main.py
```

- 실행하면 **Binance 서버 시간**과 로컬 시간 차이를 확인하고, 초기 데이터를 수집한 뒤 루프를 돌면서 자동 매매를 시도합니다.
- 정상 동작 시, 매매 결과나 에러 정보 등이 콘솔 로그와 Slack 채널에 전송됩니다.

---

## 4. 실행 로직 요약

1. **환경 설정**  
   - `config.py`에서 `.env` 파일을 로드하여 Binance API Key, Slack API Key, 선물 레버리지, 마진 타입, 그리고 코인 티커 목록 등을 불러옵니다.

2. **객체 초기화**  
   - `main.py`에서 `Config`, `Client`, `Data_Control`, `Notifier`, `Strategy`, `Order`, `TradeManager` 인스턴스를 생성합니다.
   - `Notifier`는 Slack과 바이낸스 계좌 정보를 조회/알림을 담당합니다.
   - `TradeManager`는 실제 매매 로직(스팟/선물)을 관리하며 `Order`를 통해 바이낸스 주문 API를 호출합니다.

3. **데이터 수집 및 지표 계산**  
   - `data_control.py`에서 제공하는 `data()` 또는 `update_data()` 함수를 통해 **과거 캔들**을 가져오고,  
   - 이어서 `cal_indicator()`로 SMA, RSI, MACD, Bollinger Band, OBV, ADX 등 지표를 계산합니다.

4. **초기 자산 정보 조회**  
   - `Notifier.get_asset_info()` / `get_futures_asset_info()`로 현물·선물 잔고 조회,  
   - `notifier.get_limit_amount()` / `futures_get_limit_amount()`로 코인별 주문 가능 금액 계산,  
   - Slack 채널에 초기 잔고 정보 및 주문 가능금액 알림을 전송합니다.

5. **무한 루프(Main Loop)**  
   - 1분, 5분, 1시간봉 최신 캔들 업데이트  
   - 전략(`strategy.signal`)으로 매매 신호(예: `"buy"`, `"sell"`, `"L_buy"`, `"S_sell"` 등) 계산  
   - `TradeManager.process_spot_trade()` 또는 `process_futures_trade()` 호출  
     - 단계별 매매(`stage`) 로직 적용  
     - 성공/실패 시 Slack 알림 전송  
   - `time.sleep(1)`로 잠시 대기 후 반복

---

## 5. 주요 로직 및 파일 설명

### (A) `data_control.py`
- **주요 함수**  
  - `data()`, `update_data()`: 바이낸스 API를 통해 과거 및 최근 캔들 데이터를 수집  
  - `cal_indicator()`: 이동평균선(SMA), RSI, Bollinger Band, OBV, MACD, ADX 등 여러 지표를 계산

### (B) `notifier.py`
- **주요 기능**  
  - `get_asset_info()`: 현물 잔고 조회  
  - `get_futures_asset_info()`: 선물 계좌 정보 조회  
  - `send_slack_message(channel_id, message)`: Slack 채널에 메시지 전송  
  - `send_asset_info(...)`: 초기 잔고/한도를 Slack에 알리는 함수

### (C) `strategy.py`
- **매매 전략**  
  - `signal()`: 내부적으로 `utils.MACD_signal()` 호출 → MACD 기반의 매수/매도 여부 결정  
  - 최종적으로 `{"signal": "...", "weight": ..., "reason": ...}` 형태로 리턴

### (D) `trade_manager.py`
- **매매 로직 (스팟/선물)**  
  - `process_spot_trade()`: `"buy"`/`"sell"` 신호에 따라 단계별 매수/매도  
  - `process_futures_trade()`: `"L_buy"`, `"L_sell"`, `"S_buy"`, `"S_sell"` 신호에 따라 롱/숏 진입·청산  
  - 각 단계마다 주문 가능한 수량 계산 후 `order_executor.Order` 호출 → 바이낸스 주문 실행

### (E) `order_executor.py`
- **실제 주문 실행**  
  - `buy`, `sell`, `L_buy`, `L_sell`, `S_buy`, `S_sell` 함수로 현물/선물 주문을 처리  
  - 체결 후 주문 상태를 확인하고 로깅

### (F) `utils.py`
- **유틸 함수**  
  - `MACD_signal()`: MACD와 RSI를 확인하여 매매 신호를 생성  
  - 전역 변수 `profit_sell` 관리 등 추가 로직이 포함될 수 있음

---

## 6. 백테스트 (선택)

- `backtester/` 폴더 안의 `backtester.py`, `backtest_engine.py`, `data_loader.py`를 사용하면 과거 데이터로 전략을 백테스트할 수 있습니다.  
- `python backtester/backtester.py` 등으로 실행 후, 수익률·MDD·거래 내역 CSV 파일을 확인할 수 있습니다.

---

## 7. 참고 / 주의사항

1. **실거래 위험**  
   - 본 코드는 **실제 바이낸스 API를 통해 매매**가 이뤄집니다. API Key 유출이나 전략 오류로 인한 손실 위험이 있으므로 주의가 필요합니다.
2. **시뮬레이션 vs 실거래**  
   - 백테스트 결과와 실거래는 슬리피지, 주문 실패, 네트워크 지연 등으로 차이가 발생할 수 있습니다.
3. **에러 로그**  
   - `SLACK_ERROR_CHANNEL_ID` 채널로 주문 실패, API 오류 등의 메시지가 전송됩니다.  
   - 에러 발생 시 콘솔 로그와 Slack 알림을 꼼꼼히 확인하세요.

---

## 8. 라이선스
해당 코드는 자유롭게 수정/배포 가능합니다. 단, 사용으로 인한 투자 손실은 전적으로 사용자 본인에게 귀속됩니다.
