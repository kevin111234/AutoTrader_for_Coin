def get_trend_info(df):
    """
    df: trend 칼럼이 있는 데이터프레임 (예: 5분봉 등)
    
    반환:
      current_trend:   T0 - 가장 최근 봉의 추세
      previous_trend:  T-1 - 현재 추세로 바뀌기 직전 봉의 추세
      bars_since_change: 현재 추세(T0)로 바뀐 후 지난 봉 수
      trend_t_minus_2: T-2 - 이전추세(previous_trend)로 바뀌기 직전의 추세 (더 과거)
      bars_since_t_minus_1: T-1 추세가 시작된 뒤 얼마나 유지되었는지(봉 수)
                          (T-1이 변하기 직전까지 유지된 봉 수)
    """
    # ---------------------------
    # 1) 현재 추세(T0) 찾기
    # ---------------------------
    current_trend = df["trend"].iloc[-1]

    # i를 뒤에서부터 탐색해 현재 추세와 다른 값이 나오는 순간이 "이전 추세"의 시작점
    i = len(df) - 2
    while i >= 0 and (df["trend"].iloc[i] == current_trend or df["trend"].iloc[i] == 10 or df["trend"].iloc[i] == 0):
        i -= 1

    if i < 0:
        # 데이터 전체가 같은 추세였을 경우
        previous_trend = current_trend
        bars_since_change = len(df) - 1
        trend_t_minus_2 = current_trend
        bars_since_t_minus_1 = 0
    else:
        # 이전 추세(T-1) 및 현재 추세로 바뀐 후 지난 봉 수
        previous_trend = df["trend"].iloc[i]
        bars_since_change = (len(df) - 1) - i

        # ---------------------------
        # 2) 더 과거 추세(T-2) 찾기
        # ---------------------------
        # j를 i-1부터 거슬러 올라가, previous_trend와 다른 값이 나오는 순간이 T-2
        j = i - 1
        while j >= 0 and (df["trend"].iloc[j] == previous_trend or df["trend"].iloc[i] == 10 or df["trend"].iloc[i] == 0):
            j -= 1

        if j < 0:
            # T-1 추세로만 데이터가 쭉 이어졌던 경우 (T-2가 없음)
            trend_t_minus_2 = previous_trend
            # i는 "이전 추세"가 몇 봉 동안 유지되었는지 알 수 있는 지점
            # i가 0까지 내려갔다면 전체가 T-1 추세였다는 뜻
            bars_since_t_minus_1 = i  # 0-based index에서 i까지가 T-1 추세
        else:
            trend_t_minus_2 = df["trend"].iloc[j]
            # T-1 추세가 언제부터 언제까지였는지
            bars_since_t_minus_1 = i - j

    return (
        current_trend,         # T0
        previous_trend,        # T-1
        bars_since_change,     # T0 추세로 바뀐 뒤 지난 봉 수
        trend_t_minus_2,       # T-2
        bars_since_t_minus_1,  # T-1 추세가 몇 봉 유지되었는지
    )

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
            current_trend_1m, t1_trend_1m, t1_1m, t2_trend_1m, t2_1m = get_trend_info(df_1m)
            current_trend_5m, t1_trend_5m, t1_5m, t2_trend_5m, t2_5m = get_trend_info(df_5m)
            current_trend_1h, t1_trend_1h, t1_1h, t2_trend_1h, t2_1h = get_trend_info(df_1h)

            # 3) 보조 지표 계산 == rsi, obv, obv_diff, 5일 거래량 평균, 매수세 비중
            # 3-1) 1분봉
            previous_1m = df_1m.iloc[-2]
            last_1m = df_1m.iloc[-1]
            obv_1m = last_1m["obv"]
            obv_past_1m = (df_1m["obv"].iloc[ -(obv_lookback + 1) : -1].mean()) / obv_lookback
            obv_diff_1m = obv_1m - obv_past_1m

            # 3-2) 5분봉
            previous_5m = df_5m.iloc[-2]
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
                "current_trend_1m": int(current_trend_1m), # 1분봉 현재 추세
                "t1_trend_1m": int(t1_trend_1m),           # 1분봉 직전 추세
                "t1_1m": int(t1_1m),                       # 1분봉 현재 추세 지속시간
                "t2_trend_1m": int(t2_trend_1m),           # 1분봉 직전의 직전 추세
                "t2_1m": int(t2_1m),                       # 1분봉 직전 추세 지속시간

                "current_trend_5m": int(current_trend_5m), # 5분봉 현재 추세
                "t1_trend_5m": int(t1_trend_5m),           # 5분봉 직전 추세
                "t1_5m": int(t1_5m),                       # 5분봉 현재 추세 지속시간
                "t2_trend_5m": int(t2_trend_5m),           # 5분봉 직전의 직전 추세
                "t2_5m": int(t2_5m),                       # 5분봉 직전 추세 지속시간

                "current_trend_1h": int(current_trend_1h), # 1시간봉 현재 추세 
                "t1_trend_1h": int(t1_trend_1h),           # 1시간봉 직전 추세
                "t1_1h": int(t1_1h),                       # 1시간봉 현재 추세 지속시간
                "t2_trend_1h": int(t2_trend_1h),           # 1시간봉 직전의 직전 추세
                "t2_1h": int(t2_1h),                       # 1시간봉 직전 추세 지속시간

                "volume_ratio":volume_ratio,         # 거래량이 최근 평균보다 높으면 1보다 크고, 낮으면 1보다 작음
                "buy_volume_ratio":buy_volume_ratio, # 총 거래량 중 시장가 매수 비율

                "previous_1m": previous_1m,
                "last_1m":last_1m,
                "obv_diff_1m":obv_diff_1m,

                "previous_5m": previous_5m,
                "last_5m":last_5m,
                "obv_diff_5m":obv_diff_5m,
            }

