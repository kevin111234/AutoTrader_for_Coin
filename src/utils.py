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

def MACD_signal(data_dict, future, account_info):
    global profit_sell

    entry_price = account_info.get("entry_price", 0)
    holdings = account_info.get("holdings", 0)

    if holdings == 0:
        profit_sell = False

    # 5분봉 데이터 사용
    df = data_dict['5m']

    # 최신 종가 (문자열일 경우 float 변환)
    current_price = float(df['Close'].iloc[-1])
    current_trend = int(df["trend"].iloc[-1])

    if entry_price is None or entry_price == 0:
        profit_rate = 0
    else:
        profit_rate = ((current_price - entry_price) / entry_price) * 100

    # 이동평균선 값 (마지막 행)
    sma20 = float(df['SMA_20'].iloc[-1])
    sma60 = float(df['SMA_60'].iloc[-1])
    sma120 = float(df['SMA_120'].iloc[-1])
    
    # 상승추세, 하락추세 판단
    ma_up = (sma20 > sma60) and (sma60 > sma120)
    ma_down = (sma120 > sma60) and (sma60 > sma20)

    if current_trend == 0:
        ma_up = False
        ma_down = False
    
    # 최신 MACD, MACD_signal 값
    macd_curr = float(df['MACD'].iloc[-1])
    macd_signal_curr = float(df['MACD_signal'].iloc[-1])

    # 최신 RSI, 직전 RSI 값
    rsi_curr = df['rsi'].iloc[-1]
    rsi_prev = df['rsi'].iloc[-2]

    # 기본 손절/익절 설정
    stop_loss = 0.97
    take_profit = 1.1

    # 최근 5봉(최신 봉 제외) 값 확보
    if len(df) >= 6:
        prev_macd_range = df['MACD'].iloc[-6:-1].astype(float)
        prev_macd_signal_range = df['MACD_signal'].iloc[-6:-1].astype(float)
    else:
        prev_macd_range = df['MACD'].iloc[-2:-1].astype(float)
        prev_macd_signal_range = df['MACD_signal'].iloc[-2:-1].astype(float)

    signal = ""
    reason = ""
    weight = 0

    # 상승추세: 롱 포지션 관련 신호
    if ma_up:
        # 롱 진입 조건 (매수)
        buy_weight = 1  # 기본 +1
        reason_buy = "상승추세: 기본 +1"
        if macd_curr > 0:
            buy_weight += 2
            reason_buy += ", MACD 양수 +2"
        if prev_macd_range.min() < 0 and macd_curr > 0:
            buy_weight += 2
            reason_buy += ", MACD 상향돌파 +2"
        # 롱 청산 조건 (매도)
        sell_weight = 0
        reason_sell = ""
        if macd_curr < 0:
            sell_weight = 5
            reason_sell += "MACD 음수 +5"

        # 신호 결정 (threshold: 조건 만족 시)
        if buy_weight >= 3 or sell_weight >= 2:
            if buy_weight >= sell_weight and (not profit_sell or buy_weight >= 4):
                weight = buy_weight
                signal = "L_buy" if future else "buy"
                reason = reason_buy
            else:
                weight = sell_weight
                signal = "L_sell" if future else "sell"
                reason = reason_sell
        else:
            weight = 0
            signal = "hold"
            reason = "신호 조건 미충족"

    # 하락추세: 숏 포지션 관련 신호
    elif ma_down:
        # 숏 진입 조건 (매도)
        sell_weight = 1  # 기본 +1
        reason_sell = "하락추세: 기본 +1"
        if macd_curr < 0:
            sell_weight += 2
            reason_sell += ", MACD 음수 +2"
        if prev_macd_range.max() > 0 and macd_curr < 0:
            sell_weight += 2
            reason_sell += ", MACD 하향돌파 +2"
        
        # 숏 청산 조건 (매수)
        buy_weight = 0
        reason_buy = ""
        if macd_curr > 0:
            buy_weight = 5
            reason_buy += "MACD 양수 +5"

        # 신호 결정 (threshold: 조건 만족 시)
        if sell_weight >= 3 or buy_weight >= 2:
            if sell_weight >= buy_weight and (not profit_sell or sell_weight >= 4):
                weight = sell_weight
                signal = "S_buy" if future else "sell"  # 숏 진입은 현물에서는 sell, 선물에서는 S_buy
                reason = reason_sell
            else:
                weight = buy_weight
                signal = "S_sell" if future else "buy"  # 숏 청산은 현물에서는 buy, 선물에서는 S_sell
                reason = reason_buy
        else:
            weight = 0
            signal = "hold"
            reason = "신호 조건 미충족"
    else:
        weight = 0
        signal = "close" if future else "hold"
        reason = "이동평균선 배치가 명확하지 않음"

    # 매수 후 처음 수익률 0.5% 돌파 시 profit_sell 조건 적용 (단, 아직 sell 신호가 발생하지 않은 경우)
    if profit_rate > 0.5 and not profit_sell:
        signal = "sell"
        weight = 2
        reason = "수익률 0.5% 돌파"
        profit_sell = True

    # 추가 RSI 조건 (예시)
    if rsi_curr > 70 and profit_rate > 1.0:
        signal = "sell"
        weight = 3
        reason = "RSI 70 돌파"
        if rsi_curr > 80:
            weight += 2
            reason = "RSI 80 돌파"

    return current_price, signal, weight, reason, stop_loss, take_profit
