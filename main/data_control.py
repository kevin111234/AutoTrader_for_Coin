from config import Config
import pandas as pd
class Data_Control():
    def __init__(self):
        print("Config에서 API 키를 불러옵니다.")
        print("API 객체 생성")

    def get_current_price(self,client,symbol):
        print("현재 가격을 불러옵니다...")
        price = client.get_symbol_ticker(symbol)
        current_price = price["price"]
        return current_price
    
    def cal_rsi(self,data):
        print("RSI를 계산합니다...")

        rsi = int()
        pre_rsi_1 = int()
        pre_rsi_2 = int()

        return rsi, pre_rsi_1, pre_rsi_2
    
    def cal_bollinger_band(self,data):
        print("볼린저밴드를 계산합니다...")

        upper_band = int()
        middle_band = int()
        lower_band = int()

        bollinger_band = []

        return bollinger_band

    def cal_volume_profile(self, data):
        print("볼륨 프로파일을 계산합니다...")

        support_price = int()
        resistance_price = int()

        self.volume_profile = []

        return support_price, resistance_price

    def cal_OBV(self, data):
        print("OBV를 계산합니다...")

        obv = []

        return obv
    
    def nor_rsi(self, data):
        print("RSI를 정규화합니다...")

        nor_rsi = int()

        return nor_rsi

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
        data["Open Time"] = pd.to_datetime(data["Open Time"], unit='ms')  # 시간 변환

        print("기술적 지표를 데이터에 추가합니다.")
        
        return data
    
    def data_update(self,client,symbol,timeframe,data):
        print("가장 최신 데이터를 확인합니다. 캔들이 완성된 봉을 기준으로 확인합니다.")

        print("데이터를 업데이트합니다")

        print("기술적 지표를 업데이트합니다")

        return data