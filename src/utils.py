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
    while i >= 0 and (df["trend"].iloc[i] == current_trend or df["trend"].iloc[i] == 0):
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
        while j >= 0 and (df["trend"].iloc[j] == previous_trend or df["trend"].iloc[i] == 0):
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

    # 1. 기본 데이터 준비
    current_price = data_core["last_1m"]["Close"]
    
    # RSI 및 거래량 데이터
    rsi_1m = data_core["last_1m"].get("rsi", 50)
    volume_ratio = data_core.get("volume_ratio", 1)
    buy_volume_ratio = data_core.get("buy_volume_ratio", 0.5)
    
    # 볼린저 밴드 데이터
    bb_upper = data_core["last_5m"].get("upper_boll")
    bb_lower = data_core["last_5m"].get("lower_boll")
    bb_middle = data_core["last_5m"].get("middle_boll")
    percent_b = data_core["last_5m"].get("percent_b", 0.5)
    
    # 추세 데이터
    trend_1h = data_core.get("current_trend_1h", 0)
    trend_5m = data_core.get("current_trend_5m", 0)
    
    # OBV 데이터
    obv_diff = data_core.get("obv_diff_5m", 0)
    
    # Funding Rate (선물 전용)
    funding_rate = data_core["last_5m"].get("fundingRate", 0) if future else 0
    
    # 2. 신호 및 기본값 초기화
    signal = "hold"
    weight = 0
    reason = []
    stop_loss = current_price * 0.98
    take_profit = current_price * 1.02
    
    # 3. 시장 상태 분석
    t_5m = 0 if trend_5m == 10 else trend_5m
    t_1h = 0 if trend_1h == 10 else trend_1h
    # 추세 점수 계산 (1시간봉 가중치 2배)
    trend_score = (t_5m + (t_1h * 2)) / 3
    
    # RSI 상태
    is_oversold = rsi_1m < 30
    is_overbought = rsi_1m > 70
    
    # 볼린저 밴드 상태
    is_near_lower = percent_b < 0.2
    is_near_upper = percent_b > 0.8
    
    # 거래량 상태
    strong_buy_volume = volume_ratio > 1.2 and buy_volume_ratio > 0.6
    strong_sell_volume = volume_ratio > 1.2 and buy_volume_ratio < 0.4
    
    # 4. 선물 거래 신호 생성
    if future:
        long_conditions = 0
        short_conditions = 0
        
        # 롱 포지션 진입 조건
        if is_oversold:
            long_conditions += 1
        if is_near_lower and trend_score > 0:
            long_conditions += 1
        if strong_buy_volume:
            long_conditions += 1
        if obv_diff > 0:
            long_conditions += 1
        if funding_rate < -0.01:  # 네거티브 펀딩
            long_conditions += 1
            
        # 숏 포지션 진입 조건
        if is_overbought:
            short_conditions += 1
        if is_near_upper and trend_score < 0:
            short_conditions += 1
        if strong_sell_volume:
            short_conditions += 1
        if obv_diff < 0:
            short_conditions += 1
        if funding_rate > 0.01:  # 포지티브 펀딩
            short_conditions += 1
        
        # 롱 진입/청산 신호
        if long_conditions >= 3 and trend_score > 0:
            signal = "L_buy"
            weight = min(long_conditions, 4)
            stop_loss = current_price * 0.985  # 레버리지 고려하여 손절폭 축소
            take_profit = current_price * 1.025
            reason.append(f"롱 진입: {long_conditions}개 조건 충족")
            
        elif trend_score < -0.5 or (is_overbought and trend_score < 0):
            signal = "L_sell"
            weight = 5  # 빠른 청산 필요
            reason.append("롱 청산: 추세 반전")
            
        # 숏 진입/청산 신호
        elif short_conditions >= 3 and trend_score < 0:
            signal = "S_buy"
            weight = min(short_conditions, 4)
            stop_loss = current_price * 1.015  # 레버리지 고려하여 손절폭 축소
            take_profit = current_price * 0.975
            reason.append(f"숏 진입: {short_conditions}개 조건 충족")
            
        elif trend_score > 0.5 or (is_oversold and trend_score > 0):
            signal = "S_sell"
            weight = 5  # 빠른 청산 필요
            reason.append("숏 청산: 추세 반전")
            
    # 5. 현물 거래 신호 생성
    else:
        buy_conditions = 0
        sell_conditions = 0
        
        # 매수 조건 체크
        if is_oversold:
            buy_conditions += 1
        if is_near_lower and trend_score > 0:
            buy_conditions += 1
        if strong_buy_volume:
            buy_conditions += 1
        if obv_diff > 0:
            buy_conditions += 1
            
        # 매도 조건 체크
        if is_overbought:
            sell_conditions += 1
        if is_near_upper and trend_score < 0:
            sell_conditions += 1
        if strong_sell_volume:
            sell_conditions += 1
        if obv_diff < 0:
            sell_conditions += 1
        
        # 최종 신호 결정
        if buy_conditions >= 3:
            signal = "buy"
            weight = min(buy_conditions, 5)
            reason.append(f"현물 매수: {buy_conditions}개 조건 충족")
            
        elif sell_conditions >= 3:
            signal = "sell"
            weight = min(sell_conditions, 5)
            reason.append(f"현물 매도: {sell_conditions}개 조건 충족")
        
    # 6. 변동성에 따른 보정
    if "bandwidth" in data_core["last_5m"]:
        bandwidth = data_core["last_5m"]["bandwidth"]
        if bandwidth > 0.05:  # 높은 변동성
            weight = max(1, weight - 1)
            reason.append("변동성 고려 주문량 감소")
    
    reason = " + ".join(reason)

    return signal, weight, reason, stop_loss, take_profit

