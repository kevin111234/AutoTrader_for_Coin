from config import Config

import pandas as pd
import numpy as np
class Data_Control():
    def __init__(self):
        pass
    
    def cal_moving_average(self, df, period=[20, 60, 120]):
        """
        period 리스트에 명시된 기간별 이동평균선을 구해주는 함수.
        이미 계산된 구간은 건너뛰고, NaN인 부분만 업데이트함.
        예: period=[20,60,120] -> ma_20, ma_60, ma_120 열 생성/갱신
        """
        
        # 예외 처리
        if 'Close' not in df.columns or df.empty:
            raise ValueError("DataFrame에 'Close' 열이 없거나 데이터가 없습니다.")
        
        # period 리스트에 있는 각 기간별로 이동평균선 계산
        for p in period:
            col_name = f"SMA_{p}"
            
            # (1) SMA 컬럼 없으면 생성
            if col_name not in df.columns:
                df[col_name] = np.nan
            
            # (2) NaN 부분만 필터링하여 계산
            nan_indices = df[df[col_name].isna()].index
            for i in nan_indices:
                # p일치 안 되면 계산 불가
                if i < p - 1:
                    continue
                
                # 직전 p개 구간 mean
                window_close = df.loc[max(0, i - p + 1) : i, 'Close']
                df.loc[i, col_name] = window_close.mean()
        
        return df
    
    def cal_rsi(self, df, period = 14, signal_period = 14):
    
        # 1) rsi / rsi_signal 컬럼이 없으면 만들어 둠
        if 'rsi' not in df.columns:
            df['rsi'] = np.nan
        if 'rsi_signal' not in df.columns:
            df['rsi_signal'] = np.nan

        # 2) 이미 계산된 구간(last_valid_rsi) 찾아서, 그 다음 행부터 재계산
        last_valid_rsi = df['rsi'].last_valid_index()
        if last_valid_rsi is None:
            last_valid_rsi = -1  # 전부 NaN이면 -1로 설정 -> 0부터 계산

        # 3) for문으로 last_valid_rsi + 1 ~ 끝까지 순회
        for i in range(last_valid_rsi + 1, len(df)):
            # period 미만 구간은 RSI를 정확히 구하기 어려우니 skip
            if i < period:
                continue
            
            # 이미 NaN이 아니면 = 계산돼 있다면 패스
            if pd.isna(df.loc[i, 'rsi']):
                # (a) rolling 방식으로 i번째 행까지 slice하여 RSI 계산
                window_df = df.loc[:i].copy()
                window_df['diff'] = window_df['Close'].diff()
                window_df['gain'] = window_df['diff'].clip(lower=0)
                window_df['loss'] = -window_df['diff'].clip(upper=0)
                window_df['avg_gain'] = window_df['gain'].rolling(period).mean()
                window_df['avg_loss'] = window_df['loss'].rolling(period).mean()
                
                last_avg_gain = window_df['avg_gain'].iloc[-1]
                last_avg_loss = window_df['avg_loss'].iloc[-1]
                
                if pd.isna(last_avg_gain) or pd.isna(last_avg_loss):
                    # rolling 구간이 아직 안 찼다면 NaN 유지
                    continue
                
                if last_avg_loss == 0:
                    # 하락이 전혀 없으면 RSI=100 처리
                    rsi_val = 100.0
                else:
                    rs = last_avg_gain / last_avg_loss
                    rsi_val = 100 - (100 / (1 + rs))
                
                df.loc[i, 'rsi'] = rsi_val
            
            # (b) signal_period가 있다면, i번째 RSI까지 rolling으로 rsi_signal 계산
            if signal_period > 0 and i >= signal_period and not pd.isna(df.loc[i, 'rsi']):
                rsi_signal_val = df.loc[:i, 'rsi'].rolling(signal_period).mean().iloc[-1]
                df.loc[i, 'rsi_signal'] = rsi_signal_val

        return df
    
    def nor_rsi(self, rsi):
        if rsi >= 50:
            rsi = 100 - rsi
        if rsi <= 20:
            return 20
        elif rsi <= 25:
            return 25
        elif rsi <= 30:
            return 30
        elif rsi <= 35:
            return 35
        else:
            return 50
    
    def cal_bollinger_band(self, df, period=20, num_std=2):
        """
        볼린저 밴드, %b 및 Bandwidth를 계산하는 함수
        
        매개변수:
        df : pandas DataFrame - 'Close' 열이 포함된 데이터프레임
        period : int - 볼린저 밴드 이동평균 기간 (기본값 20)
        num_std : int - 표준편차 배수 (기본값 2)
        
        반환:
        df : pandas DataFrame - 수정된 볼린저 밴드, %b 및 밴드폭 포함
        """
        
        # 1) 볼린저 및 %b, 밴드폭 컬럼들이 없으면 만들어 둠
        if 'middle_boll' not in df.columns:
            df['middle_boll'] = np.nan
        if 'upper_boll' not in df.columns:
            df['upper_boll'] = np.nan
        if 'lower_boll' not in df.columns:
            df['lower_boll'] = np.nan
        if 'percent_b' not in df.columns:
            df['percent_b'] = np.nan
        if 'bandwidth' not in df.columns:
            df['bandwidth'] = np.nan

        # 2) 마지막으로 유효한 볼린저밴드 인덱스 확인
        last_valid_boll = df['middle_boll'].last_valid_index()
        if last_valid_boll is None:
            last_valid_boll = -1  # NaN이면 -1로 설정해서 처음부터 계산

        # 3) last_valid_boll + 1부터 끝까지 순회하며 볼린저 밴드 및 추가 지표 계산
        for i in range(last_valid_boll + 1, len(df)):
            # period 미만 구간은 볼린저밴드 계산 불가
            if i < period:
                continue
            
            # 볼린저밴드 값이 이미 존재하면 건너뛰기
            if (pd.notna(df.loc[i, 'middle_boll']) and 
                pd.notna(df.loc[i, 'upper_boll']) and
                pd.notna(df.loc[i, 'lower_boll']) and
                pd.notna(df.loc[i, 'percent_b']) and
                pd.notna(df.loc[i, 'bandwidth'])):
                continue

            # i번째까지 슬라이스하여 롤링 평균 및 표준편차 계산
            window_series = df.loc[:i, 'Close'].rolling(period)
            mean_val = window_series.mean().iloc[-1]
            std_val = window_series.std().iloc[-1]

            # 볼린저밴드 계산
            upper_val = mean_val + num_std * std_val
            lower_val = mean_val - num_std * std_val

            # %b 계산
            current_price = df.loc[i, 'Close']
            percent_b = (current_price - lower_val) / (upper_val - lower_val)

            # 밴드폭(Bandwidth) 계산
            bandwidth = ((upper_val - lower_val) / mean_val) * 100

            # 결과 반영
            df.loc[i, 'middle_boll'] = mean_val
            df.loc[i, 'upper_boll'] = upper_val
            df.loc[i, 'lower_boll'] = lower_val
            df.loc[i, 'percent_b'] = percent_b
            df.loc[i, 'bandwidth'] = bandwidth

        return df

    def cal_tpo_volume_profile(self, data, 
                              price_col='Close', 
                              volume_col='Volume', 
                              taker_buy_col='Taker Buy Base Asset Volume', 
                              taker_sell_col='Taker Sell Base Asset Volume', 
                              bins=20):
        """
        TPO(Time at Price)와 볼륨 프로파일(VP)을 함께 계산하는 함수.
        또한 Taker Buy / Sell 거래량을 구간별로 집계할 수 있습니다.
        
        :param data: 가격, 거래량 및 Taker Buy/Sell 칼럼을 포함한 Pandas DataFrame
        :param price_col: 가격 컬럼명(기본값: 'Close')
        :param volume_col: 전체 거래량 컬럼명(기본값: 'Volume')
        :param taker_buy_col: Taker 매수 거래량 컬럼명(기본값: 'Taker Buy Base Asset Volume')
        :param taker_sell_col: Taker 매도 거래량 컬럼명(기본값: 'Taker Sell Base Asset Volume')
        :param bins: 가격 구간(bin) 수 (기본값: 20)
        :return: 
            profile_df: 각 가격 구간별 VP, TPO, Taker Buy/Sell Volume 정보를 담은 DataFrame
            sr_levels: POC 및 상위 레벨 정보를 담은 dictionary
        """

        prices = data[price_col]
        volumes = data[volume_col]

        # Taker 매수/매도 거래량 시리즈
        taker_buy_volumes = data[taker_buy_col]
        taker_sell_volumes = data[taker_sell_col]

        # 가격 범위 설정
        price_min, price_max = prices.min(), prices.max()
        bin_edges = np.linspace(price_min, price_max, bins + 1)

        # 각 가격이 속하는 구간 식별
        bin_indices = np.digitize(prices, bin_edges)  # 결과는 1 ~ bins+1 범위

        # 볼륨 프로파일: 구간별 거래량 합계
        volume_profile = pd.Series(0.0, index=range(1, bins + 1))
        # TPO 프로파일: 구간별 등장 횟수(= 시장이 해당 가격대 근처에 머문 횟수)
        tpo_profile = pd.Series(0, index=range(1, bins + 1))
        # Taker Buy/Sell 구간별 거래량
        taker_buy_profile = pd.Series(0.0, index=range(1, bins + 1))
        taker_sell_profile = pd.Series(0.0, index=range(1, bins + 1))

        # 각 행에 대해 해당 구간에 거래량 및 TPO 할당
        for idx, vol, tb_vol, ts_vol in zip(bin_indices, volumes, taker_buy_volumes, taker_sell_volumes):
            if 1 <= idx <= bins:
                volume_profile[idx] += vol
                tpo_profile[idx] += 1
                taker_buy_profile[idx] += tb_vol
                taker_sell_profile[idx] += ts_vol

        # 결과 DataFrame 생성
        profile_df = pd.DataFrame({
            'Bin': range(1, bins + 1),
            'Price_Low': bin_edges[:-1],
            'Price_High': bin_edges[1:],
            'Volume': volume_profile.values,
            'TPO': tpo_profile.values,
            'Taker_Buy_Volume': taker_buy_profile.values,
            'Taker_Sell_Volume': taker_sell_profile.values
        })

        # 거래량과 TPO 모두 상위권인 구간 식별 (간단한 가중합 방식)
        profile_df['Volume_norm'] = profile_df['Volume'] / profile_df['Volume'].sum() if profile_df['Volume'].sum() != 0 else 0
        profile_df['TPO_norm'] = profile_df['TPO'] / profile_df['TPO'].sum() if profile_df['TPO'].sum() != 0 else 0
        profile_df['Score'] = profile_df['Volume_norm'] + profile_df['TPO_norm']

        # Score 기준 내림차순 정렬
        sorted_df = profile_df.sort_values('Score', ascending=False).reset_index(drop=True)
        
        # 상위 3개를 잠재적 지지/저항 구간으로 추출 (예시)
        top_zones = sorted_df.head(3)

        # 가장 높은 Score를 가진 구간을 POC(Point of Control)로 간주
        poc = top_zones.iloc[0].to_dict()
        other_zones = top_zones.iloc[1:].to_dict('records')

        # 지지/저항선 정보 dictionary
        sr_levels = {
            'POC': poc,
            'Levels': other_zones
        }

        return profile_df, sr_levels

    def cal_obv(self, df, price_col='Close', volume_col='Volume',
                obv_col='obv', period_1=5, period_2 = 60):
        """
        1) OBV(On-Balance Volume) 계산
          - 이미 계산된 구간( NaN이 아닌 부분 )은 건너뛰고, NaN인 곳만 업데이트
          - OBV[i] = OBV[i-1] ± volume  (종가 상승/하락 시)
        2) 최근 p개 봉(또는 일)에 대한 OBV 고점/저점 계산 (현재 OBV 제외)
          - obv_max_p, obv_min_p
        3) (고점 - 현재값) 기울기, (저점 - 현재값) 기울기
          - 예: obv_slope_from_max = ( current_obv - max_obv_in_p ) / p
          - 예: obv_slope_from_min = ( current_obv - min_obv_in_p ) / p
        4) 반환: df ( obv, obv_slope_from_max, obv_slope_from_min 컬럼 포함 )
        """

        # ---------------------------
        # 0) 컬럼 준비
        # ---------------------------
        # obv가 없으면 생성
        if obv_col not in df.columns:
            df[obv_col] = np.nan

        # 고점/저점 & 기울기 컬럼들
        obv_max_col = f'{obv_col}_max_{period_1}'
        obv_min_col = f'{obv_col}_min_{period_1}'
        slope_from_max_col = f'{obv_col}_slope_from_max'
        slope_from_min_col = f'{obv_col}_slope_from_min'

        for col in [obv_max_col, obv_min_col, slope_from_max_col, slope_from_min_col]:
            if col not in df.columns:
                df[col] = np.nan

        # ---------------------------
        # 1) OBV 계산
        # ---------------------------
        last_valid = df[obv_col].last_valid_index()
        if last_valid is None:
            last_valid = -1

        for i in range(last_valid + 1, len(df)):
            if i == 0:
                df.loc[i, obv_col] = df.loc[i, volume_col]
                continue

            # 이미 값이 있으면 스킵
            if not pd.isna(df.loc[i, obv_col]):
                continue

            prev_price = df.loc[i - 1, price_col]
            curr_price = df.loc[i, price_col]
            prev_obv = df.loc[i - 1, obv_col]
            if pd.isna(prev_obv):
                prev_obv = 0

            curr_vol = df.loc[i, volume_col]

            # period_2보다 작을 때는 기존 OBV 계산법 적용
            if i <= period_2:
                if curr_price > prev_price:
                    df.loc[i, obv_col] = prev_obv + curr_vol
                elif curr_price < prev_price:
                    df.loc[i, obv_col] = prev_obv - curr_vol
                else:
                    df.loc[i, obv_col] = prev_obv
            else:
                # Rolling Window에서 가장 오래된 기간의 거래량 계산
                oldest_vol = df.loc[i - period_2, volume_col]
                oldest_price = df.loc[i - period_2, price_col]

                if curr_price > prev_price:
                    # 상승 시 최신 거래량 더하고, 가장 오래된 거래량의 영향 제거
                    if oldest_price > df.loc[i - period_2 - 1, price_col]:
                        df.loc[i, obv_col] = prev_obv + curr_vol - oldest_vol
                    else:
                        df.loc[i, obv_col] = prev_obv + curr_vol + oldest_vol
                elif curr_price < prev_price:
                    # 하락 시 최신 거래량 빼고, 가장 오래된 거래량의 영향 제거
                    if oldest_price < df.loc[i - period_2 - 1, price_col]:
                        df.loc[i, obv_col] = prev_obv - curr_vol + oldest_vol
                    else:
                        df.loc[i, obv_col] = prev_obv - curr_vol - oldest_vol
                else:
                    df.loc[i, obv_col] = prev_obv
        # ---------------------------
        # 2) p개 구간의 OBV 고점/저점 계산 (현재 OBV 제외)
        # ---------------------------
        # 고점/저점 컬럼의 last_valid
        last_valid_max = df[obv_max_col].last_valid_index()
        last_valid_min = df[obv_min_col].last_valid_index()
        candidate_idx = []
        if last_valid_max is not None:
            candidate_idx.append(last_valid_max)
        if last_valid_min is not None:
            candidate_idx.append(last_valid_min)

        if len(candidate_idx) > 0:
            last_valid_highlow = min(candidate_idx)
        else:
            last_valid_highlow = -1

        for i in range(last_valid_highlow + 1, len(df)):
            current_obv_val = df.loc[i, obv_col]
            if pd.isna(current_obv_val):
                continue  # OBV가 NaN이면 건너뜀

            # p봉 전부터 i-1까지 구간 (현재 i는 제외)
            if i < period_1:
                # p개 이전 인덱스가 유효하지 않으면 패스
                continue

            # 이미 값 있으면 스킵
            if (not pd.isna(df.loc[i, obv_max_col])) and (not pd.isna(df.loc[i, obv_min_col])):
                continue

            start_idx = i - period_1
            end_idx = i - 1
            obv_subset = df.loc[start_idx:end_idx, obv_col]

            if len(obv_subset) < period_1:
                # 충분한 데이터가 없으면 패스
                continue

            df.loc[i, obv_max_col] = obv_subset.max()
            df.loc[i, obv_min_col] = obv_subset.min()

        # ---------------------------
        # 3) (고점 - 현재값), (저점 - 현재값) 기울기 계산
        # ---------------------------
        # 여기서는 (현재 - 고점)/p, (현재 - 저점)/p 로 정의함
        # 질문 내용이 "고점 - 현재값 기울기"였지만, 부호 방향을 어떻게 할지는 자유
        # 원하는 대로 수정해서 쓰세요 :)
        last_valid_slope_max = df[slope_from_max_col].last_valid_index()
        last_valid_slope_min = df[slope_from_min_col].last_valid_index()
        candidate_idx_2 = []
        if last_valid_slope_max is not None:
            candidate_idx_2.append(last_valid_slope_max)
        if last_valid_slope_min is not None:
            candidate_idx_2.append(last_valid_slope_min)

        if len(candidate_idx_2) > 0:
            last_valid_slope = min(candidate_idx_2)
        else:
            last_valid_slope = -1

        for i in range(last_valid_slope + 1, len(df)):
            current_obv_val = df.loc[i, obv_col]
            max_val = df.loc[i, obv_max_col]
            min_val = df.loc[i, obv_min_col]

            if pd.isna(current_obv_val) or pd.isna(max_val) or pd.isna(min_val):
                continue

            # (현재 OBV - 고점) / p
            # 질문에서 "고점 - 현재값 기울기"라고 했으니 부호 반대로 할 수도 있음
            df.loc[i, slope_from_max_col] = (max_val - current_obv_val) / period_1
            df.loc[i, slope_from_min_col] = (min_val - current_obv_val) / period_1

        # ---------------------------
        # 4) 반환
        # ---------------------------
        # 최종적으로 obv, obv_slope_from_max, obv_slope_from_min 등을 포함한 df 반환
        return df

    def LT_trand_check(self, df):
        """
        상승 및 하락 추세 판단 함수
        볼린저 밴드 %b 및 Bandwidth 기반으로 추세 분석 강화
        Relative Bandwidth 계산을 포함하여 추세 전환 가능성까지 감지
        
        매개변수:
        df : pandas DataFrame - 볼린저 밴드 및 가격 데이터가 포함된 데이터프레임
        
        반환:
        df : pandas DataFrame - Trend 열에 추세 레벨을 반영하여 반환
        """

        # MA 트렌드 판별 함수
        def check_ma_trend(sma20, sma60, sma120, rbw, tol_ratio=0.005):
            """
            이동평균선 상태 및 상대 밴드폭(RBW)을 바탕으로 추세 상태를 정수로 매핑하는 함수
            
            매개변수:
            sma20 : float - 20일 이동평균선
            sma60 : float - 60일 이동평균선
            sma120 : float - 120일 이동평균선
            rbw : float - 상대 밴드폭 (Relative Bandwidth)
            
            반환:
            int - 트렌드 상태 (-9 ~ 9)
            """
            # -------------------------------------------------------
            # 1) 보조 함수: 두 SMA가 tol_ratio 이내로 근접한지 판별
            # -------------------------------------------------------
            def is_near(a, b, tolerance=tol_ratio):
                # 분모를 b 혹은 (a+b)/2 등으로 조정 가능
                # 절대값 기준으로 쓰고 싶다면 abs(a - b) < 특정값으로 변경
                return abs(a - b) <= abs(b) * tolerance

            near_20_60 = is_near(sma20, sma60)
            near_20_120 = is_near(sma20, sma120)
            near_60_120 = is_near(sma60, sma120)

            # -------------------------------------------------------
            # 모든 SMA(20,60,120)가 서로 근접 → 완전 박스권
            # -------------------------------------------------------
            if near_20_60 and near_20_120 and near_60_120:
                return 10  # Code 10: 단기·중기·장기 선이 사실상 동일 -> 강한 횡보(추세 모호)

            # (A) 강한 상승 배열: sma120 < sma60 < sma20
            #     근접 판정이 있는 경우: sma120 <= sma60 <= sma20
            if (sma120 < sma60 or is_near(sma120, sma60)) and \
              (sma60 < sma20 or is_near(sma60, sma20)) and \
              (sma120 < sma20 and not is_near(sma20, sma120)):  # 가장 긴 ~ 가장 짧은 것 사이에선 일단 확실히 상승
                if rbw > 1.1:
                    return 1
                elif 0.8 <= rbw <= 1.1:
                    return 2
                else:  # rbw < 0.8
                    return 3

            # (B) 불안정 상승 배열: sma60 < sma120 < sma20
            elif (sma60 < sma120 or is_near(sma60, sma120)) and \
                (sma120 < sma20 or is_near(sma120, sma20)) and \
                (sma60 < sma20 and not is_near(sma20, sma60)):
                if rbw > 1.1:
                    return 4
                elif 0.8 <= rbw <= 1.1:
                    return 5
                else:
                    return 6

            # (C) 약세 반등 배열: sma120 < sma20 < sma60
            elif (sma120 < sma20 or is_near(sma120, sma20)) and \
                (sma20 < sma60 or is_near(sma20, sma60)) and \
                (sma120 < sma60 and not is_near(sma60, sma120)):
                if rbw > 1.1:
                    return 7
                elif 0.8 <= rbw <= 1.1:
                    return 8
                else:
                    return 9

            # (D) 강한 하락 배열: sma20 < sma120 < sma60
            elif (sma20 < sma120 or is_near(sma20, sma120)) and \
                (sma120 < sma60 or is_near(sma120, sma60)) and \
                (sma20 < sma60 and not is_near(sma20, sma60)):
                if rbw > 1.1:
                    return -1
                elif 0.8 <= rbw <= 1.1:
                    return -2
                else:
                    return -3

            # (E) 불안정 하락 배열: sma60 < sma20 < sma120
            elif (sma60 < sma20 or is_near(sma60, sma20)) and \
                (sma20 < sma120 or is_near(sma20, sma120)) and \
                (sma60 < sma120 and not is_near(sma60, sma120)):
                if rbw > 1.1:
                    return -4
                elif 0.8 <= rbw <= 1.1:
                    return -5
                else:
                    return -6

            # (F) 급격한 하락 배열: sma20 < sma60 < sma120
            elif (sma20 < sma60 or is_near(sma20, sma60)) and \
                (sma60 < sma120 or is_near(sma60, sma120)) and \
                (sma20 < sma120 and not is_near(sma20, sma120)):
                if rbw > 1.1:
                    return -7
                elif 0.8 <= rbw <= 1.1:
                    return -8
                else:
                    return -9

            # (G) 그 외 → 횡보 or 추세 모호
            else:
                return 0

        # 1) 필요한 컬럼들이 없으면 새로 만듦
        needed_cols = ['trend', 'RBW']
        for col in needed_cols:
            if col not in df.columns:
                df[col] = np.nan

        # 2) 'Trend' 컬럼을 기준으로 last_valid_index 가져오기
        last_valid = df['trend'].last_valid_index()
        if last_valid is None:
            last_valid = -1  # 전부 NaN이면 -1로 설정

        # 3) MA 트렌드 및 횡보 상태 판별
        for i in range(last_valid + 1, len(df)):
            if pd.notna(df.loc[i, 'trend']):
                continue
            
            # 이동평균선 데이터
            sma20 = df.loc[i, 'SMA_20']
            sma60 = df.loc[i, 'SMA_60']
            sma120 = df.loc[i, 'SMA_120']
            bandwidth = df.loc[i, 'bandwidth']

            # 데이터 누락 시 건너뛰기
            if pd.isna(sma20) or pd.isna(sma60) or pd.isna(sma120) or pd.isna(bandwidth):
                continue

            # RBW(상대 밴드폭) 계산
            rbw = bandwidth / df['bandwidth'].rolling(60).mean().iloc[i]
            df.loc[i, 'RBW'] = rbw

            # MA 트렌드 판별 (새로운 함수 활용)
            trend_state = check_ma_trend(sma20, sma60, sma120, rbw)

            # Trend 컬럼에 상태 업데이트
            df.loc[i, 'trend'] = trend_state

        return df


    def data(self,client,symbol,timeframe, limit = 300, futures=False):
        symbol = f"{symbol}USDT"
        if futures:
            candles = client.futures_klines(symbol=symbol, interval=timeframe, limit=limit)
        else:
            candles = client.get_klines(symbol=symbol, interval=timeframe, limit=limit)

        # 새로운 데이터를 DataFrame으로 변환
        data = pd.DataFrame(candles, columns=[
            "Open Time", "Open", "High", "Low", "Close", "Volume",
            "Close Time", "Quote Asset Volume", "Number of Trades",
            "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume", "Ignore"
        ])
        selected_columns = ["Open Time", "Open", "High", "Low", "Close", "Volume", "Taker Buy Base Asset Volume"]
        data = data[selected_columns]
        # 자료형 변환
        data["Open"] = data["Open"].astype(float)
        data["High"] = data["High"].astype(float)
        data["Low"] = data["Low"].astype(float)
        data["Close"] = data["Close"].astype(float)
        data["Volume"] = data["Volume"].astype(float)
        data["Taker Buy Base Asset Volume"] = data["Taker Buy Base Asset Volume"].astype(float)

        # 시간 변환
        data["Open Time"] = pd.to_datetime(data["Open Time"], unit='ms')
        data["Taker Sell Base Asset Volume"] = data["Volume"] - data["Taker Buy Base Asset Volume"]
        data["Open Time"] = pd.to_datetime(data["Open Time"], unit='ms')  # 시간 변환
        data = data.sort_values(by="Open Time").reset_index(drop=True)
        
        if futures:
            # Funding Rate 수집
            funding_rate = client.futures_funding_rate(symbol=symbol)
            funding_df = pd.DataFrame(funding_rate)
            funding_df = funding_df.tail(300)  # 최근 300개의 Funding Rate만 유지
            funding_df["fundingRate"] = funding_df["fundingRate"].astype(float)
            funding_df["fundingTime"] = pd.to_datetime(funding_df["fundingTime"], unit='ms')
            
            # 5. 데이터 병합 (가장 최근 값으로 병합)
            data = pd.merge_asof(data.sort_values("Open Time"), funding_df.sort_values("fundingTime"), 
                                  left_on="Open Time", right_on="fundingTime", direction="backward")
            
            # 필요 없는 열 정리
            data.drop(columns=["fundingTime", "symbol", "markPrice"], inplace=True)

        return data
    
    def update_data(self, client, symbol, timeframe, existing_data, futures=False, funding_limit=3):
        try:
            # 새 데이터 수집 (3개 캔들 데이터만 요청)
            symbol = f"{symbol}USDT"
            candles = None
            if futures:
                candles = client.futures_klines(symbol=symbol, interval=timeframe, limit=3)
            else:
                candles = client.get_klines(symbol=symbol, interval=timeframe, limit=3)

            # 새로운 데이터를 DataFrame으로 변환
            temp_data = pd.DataFrame(candles, columns=[
                "Open Time", "Open", "High", "Low", "Close", "Volume",
                "Close Time", "Quote Asset Volume", "Number of Trades",
                "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume", "Ignore"
            ])
            
            # 필요한 컬럼만 선택 및 전처리
            selected_columns = ["Open Time", "Open", "High", "Low", "Close", "Volume", "Taker Buy Base Asset Volume"]
            temp_data = temp_data[selected_columns]
            temp_data["Open"]  = temp_data["Open"].astype(float)
            temp_data["High"]  = temp_data["High"].astype(float)
            temp_data["Low"]   = temp_data["Low"].astype(float)
            temp_data["Close"] = temp_data["Close"].astype(float)
            temp_data["Volume"] = temp_data["Volume"].astype(float)
            temp_data["Taker Buy Base Asset Volume"]  = temp_data["Taker Buy Base Asset Volume"].astype(float)
            temp_data["Taker Sell Base Asset Volume"] = temp_data["Volume"] - temp_data["Taker Buy Base Asset Volume"]
            temp_data["Open Time"] = pd.to_datetime(temp_data["Open Time"], unit='ms')
            
            # 선물 데이터에 추가 정보를 병합
            if futures:
                # Funding Rate 수집
                funding_rate = client.futures_funding_rate(symbol=symbol, limit=funding_limit)
                funding_df = pd.DataFrame(funding_rate)
                funding_df["fundingRate"] = funding_df["fundingRate"].astype(float)
                funding_df["fundingTime"] = pd.to_datetime(funding_df["fundingTime"], unit='ms')

                # 데이터 병합
                temp_data = pd.merge_asof(temp_data.sort_values("Open Time"), funding_df.sort_values("fundingTime"),
                                          left_on="Open Time", right_on="fundingTime", direction="backward")
                
                # 필요 없는 열 제거
                temp_data.drop(columns=["fundingTime", "symbol", "markPrice"], inplace=True)

            ## `Open Time` 기준 병합
            combined_data = pd.concat([existing_data, temp_data]).drop_duplicates(subset="Open Time", keep="last")
            combined_data = combined_data.sort_values(by="Open Time").reset_index(drop=True)

            if len(combined_data) > 140:
                combined_data = combined_data.iloc[-140:].reset_index(drop=True)

            return combined_data
            
        except Exception as e:
            print(f"데이터 업데이트 중 오류 발생: {e}")
            return existing_data