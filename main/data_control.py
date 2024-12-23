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
    
    def cal_moving_average(self, data, period=20, method='SMA'):
        """
        이동평균선을 계산하는 함수
        :param data: 'Close' 컬럼을 포함한 pandas DataFrame
        :param period: 이동평균을 계산할 기간 (기본값: 20)
        :param method: 이동평균 방식 ('SMA' 또는 'EMA')
        :return: 이동평균선이 추가된 DataFrame
        """
        if method == 'SMA':
            # 단순 이동평균(SMA)
            data[f'SMA_{period}'] = data['Close'].rolling(window=period).mean()
        elif method == 'EMA':
            # 지수 이동평균(EMA)
            data[f'EMA_{period}'] = data['Close'].ewm(span=period, adjust=False).mean()
        else:
            raise ValueError("method는 'SMA' 또는 'EMA' 중 하나여야 합니다.")

        return data
    
    def cal_rsi(self, data, period = 14):
        # 'Close' 컬럼의 변화량 계산
        delta = data['Close'].diff()
        gains = delta.clip(lower=0)
        losses = -delta.clip(upper=0)

        # 초기 평균 계산 (첫 n개 구간)
        avg_gain = gains[:period].mean()
        avg_loss = losses[:period].mean()

        avg_gain_list = [avg_gain]
        avg_loss_list = [avg_loss]

        # n번째 이후 값들에 대해 와일더 방식 적용
        for i in range(period, len(gains)):
            gain = gains.iloc[i]
            loss = losses.iloc[i]

            avg_gain = ((avg_gain * (period - 1)) + gain) / period
            avg_loss = ((avg_loss * (period - 1)) + loss) / period

            avg_gain_list.append(avg_gain)
            avg_loss_list.append(avg_loss)

        # RS 및 RSI 계산
        rs = pd.Series(avg_gain_list, index=data.index[period-1:]) / pd.Series(avg_loss_list, index=data.index[period-1:])
        rsi = 100 - (100 / (1 + rs))

        # RSI를 원본 인덱스 전체로 확장. n-1 이전 구간은 RSI 미계산 구간이므로 NaN
        rsi_full = pd.Series(index=data.index, dtype=float)
        rsi_full.loc[rsi.index] = rsi

        # 데이터프레임에 RSI 칼럼 추가
        data['RSI'] = rsi_full
        
        return data

    
    def cal_bollinger_band(self, data, period=20, num_std=2):
        # Simple Moving Average(단순 이동 평균)
        sma = data['Close'].rolling(window=period).mean()

        # Rolling Std Deviation(구간 표준편차)
        std = data['Close'].rolling(window=period).std()

        # Upper Band와 Lower Band 계산
        upper_band = sma + (num_std * std)
        lower_band = sma - (num_std * std)

        # 결과 컬럼 추가
        data['Bollinger_MA'] = sma
        data['Bollinger_Upper'] = upper_band
        data['Bollinger_Lower'] = lower_band
        data['Bollinger_BW'] = upper_band-lower_band

        return data

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

    def cal_obv(self, data, price_col='Close', volume_col='Volume'):
        """
        OBV(On-Balance Volume)를 계산하는 함수.
        :param data: 'Close'와 'Volume' 컬럼을 포함한 pandas DataFrame
        :param price_col: 종가 컬럼명(기본: 'Close')
        :param volume_col: 거래량 컬럼명(기본: 'Volume')
        :return: OBV 컬럼이 추가된 DataFrame
        """
        # Close와 Volume 시리즈를 준비
        closes = data[price_col]
        volumes = data[volume_col]

        obv = [0]  # 첫 번째 값은 0으로 시작

        for i in range(1, len(data)):
            if closes.iloc[i] > closes.iloc[i - 1]:
                obv.append(obv[-1] + volumes.iloc[i])
            elif closes.iloc[i] < closes.iloc[i - 1]:
                obv.append(obv[-1] - volumes.iloc[i])
            else:
                # 종가가 이전 종가와 같은 경우 변화 없음
                obv.append(obv[-1])

        data['OBV'] = obv
        return data
    
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

    def data(self,client,symbol,timeframe, limit = 100):
        
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
        data["Taker Sell Base Asset Volume"] = data["Volume"] - data["Taker Buy Base Asset Volume"]
        data["Open Time"] = pd.to_datetime(data["Open Time"], unit='ms')  # 시간 변환
        data = data.sort_values(by="Open Time").reset_index(drop=True)
        
        return data
    
    def update_data(self, client, symbol, timeframe, existing_data):
        try:
            # 최신 23개 데이터 가져오기 (가장 긴 기간인 Bollinger Band 기준)
            if timeframe == "1MINUTE":
                candles = client.get_klines(symbol=symbol, interval=client.KLINE_INTERVAL_1MINUTE, limit=23)
            elif timeframe == "5MINUTE":
                candles = client.get_klines(symbol=symbol, interval=client.KLINE_INTERVAL_5MINUTE, limit=23)
            elif timeframe == "1HOUR":
                candles = client.get_klines(symbol=symbol, interval=client.KLINE_INTERVAL_1HOUR, limit=23)
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
            temp_data["Taker Sell Base Asset Volume"] = temp_data["Volume"] - temp_data["Taker Buy Base Asset Volume"]
            temp_data["Open Time"] = pd.to_datetime(temp_data["Open Time"], unit='ms')
            
            # 기술적 지표 계산
            for period in [20, 60, 100]:
                if f'SMA_{period}' in existing_data.columns:
                    temp_data = self.cal_moving_average(temp_data, period, method="SMA")
            if 'RSI' in existing_data.columns:
                temp_data = self.cal_rsi(temp_data)
            if 'Bollinger_MA' in existing_data.columns:
                temp_data = self.cal_bollinger_band(temp_data)
            if 'OBV' in existing_data.columns:
                temp_data = self.cal_obv(temp_data)
                
            # 최신 3개 데이터만 추출
            new_data = temp_data.tail(3)
            
            ## `Open Time` 기준 병합
            combined_data = pd.concat([existing_data, new_data]).drop_duplicates(subset="Open Time", keep="last")
            combined_data = combined_data.sort_values(by="Open Time").reset_index(drop=True)

            if len(combined_data) > 100:
                combined_data = combined_data.iloc[-100:].reset_index(drop=True)

            return combined_data
            
        except Exception as e:
            print(f"데이터 업데이트 중 오류 발생: {e}")
            return existing_data