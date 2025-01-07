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
        
        # period 리스트에 있는 각 기간별로 이동평균선 계산
        for p in period:
            col_name = f"SMA_{p}"
            
            # (1) SNA_XX 컬럼 없으면 만들기
            if col_name not in df.columns:
                df[col_name] = np.nan
            
            # (2) 이미 계산된 마지막 인덱스 찾기
            last_valid = df[col_name].last_valid_index()
            if last_valid is None:
                last_valid = -1
            
            # (3) 마지막 계산 인덱스 + 1부터 끝까지
            for i in range(last_valid + 1, len(df)):
                # p일치 안 되면 계산 불가
                if i < p - 1:
                    continue
                
                # 값이 이미 있으면 건너뛰기
                if not pd.isna(df.loc[i, col_name]):
                    continue
                
                # 직전 p개 구간 mean
                window_close = df.loc[i - p + 1 : i, 'Close']
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

    def cal_obv(self, df, price_col='Close', volume_col='Volume'):
        """
        OBV(On-Balance Volume) 계산
        - 이미 계산된 구간은 건너뛰고, NaN인 곳만 업데이트
        - OBV[i] = OBV[i-1] + volume  (종가 상승 시)
                = OBV[i-1] - volume  (종가 하락 시)
                = OBV[i-1]           (종가 동일 시)
        """

        # 1) obv 컬럼 없으면 만들어 둠
        if 'obv' not in df.columns:
            df['obv'] = np.nan

        # 2) 마지막으로 유효한 인덱스 찾기
        last_valid = df['obv'].last_valid_index()
        if last_valid is None:
            last_valid = -1  # 전부 NaN이면 -1로 설정

        # 3) last_valid + 1부터 끝까지 계산
        for i in range(last_valid + 1, len(df)):
            # 맨 첫 행이면 초기값 설정 (볼륨 그대로 넣거나 0으로 시작 등 원하는 로직)
            if i == 0:
                df.loc[i, 'obv'] = df.loc[i, volume_col]
                continue
            
            # 이미 값이 있으면 스킵
            if not pd.isna(df.loc[i, 'obv']):
                continue
            
            prev_price = df.loc[i - 1, price_col]
            curr_price = df.loc[i, price_col]
            prev_obv = df.loc[i - 1, 'obv'] if not pd.isna(df.loc[i - 1, 'obv']) else 0
            curr_vol = df.loc[i, volume_col]

            if curr_price > prev_price:
                df.loc[i, 'obv'] = prev_obv + curr_vol
            elif curr_price < prev_price:
                df.loc[i, 'obv'] = prev_obv - curr_vol
            else:
                # 가격이 동일하다면 변화 없음
                df.loc[i, 'obv'] = prev_obv

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
        def check_ma_trend(sma20, sma60, sma120, rbw):
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
            # 강한 상승 배열 sma120 < sma60 < sma20
            if sma120 < sma60 < sma20:
                # 1. 급격한 상승, 과매수 위험 구간
                if 1.1 < rbw:
                    return 1

                # 2. 안정적 상승 추세
                elif 0.8 <= rbw <= 1.1:
                    return 2

                # 3. 상승 추세에서 조정 가능성
                elif rbw < 0.8:
                    return 3

            # 불안정 상승 배열 sma60 < sma120 < sma20
            elif sma60 < sma120 < sma20:
                # 4. 상승 반전 시도, 변동성 높음
                if 1.1 < rbw:
                    return 4

                # 5. 상승 전환 박스권
                elif 0.8 <= rbw <= 1.1:
                    return 5

                # 6. 상승 전환 준비
                elif rbw < 0.8:
                    return 6

            # 약세 반등 배열 sma120 < sma20 < sma60
            elif sma120 < sma20 < sma60:
                # 7. 일시적 반등, 불안정
                if 1.1 < rbw:
                    return 7

                # 8. 약세장 속 반등
                elif 0.8 <= rbw <= 1.1:
                    return 8

                # 9. 하락 추세 재진입 가능성
                elif rbw < 0.8:
                    return 9

            # 강한 하락 배열 sma20 < sma120 < sma60
            elif sma20 < sma120 < sma60:
            # -1. 급격한 하락, 과매도 위험
                if 1.1 < rbw:
                    return -1

                # -2. 안정적 하락 추세
                elif 0.8 <= rbw <= 1.1:
                    return -2

                # -3. 하락 추세에서 반등 가능성
                elif rbw < 0.8:
                    return -3

            # 불안정 하락 배열 sma60 < sma20 < sma120
            elif sma60 < sma20 < sma120:
                # -4. 하락 반전 시도, 변동성 높음
                if 1.1 < rbw:
                    return -4

                # -5. 하락 전환 박스권
                elif 0.8 <= rbw <= 1.1:
                    return -5

                # -6. 하락 전환 준비
                elif rbw < 0.8:
                    return -6

            # 급격한 하락 배열 sma20 < sma60 < sma120
            elif sma20 < sma60 < sma120:
                # -7. 패닉셀, 과매도 구간 진입 가능성
                if 1.1 < rbw:
                    return -7

                # -8. 급락 후 안정화 진행중
                elif 0.8 <= rbw <=1.1:
                    return -8

                # -9. 급락 추세 소멸, 기술적 반등 가능성 존재
                elif rbw < 0.8:
                    return -9

            # 그 외 상황 (예외적 횡보, 추세 모호)
            else:
                return 0

        # 1) 필요한 컬럼들이 없으면 새로 만듦
        needed_cols = ['Trend', 'RBW']
        for col in needed_cols:
            if col not in df.columns:
                df[col] = np.nan

        # 2) 'Trend' 컬럼을 기준으로 last_valid_index 가져오기
        last_valid = df['Trend'].last_valid_index()
        if last_valid is None:
            last_valid = -1  # 전부 NaN이면 -1로 설정

        # 3) MA 트렌드 및 횡보 상태 판별
        for i in range(last_valid + 1, len(df)):
            if pd.notna(df.loc[i, 'Trend']):
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
            rbw = bandwidth / df['bandwidth'].rolling(20).mean().iloc[i]
            df.loc[i, 'RBW'] = rbw

            # MA 트렌드 판별 (새로운 함수 활용)
            trend_state = check_ma_trend(sma20, sma60, sma120, rbw)

            # Trend 컬럼에 상태 업데이트
            df.loc[i, 'Trend'] = trend_state

        return df


    def data(self,client,symbol,timeframe, limit = 300):
        symbol = f"{symbol}USDT"
        if timeframe == "1MINUTE":
            candles = client.get_klines(symbol=symbol, interval=client.KLINE_INTERVAL_1MINUTE, limit=limit)
        elif timeframe == "5MINUTE":
            candles = client.get_klines(symbol=symbol, interval=client.KLINE_INTERVAL_5MINUTE, limit=limit)
        elif timeframe == "1HOUR":
            candles = client.get_klines(symbol=symbol, interval=client.KLINE_INTERVAL_1HOUR, limit=limit)
        else:
            raise ValueError("Invalid timeframe. Please use '1MINUTE', '5MINUTE', or '1HOUR'.")

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
        
        return data
    
    def update_data(self, client, symbol, timeframe, existing_data):
        try:
            if timeframe == "1MINUTE":
                candles = client.get_klines(symbol=symbol, interval=client.KLINE_INTERVAL_1MINUTE, limit=3)
            elif timeframe == "5MINUTE":
                candles = client.get_klines(symbol=symbol, interval=client.KLINE_INTERVAL_5MINUTE, limit=3)
            elif timeframe == "1HOUR":
                candles = client.get_klines(symbol=symbol, interval=client.KLINE_INTERVAL_1HOUR, limit=3)
            else:
                raise ValueError("Invalid timeframe")

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
            
            ## `Open Time` 기준 병합
            combined_data = pd.concat([existing_data, temp_data]).drop_duplicates(subset="Open Time", keep="last")
            combined_data = combined_data.sort_values(by="Open Time").reset_index(drop=True)

            if len(combined_data) > 140:
                combined_data = combined_data.iloc[-140:].reset_index(drop=True)

            return combined_data
            
        except Exception as e:
            print(f"데이터 업데이트 중 오류 발생: {e}")
            return existing_data