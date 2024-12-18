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
    
    def cal_rsi(self, data, period = 14):
        print("RSI를 계산합니다...")

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
        print("볼린저밴드를 계산합니다...")

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