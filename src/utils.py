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

def MACD_signal(data_dict, future):
    # 5분봉 데이터 사용
    df = data_dict['5m']

    # 최신 종가 (문자열일 경우 float 변환)
    current_price = float(df['Close'].iloc[-1])

    # 이동평균선 값 (마지막 행)
    sma20 = float(df['SMA_20'].iloc[-1])
    sma60 = float(df['SMA_60'].iloc[-1])
    sma120 = float(df['SMA_120'].iloc[-1])
    
    # 상승추세, 하락추세 판단
    ma_up = (sma20 > sma60) and (sma60 > sma120)
    ma_down = (sma120 > sma60) and (sma60 > sma20)
    
    # 최신 MACD, MACD_signal 값 (최신 봉)
    macd_curr = float(df['MACD'].iloc[-1])
    macd_signal_curr = float(df['MACD_signal'].iloc[-1])
    
    # 기본값 설정
    signal = "hold"
    weight = 0
    reason = "특별한 신호 없음"
    stop_loss = 0.98
    take_profit = 1.03

    # 최근 5봉(최신 봉 제외) 기준 이전값 계산
    if len(df) >= 6:
        prev_macd_range = df['MACD'].iloc[-6:-1].astype(float)
        prev_macd_signal_range = df['MACD_signal'].iloc[-6:-1].astype(float)
    else:
        prev_macd_range = df['MACD'].iloc[-2:-1].astype(float)
        prev_macd_signal_range = df['MACD_signal'].iloc[-2:-1].astype(float)
    
    if future:
        if ma_up:
            signal = "L_buy"
            weight = 3
            reason = "상승추세 확인 (롱 진입)"
            # 롱 진입: 이전 5봉 중 MACD_signal 최저 < 0, 현재 > 0
            prev_macd_signal = prev_macd_signal_range.min()
            if prev_macd_signal < 0 and macd_signal_curr > 0:
                signal = "L_buy"
                weight = 5
                reason = "상승추세 및 최근 5봉 기준 MACD_signal 최저값이 0미만에서 상향돌파 (롱 진입)"
            # 롱 정리: 이전 5봉 중 MACD 최고 > 0, 현재 < 0
            prev_macd = prev_macd_range.max()
            if prev_macd > 0 and macd_curr < 0:
                signal = "L_sell"
                weight = 5
                reason = "상승추세에서 최근 5봉 기준 MACD 최고값이 0초과에서 하향돌파 (롱 정리)"
        elif ma_down:
            # 숏 진입: 이전 5봉 중 MACD_signal 최고 > 0, 현재 < 0
            prev_macd_signal = prev_macd_signal_range.max()
            if prev_macd_signal > 0 and macd_signal_curr < 0:
                signal = "S_buy"
                weight = 2
                reason = "하락추세 및 최근 5봉 기준 MACD_signal 최고값이 0초과에서 하향돌파 (숏 진입)"
            # 숏 정리: 이전 5봉 중 MACD 최저 < 0, 현재 > 0
            prev_macd = prev_macd_range.min()
            if prev_macd < 0 and macd_curr > 0:
                signal = "S_sell"
                weight = 2
                reason = "하락추세에서 최근 5봉 기준 MACD 최저값이 0미만에서 상향돌파 (숏 정리)"
        else:
            signal = "close"
            weight = 5
            reason = "이동평균선 배치가 명확하지 않음"
    else:
        # 현물 거래: 선물과 유사하게 처리
        if ma_up:
            signal = "buy"
            weight = 3
            prev_macd_signal = prev_macd_signal_range.min()
            if prev_macd_signal < 0 and macd_signal_curr > 0:
                signal = "buy"
                weight = 5
                reason = "상승추세 및 최근 5봉 기준 MACD_signal 최저값이 0미만에서 상향돌파 (매수)"
            prev_macd = prev_macd_range.max()
            if prev_macd > 0 and macd_curr < 0:
                signal = "sell"
                weight = 5
                reason = "상승추세에서 최근 5봉 기준 MACD 최고값이 0초과에서 하향돌파 (매도)"
        else:
            signal = "sell"
            weight = 5
            reason = "상승추세 이탈"
    
    return current_price, signal, weight, reason, stop_loss, take_profit
