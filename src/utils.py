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

def trend1_signal(
    trend_1h,
    # --- 1분봉 지표 ---
    rsi_1m,
    obv_1m,
    obv_1m_prev,
    # --- 5분봉 지표 ---
    rsi_5m,
    obv_5m,
    obv_5m_prev,
    # --- 파라미터 ---
    rsi_overbought_1m=70,  # 1분봉 과매수 기준
    rsi_extreme_1m=80,     # 1분봉 극단 과매수
    rsi_overbought_5m=65,  # 5분봉 과매수 기준(조금 더 낮게 설정 가능)
    obv_drop_ratio=0.9,    # OBV 10% 이상 감소 시 급감 판단
):
    """
    5분봉 추세가 1일 때 매수/매도 결정 + 비중(0~5단계) 예시 함수

    인자:
      trend_1h (int): 1시간봉 추세 점수 (중기 추세 참고)
      rsi_1m (float): 1분봉 RSI
      obv_1m (float): 1분봉 OBV(최근 값)
      obv_1m_prev (float): 1분봉 OBV(직전 또는 n봉 전)
      rsi_5m (float): 5분봉 RSI
      obv_5m (float): 5분봉 OBV(최근 값)
      obv_5m_prev (float): 5분봉 OBV(직전 또는 n봉 전)
      rsi_overbought_1m (float): 1분봉 과매수 기준
      rsi_extreme_1m (float): 1분봉 극단적 과매수 기준
      rsi_overbought_5m (float): 5분봉 과매수 기준
      obv_drop_ratio (float): OBV가 직전 대비 몇 % 이하로 떨어지면 급감으로 볼지 (기본 0.9)

    반환:
      action (str): "buy", "sell", "hold" 중 하나
      weight (int): 0~5 사이의 가중치
      reason (str): 결정 사유
    """

    # 초기값
    action = "hold"
    weight = 0
    reason = ""

    # --------------------------------------------------------------------------
    # 1) 매수 시나리오
    # --------------------------------------------------------------------------
    #  - 1시간봉 추세가 0 이상(중립 이상)
    #  - 1분봉 RSI가 과매수 아님(rsi_overbought_1m 미만)
    #  - 5분봉 RSI도 과매수 아님(rsi_overbought_5m 미만)
    #  - 1분봉, 5분봉 OBV 모두 증가 경향
    # --------------------------------------------------------------------------
    if (trend_1h >= 0
        and rsi_1m < rsi_overbought_1m
        and rsi_5m < rsi_overbought_5m
        and obv_1m > obv_1m_prev
        and obv_5m > obv_5m_prev
        ):
        # RSI가 매우 낮거나, OBV가 크게 증가했다면 강한 매수
        # 예: 1분봉 RSI 50 미만, 5분봉 RSI 50 미만, 등등
        if (rsi_1m < (rsi_overbought_1m - 20)) and (rsi_5m < (rsi_overbought_5m - 15)):
            action = "buy"
            weight = 5
            reason = "5분=1 + 1시간봉>=0 + 1/5분봉 RSI 모두 낮고 OBV↑"
        else:
            action = "buy"
            weight = 3
            reason = "5분=1 + 1시간봉>=0 + 1/5분봉 RSI 과매수 미만 + OBV 증가"

    # --------------------------------------------------------------------------
    # 2) 부분 매도 시나리오 (익절 등)
    # --------------------------------------------------------------------------
    # - 1분봉 RSI가 극단적 과매수 (예: rsi_extreme_1m 이상)
    # - 5분봉 RSI가 과매수 기준 초과
    # - OBV 급감 (ex: OBV가 10% 이상 감소)
    # --------------------------------------------------------------------------
    # (2-1) 극단적 과매수
    if rsi_1m >= rsi_extreme_1m:
        action = "sell"
        weight = 3  # 부분 매도
        reason = "5분=1 유지, 1분봉 RSI 극단적 과매수"

    # (2-2) 5분봉이 과매수 진입(rsi_5m >= rsi_overbought_5m)
    elif rsi_5m >= rsi_overbought_5m:
        action = "sell"
        weight = 2  # 부분 매도
        reason = "5분=1 유지, 5분봉 RSI 과매수"

    # (2-3) OBV 급감
    elif obv_1m < obv_1m_prev * obv_drop_ratio or obv_5m < obv_5m_prev * obv_drop_ratio:
        action = "sell"
        weight = 2
        reason = "5분=1 유지, 1분봉 혹은 5분봉 OBV 급감"

    # --------------------------------------------------------------------------
    # 3) 전량 매도 시나리오
    # --------------------------------------------------------------------------
    # - 1시간봉이 강한 하락(-8 이하)으로 급변
    # --------------------------------------------------------------------------
    if trend_1h <= -8:
        action = "sell"
        weight = 5  # 전량 매도
        reason = "5분=1 vs 1시간봉 -8 이하 전환 → 하락 리스크"

    return action, weight, reason
