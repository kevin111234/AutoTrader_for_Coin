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

def trend1_signal(trend_1m,
                  trend_1h,
                  current_price,
                  sma20_5m,
                  rsi_1m,
                  prev_rsi_1m,
                  obv_1m,
                  obv_1m_prev,
                  rsi_5m,
                  prev_rsi_5m,
                  percent_b,
                  volume_ratio,
                  buy_volume_ratio,
                  bars_since_5m,
                  bars_since_1h):
    """
    5분봉 코드=1 (급격 상승, RBW>1.1)에서의 매수/매도 시그널 예시.

    매개변수:
      - trend_1m: 1분봉 추세 코드 (참고용)
      - trend_1h: 1시간봉 추세 코드 (상위 추세 판단)
      - current_price: 현재 5분봉 종가
      - sma20_5m: 5분봉 SMA_20 (참고)
      - rsi_1m, prev_rsi_1m: 1분봉 RSI(현재/직전)
      - obv_1m, obv_1m_prev: 1분봉 OBV(현재/직전)
      - rsi_5m, prev_rsi_5m: 5분봉 RSI(현재/직전)
      - percent_b: 볼린저 %b (0~1 범위, 1 이상이면 상단 돌파)
      - volume_ratio: 현재 5분봉 거래량 / 이전 5봉 평균 거래량
      - buy_volume_ratio: 5분봉 매수 거래량 비율 (taker buy / total volume)
      - bars_since_5m: 5분봉 추세가 코드1로 전환된 뒤 경과 봉 수
      - bars_since_1h: 1시간봉 추세 전환 후 경과 봉 수 (참고)

    반환:
      signal: "buy", "sell", "hold" 중 하나
      weight: 1~5 (포지션 비중)
      reason: 간단한 설명
    """

    signal = "hold"
    weight = 0
    reason = ""

    # --------------------------------------------------------------------------------
    # 1) 우선 과매수 / 급등락 확인 → 매도 조건(익절 or 위험 회피) 우선 체크 예시
    # --------------------------------------------------------------------------------
    if rsi_5m >= 80:
        signal = "sell"
        weight = 5  # 부분 익절 (강제)
        reason = "5분봉 RSI>=80 과매수 구간 - 부분 청산"
        return signal, weight, reason
    elif obv_1m < obv_1m_prev * 0.95:
        # OBV가 직전 대비 5% 이상 급감 -> 매수세 이탈 신호
        signal = "sell"
        weight = 3
        reason = "1분봉 OBV 급감 - 단기 매수세 이탈"
        return signal, weight, reason

    # --------------------------------------------------------------------------------
    # 2) 매수 접근 로직
    #    (A) 상위 타임프레임(1시간봉) 추세가 양수/중립일 때 vs 음수일 때
    #    (B) bars_since_5m (막 전환 초입 여부)
    #    (C) 1분봉 RSI/OBV 등 추가 확인
    # --------------------------------------------------------------------------------

    # (A) 1시간봉 추세에 따라 기본 베이스 가중치 설정
    if trend_1h >= 0:
        # 상위도 상승/중립 => 공격적 접근 가능
        base_weight = 3
        base_reason = "1시간봉 상승/중립"
    else:
        # 상위가 하락 => 단기 반등 가능성은 있으나 보수적 접근
        base_weight = 1
        base_reason = "1시간봉 하락, 단기 반등 가정"

    # (B) 5분봉 추세 막 전환 여부
    if bars_since_5m <= 2:
        # 막 전환이면 추세 초입으로 볼 수 있음 => 가중치 플러스
        base_weight += 1
        base_reason += " + 5분봉 추세 전환 초입"

    # (C) 1분봉 RSI/OBV 확인 (추가 플러스/마이너스)
    if rsi_1m < 70 and obv_1m > obv_1m_prev:
        # 과매수 아님 + OBV 상승 => 매수 가중치 추가
        base_weight += 1
        base_reason += " + 1분봉 RSI<70 & OBV 상승"
    else:
        # rsi_1m>=70이면 이미 단기 과열이거나 OBV가 줄어든 상태 => 가중치 억제
        base_reason += " (1분봉 과열 or OBV 약화)"

    # volume_ratio나 buy_volume_ratio를 활용해서 매수세가 특별히 강한지 추가 판단 가능
    if volume_ratio > 2 and buy_volume_ratio > 0.6:
        # 거래량 폭발 + 매수 비중 높음 => 추세 신뢰도 상승
        base_weight += 1
        base_reason += f" + 거래량폭발({volume_ratio:.2f}), 매수비율({buy_volume_ratio:.2f})"

    # --------------------------------------------------------------------------------
    # 3) 최종 매수 시그널 결정
    # --------------------------------------------------------------------------------
    # 과도하게 커지지 않도록 클램프
    final_weight = min(max(base_weight, 0), 5)

    if final_weight <= 0:
        signal = "hold"
        weight = 0
        reason = "매수 근거 미약 or 음수"
    else:
        signal = "buy"
        weight = final_weight
        reason = f"{base_reason}, weight={final_weight}"

    return signal, weight, reason


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

