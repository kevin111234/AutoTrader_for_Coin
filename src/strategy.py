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
        current_trend_1m, previous_trend_1m, bars_since_1m = utils.get_trend_info(df_1m)
        current_trend_5m, previous_trend_5m, bars_since_5m = utils.get_trend_info(df_5m)
        current_trend_1h, previous_trend_1h, bars_since_1h = utils.get_trend_info(df_1h)

        trend_score = current_trend_5m

        # 3-1) 보조 지표(1분봉 RSI, OBV 등)
        last_1m = df_1m.iloc[-1]
        rsi_1m = last_1m["rsi"]
        obv_1m = last_1m["obv"]
        obv_past_1m = df_1m["obv"].iloc[-1 - obv_lookback]
        obv_diff_1m = obv_1m - obv_past_1m

        # 3-2) 보조 지표(5분봉 RSI, OBV 등)
        last_5m = df_5m.iloc[-1]
        rsi_5m = last_5m["rsi"]
        obv_5m = last_5m["obv"]
        obv_past_5m = df_5m["obv"].iloc[-1 - obv_lookback]
        obv_diff_5m = obv_5m - obv_past_5m

        # volume_ratio 계산 (현재 거래량 / 이전 5봉 평균)
        avg_volume_5 = df_5m["Volume"].iloc[-6:-1].mean()  # 이전 5봉 평균
        volume_ratio = last_5m["Volume"] / avg_volume_5 if avg_volume_5 != 0 else 0

        # buy_volume_ratio 계산 (매수 거래량 비율)
        buy_volume_ratio = last_5m["Taker Buy Base Asset Volume"] / last_5m["Volume"] if last_5m["Volume"] != 0 else 0

        # 4) 기본 시그널과 가중치
        signal = "hold"
        weight = 0

        if trend_score == 1:
            # trend1_signal 호출 수정
            signal, weight, reason = utils.trend1_signal(
                trend_1m=current_trend_1m,
                current_price=last_5m["Close"],
                sma20_5m=last_5m["SMA_20"],
                rsi_1m=rsi_1m,
                prev_rsi_1m=df_1m["rsi"].iloc[-2],  # 이전 1분봉 RSI
                obv_1m=obv_1m,
                obv_1m_prev=df_1m["obv"].iloc[-2],  # 이전 1분봉 OBV
                rsi_5m=rsi_5m,
                prev_rsi_5m=df_5m["rsi"].iloc[-2],  # 이전 5분봉 RSI
                percent_b=last_5m["percent_b"],
                volume_ratio=volume_ratio,           # 계산 필요
                buy_volume_ratio=buy_volume_ratio    # 계산 필요
            )
        elif trend_score == 2:
            # trend2_signal 호출 수정
            signal, weight, reason = utils.trend2_signal(
                trend_1m=current_trend_1m,
                current_price=last_5m["Close"],
                sma20_5m=last_5m["SMA_20"],
                rsi_1m=rsi_1m,
                prev_rsi_1m=df_1m["rsi"].iloc[-2],
                obv_1m=obv_1m,
                obv_1m_prev=df_1m["obv"].iloc[-2],
                rsi_5m=rsi_5m,
                prev_rsi_5m=df_5m["rsi"].iloc[-2],
                percent_b=last_5m["percent_b"],
                volume_ratio=volume_ratio,
                buy_volume_ratio=buy_volume_ratio
            )
        elif trend_score == 3:
            # trend3_signal 호출 추가
            signal, weight, reason = utils.trend3_signal(
                trend_1m=current_trend_1m,
                current_price=last_5m["Close"],
                sma20_5m=last_5m["SMA_20"],
                rsi_5m=rsi_5m,
                prev_rsi_5m=df_5m["rsi"].iloc[-2],
                percent_b=last_5m["percent_b"],
                volume_ratio=volume_ratio,
                buy_volume_ratio=buy_volume_ratio,
                obv_1m=obv_1m,
                obv_1m_prev=df_1m["obv"].iloc[-2]
            )


        return {
            "signal": signal,
            "weight": weight,
            "reason": reason,
            "current_trend_1m": current_trend_1m,
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
