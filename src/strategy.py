from data_control import Data_Control
from config import Config
import numpy as np
class Strategy():
    def __init__(self):
      pass

    def signal(self, 
                data_dict,
                rsi_buy_threshold=30,
                rsi_sell_threshold=70,
                ratio_bullish=1.2,
                ratio_bearish=0.8,
                obv_lookback=10):
        """
        data_dict: {
            "1m": DataFrame(...),
            "5m": DataFrame(...),
            "1h": DataFrame(...)
            # 필요하면 다른 타임프레임도 추가
        }
        각 DataFrame은 다음 컬럼을 포함한다고 가정:
        [Open Time, Open, High, Low, Close, Volume, Taker Buy Base Asset Volume, Taker Sell Base Asset Volume,
          SMA_20, SMA_60, SMA_120, rsi, rsi_signal, middle_boll, upper_boll, lower_boll, persent_b, bandwidth, obv]
        """

        def get_trend_info(df):
            """
            df: trend 칼럼이 있는 데이터프레임 (예: 5분봉, 1시간봉 등)
            반환:
              current_trend: 가장 최근 봉의 추세
              previous_trend: 해당 추세로 바뀌기 직전 봉의 추세
              bars_since_change: 추세 변환 후 몇 개의 봉이 지났는지
            """
            current_trend = df["trend"].iloc[-1]
            i = len(df) - 2

            # 마지막에서부터 거슬러 올라가며 현재 추세와 달라진 지점 탐색
            while i >= 0 and df["trend"].iloc[i] == current_trend:
                i -= 1

            # 전체가 같은 추세였으면 previous_trend는 None 처리
            if i < 0:
                previous_trend = None
                bars_since_change = len(df) - 1
            else:
                previous_trend = df["trend"].iloc[i]
                bars_since_change = (len(df) - 1) - i

            return current_trend, previous_trend, bars_since_change

        # 1) 필요한 데이터 꺼내기
        df_1m = data_dict["1m"]
        df_5m = data_dict["5m"]
        df_1h = data_dict["1h"]

        # 2) 추세 정보 구하기
        current_trend_5m, previous_trend_5m, bars_since_5m = get_trend_info(df_5m)
        current_trend_1h, previous_trend_1h, bars_since_1h = get_trend_info(df_1h)

        # 여기서는 단순히 5분, 1시간 중 “더 극단적인” 추세(절댓값 큰 쪽)를 선택
        if abs(current_trend_5m) > abs(current_trend_1h):
            trend_score = current_trend_5m
        else:
            trend_score = current_trend_1h

        # 3) 보조 지표(1분봉 RSI, OBV 등)
        last_1m = df_1m.iloc[-1]
        rsi_current = last_1m["rsi"]
        obv_current = last_1m["obv"]
        obv_past = df_1m["obv"].iloc[-1 - obv_lookback]
        obv_diff = obv_current - obv_past

        # 4) 기본 시그널과 가중치
        signal_type = "hold"
        weight = 0

        if trend_score == 9:
            signal_type = "buy"
            weight = 5
        elif trend_score == 8:
            signal_type = "buy"
            weight = 4
        elif trend_score == 7:
            signal_type = "buy"
            weight = 2
        elif trend_score == 0:
            signal_type = "hold"
            weight = 0
        elif trend_score == -7:
            signal_type = "sell"
            weight = 2
        elif trend_score == -8:
            signal_type = "sell"
            weight = 3
        elif trend_score == -9:
            signal_type = "sell"
            weight = 5
        else:
            signal_type = "hold"
            weight = 0

        # 5) RSI, OBV 등으로 시그널 보정 예시
        if signal_type == "buy":
            if rsi_current > rsi_sell_threshold:
                weight -= 1
            if obv_diff > 0:
                weight += 1
        elif signal_type == "sell":
            if rsi_current < rsi_buy_threshold:
                weight -= 1
            if obv_diff < 0:
                weight += 1

        weight = max(weight, 0)

        # 6) 필요하다면 이전 추세나 변환 후 지난 봉 수(bars_since_5m, bars_since_1h)를 활용해
        #    추가 조건을 걸 수도 있음
        #    (예: 추세 전환 직후에는 신호를 보수적으로 해석 등)
        # 예시:
        if bars_since_5m <= 2 or bars_since_1h <= 1:
            # 막 추세가 바뀌었으면 시그널 가중치 줄이는 식
            weight = max(weight - 1, 0)

        return {
            "signal": signal_type,
            "weight": weight,
            "current_trend_5m": current_trend_5m,
            "previous_trend_5m": previous_trend_5m,
            "bars_since_5m": bars_since_5m,
            "current_trend_1h": current_trend_1h,
            "previous_trend_1h": previous_trend_1h,
            "bars_since_1h": bars_since_1h
        }

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