def signal_maker_1(data_core, future):

    # 신호 및 기본값 초기화
    current_price = data_core["last_1m"]["Close"]
    trend_5m = data_core.get("current_trend_5m", 0)

    GC_20_60 = trend_5m in [1, 2, 3, 4, 5, 6, -4, -5, -6] and data_core["t1_trend_5m"] in [7, 8, 9, -1, -2, -3, -7, -8, -9] and data_core["t1_5m"] < 5
    GC_60_120 =  trend_5m in [1, 2, 3, 7, 8, 9, -1, -2, -3] and data_core["t1_trend_5m"] in [4, 5, 6, -4, -5, -6, -7, -8, -9] and data_core["t1_5m"] < 5
    GC_rsi = data_core["last_5m"]["rsi"] > data_core["last_5m"]["rsi_signal"] and data_core["previous_5m"]["rsi"] < data_core["previous_5m"]["rsi_signal"]

    DC_20_60 = trend_5m in [7, 8, 9, -1, -2, -3, -7, -8, -9] and data_core["t1_trend_5m"] in [1, 2, 3, 4, 5, 6, -4, -5, -6] and data_core["t1_5m"] < 5
    DC_60_120 =  trend_5m in [4, 5, 6, -4, -5, -6, -7, -8, -9] and data_core["t1_trend_5m"] in [1, 2, 3, 7, 8, 9, -1, -2, -3] and data_core["t1_5m"] < 5
    DC_rsi = data_core["last_5m"]["rsi"] < data_core["last_5m"]["rsi_signal"] and data_core["previous_5m"]["rsi"] > data_core["previous_5m"]["rsi_signal"]

    signal = "hold"
    weight = 0
    reason = []
    stop_loss = current_price * 0.95
    take_profit = current_price * 1.05

    # sma120 < sma60 < sma20
    if trend_5m in [1, 2, 3]:
        if data_core["volume_ratio"] > 1:
            weight += 1
        if data_core["buy_volume_ratio"] > 0.6:
            weight += 1
        if GC_rsi and data_core["last_5m"]["rsi"] < 70:
            weight += 2
        if data_core["last_5m"]["percent_b"] > 0.4:
            weight += 1
        
        if weight > 0:
            if future:
                signal = "L_buy"
            else:
                signal = "buy"
        
        # 손절조건
        if data_core["last_5m"]["rsi"] < 50 and data_core["volume_ratio"] < 0.8 and data_core["last_5m"]["obv_slope_from_min"] > 0:
            if future:
                signal = "L_sell"
            else:
                signal = "sell"
            weight = 5
        
        # 익절조건
        if data_core["last_5m"]["rsi"] > 70 and data_core["last_5m"]["rsi"] + 1 < data_core["previous_5m"]["rsi"]:
            if future:
                signal = "L_sell"
            else:
                signal = "sell"
            weight = 5
    
    # sma120 < sma20 < sma60
    elif trend_5m in [7, 8, 9]:
        if data_core["last_5m"]["obv_slope_from_min"] < 0:
            weight += 1
        if data_core["volume_ratio"] > 1.0 and data_core["buy_volume_ratio"] > 0.6:
            weight += 1
        if GC_rsi and 60 > data_core["last_5m"]["rsi"] > 50:
            weight += 2
        
        if weight > 0:
            if future:
                signal = "L_buy"
            else:
                signal = "buy"

        # 손절조건
        if data_core["last_5m"]["percent_b"] < 0.4 and data_core["last_5m"]["rsi"] < 50:
            if future:
                signal = "L_sell"
            else:
                signal = "sell"
            weight = 5

        # 익절조건
        if data_core["volume_ratio"] < 0.8 and data_core["last_5m"]["rsi"] > 70:
            if future:
                signal = "L_sell"
            else:
                signal = "sell"
            weight = 5

    # sma20 < sma120 < sma60
    # 일단 패스

    # sma20 < sma60 < sma120
    elif trend_5m in [-7, -8,-9]:
        if DC_rsi and data_core["last_5m"]["rsi"] >30:
            weight += 1
        if data_core["volume_ratio"] > 0.8 and data_core["buy_volume_ratio"] < 0.4:
            weight += 2
        if data_core["last_5m"]["percent_b"] < 0.4:
            weight += 1

        if weight > 0:
            if future:
                signal = "S_buy"
            else:
                signal = "sell"

        # 숏 손절조건
        if GC_20_60 and data_core["buy_volume_ratio"] > 0.6 and data_core["volume_ratio"] > 0.8:
            if future:
                signal = "L_buy"
                weight = 2
            else:
                signal = "buy"
                weight = 2
        
        # 숏 익절조건
        if data_core["last_5m"]["rsi"] < 25:
            if future:
                signal = "S_sell"
                weight = 5

    """
    trend 변화
    sma120 < sma60 < sma20    # 1, 2, 3
    sma120 < sma20 < sma60    # 7, 8, 9
    sma20 < sma120 < sma60    # -1, -2, -3
    sma20 < sma60 < sma120    # -7, -8, -9
    sma60 < sma20 < sma120    # -4, -5, -6
    sma60 < sma120 < sma20    # 4, 5, 6
    """

    # 이동평균선 전략
    """
        **매수 조건**  
    1. **전반적 상승 추세 확인**  
    - 현재 가격이 120일 SMA 위에 있어야 함  
    2. **단기 모멘텀 상승 신호**  
    - 20일 EMA가 60일 EMA를 아래에서 위로 교차하는 순간 발생  
        - 전일: 20일 EMA ≤ 60일 EMA  
        - 당일: 20일 EMA > 60일 EMA  
    3. **중기 확인**  
    - 60일 EMA가 120일 SMA 위에 있어, 중기 추세도 상승임을 확인  
    4. **추가 확인 (옵션)**  
    - 거래량이 평균보다 상승하거나, RSI(14)가 50 이상이면 신호의 신뢰도 상승
    ---

    **매도 조건**  
    1. **전반적 하락 추세 확인**  
    - 현재 가격이 120일 SMA 아래에 있어야 함  
    2. **단기 모멘텀 약세 신호**  
    - 20일 EMA가 60일 EMA를 위에서 아래로 교차하는 순간 발생  
        - 전일: 20일 EMA ≥ 60일 EMA  
        - 당일: 20일 EMA < 60일 EMA  
    3. **중기 확인**  
    - 60일 EMA가 120일 SMA 아래에 있어, 중기 추세도 하락임을 확인  
    4. **추가 확인 (옵션)**  
    - 거래량 급증 시 가격 하락 동반, 또는 RSI(14)가 50 이하이면 신호 강화

    """

    # rsi 전략
    """
    **매수 조건**  
    1. **과매도 구간:**  
        - RSI14가 30 이하일 때, 시장이 과매도 상태임을 의미  
    2. **반전 신호:**  
        - RSI14가 자신의 14일 SMA(RSI SMA14)를 하향에서 상향 돌파할 때  
        - 근거: 단순 과매도 상태에서 반등 신호가 발생하며, SMA와의 교차로 모멘텀 전환을 확인  
    3. **추가 필터:**  
        - 거래량이나 다른 모멘텀 지표로 상승 모멘텀을 추가 확인하면 신뢰도 상승

    **매수 반전 신호 구체화**  
    1. **과매도 구간 진입 확인**  
        - RSI14가 30 이하에 머무르며 시장이 극심한 매도 압력을 받고 있음을 확인  
        - 단, 단기 노이즈로 인한 스파이크 방지를 위해 2~3일 연속 30 이하인 경우를 고려
    
    2. **반전 교차 포착**  
        - RSI14가 자신의 14일 SMA를 아래에서 위로 교차하는 순간을 포착  
        - 교차 발생 시, RSI14가 30에서 상승하기 시작하고, SMA와의 간격이 서서히 벌어지는 패턴이면 강력한 반전 신호로 판단
    
    3. **추가 모멘텀 확인**  
        - 교차 후 RSI14가 35 이상으로 상승하며, 상승세를 유지하는지 관찰  
        - 거래량 증가나 가격 반등 등 다른 모멘텀 지표와 함께 나타난다면 신호의 신뢰도가 상승
    
    4. **실시간 모니터링 및 진입**  
        - 반전 신호 발생 후 다음 캔들에서 확인 차 매수 진입  
        - 단, 이후에도 RSI14가 단기적으로 하락 전환되는 모양새가 보이면 진입을 재검토
    ---

    **매도 조건**  
    1. **과매수 구간:**  
        - RSI14가 70 이상일 때, 시장이 과매수 상태임을 의미  
    2. **반전 신호:**  
        - RSI14가 자신의 14일 SMA를 상향에서 하향 돌파할 때  
        - 근거: 과매수 상태에서 하락 전환 가능성이 커지며, SMA와의 교차가 단기 모멘텀 약화를 반영  
    3. **추가 필터:**  
        - 거래량 급증 등 추가 신호가 뒷받침되면 매도 신호의 신뢰도 강화
    
    **매도 반전 신호 구체화**  
    1. **과매수 구간 진입 확인**  
        - RSI14가 70 이상에 머무르며 과도한 매수 심리가 형성됨을 확인  
        - 2~3일 연속 70 이상일 경우 과매수 구간이 안정적으로 유지되고 있다고 판단
    
    2. **반전 교차 포착**  
        - RSI14가 자신의 14일 SMA를 위에서 아래로 교차하는 순간을 포착  
        - 교차 발생 시, RSI14가 70 이하로 내려가면서 SMA와의 간격이 좁혀지는 패턴이면 강력한 반전 신호로 판단
    
    3. **추가 모멘텀 확인**  
        - 교차 후 RSI14가 65 이하로 떨어지며, 하락세가 지속되는지 확인  
        - 거래량 급증이나 가격 하락 모멘텀이 동반되면 신호의 신뢰도가 상승
    
    4. **실시간 모니터링 및 청산**  
        - 반전 신호 발생 후 다음 캔들에서 확인 차 매도 진입 또는 포지션 청산  
        - 이후 RSI14가 다시 상승하는 모양새를 보이면 조기 청산이나 포지션 축소 고려
    """

    # obv 전략
    """
    **매수 조건 (OBV 기반 반전 및 모멘텀 회복 신호)**

    1. **장기 OBV 상승 추세 확인**  
        - OBV가 최근 상승세를 보이며, 전반적으로 누적 매수 압력이 증가하고 있는지 확인  
        - 근거: OBV가 상승하면 거래량과 가격 상승이 동반되어 상승 모멘텀이 강화됨

    2. **최소값 대비 기울기 확인**  
        - 최근 5개봉 OBV 최소값 대비 기울기 { (이전 5개봉 OBV 최소값 - 현재 OBV)/6 }가 양수로 전환되고 일정 수준(예: 0.5 이상)으로 증가  
        - 근거: 과거 최저점 대비 현재 OBV가 상승세로 전환되면 매수세가 강화되는 신호로 볼 수 있음

    3. **최대값 대비 기울기 안정성 검토 (옵션 필터)**  
        - 최근 5개봉 OBV 최대값 대비 기울기 { (이전 5개봉 OBV 최대값 - 현재 OBV)/6 }는 상대적으로 낮은 수치를 유지하거나, 완만하게 변화  
        - 근거: 매수 압력이 최고점에서 크게 하락하지 않고, 안정적으로 상승 모멘텀을 유지하고 있음을 암시

    ---

    **매도 조건 (OBV 기반 고점 다이버전스 및 약세 신호)**

    1. **장기 OBV 하락 추세 확인**  
        - OBV가 하락세에 있거나, 고점 대비 상승 폭이 줄어들어 매도 압력이 점차 커지는지 확인  
        - 근거: OBV가 하락하면 거래량과 가격 하락이 동반되어 하락 모멘텀이 강화됨

    2. **최대값 대비 기울기 확인**  
        - 최근 5개봉 OBV 최대값 대비 기울기 { (이전 5개봉 OBV 최대값 - 현재 OBV)/6 }가 양수로 상승하며, 일정 임계치(예: 0.5 이상)를 초과  
        - 근거: 최고점 대비 OBV가 크게 하락하면 매수세가 약화되고 매도 압력이 나타나는 신호로 볼 수 있음

    3. **최소값 대비 기울기 안정성 검토 (옵션 필터)**  
        - 최근 5개봉 OBV 최소값 대비 기울기는 크게 변화하지 않거나 완만한 하락세를 보일 경우, 이미 바닥을 찍은 상태로 판단  
        - 근거: 최소값 대비 기울기가 크게 변화하지 않으면, 하락 모멘텀이 지속될 가능성이 크므로 매도 신호 강화
    """

    return signal, weight, reason, stop_loss, take_profit

