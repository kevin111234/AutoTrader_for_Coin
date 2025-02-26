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
    rsi = data_core["last_5m"]["rsi"]
    previous_rsi = data_core["previous_5m"]["rsi"]

    trend_5m = data_core["current_trend_5m"]

    signal = "hold"
    weight = 0
    reason = []
    stop_loss = 0.9
    take_profit = 1.1

    if trend_5m > 0:

        if rsi < 35 and previous_rsi + 1 < rsi:
            signal = "buy"
            weight = 1
            if rsi < 30:
                weight += 1
                if rsi < 25:
                    weight += 1
                    if rsi < 20:
                        weight += 1
                        if rsi < 15:
                            weight += 1
            reason = f"rsi = {rsi}, previous_rsi = {previous_rsi}"

    if rsi > 65 and previous_rsi > rsi + 1:
        signal = "sell"
        weight = 1
        if rsi > 70:
            weight += 1
            if rsi > 75:
                weight += 1
                if rsi > 80:
                    weight += 1
                    if rsi > 85:
                        weight += 1
        reason = f"rsi = {rsi}, previous_rsi = {previous_rsi}"

    return signal, weight, reason, stop_loss, take_profit

def signal_maker_2(data_core, future):

    # 신호 및 기본값 초기화
    current_price = data_core["last_1m"]["Close"]
    trend_5m = data_core.get("current_trend_5m", 0)

    GC_20_60 = (
        trend_5m in [1, 2, 3, 4, 5, 6, -4, -5, -6]
        and data_core["t1_trend_5m"] in [7, 8, 9, -1, -2, -3, -7, -8, -9]
        and data_core["t1_5m"] < 5
    )
    GC_60_120 = (
        trend_5m in [1, 2, 3, 7, 8, 9, -1, -2, -3]
        and data_core["t1_trend_5m"] in [4, 5, 6, -4, -5, -6, -7, -8, -9]
        and data_core["t1_5m"] < 5
    )
    GC_rsi = (
        data_core["last_5m"]["rsi"] > data_core["last_5m"]["rsi_signal"]
        and data_core["previous_5m"]["rsi"] < data_core["previous_5m"]["rsi_signal"]
    )

    DC_20_60 = (
        trend_5m in [7, 8, 9, -1, -2, -3, -7, -8, -9]
        and data_core["t1_trend_5m"] in [1, 2, 3, 4, 5, 6, -4, -5, -6]
        and data_core["t1_5m"] < 5
    )
    DC_60_120 = (
        trend_5m in [4, 5, 6, -4, -5, -6, -7, -8, -9]
        and data_core["t1_trend_5m"] in [1, 2, 3, 7, 8, 9, -1, -2, -3]
        and data_core["t1_5m"] < 5
    )
    DC_rsi = (
        data_core["last_5m"]["rsi"] < data_core["last_5m"]["rsi_signal"]
        and data_core["previous_5m"]["rsi"] > data_core["previous_5m"]["rsi_signal"]
    )

    # rsi 정규화
    rsi = data_core["last_5m"]["rsi"]
    previous_rsi = data_core["previous_5m"]["rsi"]

    signal = "hold"
    weight = 0
    reason = []
    stop_loss = 0.95
    take_profit = 1.05

    # 1) 이동평균선 활용 전략
    if trend_5m in [1, 2, 3]:
        # 상승 추세로 간주
        # 진입조건 예시
        if data_core["last_5m"]["percent_b"] > 0.4 and data_core["last_5m"]["SMA_20"] * 1.01 > current_price:
            weight += 1
            reason.append("20일선 근접 지지 및 Bollinger %b > 0.4")

        if data_core["volume_ratio"] > 1.0:
            weight += 1
            reason.append(f"거래량 증가(volume_ratio={data_core['volume_ratio']:.2f} > 1)")

        if data_core["buy_volume_ratio"] > 0.6:
            weight += 1
            reason.append(f"시장가 매수 비중 증가(buy_volume_ratio={data_core['buy_volume_ratio']:.2f} > 0.6)")

        if GC_20_60:
            weight += 1
            reason.append("20-60 이동평균선 골든크로스 발생")
            if GC_60_120:
                weight += 1
                reason.append("60-120 이동평균선 골든크로스 발생 추가")

        if GC_rsi:
            weight += 2
            reason.append("RSI 골든크로스")

        if data_core["last_5m"]["rsi"] > data_core["last_5m"]["rsi_signal"]:
            weight += 1
            reason.append("RSI가 시그널 상향 돌파 중")

        if data_core["last_5m"]["obv_slope_from_max"] < 0:
            weight += 2
            reason.append("OBV 고점 대비 기울기 하락(매수세 유입 가능성)")

        # weight 보정
        weight -= 5  # (예: 총합 10 정도면 절반 보정)
        if weight > 0:
            if future:
                signal = "L_buy"
                reason.append("선물 롱 진입")
            else:
                signal = "buy"
                reason.append("현물 매수")
            stop_loss = 0.97
            take_profit = 1.1
        elif weight < 0:
            # 음수면 0으로 고정
            weight = 0

        # 손절조건 예시
        if data_core["last_5m"]["percent_b"] < 0.4:
            if future:
                signal = "L_sell"
                reason.append("하락 반전으로 롱 포지션 손절(%b < 0.4)")
            else:
                signal = "sell"
                reason.append("하락 반전으로 현물 청산(%b < 0.4)")
            weight = 5

    elif trend_5m in [-7, -8, -9]:
        # 하락 추세로 간주
        # 진입조건 예시
        if data_core["last_5m"]["percent_b"] < 0.6:
            weight += 1
            reason.append("20일선 저항 가능성(%b < 0.6)")

        if data_core["volume_ratio"] > 1.0:
            weight += 1
            reason.append(f"거래량 증가(volume_ratio={data_core['volume_ratio']:.2f} > 1)")

        if data_core["buy_volume_ratio"] < 0.4:
            weight += 1
            reason.append(f"매수세 비중 감소(buy_volume_ratio={data_core['buy_volume_ratio']:.2f} < 0.4)")

        if DC_20_60:
            weight += 1
            reason.append("20-60 이동평균선 데드크로스")
            if DC_60_120:
                weight += 1
                reason.append("60-120 이동평균선 데드크로스")

        if DC_rsi:
            weight += 2
            reason.append("RSI 데드크로스")

        if data_core["last_5m"]["rsi"] < data_core["last_5m"]["rsi_signal"]:
            weight += 1
            reason.append("RSI가 시그널 하향 돌파 중")

        if data_core["last_5m"]["obv_slope_from_min"] > 0:
            weight += 2
            reason.append("OBV 저점 대비 기울기 상승 → 매도세 유입")

        weight -= 5
        if weight > 0:
            # 숏 진입
            if future:
                signal = "S_buy"
                reason.append("선물 숏 진입")
                stop_loss = 1.05
                take_profit = 0.9
            else:
                signal = "sell"
                reason.append("현물 매도")
        elif weight < 0:
            weight = 0

        # 손절조건 예시
        if data_core["last_5m"]["percent_b"] > 0.6:
            if future:
                signal = "S_sell"
                reason.append("상승 반전으로 숏 포지션 손절(%b > 0.6)")
            else:
                signal = "sell"
                reason.append("상승 반전으로 포지션 정리(%b > 0.6)")
            weight = 5

    else:
        # 박스권 등 기타 추세
        # 아래는 예시로 숏 조건만 체크한 뒤, 음수 가중치면 매도 신호를 준 코드
        if data_core["last_5m"]["percent_b"] > 0.9:
            weight -= 1
            reason.append("Bollinger 상단 접근(%b > 0.9) → 숏 우위")
        if 0.7 < data_core["volume_ratio"] < 1.0:
            weight -= 1
            reason.append(f"거래량 애매(volume_ratio={data_core['volume_ratio']:.2f}) → 숏 우위")
        if data_core["buy_volume_ratio"] < 0.5:
            weight -= 1
            reason.append(f"매수세 부족(buy_volume_ratio={data_core['buy_volume_ratio']:.2f} < 0.5)")
        if data_core["last_5m"]["rsi"] > 70:
            weight -= 2
            reason.append(f"RSI 과매수(rsi={data_core['last_5m']['rsi']:.2f} >70)")
        elif data_core["last_5m"]["rsi"] > 55:
            weight -= 1
            reason.append(f"RSI 다소 높음(rsi={data_core['last_5m']['rsi']:.2f} >55)")

        # 숏 진입
        if weight < 0:
            weight *= -1  # 절댓값으로 사용
            if future:
                signal = "S_buy"
                reason.append("선물 숏 진입")
            else:
                signal = "sell"
                reason.append("현물 매도")

        # 추가 예시: RBW < 0.8 일 때 강제 매도
        if data_core["last_5m"]["RBW"] < 0.8:
            weight = 5
            signal = "sell"
            reason.append(f"밴드폭 축소(RBW={data_core['last_5m']['RBW']:.2f} <0.8) → 리스크 회피 매도")

    # reason 리스트를 합쳐 문자열로 변환
    reason_str = " | ".join(reason)

    return signal, weight, reason_str, stop_loss, take_profit

