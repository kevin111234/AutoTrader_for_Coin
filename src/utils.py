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
    # 추세 정보
    trend_1m,         # 1분봉 추세
    trend_1h,         # 1시간봉 추세 (참고용)
    
    # 가격 정보
    current_price,    # 현재가
    sma20_5m,        # 5분봉 20이평
    
    # 1분봉 지표
    rsi_1m,          # 1분봉 RSI
    obv_1m,          # 1분봉 현재 OBV
    obv_1m_prev,     # 1분봉 이전 OBV
    
    # 5분봉 지표
    rsi_5m,          # 5분봉 RSI
    percent_b,       # 5분봉 %B
    volume_ratio,    # 거래량 비율 (현재/이전5봉평균)
    buy_volume_ratio # 매수 거래량 비율
):
    """
    추세 1번 상태(급격한 상승 + 높은 변동성)의 매매 시그널
    """
    action = "hold"
    weight = 0
    reason = []

    # 1. 전량 매도 조건 (가중치 5) 체크
    if trend_1m <= -2:
        action = "sell"
        weight = 5
        reason.append("1분봉 추세 급락")
    
    elif (rsi_5m >= 75 and rsi_1m >= 80 and 
          percent_b >= 0.95 and 
          obv_1m < obv_1m_prev * 0.95 and
          (1 - buy_volume_ratio) >= 0.65):  # sell_volume_ratio
        action = "sell"
        weight = 5
        reason.append("과매수+매도세 강화")
    
    elif (current_price < sma20_5m and volume_ratio > 2):
        action = "sell"
        weight = 5
        reason.append("SMA20 하향돌파+거래량급증")

    # 2. 부분 매도 조건 (가중치 3) 체크
    elif trend_1m <= 0:
        if rsi_1m >= 75 and rsi_5m >= 70:
            action = "sell"
            weight = 3
            reason.append("상승세둔화+과매수진입")
    
    elif (percent_b >= 0.85 and
          current_price > sma20_5m * 1.02 and
          volume_ratio < 0.7):
        action = "sell"
        weight = 3
        reason.append("과매수경계+거래량감소")

    # 3. 소규모 매도 조건 (가중치 2) 체크
    elif (rsi_5m >= 65 and rsi_1m >= 70 and
          percent_b >= 0.8):
        action = "sell"
        weight = 2
        reason.append("초기과매수")
    
    elif (volume_ratio < 0.8 and
          buy_volume_ratio < 0.5):
        action = "sell"
        weight = 2
        reason.append("매수세약화")

    # 4. 매수 조건 체크 (매도 시그널 없을 경우에만)
    elif action == "hold":
        # 4-1. 안전 매수 조건 (가중치 5)
        if (10 > trend_1h >= 2 and  # 상위 추세 강함
            abs(current_price/sma20_5m - 1) <= 0.01 and  # SMA20 1% 이내
            35 <= rsi_5m <= 45 and
            0.3 <= percent_b <= 0.5 and
            obv_1m > obv_1m_prev and
            volume_ratio >= 1.5 and
            buy_volume_ratio >= 0.6):
            action = "buy"
            weight = 5
            reason.append("안전매수조건충족")

        # 4-2. 일반 매수 조건 (가중치 3)
        elif (10 > trend_1h > 0 and  # 상위 추세 긍정
              abs(current_price/sma20_5m - 1) <= 0.015 and  # SMA20 1.5% 이내
              40 <= rsi_5m <= 50 and
              0.4 <= percent_b <= 0.6 and
              obv_1m > obv_1m_prev and
              volume_ratio >= 1.2):
            action = "buy"
            weight = 3
            reason.append("일반매수조건충족")

        # 4-3. 매수 제한 조건 체크
        if action == "buy":
            if (rsi_5m >= 60 or rsi_1m >= 70 or
                percent_b >= 0.8 or
                current_price > sma20_5m * 1.015):
                action = "hold"
                weight = 0
                reason = ["매수제한조건해당"]

    # 5. 매도 제한 조건 체크 (매도 시그널 있을 경우)
    if action == "sell":
        if (trend_1m >= 2 and
            volume_ratio > 2 and
            buy_volume_ratio > 0.7):
            action = "hold"
            weight = 0
            reason = ["매도제한:강한상승지속"]
        
        elif (current_price >= sma20_5m and
              rsi_5m < 65):
            action = "hold"
            weight = 0
            reason = ["매도제한:지지선안정"]

    return action, weight, " + ".join(reason)