def trend3_signal(
    # 추세 정보
    trend_1m,         # 1분봉 추세
    
    # 가격 정보
    current_price,    # 현재가
    sma20_5m,        # 5분봉 20이평
    
    # 5분봉 지표
    rsi_5m,          # 5분봉 현재 RSI
    prev_rsi_5m,     # 5분봉 이전 RSI
    percent_b,       # 5분봉 %B
    
    # 거래량 지표
    volume_ratio,    # 거래량 비율 (현재/이전5봉평균)
    buy_volume_ratio,# 매수 거래량 비율
    obv_1m,          # 1분봉 현재 OBV
    obv_1m_prev      # 1분봉 이전 OBV
):
    """
    추세 3번 상태(상승 추세 내 조정 + 낮은 변동성)의 매매 시그널
    """
    action = "hold"
    weight = 0
    reason = []

    # 1. 전량 매도 조건 (가중치 5) 체크
    if (
        # 1-1. 과매수 해소 + 하락 전환
        (prev_rsi_5m >= 70 and          # 이전 5분봉 과매수
        rsi_5m < 70 and                # 과매수 해소 진입
        trend_1m < 0) or               # 하락 전환
        
        # 1-2. 핵심 지지선 붕괴
        (current_price < sma20_5m and    # 20이평 하향 돌파
        volume_ratio >= 2.0 and         # 거래량 급증
        buy_volume_ratio <= 0.4 and     # 매도세 우위
        obv_1m < obv_1m_prev * 0.97)    # OBV 3% 이상 감소
    ):
        action = "sell"
        weight = 5
        reason.append("전량매도: 과매수해소/지지선붕괴")

    # 2. 부분 매도 조건 (가중치 3) 체크
    elif (
        current_price > sma20_5m * 1.015 and  # 이격도 1.5% 이상
        trend_1m < 0 and                      # 하락 전환
        volume_ratio < 0.8 and                # 거래량 감소
        buy_volume_ratio < 0.45               # 매수세 약화
    ):
        action = "sell"
        weight = 3
        reason.append("부분매도: 이격도과다+하락전환")

    # 3. 매수 조건 체크 (매도 신호 없을 경우)
    elif action == "hold":
        # 3-1. 적극 매수 조건 (가중치 5)
        if (
            # 가격이 20이평 지지 확인
            0.995 <= current_price/sma20_5m <= 1.005 and
            
            # 과매도 후 반등 시도
            30 <= rsi_5m <= 40 and          # 과매도 벗어나는 구간
            prev_rsi_5m < rsi_5m and        # RSI 상승 전환
            0.2 <= percent_b <= 0.3 and     # 밴드 하단 지지
            
            # 매수세 유입 확인
            volume_ratio >= 2.0 and         # 거래량 급증
            buy_volume_ratio >= 0.65 and    # 강한 매수세
            obv_1m > obv_1m_prev * 1.02     # OBV 2% 이상 증가
        ):
            action = "buy"
            weight = 5
            reason.append("적극매수: 이평지지+과매도반등+매수세강화")

        # 3-2. 일반 매수 조건 (가중치 3)
        elif (
            # 20이평 지지 근처
            0.99 <= current_price/sma20_5m <= 1.01 and
            
            # 적정 조정 구간
            35 <= rsi_5m <= 45 and          # 적정 조정
            prev_rsi_5m < rsi_5m and        # RSI 상승 전환
            0.3 <= percent_b <= 0.4 and     # 밴드 하단 벗어남
            
            # 거래량 조건
            volume_ratio >= 1.5 and         # 거래량 증가
            buy_volume_ratio >= 0.6 and     # 매수세 우위
            obv_1m > obv_1m_prev            # OBV 증가
        ):
            action = "buy"
            weight = 3
            reason.append("일반매수: 이평근접+적정조정+거래량증가")

        # 3-3. 매수 제한 조건 체크
        if action == "buy":
            if (
                trend_1m <= -2 or              # 단기 급락
                rsi_5m < 30 or                 # 과매도 지속
                percent_b < 0.2 or             # 밴드 하단 이탈
                volume_ratio < 1.2 or          # 거래량 부족
                buy_volume_ratio < 0.5 or      # 매수세 약화
                obv_1m < obv_1m_prev * 0.98    # OBV 감소
            ):
                action = "hold"
                weight = 0
                reason = ["매수제한조건해당"]

    # 4. 매도 제한 조건 체크 (매도 신호 있을 경우)
    if action == "sell":
        if (
            trend_1m >= 2 and               # 단기 강한 상승
            volume_ratio >= 2.0 and         # 거래량 급증
            buy_volume_ratio >= 0.65 and    # 강한 매수세
            obv_1m > obv_1m_prev * 1.02     # OBV 2% 이상 증가
        ):
            action = "hold"
            weight = 0
            reason = ["매도제한:강한상승지속"]

    return action, weight, " + ".join(reason)
