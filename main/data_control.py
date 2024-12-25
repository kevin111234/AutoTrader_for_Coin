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
    
    def cal_moving_average(self, data, period=[20, 60, 120]):

        return data
    
    def cal_rsi(self, data, period = 14, signal_period = 14):
        
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
    
    def cal_bollinger_band(self, data, period=20, num_std=2):
        
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
        
        return data
    
    def LT_trand_check(self, data):
        
        return data

    def data(self,client,symbol,timeframe, limit = 220):
        
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
            temp_data["Taker Sell Base Asset Volume"] = temp_data["Volume"] - temp_data["Taker Buy Base Asset Volume"]
            temp_data["Open Time"] = pd.to_datetime(temp_data["Open Time"], unit='ms')
            
            ## `Open Time` 기준 병합
            combined_data = pd.concat([existing_data, temp_data]).drop_duplicates(subset="Open Time", keep="last")
            combined_data = combined_data.sort_values(by="Open Time").reset_index(drop=True)

            if len(combined_data) > 120:
                combined_data = combined_data.iloc[-120:].reset_index(drop=True)

            return combined_data
            
        except Exception as e:
            print(f"데이터 업데이트 중 오류 발생: {e}")
            return existing_data