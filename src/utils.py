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

def trend1_signal(data_core):
    """
    추세 코드 1
    SMA20 > SMA60 > SMA120
    RBW > 1.1
    변동성이 높고 전형적인 상승 추세 정렬 -> 보수적 매수, 적극적 매도도
    과매수를 주의하고, 단기적 조정에 의한 급상승이 아닌지 꼭 확인해야 함.
    rsi가 70 이상이거나, obv 기울기가 음수이거나, %b가 0.4 이하이면 매도
    rsi가 70 이하, obv 기울기가 양수이면 매수, but 1시간봉 추세가 음수이거나 "buy_volume_ratio"가 0.5 이하이면 매수금지
    """
    print(1)

def trend2_signal(data_core):
    """
    추세 코드 2
    SMA20 > SMA60 > SMA120
    0.8 < RBW < 1.1
    안정적인 상승추세 -> 이전 추세 확인!
    """
    print(2)

def trend3_signal(data_core):
    """
    추세 코드 3
    SMA20 > SMA60 > SMA120
    RBW < 0.8
    상승 이후 조정 국면 -> 이전 추세 확인 필수!
    """
    print(3)

# --------------------------

def trend4_signal(data_core):
    """
    추세 코드 4
    SMA20 > SMA120 > SMA60
    RBW < 1.1
    """
    print(4)

def trend5_signal(data_core):
    """
    추세 코드 5
    SMA20 > SMA120 > SMA60
    0.8 < RBW < 1.1
    """
    print(5)

def trend6_signal(data_core):
    """
    추세 코드 6
    SMA20 > SMA120 > SMA60
    RBW < 0.8
    """
    print(6)

# -------------------------

def trend7_signal(data_core):
    """
    추세 코드 7
    SMA60 > SMA20 > SMA120
    RBW < 1.1
    """
    print(7)

def trend8_signal(data_core):
    """
    추세 코드 8
    SMA60 > SMA20 > SMA120
    0.8 < RBW < 1.1
    """
    print(8)

def trend9_signal(data_core):
    """
    추세 코드 9
    SMA60 > SMA20 > SMA120
    RBW < 0.8
    """
    print(9)

#-------------------------

def trend_1_signal(data_core):
    """
    추세 코드 -1
    SMA60 > SMA120 > SMA20
    RBW < 1.1
    """
    print(-1)

def trend_2_signal(data_core):
    """
    추세 코드 -2
    SMA60 > SMA120 > SMA20
    0.8 < RBW < 1.1
    """
    print(-2)

def trend_3_signal(data_core):
    """
    추세 코드 -3
    SMA60 > SMA120 > SMA20
    RBW < 0.8
    """
    print(-3)

# -----------------------

def trend_4_signal(data_core):
    """
    추세 코드 -4
    SMA120 > SMA20 > SMA60
    RBW < 1.1
    """
    print(-4)

def trend_5_signal(data_core):
    """
    추세 코드 -5
    SMA120 > SMA20 > SMA60
    0.8 < RBW < 1.1
    """
    print(-5)

def trend_6_signal(data_core):
    """
    추세 코드 -6
    SMA120 > SMA20 > SMA60
    RBW < 0.8
    """
    print(-6)

# -----------------------4
def trend_7_signal(data_core):
    """
    추세 코드 -7
    SMA120 > SMA60 > SMA20
    RBW < 1.1
    """
    print(-7)

def trend_8_signal(data_core):
    """
    추세 코드 -7
    SMA120 > SMA60 > SMA20
    0.8 < RBW < 1.1
    """
    print(-8)

def trend_9_signal(data_core):
    """
    추세 코드 -7
    SMA120 > SMA60 > SMA20
    RBW < 0.8
    """
    print(-9)