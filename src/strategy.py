from data_control import Data_Control
from config import Config
import numpy as np

import utils
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

        

        # 1) 필요한 데이터 꺼내기
        df_1m = data_dict["1m"]
        df_5m = data_dict["5m"]
        df_1h = data_dict["1h"]

        # 2) 추세 정보 구하기
        current_trend_5m, previous_trend_5m, bars_since_5m = utils.get_trend_info(df_5m)
        current_trend_1h, previous_trend_1h, bars_since_1h = utils.get_trend_info(df_1h)

        trend_score = current_trend_5m

        # 3) 보조 지표(1분봉 RSI, OBV 등)
        last_1m = df_1m.iloc[-1]
        rsi_1m = last_1m["rsi"]
        obv_1m = last_1m["obv"]
        obv_past_1m = df_1m["obv"].iloc[-1 - obv_lookback]
        obv_diff_1m = obv_1m - obv_past_1m

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

        return {
            "signal": signal_type,
            "weight": weight,
            "current_trend_5m": current_trend_5m,
            "current_trend_1h": current_trend_1h,
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
