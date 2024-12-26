from config import Config

import pandas as pd
import numpy as np
class Data_Control():
    def __init__(self):
        pass

    def get_current_price(self,client,symbol):
        price = client.get_symbol_ticker(symbol)
        current_price = price["price"]
        return current_price
    
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
        data: 'Close' 열이 포함된 pandas DataFrame
        period: 볼린저 밴드 계산용 이동평균 기간 (기본=20)
        num_std: 표준편차 배수 (기본=2)
        """
        
        # 1) 볼린저 컬럼들이 없으면 만들어 둠
        if 'middle_boll' not in df.columns:
            df['middle_boll'] = np.nan
        if 'upper_boll' not in df.columns:
            df['upper_boll'] = np.nan
        if 'lower_boll' not in df.columns:
            df['lower_boll'] = np.nan

        # 2) 마지막으로 유효한(=NaN이 아닌) 중간선(middle_boll) 인덱스를 찾음
        #    세 컬럼 중 하나만 봐도 되지만, 여기선 middle_boll 기준으로 예시
        last_valid_boll = df['middle_boll'].last_valid_index()
        if last_valid_boll is None:
            last_valid_boll = -1  # 전부 NaN이면 -1로 설정해서 0부터 계산

        # 3) last_valid_boll + 1부터 끝까지 순회
        for i in range(last_valid_boll + 1, len(df)):
            # period 미만 구간은 볼린저밴드 계산 불가능 -> skip
            if i < period:
                continue
            
            # 이미 값이 들어있다면( NaN이 아니라면 ) 건너뛰기
            # 혹은 middle/upper/lower 중 하나라도 NaN이면 재계산
            if (pd.notna(df.loc[i, 'middle_boll']) and 
                pd.notna(df.loc[i, 'upper_boll']) and
                pd.notna(df.loc[i, 'lower_boll'])):
                continue
            
            # i번째 행까지 slice해서 rolling
            window_series = df.loc[:i, 'Close'].rolling(period)
            mean_val = window_series.mean().iloc[-1]
            std_val = window_series.std().iloc[-1]

            # 볼린저밴드 계산
            upper_val = mean_val + num_std * std_val
            lower_val = mean_val - num_std * std_val

            # 해당 인덱스에 기록
            df.loc[i, 'middle_boll'] = mean_val
            df.loc[i, 'upper_boll'] = upper_val
            df.loc[i, 'lower_boll'] = lower_val

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
        기존 LT_trand_check 함수를 '2번 방식' 개념으로 수정:
        이미 계산된 구간은 건너뛰고, NaN 값만 업데이트.

        data_1HOUR: 반드시
          - 'SMA_20', 'SMA_60', 'SMA_120'
          - 'Close', 'Volume'
        컬럼이 존재한다고 가정.
        """
        # 편의상 data_1HOUR를 df로 복사
        df = df.reset_index(drop=True)
        
        # 1) 필요한 컬럼들이 없으면 새로 만듦(처음 실행 시)
        needed_cols = [
            'MA_Trend', 
            'Spread_20_60', 'Spread_60_120', 'Spread_20_120',
            'Spread_20_60_diff', 'Spread_60_120_diff', 'Spread_20_120_diff',
            'OBV', 'OBV_diff',
            'Trend',
            'Spread_20_60_MA', 'Spread_60_120_MA', 'Spread_20_120_MA'
        ]
        for col in needed_cols:
            if col not in df.columns:
                df[col] = np.nan

        # 2) MA 트렌드 판별 함수
        def check_ma_trend(sma20, sma60, sma120):
            if sma20 > sma60 > sma120:
                return "UpTrend"
            elif sma20 < sma60 < sma120:
                return "DownTrend"
            else:
                return "SideWays"

        # 3) 추세(Trend) 판별 함수
        def detect_trend(ma_trend, spread_20_60_diff, obv_diff):
            if ma_trend == "UpTrend" and spread_20_60_diff > 0 and obv_diff > 0:
                return "Level 3 UpTrend"
            elif ma_trend == "UpTrend" and (spread_20_60_diff > 0 or obv_diff > 0):
                return "Level 2 UpTrend"
            elif ma_trend == "UpTrend":
                return "Level 1 UpTrend"
            elif ma_trend == "DownTrend" and spread_20_60_diff < 0 and obv_diff < 0:
                return "Level 3 DownTrend"
            elif ma_trend == "DownTrend" and (spread_20_60_diff < 0 or obv_diff < 0):
                return "Level 2 DownTrend"
            elif ma_trend == "DownTrend":
                return "Level 1 DownTrend"
            else:
                return "SideWays"

        # 4) 'Trend' 컬럼을 기준으로 last_valid_index 가져오기
        #    이미 Trend가 채워져 있는 구간은 건너뛴다는 개념
        last_valid = df['Trend'].last_valid_index()
        if last_valid is None:
            last_valid = -1  # 전부 NaN이면 -1로

        # 5) for문으로 (마지막 유효인덱스 + 1) ~ 끝까지 순회
        for i in range(last_valid + 1, len(df)):
            # 이미 Trend가 있으면( NaN이 아니면 ) 건너뛰기
            if pd.notna(df.loc[i, 'Trend']):
                continue
            
            # =============== (1) MA_Trend 판별 ===============
            sma20 = df.loc[i, 'SMA_20']
            sma60 = df.loc[i, 'SMA_60']
            sma120 = df.loc[i, 'SMA_120']
            
            # 값이 하나라도 NaN이면 트렌드 판단 불가
            if pd.isna(sma20) or pd.isna(sma60) or pd.isna(sma120):
                continue
            
            # MA_Trend 업데이트
            df.loc[i, 'MA_Trend'] = check_ma_trend(sma20, sma60, sma120)

            # =============== (2) Spread 계산 ===============
            df.loc[i, 'Spread_20_60']  = sma20 - sma60
            df.loc[i, 'Spread_60_120'] = sma60 - sma120
            df.loc[i, 'Spread_20_120'] = sma20 - sma120
            df.loc[i, 'Spread_20_60_MA'] = df.loc[i-19:i, 'Spread_20_60'].mean()
            df.loc[i, 'Spread_60_120_MA'] = df.loc[i-19:i, 'Spread_60_120'].mean()
            df.loc[i, 'Spread_20_120_MA'] = df.loc[i-19:i, 'Spread_20_120'].mean()

            # =============== (3) Spread 기울기(3틱 전 대비 차이) ===============
            # i-3 >= 0 일 때만 계산 가능
            if i >= 3:
                df.loc[i, 'Spread_20_60_diff']  = df.loc[i, 'Spread_20_60']  - df.loc[i-3, 'Spread_20_60']
                df.loc[i, 'Spread_60_120_diff'] = df.loc[i, 'Spread_60_120'] - df.loc[i-3, 'Spread_60_120']
                df.loc[i, 'Spread_20_120_diff'] = df.loc[i, 'Spread_20_120'] - df.loc[i-3, 'Spread_20_120']

            # =============== (4) OBV 업데이트 (이미 있으면 스킵, 없으면 계산) ===============
            # i=0인 경우엔 OBV를 초기화, i>0이면 이전 값 기반
            if i == 0:
                if pd.isna(df.loc[i, 'OBV']):
                    # 첫 캔들이라면 그냥 현재 volume으로 시작하거나 0으로 시작 가능
                    df.loc[i, 'OBV'] = df.loc[i, 'Volume']
            else:
                if pd.isna(df.loc[i, 'OBV']):
                    prev_price = df.loc[i-1, 'Close']
                    curr_price = df.loc[i, 'Close']
                    prev_obv = df.loc[i-1, 'OBV'] if not pd.isna(df.loc[i-1, 'OBV']) else 0
                    curr_vol = df.loc[i, 'Volume']
                    
                    if curr_price > prev_price:
                        df.loc[i, 'OBV'] = prev_obv + curr_vol
                    elif curr_price < prev_price:
                        df.loc[i, 'OBV'] = prev_obv - curr_vol
                    else:
                        df.loc[i, 'OBV'] = prev_obv
            
            # =============== (5) OBV 기울기(3틱 전 대비 차이) ===============
            if i >= 3 and not pd.isna(df.loc[i, 'OBV']) and not pd.isna(df.loc[i-3, 'OBV']):
                df.loc[i, 'OBV_diff'] = df.loc[i, 'OBV'] - df.loc[i-3, 'OBV']

            # =============== (6) 최종 Trend 판별 ===============
            # MA_Trend, Spread_20_60_diff, OBV_diff 중 하나라도 NaN이면 판별 불가
            ma_trend_val = df.loc[i, 'MA_Trend']
            spread_20_60_diff_val = df.loc[i, 'Spread_20_60_diff']
            obv_diff_val = df.loc[i, 'OBV_diff']

            if pd.isna(ma_trend_val) or pd.isna(spread_20_60_diff_val) or pd.isna(obv_diff_val):
                # 아직 3틱 안 됐거나, 필요한 값이 NaN이면 Trend를 구할 수 없음
                continue
            
            # Trend 업데이트
            df.loc[i, 'Trend'] = detect_trend(ma_trend_val, spread_20_60_diff_val, obv_diff_val)

        return df


    def data(self,client,symbol,timeframe, limit = 300):
        
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