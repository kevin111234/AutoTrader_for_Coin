from data_control import Data_Control
from config import Config
import numpy as np

import utils
class Strategy:
    def __init__(self):
        pass

    def signal(self, data_dict):
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
        def data_source(data_dict,
                        rsi_buy_threshold=30,
                        rsi_sell_threshold=70,
                        volume_loockback = 5,
                        obv_lookback=10):
            # 1) 필요한 데이터 꺼내기
            df_1m = data_dict["1m"]
            df_5m = data_dict["5m"]
            df_1h = data_dict["1h"]

            # 2) 추세 정보 구하기 (확장된 get_trend_info)
            #    --> 현재 추세, 이전 추세, 추세 변화 후 경과 봉수, 그 이전 추세 등
            current_trend_1m, t1_trend_1m, t1_1m, t2_trend_1m, t2_1m = utils.get_trend_info(df_1m)
            current_trend_5m, t1_trend_5m, t1_5m, t2_trend_5m, t2_5m = utils.get_trend_info(df_5m)
            current_trend_1h, t1_trend_1h, t1_1h, t2_trend_1h, t2_1h = utils.get_trend_info(df_1h)

            # 3) 보조 지표 계산 == rsi, obv, obv_diff, 5일 거래량 평균, 매수세 비중
            # 3-1) 1분봉
            last_1m = df_1m.iloc[-1]
            obv_1m = last_1m["obv"]
            obv_past_1m = (df_1m["obv"].iloc[ -(obv_lookback + 1) : -1].mean()) / obv_lookback
            obv_diff_1m = obv_1m - obv_past_1m

            # 3-2) 5분봉
            last_5m = df_5m.iloc[-1]
            obv_5m = last_5m["obv"]
            obv_past_5m = (df_5m["obv"].iloc[ -(obv_lookback + 1) : -1].mean()) / obv_lookback
            obv_diff_5m = obv_5m - obv_past_5m

            # 거래량 지표
            avg_volume_5 = df_5m["Volume"].iloc[-(1 + volume_loockback):-1].mean()
            volume_ratio = last_5m["Volume"] / avg_volume_5
            buy_volume_ratio = 0
            if last_5m["Volume"] != 0:
                buy_volume_ratio = last_5m["Taker Buy Base Asset Volume"] / last_5m["Volume"]
            
            return {
              "current_trend_1m":current_trend_1m, # 1분봉 현재 추세
              "t1_trend_1m":t1_trend_1m,           # 1분봉 직전 추세
              "t1_1m":t1_1m,                       # 1분봉 현재 추세 지속시간
              "t2_trend_1m":t2_trend_1m,           # 1분봉 직전의 직전 추세
              "t2_1m":t2_1m,                       # 1분봉 직전 추세 지속시간

              "current_trend_5m":current_trend_5m, # 5분봉 현재 추세
              "t1_trend_5m":t1_trend_5m,           # 5분봉 직전 추세
              "t1_5m":t1_5m,                       # 5분봉 현재 추세 지속시간
              "t2_trend_5m":t2_trend_5m,           # 5분봉 직전의 직전 추세
              "t2_5m":t2_5m,                       # 5분봉 직전 추세 지속시간

              "current_trend_1h":current_trend_1h, # 1시간봉 현재 추세 
              "t1_trend_1h":t1_trend_1h,           # 1시간봉 직전 추세
              "t1_1h":t1_1h,                       # 1시간봉 현재 추세 지속시간
              "t2_trend_1h":t2_trend_1h,           # 1시간봉 직전의 직전 추세
              "t2_1h":t2_1h,                       # 1시간봉 직전 추세 지속시간

              "volume_ratio":volume_ratio,         # 거래량이 최근 평균보다 높으면 1보다 크고, 낮으면 1보다 작음
              "buy_volume_ratio":buy_volume_ratio, # 총 거래량 중 시장가 매수 비율

              "last_1m":last_1m,
              "obv_diff_1m":obv_diff_1m,

              "last_5m":last_5m,
              "obv_diff_5m":obv_diff_5m,
            }

        try:
            data_core = data_source(data_dict)

            signal, weight, reason, stop_loss, take_profit = utils.trend_signal(data_core)

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
