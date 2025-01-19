def get_trend_info(df):
    """
    df: trend 칼럼이 있는 데이터프레임 (예: 5분봉, 1시간봉 등)
    반환:
      current_trend: 가장 최근 봉의 추세
      previous_trend: 해당 추세로 바뀌기 직전 봉의 추세
      bars_since_change: 추세 변환 후 몇 개의 봉이 지났는지
    """
    current_trend = df["trend"].iloc[-1]
    i = len(df) - 2

    # 마지막에서부터 거슬러 올라가며 현재 추세와 달라진 지점 탐색
    while i >= 0 and df["trend"].iloc[i] == current_trend:
        i -= 1

    # 전체가 같은 추세였으면 previous_trend는 None 처리
    if i < 0:
        previous_trend = None
        bars_since_change = len(df) - 1
    else:
        previous_trend = df["trend"].iloc[i]
        bars_since_change = (len(df) - 1) - i

    return current_trend, previous_trend, bars_since_change