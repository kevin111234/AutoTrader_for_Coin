from data_control import Data_Control
from config import Config
import numpy as np

import utils
class Strategy:
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
        각 DataFrame에는 다음과 같은 컬럼이 있다고 가정:
        [Open Time, Open, High, Low, Close, Volume, Taker Buy Base Asset Volume, Taker Sell Base Asset Volume,
          SMA_20, SMA_60, SMA_120, rsi, rsi_signal, middle_boll, upper_boll, lower_boll,
          percent_b, bandwidth, obv, ...]
        
        rsi_buy_threshold / rsi_sell_threshold : RSI 매수/매도 임계값 (과매도, 과매수)
        ratio_bullish / ratio_bearish : 볼린저밴드 기반 등에서 사용하는 상승/하락 임계값
        obv_lookback : OBV 비교를 위해 과거 몇 봉 전의 OBV를 볼지
        """
        # 1) 필요한 데이터 꺼내기
        df_1m = data_dict["1m"]
        df_5m = data_dict["5m"]
        df_1h = data_dict["1h"]

        # 2) 추세 정보 구하기 (확장된 get_trend_info)
        #    --> 현재 추세, 이전 추세, 추세 변화 후 경과 봉수, 그 이전 추세 등
        current_trend_1m, prev_trend_1m, bars_1m, prev2_trend_1m, bars2_1m = utils.get_trend_info(df_1m)
        current_trend_5m, prev_trend_5m, bars_5m, prev2_trend_5m, bars2_5m = utils.get_trend_info(df_5m)
        current_trend_1h, prev_trend_1h, bars_1h, prev2_trend_1h, bars2_1h = utils.get_trend_info(df_1h)

        # 여기서는 5분봉 추세를 주 추세로 쓰겠다고 가정
        trend_score = current_trend_5m

        # 3) 보조 지표 계산
        # 3-1) 1분봉
        last_1m = df_1m.iloc[-1]
        rsi_1m = last_1m["rsi"]
        obv_1m = last_1m["obv"]
        obv_past_1m = df_1m["obv"].iloc[-1 - obv_lookback]
        obv_diff_1m = obv_1m - obv_past_1m

        # 3-2) 5분봉
        last_5m = df_5m.iloc[-1]
        rsi_5m = last_5m["rsi"]
        obv_5m = last_5m["obv"]
        obv_past_5m = df_5m["obv"].iloc[-1 - obv_lookback]
        obv_diff_5m = obv_5m - obv_past_5m

        # 거래량 지표
        avg_volume_5 = df_5m["Volume"].iloc[-6:-1].mean() if len(df_5m) >= 6 else 0
        volume_ratio = last_5m["Volume"] / avg_volume_5
        buy_volume_ratio = 0
        if last_5m["Volume"] != 0:
            buy_volume_ratio = last_5m["Taker Buy Base Asset Volume"] / last_5m["Volume"]

        # 4) 기본 시그널 초기화
        signal = "hold"
        weight = 0
        reason = ""

        # 5) 추세 코드별 시그널 분기
        # SMA20 > 60 > 120
        if trend_score == 1:
            print(1)
        elif trend_score == 2:
            print(2)
        elif trend_score == 3:
            print(3)

        else:
            # 기본 hold
            signal = "hold"
            weight = 0
            reason = f"No specific strategy for trend_score={trend_score}"

        # 6) 결과 반환
        return {
            "signal": signal,
            "weight": weight,
            "reason": reason,
            "trend_5m": current_trend_5m,
            "previous_trend_5m": prev_trend_5m,
            "bars_since_5m": bars_5m,
            "trend_1h": current_trend_1h,
            "previous_trend_1h": prev_trend_1h,
            "bars_since_1h": bars_1h,
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
