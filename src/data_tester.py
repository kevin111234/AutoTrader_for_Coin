from binance.client import Client
import time
import pandas as pd
from config import Config
from data_control import Data_Control
from notifier import Notifier
from strategy import Strategy
from order_executor import Order
import utils
import math
import openpyxl

def tester():
    print("투자 프로그램 테스트를 시작합니다.")

    # Config에서 환경변수 및 고정변수 불러오기
    config = Config()
    ticker_list = config.coin_tickers.split(" ")
    future_use = bool(config.futures_use)
    if future_use:
        future_ticker_list = config.futures_coin_tickers.split(" ")
    client = Client(config.binance_access_key, config.binance_secret_key)
    data_control = Data_Control()
    notifier = Notifier()
    strategy = Strategy()
    order = Order(client)

    # 서버 시간과 로컬 시간 동기화
    local_time = int(time.time() * 1000)
    server_time = client.get_server_time()
    time_diff = server_time['serverTime'] - local_time

    if abs(time_diff) > 1000:
        print(f"시간 차이 발생: {time_diff}ms, 시스템 시간 동기화 필요")
        time.sleep(time_diff / 1000)

    # 초기 데이터 저장용 딕셔너리
    initial_data = {}
    vp_data = {}
    tpo_data = {}
    futures_data = {}
    futures_vp_data = {}
    futures_tpo_data = {}

    spot_symbol_info = {}
    future_symbol_info = {}

    for symbol in ticker_list:
        initial_data[symbol] = {}
        vp_data[symbol] = {}
        tpo_data[symbol] = {}
        spot_symbol_info[symbol] = utils.get_symbol_info(f"{symbol}USDT", client)

        for timeframe in ["1m", "5m", "1h"]:
            data = data_control.data(client, symbol, timeframe, limit=300)
            data = data_control.cal_moving_average(data)
            data = data_control.cal_rsi(data)
            data = data_control.cal_bollinger_band(data)
            data = data_control.cal_obv(data)
            data = data_control.LT_trand_check(data)
            data = data.dropna()

            if len(data) > 140:
                data = data.iloc[-140:].reset_index(drop=True)
            
            initial_data[symbol][timeframe] = data

            profile_df, sr_levels = data_control.cal_tpo_volume_profile(data)
            vp_data[symbol][timeframe] = profile_df
            tpo_data[symbol][timeframe] = pd.DataFrame([sr_levels])  # 리스트를 DataFrame으로 변환

    if future_use:
        for symbol in future_ticker_list:
            futures_data[symbol] = {}
            futures_vp_data[symbol] = {}
            futures_tpo_data[symbol] = {}
            future_symbol_info[symbol] = utils.get_symbol_info(f"{symbol}USDT", client)

            for timeframe in ["1m", "5m", "1h"]:
                future_data = data_control.data(client, symbol, timeframe, limit=300, futures=True)
                future_data = data_control.cal_moving_average(future_data)
                future_data = data_control.cal_rsi(future_data)
                future_data = data_control.cal_bollinger_band(future_data)
                future_data = data_control.cal_obv(future_data)
                future_data = data_control.LT_trand_check(future_data)
                future_data = future_data.dropna()

                if len(future_data) > 140:
                    future_data = future_data.iloc[-140:].reset_index(drop=True)

                futures_data[symbol][timeframe] = future_data

                profile_df, sr_levels = data_control.cal_tpo_volume_profile(future_data)
                futures_vp_data[symbol][timeframe] = profile_df
                futures_tpo_data[symbol][timeframe] = pd.DataFrame([sr_levels])  # 리스트를 DataFrame으로 변환

    # 엑셀 저장 (하나의 파일 내에 여러 시트로 저장)
    with pd.ExcelWriter("data/market_data.xlsx", engine="openpyxl") as writer:
        for symbol in ticker_list:
            for timeframe in ["1m", "5m", "1h"]:
                initial_data[symbol][timeframe].to_excel(writer, sheet_name=f"init_{symbol}_{timeframe}")
                vp_data[symbol][timeframe].to_excel(writer, sheet_name=f"vp_{symbol}_{timeframe}")
                tpo_data[symbol][timeframe].to_excel(writer, sheet_name=f"tpo_{symbol}_{timeframe}")

        if future_use:
            for symbol in future_ticker_list:
                for timeframe in ["1m", "5m", "1h"]:
                    futures_data[symbol][timeframe].to_excel(writer, sheet_name=f"fut_{symbol}_{timeframe}")
                    futures_vp_data[symbol][timeframe].to_excel(writer, sheet_name=f"fut_vp_{symbol}_{timeframe}")
                    futures_tpo_data[symbol][timeframe].to_excel(writer, sheet_name=f"fut_tpo_{symbol}_{timeframe}")

if __name__ == "__main__":
    tester()
