from data_control import Data_Control
from config import Config
import numpy as np

import utils
class Strategy:
    def __init__(self):
        pass

    def signal(self, data_dict, future):
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
        obv_lookback : OBV 비교를 위해 과거 몇 봉 전의 OBV를 볼지
        """

        try:
            data_core = utils.data_source(data_dict)

            signal, weight, reason, stop_loss, take_profit = utils.trend_signal(data_core, future)

            # 결과 반환
            return {
                "current_price": data_core["last_5m"]["Close"],
                "signal": signal,
                "weight": weight,
                "reason": reason,
                "stop_loss":stop_loss,
                "take_profit":take_profit,
                "trend_5m": data_core["current_trend_5m"],
                "trend_1h": data_core["current_trend_1h"],
            }
        except Exception as e:
            print(f"signal 함수 오류: {e}")
