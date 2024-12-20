**암호화폐 자동투자 프로그램 기획서 (종합본)**  

--------------------------------------------

**1. 프로젝트 개요**  
1.1 목적  
- Python 기반 암호화폐 자동투자 시스템 구축  
- 상위 타임프레임(1시간봉)과 하위 타임프레임(5분봉)을 복합적으로 활용, RSI를 기반으로 매매 타이밍 결정  
- 거래량, 볼륨 프로파일, 변동성(BandWidth, %b, OBV) 지표를 통한 변동성 점수화로 시장 상황 반영  
- Slack 알림 및 로깅 기능을 통해 실시간 모니터링과 리스크 관리 강화  
- 지정가매도(Stop-Limit)와 시장가 매도 전략을 통해 손실 최소화

1.2 기대효과  
- 다양한 지표 활용으로 단순 RSI 기반 전략의 단점을 보완  
- 상위 타임프레임 정보로 추세 파악, 변동성 점수로 포지션 사이징 및 진입·청산 시점 최적화  
- 실시간 알림과 부분 자동화로 운영 편의성 극대화

--------------------------------------------

**2. 시스템 구조 및 데이터 관리**  
2.1 전체 아키텍처  
- **거래소 모듈**: Upbit로 원화 자금 관리 후 Binance로 송금, Binance에서 매매 실행  
- **데이터 수집 모듈**:  
  - 초기 구동 시 1시간봉 100개, 5분봉 1000개 정도의 히스토리 데이터를 수집  
  - RSI, Bollinger Band(밴드폭, %b), OBV, 볼륨 프로파일, ATR 등 지표 계산  
  - 새로운 캔들 발생 시 해당 부분만 추가 계산(증분 업데이트)  
- **전략 모듈**:  
  - RSI 기반 매매 타이밍 결정  
  - 볼륨 프로파일로 지지/저항 구간 파악  
  - 볼린저밴드 BandWidth, %b, OBV 급등 등으로 변동성 점수 산정  
  - 변동성 점수와 상위 타임프레임(1시간봉) 추세에 따라 매수/매도 비중 및 시점 조절  
- **주문 실행 모듈**:  
  - RSI 구간별 매수/매도  
  - 매수 시 -2% 손절 라인에 Stop-Limit 주문 설정  
  - 매도 시그널 발생 시 Stop-Limit 취소 후 시장가 매도  
- **알림 및 로깅 모듈**: Slack 알림(30분 주기 자산현황, 매수 시 실시간 알림), 주문 실패나 예외 시 즉각 알림  
- **백테스팅/테스트 모듈**: 추후 별도 환경에서 백테스팅 진행(현재는 우선순위 낮춤)

2.2 데이터 관리 상세  
- 초기로드:  
  - 1시간봉: 약 100개 (약 4일치) → RSI, 볼린저밴드, 거래량 지표 계산 안정적  
  - 5분봉: 약 1000개 (3~4일치) → 단기 시그널용 지표 계산 풍부  
- 메모리 최적화:  
  - Pandas DataFrame 활용, 초기 로드 시 모든 지표 컬럼 계산  
  - 새 캔들 도착 시 해당 부분 지표만 업데이트  
  - 필요 없는 오래된 데이터는 슬라이딩 윈도우 방식으로 제거, 최소 계산량 유지

--------------------------------------------

**3. 전략 알고리즘**  
3.1 기본 개념  
- **RSI**:  
  - 과매도 구간에서 매수, 과매수 구간에서 매도  
  - 상위 타임프레임 추세와 변동성 점수에 따라 매수/매도 비중 및 조건 조정  
- **볼륨 프로파일**:  
  - 주요 지지/저항 레벨 파악  
  - 가격이 지지선 이탈 또는 저항선 돌파 시 변동성 점수 +1  