def signal_maker_2(data_core, future):

    # 신호 및 기본값 초기화
    current_price = data_core["last_1m"]["Close"]
    trend_5m = data_core.get("current_trend_5m", 0)

    GC_20_60 = trend_5m in [1, 2, 3, 4, 5, 6, -4, -5, -6] and data_core["t1_trend_5m"] in [7, 8, 9, -1, -2, -3, -7, -8, -9] and data_core["t1_5m"] < 5
    GC_60_120 =  trend_5m in [1, 2, 3, 7, 8, 9, -1, -2, -3] and data_core["t1_trend_5m"] in [4, 5, 6, -4, -5, -6, -7, -8, -9] and data_core["t1_5m"] < 5
    GC_rsi = data_core["last_5m"]["rsi"] > data_core["last_5m"]["rsi_signal"] and data_core["previous_5m"]["rsi"] < data_core["previous_5m"]["rsi_signal"]

    DC_20_60 = trend_5m in [7, 8, 9, -1, -2, -3, -7, -8, -9] and data_core["t1_trend_5m"] in [1, 2, 3, 4, 5, 6, -4, -5, -6] and data_core["t1_5m"] < 5
    DC_60_120 =  trend_5m in [4, 5, 6, -4, -5, -6, -7, -8, -9] and data_core["t1_trend_5m"] in [1, 2, 3, 7, 8, 9, -1, -2, -3] and data_core["t1_5m"] < 5
    DC_rsi = data_core["last_5m"]["rsi"] < data_core["last_5m"]["rsi_signal"] and data_core["previous_5m"]["rsi"] > data_core["previous_5m"]["rsi_signal"]

    # rsi 정규화
    rsi = data_core["last_5m"]["rsi"]
    previous_rsi = data_core["previous_5m"]["rsi"]

    signal = "hold"
    weight = 0
    reason = []
    stop_loss = 0.95
    take_profit = 1.05

    # 이동평균선 활용 전략
    if trend_5m in [1, 2, 3]:
    # 진입조건
        # 가격이 20일 이동평균선 지지 (0.4 < %b)
        if data_core["last_5m"]["percent_b"] >0.4 and data_core["last_5m"]["SMA_20"] * 1.01 > current_price:
            weight += 1

        # volume_ratio > 1.0
        if data_core["volume_ratio"] > 1.0:
            weight += 1

        # buy_volume_ratio > 0.6
        if data_core["buy_volume_ratio"] > 0.6:
            weight += 1

        # 골든크로스
        if GC_20_60:
            weight += 1
            if GC_60_120:
                weight += 1

        # rsi 골든크로스
        if GC_rsi:
            weight += 2

        # rsi > rsi_signal
        if data_core["last_5m"]["rsi"] > data_core["last_5m"]["rsi_signal"]:
            weight += 1

        # obv_slope_from_max < 0
        if data_core["last_5m"]["obv_slope_from_max"] < 0:
            weight += 2

        weight = weight // 2 # weight 총합이 10이므로 2로 나눈 몫을 활용
        if weight > 0:
            if future:
                signal = "L_buy"
            else:
                signal = "buy"
            
            stop_loss = 0.97
            take_profit = 1.1

    # 손절조건
        # 가격이 20일 이동평균선 하향돌파 (%b < 0.4)
        if data_core["last_5m"]["percent_b"] < 0.4:
            if future:
                signal = "L_sell"
            else:
                signal = "sell"

            weight = 5

    elif trend_5m in [-7, -8, -9]:
    # 진입조건
        # 가격이 20일 이동평균선 저항 (%b < 0.6)
        if data_core["last_5m"]["percent_b"] < 0.6:
            weight += 1

        # volume_ratio > 1.0
        if data_core["volume_ratio"] > 1.0:
            weight += 1

        # buy_volume_ratio < 0.4
        if data_core["buy_volume_ratio"] < 0.4:
            weight += 1

        # 데드크로스
        if DC_20_60:
            weight += 1
            if DC_60_120:
                weight += 1

        # rsi 데드크로스
        if DC_rsi:
            weight += 2

        # rsi < rsi_signal
        if data_core["last_5m"]["rsi"] < data_core["last_5m"]["rsi_signal"]:
            weight += 1

        # obv_slope_from_min > 0
        if data_core["last_5m"]["obv_slope_from_min"] > 0:
            weight += 2

        weight = weight // 2
        if weight > 0:
            if future:
                signal = "S_buy"

                stop_loss = 1.05
                take_profit = 0.9
            else:
                signal = "sell"

    # 손절조건
        # 가격이 20일 이동평균선 상향돌파 (0.6 < %b)
        if data_core["last_5m"]["percent_b"] > 0.6:
            if future:
                signal = "S_sell"
                weight = 5

    else:
    # 볼린저밴드를 활용한 박스권 매매
    # 밴드폭이 급격히 줄어드는 스퀴즈 구간 주의
        # 롱 포지션
        if data_core["last_5m"]["percent_b"] < 0.1:
            weight += 1
        if 0.7 < data_core["volume_ratio"] < 1.0:
            weight -= 1
        if data_core["buy_volume_ratio"] > 0.5:
            weight += 1
        if data_core["last_5m"]["rsi"] < 30:
            weight += 2
        elif data_core["last_5m"]["rsi"] < 45:
            weight += 1
        
        # 숏 포지션
        if data_core["last_5m"]["percent_b"] > 0.9:
            weight -= 1
        if 0.7 < data_core["volume_ratio"] < 1.0:
            weight -= 1
        if data_core["buy_volume_ratio"] < 0.5:
            weight -= 1
        if data_core["last_5m"]["rsi"] > 70:
            weight -= 2
        elif data_core["last_5m"]["rsi"] > 55:
            weight -= 1

        if weight > 0:
            if future:
                signal = "L_buy"
            else:
                signal = "buy"
        
        elif weight < 0:
            weight *= -1
            if future:
                signal = "S_buy"
            else:
                signal = "sell"

        if data_core["last_5m"]["RBW"] < 0.8:
            weight = 0
            signal = "hold"

    return signal, weight, reason, stop_loss, take_profit