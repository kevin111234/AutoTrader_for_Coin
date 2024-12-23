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

    # 초기 데이터 조회 - data_control.py
    initial_data = {}
    vp_data = {}
    tpo_data = {}
    for ticker in ticker_list:
        ticker = ticker.split("-")
        symbol = str(ticker[1]) + str(ticker[0])
        initial_data[symbol] = {}
        vp_data[symbol] = {}
        tpo_data[symbol] = {}

        for timeframe in ["1MINUTE", "5MINUTE", "1HOUR"]:
            data = data_control.data(client, symbol, timeframe, limit=200)
            data = data_control.cal_moving_average(data, period=20, method="SMA")
            data = data_control.cal_rsi(data_control.cal_bollinger_band(data_control.cal_obv(data)))
            profile_df, sr_levels = data_control.cal_tpo_volume_profile(data)  # 함수 실행
            if len(data) > 100:
                data = data.iloc[-100:].reset_index(drop=True)
            initial_data[symbol][timeframe] = data
            
            vp_data[symbol][timeframe] = profile_df
            tpo_data[symbol][timeframe] = sr_levels

    # 초기 자산 조회 - notifier.py

    # 반복문 시작
    while True:
        try:
            print("매수/매도 판단을 시작합니다.")
            for ticker in ticker_list:
                ticker = ticker.split("-")
                symbol = str(ticker[1]) + str(ticker[0])

                # 데이터 업데이트
                for timeframe in ["1MINUTE", "5MINUTE", "1HOUR"]:
                    initial_data[symbol][timeframe] = data_control.update_data(
                        client, symbol, timeframe, initial_data[symbol][timeframe]
                    )
                    
                    # TPO/VP 데이터 업데이트
                    data = initial_data[symbol][timeframe]
                    profile_df, sr_levels = data_control.cal_tpo_volume_profile(data)
                    vp_data[symbol][timeframe] = profile_df
                    tpo_data[symbol][timeframe] = sr_levels

            # 매수/매도 판단

            # 주문 진행

        except Exception as e:
            print(f"메인 루프 오류: {e}")
            # notifier.py를 통해 error 로그 전송