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
    while i >= 0 and df["trend"].iloc[i] == current_trend:
        i -= 1

    if i < 0:
        # 데이터 전체가 같은 추세였을 경우
        previous_trend = None
        bars_since_change = len(df) - 1
        trend_t_minus_2 = None
        bars_since_t_minus_1 = None
    else:
        # 이전 추세(T-1) 및 현재 추세로 바뀐 후 지난 봉 수
        previous_trend = df["trend"].iloc[i]
        bars_since_change = (len(df) - 1) - i

        # ---------------------------
        # 2) 더 과거 추세(T-2) 찾기
        # ---------------------------
        # j를 i-1부터 거슬러 올라가, previous_trend와 다른 값이 나오는 순간이 T-2
        j = i - 1
        while j >= 0 and df["trend"].iloc[j] == previous_trend:
            j -= 1

        if j < 0:
            # T-1 추세로만 데이터가 쭉 이어졌던 경우 (T-2가 없음)
            trend_t_minus_2 = None
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

def get_symbol_info(self, symbol):
    """
    심볼의 거래 제한 정보를 반환 (stepSize, minQty 포함)
    """
    try:
        exchange_info = self.client.get_exchange_info()
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

def trend_signal(data_core):
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

    return signal, weight, reason, stop_loss, take_profit