def trend2_signal(
    # 추세 정보
    trend_1m,         # 1분봉 추세
    
    # 가격 정보
    current_price,    # 현재가
    sma20_5m,        # 5분봉 20이평
    
    # 1분봉 지표
    rsi_1m,          # 1분봉 현재 RSI
    prev_rsi_1m,     # 1분봉 이전 RSI
    obv_1m,          # 1분봉 현재 OBV
    obv_1m_prev,     # 1분봉 이전 OBV
    
    # 5분봉 지표
    rsi_5m,          # 5분봉 현재 RSI
    prev_rsi_5m,     # 5분봉 이전 RSI
    percent_b,       # 5분봉 %B
    volume_ratio,    # 거래량 비율 (현재/이전5봉평균)
    buy_volume_ratio # 매수 거래량 비율
):
    """
    추세 2번 상태(안정적 상승 + 정상 변동성)의 매매 시그널
    """
    action = "hold"
    weight = 0
    reason = []

    # 1. 전량 매도 조건 (가중치 5) 체크
    if (
        # 1-1. 과매수 구간에서 하락 전환
        (prev_rsi_5m >= 75 and          # 이전 5분봉 과매수
          rsi_5m <= 75 and              # 현재 과매수 해소 진입
          trend_1m < 0) or              # 하락 전환
        
        # 1-2. 핵심 지지선 붕괴
        (current_price < sma20_5m and     # 20이평 하향 돌파
          volume_ratio >= 1.8 and         # 거래량 급증
          buy_volume_ratio <= 0.4)        # 매도세 우위
    ):
        action = "sell"
        weight = 5
        reason.append("전량매도: 과매수해소전환/지지선붕괴")

    # 2. 부분 매도 조건 (가중치 3) 체크
    elif (
        # 2-1. 과매수 초기 해소
        (prev_rsi_5m >= 70 and          # 이전 5분봉 과매수
          rsi_5m <= 70 and              # 현재 과매수 해소 진입
          trend_1m < 0) or              # 하락 전환
        
        # 2-2. 이격도 과다 상태의 하락 전환
        (current_price > sma20_5m * 1.02 and  # 이격도 2% 이상
          trend_1m < 0 and                    # 하락 전환
          volume_ratio < 0.8)                 # 거래량 감소
    ):
        action = "sell"
        weight = 3
        reason.append("부분매도: 과매수해소/이격도과다")

    # 3. 매수 조건 체크 (매도 신호 없을 경우)
    elif action == "hold":
        # 3-1. 적극 매수 조건 (가중치 5)
        if (
            0.995 <= current_price/sma20_5m <= 1.005 and  # 20이평 지지 확인
            40 <= rsi_5m <= 50 and                        # 적정 조정 확인
            0.35 <= percent_b <= 0.5 and                  # 밴드 중하단 지지
            volume_ratio >= 1.5 and                       # 거래량 증가
            buy_volume_ratio >= 0.6 and                   # 매수 우위
            obv_1m > obv_1m_prev                         # OBV 상승
        ):
            action = "buy"
            weight = 5
            reason.append("적극매수: 이평지지+적정조정+매수우위")

        # 3-2. 일반 매수 조건 (가중치 3)
        elif (
            0.99 <= current_price/sma20_5m <= 1.01 and   # 20이평 근접
            45 <= rsi_5m <= 55 and                       # 중립 구간
            0.4 <= percent_b <= 0.6 and                  # 밴드 중단
            volume_ratio >= 1.2 and                      # 적정 거래량
            buy_volume_ratio >= 0.55                     # 매수 우위
        ):
            action = "buy"
            weight = 3
            reason.append("일반매수: 이평근접+중립RSI")

        # 3-3. 매수 제한 조건 체크
        if action == "buy":
            if (
                rsi_5m >= 65 or                          # 5분봉 과매수
                rsi_1m >= 70 or                          # 1분봉 과매수
                percent_b >= 0.8 or                      # 밴드 상단 접근
                trend_1m <= -2 or                        # 단기 급락
                current_price > sma20_5m * 1.015 or      # 이격도 과다
                volume_ratio < 0.8 or                    # 거래량 미달
                buy_volume_ratio < 0.4                   # 매수세 약화
            ):
                action = "hold"
                weight = 0
                reason = ["매수제한조건해당"]

    # 4. 매도 제한 조건 체크 (매도 신호 있을 경우)
    if action == "sell":
        if (
            trend_1m >= 2 and               # 단기 강한 상승
            volume_ratio >= 2 and           # 거래량 급증
            buy_volume_ratio >= 0.65        # 매수세 우위
        ):
            action = "hold"
            weight = 0
            reason = ["매도제한:강한상승지속"]

    return action, weight, " + ".join(reason)
