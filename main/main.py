from binance.client import Client

from config import Config
from data_control import Data_Control

def main():
    print("투자 프로그램을 시작합니다.")
    
    # Config에서 환경변수 및 고정변수 불러오기
    config = Config()
    ticker_list = config.coin_tickers.split(" ")
    client = Client(config.binance_access_key, config.binance_secret_key)
    data_control = Data_Control()

    # 초기 자산 조회 - notifier.py

    # 반복문 시작
    while True:
        try:
            print("매수/매도 판단을 시작합니다.")
            # 현재 가격 조회

            # 가격데이터 업데이트
            for i in ticker_list:
                i.split("-")
                symbol = i[1]+i[0]
                timeframe = "5MINUTE"
                data = data_control.data(client,symbol,timeframe)

            # 매수/매도 판단

            # 주문 진행

        except Exception as e:
            print(f"메인 루프 오류: {e}")
            # notifier.py를 통해 error 로그 전송