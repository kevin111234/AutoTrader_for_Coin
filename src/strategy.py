from data_control import Data_Control
from config import Config
import numpy as np
class Strategy():
    def __init__(self):
        self.position_check = {}
    
    def position_tracker(self):
        print("포지션 추적용 함수 실행")

        print("매수인지 매도인지 판단")
        print("매수이면 포지션 정보 기록")
        print("매도이면 포지션 정보 삭제")

    def signal(self, 
                df,
                rsi_buy_threshold=30,
                rsi_sell_threshold=70,
                ratio_bullish=1.2,
                ratio_bearish=0.8,
                obv_lookback=10):
        """
        df의 마지막 행 데이터를 참조하여 매매 시그널을 문자열로 반환하는 함수 예시.
        이 버전에서는 OBV 변화량을 '최근 obv_lookback(기본=10)개 봉의 평균 OBV'와
        현재 OBV를 비교하여 증가/감소를 판단합니다.

        매개변수:
        - df: DataFrame(혹은 2D 구조), df[-1, "컬럼명"] 식으로 인덱싱 가능한 형태
        - rsi_buy_threshold: RSI가 이 값 이하이면 과매도 판단 (기본 30)
        - rsi_sell_threshold: RSI가 이 값 이상이면 과매수 판단 (기본 70)
        - ratio_bullish: Taker Buy / Taker Sell이 이 값보다 크면 매수 우위 (기본 1.2)
        - ratio_bearish: Taker Buy / Taker Sell이 이 값보다 작으면 매도 우위 (기본 0.8)
        - obv_lookback: OBV 비교 시 사용할 봉 개수 (기본 10)

        반환:
        - signal: str
            "BUY", "SELL", "HOLD" 등 매매 시그널
        """

        # 만약 데이터 길이가 obv_lookback+1보다 짧으면 비교가 어려우므로 HOLD 처리
        if len(df) < obv_lookback + 1:
            return "HOLD"

        # 1) 마지막 행(현재 봉)의 Taker Buy / Sell Volume
        taker_buy = df[-1, "Taker Buy Base Asset Volume"]
        taker_sell = df[-1, "Taker Sell Base Asset Volume"]
        # 분모가 0이 되지 않도록 작은 값 추가
        tb_ts_ratio = taker_buy / (taker_sell + 1e-9)

        # 2) RSI, Trend, OBV
        rsi_val = df[-1, "RSI"]
        trend_val = df[-1, "Trend"]
        obv_now = df[-1, "OBV"]

        # 3) 최근 obv_lookback개 봉의 평균 OBV (마지막 봉은 제외)
        # 예: obv_lookback=10 → 바로 직전 10개 봉 사용
        # df[-(obv_lookback+1):-1, "OBV"]는 '현재 봉 이전 10개 OBV'를 의미
        obv_history = df[-(obv_lookback+1):-1, "OBV"]  # 시리즈 형태라고 가정
        obv_10_mean = obv_history.mean()

        # 4) obv_change: (현재 OBV - 최근 10봉 평균 OBV)
        obv_change = obv_now - obv_10_mean

        # OBV가 10봉 평균보다 높다면 "OBV 증가", 낮다면 "OBV 감소"로 해석
        # 예: obv_change > 0 → OBV 증가, obv_change < 0 → OBV 감소
        # 여기선 간단히 +면 증가, -면 감소로만 사용

        # 5) signal 초기값
        signal = "HOLD"

        # 6) 간단한 예시 로직
        if trend_val > 0:
            # 상승 추세
            if (tb_ts_ratio > ratio_bullish) and (obv_change > 0) and (rsi_val < rsi_sell_threshold):
                signal = "BUY"
            else:
                signal = "HOLD"
        elif trend_val < 0:
            # 하락 추세
            if (tb_ts_ratio < ratio_bearish) and (obv_change < 0) and (rsi_val > rsi_buy_threshold):
                signal = "SELL"
            else:
                signal = "HOLD"
        else:
            # Trend == 0 → 추세 모호
            signal = "HOLD"

        return signal