def get_symbol_info(symbol, client):
    """
    심볼의 거래 제한 정보를 반환 (stepSize, minQty 포함)
    """
    try:
        exchange_info = client.get_exchange_info()
        for symbol_info in exchange_info["symbols"]:
            if symbol_info["symbol"] == symbol:
                for filter in symbol_info["filters"]:
                    if filter["filterType"] == "LOT_SIZE":
                        return {
                            "stepSize": float(filter["stepSize"]),
                            "minQty": float(filter["minQty"])
                        }
        raise ValueError(f"{symbol}의 거래 제한 정보를 찾을 수 없습니다.")
    except Exception as e:
        print(f"거래 제한 정보 조회 중 오류 발생: {e}")
        return {"stepSize": 1.0, "minQty": 0.0}

def trend_signal(data_core, future):
    """
    "current_trend_1m":    # 1분봉 현재 추세
    "t1_trend_1m":         # 1분봉 직전 추세
    "t1_1m":               # 1분봉 현재 추세 지속시간
    "t2_trend_1m":         # 1분봉 직전의 직전 추세
    "t2_1m":               # 1분봉 직전 추세 지속시간

    "current_trend_5m":    # 5분봉 현재 추세
    "t1_trend_5m":         # 5분봉 직전 추세
    "t1_5m":               # 5분봉 현재 추세 지속시간
    "t2_trend_5m":         # 5분봉 직전의 직전 추세
    "t2_5m":               # 5분봉 직전 추세 지속시간

    "current_trend_1h":    # 1시간봉 현재 추세 
    "t1_trend_1h":         # 1시간봉 직전 추세
    "t1_1h":               # 1시간봉 현재 추세 지속시간
    "t2_trend_1h":         # 1시간봉 직전의 직전 추세
    "t2_1h":               # 1시간봉 직전 추세 지속시간

    "volume_ratio":        # 거래량이 최근 평균보다 높으면 1보다 크고, 낮으면 1보다 작음
    "buy_volume_ratio":    # 총 거래량 중 시장가 매수 비율

    -------------------------------------------------------------------------------------
    각 봉 데이터에는 아래 칼럼이 포함되어 있음.
    'Open Time', 'Open', 'High', 'Low', 'Close', 'Volume',
    'Taker Buy Base Asset Volume', 'Taker Sell Base Asset Volume', 'SMA_20',
    'SMA_60', 'SMA_120', 'rsi', 'rsi_signal', 'middle_boll', 'upper_boll',
    'lower_boll', 'percent_b', 'bandwidth', 'obv', 'obv_max_5', 'obv_min_5',
    'obv_slope_from_max', 'obv_slope_from_min', 'trend', 'RBW'
    선물 데이터는 'fundingRate' 칼럼 또한 포함

    "last_1m":             # 1분봉 데이터
    "obv_diff_1m":         # 1분봉 obv 기울기

    "last_5m":             # 5분봉 데이터
    "obv_diff_5m":         # 5분봉 obv 기울기
    """

    signal = "hold"
    weight = 0
    reason = ""
    stop_loss = 0.98
    take_profit = 1.02

    if data_core["current_trend_5m"] == 1 :
        # 진입 조건
        if data_core["t1_trend_5m"] in [7, 8, 9] and data_core["t1_5m"] < 5:
            reason += f"| 골든크로스 발생 "
            weight += 1
        if data_core["volume_ratio"] > 1:
            reason += f"| 거래량 평균 대비 {data_core["volume_ratio"]}배 "
            weight += 1
        if data_core["buy_volume_ratio"] > 0.5:
            reason += f"| 시장가 매수 체결 비율 {data_core["buy_volume_ratio"]} 이상 "
            weight += 1
        if data_core["last_5m"]["percent_b"] >= 0.5:
            reason += f"| %b 0.4 이상 "
            weight += 1
        if data_core["last_5m"]["obv_slope_from_max"] < 0 or data_core["obv_diff_5m"] > 0:
            reason += f"| obv 상승추세 확인 "
            weight += 1
        
        # 진입 제한 조건
        if data_core["last_5m"]["percent_b"] >= 1.0:
            weight = weight // 2
            reason += "| 상단 밴드 돌파 -> 추격 진입 약화 "
        if data_core["last_5m"]["rsi"] >= 70:
            weight = weight //2
            reason += "| RSI 과매수 경계 "

        if future:
            if weight > 0:
                signal = "L_buy"
                stop_loss = 0.95
                take_profit = 1.1
        else:
            if weight > 0:
                signal = "buy"
                stop_loss = 0.98
                take_profit = 1.04

        # 손절매 조건
        if data_core["last_5m"]["SMA_60"]*0.99 >= data_core["last_5m"]["Close"]:
            if future:
                signal = "L_sell"
            else:
                signal = "sell"
            weight = 5
            reason = "| 60이평선 지지 붕괴, 손절 "

    elif data_core["current_trend_5m"] == 2 :
        # 진입 조건
        if data_core["t1_trend_5m"] in [7, 8, 9] and data_core["t1_5m"] < 5:
            reason += "| 골든크로스 발생 "
            weight += 1
        if data_core["volume_ratio"] > 1:
            reason += f"| 거래량 평균 대비 {data_core['volume_ratio']}배 "
            weight += 1
        if data_core["buy_volume_ratio"] > 0.5:
            reason += f"| 시장가 매수 체결 비율 {data_core['buy_volume_ratio']} 이상 "
            weight += 1
        if data_core["last_5m"]["percent_b"] >= 0.4:
            reason += "| %b 0.3 이상 "
            weight += 1
        if data_core["last_5m"]["obv_slope_from_max"] < 0 or data_core["obv_diff_5m"] > 0:
            reason += "| OBV 상승추세 확인 "
            weight += 1

        # 진입 제한 조건
        if data_core["last_5m"]["percent_b"] >= 0.95:
            weight = weight // 2
            reason += "| 상단 근접 -> 추격 진입 약화 "
        if data_core["last_5m"]["rsi"] >= 70:
            weight = weight // 2
            reason += "| RSI 과매수 경계 "

        if weight > 0:
            if future:
                signal = "L_buy"
                stop_loss = 0.97
                take_profit = 1.08
            else:
                signal = "buy"
                stop_loss = 0.98
                take_profit = 1.04

        # 손절매 조건
        if data_core["last_5m"]["SMA_60"] * 0.99 >= data_core["last_5m"]["Close"]:
            if future:
                signal = "L_sell"
            else:
                signal = "sell"
            weight = 5
            reason += "| 60이평선 지지 붕괴, 손절 "

    if data_core["current_trend_5m"] == 3:
        # 진입조건
        if data_core["volume_ratio"] > 1:
            reason += f"| 거래량 {data_core['volume_ratio']}배↑ "
            weight += 1
        if data_core["buy_volume_ratio"] > 0.5:
            reason += f"| 매수우위 {data_core['buy_volume_ratio']} "
            weight += 1
        if data_core["last_5m"]["obv_diff_5m"] > 0:
            reason += "| OBV 단기 상승 "
            weight += 1
        if data_core["last_5m"]["obv_slope_from_max"] < 0:
            reason += "| OBV max 초과 가능성 "
            weight += 1
        if data_core["last_5m"]["percent_b"] >= 1.0 and data_core["previous_5m"]["percent_b"] >= 1.0:
            reason += "| %b >= 1.0 (상단이탈) "
            weight += 1

        # 제한 조건
        if data_core["volume_ratio"] < 0.8:
            weight -= 1
            reason += "| 거래량 미미 "
        if data_core["buy_volume_ratio"] < 0.4:
            weight -= 1
            reason += "| 매수세 부족 "

        # RSI가 80↑ 등 극단 과매수면 상승 돌파 후 급락 가능성
        if data_core["last_5m"]["rsi"] >= 80:
            weight = weight // 2
            reason += "| RSI 극과매수 -> 진입 축소 "

        if weight > 0:
            if future:
                signal = "L_buy"
                stop_loss = 0.98
                take_profit = 1.10
            else:
                signal = "buy"
                stop_loss = 0.98
                take_profit = 1.05

        if data_core["last_5m"]["Close"] <= data_core["last_5m"]["SMA_60"] * 0.99:
            if future:
                signal = "L_sell"
            else:
                signal = "sell"
            weight = 5
            reason += "| 60이평 이탈 손절 "

    elif data_core["current_trend_5m"] == 4 :
        if future:
            pass
        else:
            pass

    elif data_core["current_trend_5m"] == 5 :
        if future:
            pass
        else:
            pass

    elif data_core["current_trend_5m"] == 6 :
        if future:
            pass
        else:
            pass

    elif data_core["current_trend_5m"] == 7 :
        if future:
            pass
        else:
            pass

    elif data_core["current_trend_5m"] == 8 :
        if future:
            pass
        else:
            pass

    elif data_core["current_trend_5m"] == 9 :
        if future:
            pass
        else:
            pass

    elif data_core["current_trend_5m"] == -1 :
        if future:
            pass
        else:
            pass

    elif data_core["current_trend_5m"] == -2 :
        if future:
            pass
        else:
            pass

    elif data_core["current_trend_5m"] == -3 :
        if future:
            pass
        else:
            pass

    elif data_core["current_trend_5m"] == -4 :
        if future:
            pass
        else:
            pass

    elif data_core["current_trend_5m"] == -5 :
        if future:
            pass
        else:
            pass

    elif data_core["current_trend_5m"] == -6 :
        if future:
            pass
        else:
            pass

    elif data_core["current_trend_5m"] == -7 :
        if future:
            pass
        else:
            pass

    elif data_core["current_trend_5m"] == -8 :
        if future:
            pass
        else:
            pass

    elif data_core["current_trend_5m"] == -9 :
        if future:
            pass
        else:
            pass

    elif data_core["current_trend_5m"] == -9 :
        if future:
            pass
        else:
            pass

    elif data_core["current_trend_5m"] == 0 :
        if future:
            pass
        else:
            pass

    elif data_core["current_trend_5m"] == 10 :
        if future:
            pass
        else:
            pass

    return signal, weight, reason, stop_loss, take_profit