- **볼린저밴드 BandWidth 및 %b**:  
  - BandWidth로 현재 시장 변동성 수준 파악  
  - %b로 가격이 밴드 내 어느 위치에 있는지 판단  
  - BandWidth 증가 시 변동성 점수 +1  
  - 변동성 점수 높을수록 신중한 진입, 빠른 청산 고려  
- **OBV (On Balance Volume)**:  
  - 거래량 추세 파악  
  - OBV 이동평균선 대비 급등 시 변동성 점수 +1  
  - 거래량 동반 추세 형성 신호로 활용

3.2 변동성 점수 계산  
- 볼륨 프로파일 돌파: +1점  
- BandWidth 특정 기준 초과: +1점  
- OBV 급등: +1점  
- 변동성 점수를 단순 가산 후 일정 임계값(예: 2점 이상)에서 포지션 축소 또는 손절 라인을 타이트하게 조정

3.3 상위 타임프레임(1시간봉) 활용  
- 1시간봉 RSI나 이동평균 등으로 장기 추세 판단  
- 장기 상승 추세 시 과매도 구간 매수 강도 강화, 장기 하락 추세 시 매수 진입 신중  
- 변동성 점수와 조합하여, 장기 하락+고변동성 시 매수 비중 대폭 축소

3.4 포지션 관리 및 손절 전략  
- 매수 체결 시 매수가 대비 -2%에 Stop-Limit 주문 생성해 손실 제한  
- 지표 상 매도 시그널 발생 시 Stop-Limit 취소 후 시장가 매도로 즉각 청산  
- 슬리피지 고려: 희망 손절가보다 약간 더 낮게 Stop-Limit 지정해 체결률 제고

--------------------------------------------

**4. 알림 및 로깅**  
- Slack 알림:  
  - 30분마다 자산현황, 수익률 보고  
  - 매수 발생 시 즉시 알림(종목, 수량, 가격)  
  - 예외사항(주문 실패, API 문제) 즉시 알림  
- 로깅:  
  - 모든 거래 내역, 전략 신호, 오류 상황 기록  
  - 정기적으로 로그 점검 및 성능 분석

--------------------------------------------

**5. 개발 및 운영 프로세스**  
5.1 개발 단계  
- PoC: 기본 RSI 전략 + Stop-Limit 손절 로직 검증  
- 이후 볼륨 프로파일, BandWidth, OBV, 상위 타임프레임 추세 판별 기능 단계적 추가  
- 메모리 관리 및 증분 업데이트 로직 구현

5.2 테스트 및 검증  
- 단위 테스트: 데이터 파싱, 지표 계산 함수, 주문 함수  
- 통합 테스트: 페이퍼 트레이딩 모드로 전략 흐름 점검  
- 소액 실거래로 안정성 검증 후 자본 확장

5.3 유지보수  
- 백테스트 결과에 따라 임계값(RSI 레벨, BandWidth 기준치, OBV 급등 임계치) 조정  
- 거래소 API 변경 대응, 라이브러리 업데이트  
- 변동성 점수 가중치 및 신호 유효기간 도입 검토

5.3 디렉토리 구조
    main.py                 # 메인 실행 스크립트
    config.py               # 설정 파일(API 키, 슬랙 URL, 기본 파라미터)
    data_control.py         # 거래소 API를 통한 시세 데이터 수집 및 업데이트 및 RSI, Bollinger Bands, OBV 등 지표 계산
    strategy.py             # RSI 기반 매매 시그널, 변동성 점수 산출 로직
    order_executor.py       # 주문 실행(시장가/지정가/Stop-Limit), 포지션 관리
    notifier.py             # Slack 등 알림 모듈
    utils.py                # 기타 보조 함수(타임프레임 변환, 필터링 등)

--------------------------------------------

**6. 향후 발전 방향**  
- 추가 지표(MFI, ROC) 도입 검토  
- 변동성 점수 가중치화, 시간가중화로 정교한 의사결정  
- 머신러닝 기반 예측모델, 온체인 데이터, 뉴스 데이터 통합 검토