def signal_maker_3(data_core, future):
    """
    안정적인 수익과 낮은 리스크를 목표로 하며, 불필요한 손절(stop_loss) 발생을 줄이고
    확실한 상승 모멘텀이 확인될 때만 진입하는 전략.
    
    주요 조건:
      - 1시간봉에서 강한 상승 추세 (예: trend_1h >= 2)와 함께
      - 1분봉에서 RSI < 30, %b < 0.25, 거래량 비율 >= 1.0,
      - 5분봉의 추가 모멘텀 지표(예: MACD 양의 교차 또는 단기 상승 모멘텀) 조건을 만족할 때.
    
    동적 손절폭은 Bollinger 하단을 기준으로 계산하되, 80%~90% 범위를 참고합니다.
    
    반환:
      signal: "buy", "sell" 또는 "hold"
      weight: 거래 강도 (정수)
      reason: 신호 발생 근거 설명 문자열
      stop_loss: 손절 배수 (예: 0.97 => 진입가의 97%)
      take_profit: 익절 배수 (예: 1.03 => 진입가의 103%)
    """
    # 1) 기본 변수 설정 (1분봉 기준)
    current_price = data_core["last_5m"]["Close"]
    rsi = data_core["last_5m"].get("rsi", 50)
    percent_b = data_core["last_5m"].get("percent_b", 0.5)
    volume_ratio = data_core.get("volume_ratio", 1)
    trend_1h = data_core.get("current_trend_1h", 0)
    
    # Bollinger 밴드 하단 값 (없을 경우 기본값 설정)
    lower_boll = data_core["last_5m"].get("lower_boll", current_price * 0.97)
    
    # OBV 기울기 (매수의 경우 OBV 고점 대비 기울기 사용)
    obv_slope_buy = data_core["last_5m"].get("obv_slope_from_max", 0)
    
    # 추가: 5분봉의 단기 모멘텀 필터 (예: MACD나 단기 추세 변화 - 여기서는 trend_5m 활용)
    trend_5m = data_core.get("current_trend_5m", 0)
    
    signal = "hold"
    weight = 0
    reason = []
    
    # 기본 익절 목표 배수 (take_profit)와 손절 목표 배수 (stop_loss)를 설정 (배수 형태)
    take_profit = 1.03  # 103%
    stop_loss = 0.97    # 97%
    
    # 2) 강한 상승 모멘텀 필터: 1시간봉 강한 상승 추세와 단기 조건 강화
    if trend_1h >= 0:
        if rsi < 30 and percent_b < 0.25 and volume_ratio >= 1.1:
            # 추가 모멘텀 조건: 5분봉 추세가 상승이면 weight 증가
            if trend_5m > 0:
                signal = "buy"
                weight += 3
                reason.append("강한 1h 상승 추세, 1분봉 과매도, 낮은 %b, 거래량 증가, 5분 추세 상승")
            else:
                signal = "buy"
                weight += 2
                reason.append("강한 1h 상승 추세, 1분봉 과매도, 낮은 %b, 거래량 증가")
            
            # 동적 손절폭: Bollinger 하단과의 거리를 80% 반영하여 계산 (보수적 손절)
            dynamic_sl = current_price - (current_price - lower_boll) * 0.8
            # stop_loss를 기존 0.97과 비교하여 더 낮은 값을 선택 (즉, 더 넓은 손절폭)
            stop_loss = min(dynamic_sl / current_price, 0.97)
        else:
            signal = "hold"
            reason.append("롱 진입 조건 미충족 (RSI, %b, 거래량 기준 미달)")
    else:
        signal = "hold"
        reason.append("1h 강한 상승 추세 미확인")
    
    # 3) OBV 모멘텀 추가 확인: OBV 기울기가 충분히 양수면 추가 weight 부여
    if signal == "buy":
        if obv_slope_buy > 0.5:
            weight += 1
            reason.append("OBV 모멘텀 매우 강함")
        else:
            reason.append("OBV 모멘텀 보통")
    
    if weight < 0:
        weight = 0

    reason_str = " | ".join(reason)
    return signal, weight, reason_str, stop_loss, take_profit

