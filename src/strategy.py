from data_control import Data_Control
from config import Config
import numpy as np
class Strategy():
    def __init__(self):
      pass

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
        rsi = df[-1, "RSI"]
        trend_score = df[-1, "Trend"]
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

        # 기본 신호 및 비중 초기화
        signal_type = "hold"
        weight = 0.0

        # 추세 점수별 조건
        if trend_score == 9:
            # 매우 강한 상승 추세
            signal_type = "buy"
            weight = 1.0

        elif trend_score == 8:
            # 강한 상승 추세
            signal_type = "buy"
            weight = 0.6

        elif trend_score == 7:
            # 상승 추세
            signal_type = "buy"
            weight = 0.4

        elif trend_score == 0:
            # 중립 추세
            signal_type = "hold"
            weight = 0.0

        elif trend_score == -7:
            # 하락 추세
            signal_type = "sell"
            weight = 0.4

        elif trend_score == -8:
            # 강한 하락 추세
            signal_type = "sell"
            weight = 0.6

        elif trend_score == -9:
            # 매우 강한 하락 추세
            signal_type = "sell"
            weight = 1.0

        # 기본: 설정되지 않은 경우 대기
        else:
            signal_type = "hold"
            weight = 0.0

        return {"signal": signal_type, "weight": weight}

class Position_Tracker:
    def __init__(self):
        # 포지션 가중치를 추적할 리스트
        self.position_weight = []

    def buy(self, weight_level):
        # 최대 weight_level까지 모든 누락된 값 추가
        for level in range(1, weight_level + 1):
            if level not in self.position_weight:
                self.position_weight.append(level)

    def sell(self, weight_level):
        # weight_level 만큼 5부터 삭제
        for _ in range(weight_level):
            if self.position_weight and self.position_weight[-1] == 5:
                self.position_weight.pop()
            elif self.position_weight:
                max_level = max(self.position_weight)
                self.position_weight.remove(max_level)

    def __repr__(self):
        # 현재 포지션 상태를 출력
        return f"Current Position Weights: {self.position_weight}"
