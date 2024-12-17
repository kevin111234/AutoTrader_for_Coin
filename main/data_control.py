from config import Config
import pandas as pd
class Data_Control():
    def __init__(self):
        print("Config에서 API 키를 불러옵니다.")
        print("API 객체 생성")
    
    def data(self,client):
        print("데이터를 불러옵니다...")

        print("데이터가 있는 경우 일부만 불러와 업데이트합니다.")

        print("기술적 지표를 데이터에 추가합니다.")

        print("데이터 로드 완료!")

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