def signal_maker_5(data_core, future):
    """
    개선된 전략(5분봉 기반)을 바탕으로 한 매매 신호 생성 함수.
    
    주요 지표:
      - 이동평균선: SMA_20, SMA_60, SMA_120
      - 볼린저밴드: lower_boll, upper_boll, percent_b
      - MACD: MACD, MACD_signal (이전 5분봉 값도 사용)
      - ADX: ADX (5분봉 기준, 강한 추세는 ADX > 25)
      - ATR: ATR (위험관리용)
    
    매수(상승) 신호 조건:
      1. 상승 추세: SMA_20 > SMA_60 > SMA_120  + ADX > 25
      2. 가격가 볼린저밴드 하단 근접 (현재가와 lower_boll 차이가 1% 이내)
      3. MACD 골든크로스: 이전 5분봉에서 MACD < MACD_signal, 최신 5분봉에서 MACD > MACD_signal
      → 조건 2개 이상 충족 시 매수 신호 발생.
      손절: (진입가 - 3×ATR) / 진입가, 익절: (진입가 + 4×ATR) / 진입가
      
    매도(하락) 신호 조건:
      1. 하락 추세: SMA_20 < SMA_60 < SMA_120  + ADX > 25
      2. 가격이 볼린저밴드 상단 근접 (현재가와 upper_boll 차이가 1% 이내)
      3. MACD 데드크로스: 이전 5분봉에서 MACD > MACD_signal, 최신 5분봉에서 MACD < MACD_signal
      → 조건 2개 이상 충족 시 매도 신호 발생.
      손절: (진입가 + 3×ATR) / 진입가, 익절: (진입가 - 4×ATR) / 진입가
      
    future가 True인 경우, 신호 문자열은 선물용("L_buy", "S_sell")으로 반환합니다.
    
    반환:
      signal: "buy", "sell", "hold" (또는 선물의 경우 "L_buy", "S_sell")
      weight: 충족된 조건 수 (최대 4)
      reason: 신호 발생 근거 설명 문자열
      stop_loss: 손절 배수 (예: 0.98은 진입가 대비 98%)
      take_profit: 익절 배수 (예: 1.03은 진입가 대비 103%)
    """
    # 1) 기본 변수 설정 (5분봉 최신 데이터 기준)
    current_price = data_core["last_5m"]["Close"]
    SMA_20 = data_core["last_5m"].get("SMA_20")
    SMA_60 = data_core["last_5m"].get("SMA_60")
    SMA_120 = data_core["last_5m"].get("SMA_120")
    lower_boll = data_core["last_5m"].get("lower_boll")
    upper_boll = data_core["last_5m"].get("upper_boll")
    ADX = data_core["last_5m"].get("ADX", 0)
    ATR = data_core["last_5m"].get("ATR", 0)
    MACD = data_core["last_5m"].get("MACD", 0)
    MACD_signal = data_core["last_5m"].get("MACD_signal", 0)
    
    # 이전 5분봉의 MACD 값 (있을 경우)
    prev_data = data_core.get("previous_5m", {})
    prev_MACD = prev_data.get("MACD", 0)
    prev_MACD_signal = prev_data.get("MACD_signal", 0)
    
    # 2) 조건 체크 변수 초기화
    buy_conditions = 0
    sell_conditions = 0
    reasons_buy = []
    reasons_sell = []
    
    # 추세 조건
    uptrend = (SMA_20 is not None and SMA_60 is not None and SMA_120 is not None and (SMA_20 > SMA_60 > SMA_120))
    downtrend = (SMA_20 is not None and SMA_60 is not None and SMA_120 is not None and (SMA_20 < SMA_60 < SMA_120))
    
    if uptrend and ADX > 25:
        buy_conditions += 2
        reasons_buy.append("상승 추세 확인 (SMA_20 > SMA_60 > SMA_120) 및 ADX > 25")
    else:
        reasons_buy.append("상승 추세 조건 미충족")
    
    if downtrend and ADX > 25:
        sell_conditions += 2
        reasons_sell.append("하락 추세 확인 (SMA_20 < SMA_60 < SMA_120) 및 ADX > 25")
    else:
        reasons_sell.append("하락 추세 조건 미충족")
    
    # 볼린저밴드 조건: 매수는 가격가 하단 근접, 매도는 가격가 상단 근접 (차이가 1% 이내)
    if lower_boll is not None:
        if abs(current_price - lower_boll) / current_price < 0.01:
            buy_conditions += 1
            reasons_buy.append("가격이 볼린저밴드 하단 근접")
        else:
            reasons_buy.append("볼린저밴드 하단 미접근")
    else:
        reasons_buy.append("볼린저밴드 하단 데이터 없음")
    
    if upper_boll is not None:
        if abs(upper_boll - current_price) / current_price < 0.01:
            sell_conditions += 1
            reasons_sell.append("가격이 볼린저밴드 상단 근접")
        else:
            reasons_sell.append("볼린저밴드 상단 미접근")
    else:
        reasons_sell.append("볼린저밴드 상단 데이터 없음")
    
    # MACD 조건: 매수는 골든크로스, 매도는 데드크로스
    if prev_MACD < prev_MACD_signal and MACD > MACD_signal:
        buy_conditions += 1
        reasons_buy.append("MACD 골든크로스 발생")
    else:
        reasons_buy.append("MACD 골든크로스 미발생")
    
    if prev_MACD > prev_MACD_signal and MACD < MACD_signal:
        sell_conditions += 1
        reasons_sell.append("MACD 데드크로스 발생")
    else:
        reasons_sell.append("MACD 데드크로스 미발생")
    
    # 3) 매수 신호 판단 (최소 2개 조건 이상 충족)
    if buy_conditions >= 3:
        signal = "buy" if not future else "L_buy"
        weight = min(buy_conditions, 4)
        # ATR 기반 손절/익절 계산: 완화된 조건 적용 (예: 3×ATR, 4×ATR)
        if ATR > 0:
            stop_loss = (current_price - 3 * ATR) / current_price  # 매수 시 손절: 진입가 대비 3×ATR 하락
            take_profit = (current_price + 4 * ATR) / current_price  # 매수 시 익절: 진입가 대비 4×ATR 상승
        else:
            stop_loss = 0.97
            take_profit = 1.04
        reasons_buy.append(f"매수 실행: 조건 {buy_conditions}개 충족, SL: {stop_loss:.3f}, TP: {take_profit:.3f}")
        return signal, weight, " | ".join(reasons_buy), stop_loss, take_profit

    # 4) 매도 신호 판단 (최소 2개 조건 이상 충족)
    if sell_conditions >= 3:
        signal = "sell" if not future else "S_sell"
        weight = min(sell_conditions, 4)
        if ATR > 0:
            stop_loss = (current_price + 3 * ATR) / current_price  # 매도 시 손절: 진입가 대비 3×ATR 상승
            take_profit = (current_price - 4 * ATR) / current_price  # 매도 시 익절: 진입가 대비 4×ATR 하락
        else:
            stop_loss = 1.03
            take_profit = 0.96
        reasons_sell.append(f"매도 실행: 조건 {sell_conditions}개 충족, SL: {stop_loss:.3f}, TP: {take_profit:.3f}")
        return signal, weight, " | ".join(reasons_sell), stop_loss, take_profit

    # 5) 조건 미충족 시 Hold 반환
    overall_reason = "매수 조건: " + " | ".join(reasons_buy) + " || 매도 조건: " + " | ".join(reasons_sell)
    return "hold", 0, overall_reason, 0.5, 2.0
