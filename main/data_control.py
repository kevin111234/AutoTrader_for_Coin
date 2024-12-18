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

        return data

    def cal_tpo_volume_profile(data, price_col='Close', volume_col='Volume', bins=20):
        """
        TPO(Time at Price)와 볼륨 프로파일을 함께 계산하는 함수.
        - 각 가격 구간별 거래량(VP)과 TPO(해당 가격 구간에 캔들이 위치한 횟수)를 계산
        - 이후 이 정보를 토대로 지지/저항 구간을 식별하는데 활용 가능.
        """

        prices = data[price_col]
        volumes = data[volume_col]

        # 가격 범위 설정
        price_min, price_max = prices.min(), prices.max()
        bin_edges = np.linspace(price_min, price_max, bins + 1)

        # 각 가격이 속하는 구간 식별
        bin_indices = np.digitize(prices, bin_edges)  # 1 ~ bins+1 범위로 결과 나옴

        # 볼륨 프로파일: 구간별 거래량 합계
        volume_profile = pd.Series(0.0, index=range(1, bins + 1))
        # TPO 프로파일: 구간별 등장 횟수(= 시장이 해당 가격대 근처에 머문 횟수)
        tpo_profile = pd.Series(0, index=range(1, bins + 1))

        for idx, vol in zip(bin_indices, volumes):
            if 1 <= idx <= bins:
                volume_profile[idx] += vol
                tpo_profile[idx] += 1  # 해당 구간에 한 번 머물렀다고 카운트

        # 결과 DataFrame 생성
        profile_df = pd.DataFrame({
            'Bin': range(1, bins + 1),
            'Price_Low': bin_edges[:-1],
            'Price_High': bin_edges[1:],
            'Volume': volume_profile.values,
            'TPO': tpo_profile.values
        })

        # 거래량과 TPO 모두 상위권인 구간 식별 로직 (예: 단순 가중합)
        # 여기서는 간단히 Volume과 TPO를 정규화하여 합산 후 상위 몇개 구간 추출
        profile_df['Volume_norm'] = profile_df['Volume'] / profile_df['Volume'].sum()
        profile_df['TPO_norm'] = profile_df['TPO'] / profile_df['TPO'].sum()
        # 가중합 (가중치는 상황에 따라 조정 가능, 여기서는 동등 가중)
        profile_df['Score'] = profile_df['Volume_norm'] + profile_df['TPO_norm']

        # Score 기준 내림차순 정렬
        sorted_df = profile_df.sort_values('Score', ascending=False).reset_index(drop=True)
        
        # 상위 3개를 잠재적 지지/저항 구간으로 추출 (예시)
        top_zones = sorted_df.head(3)

        # 가장 높은 Score를 가진 구간을 POC로 간주
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

    def data(self,client,symbol,timeframe):
        limit = 100
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
        selected_columns = ["Open Time", "Open", "High", "Low", "Close", "Volume"]
        data = data[selected_columns]
        data["Open Time"] = pd.to_datetime(data["Open Time"], unit='ms')  # 시간 변환

        data = Data_Control.cal_bollinger_band(Data_Control.cal_rsi(Data_Control.cal_obv(data)))
        
        return data