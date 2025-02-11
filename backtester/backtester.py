import sys
import os

# 프로젝트 루트 디렉토리의 절대 경로를 구함
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from binance.client import Client

from src.config import Config
from src.data_control import Data_Control
from src.utils import data_source
from backtester.test_strategy import rsi_stratage

from backtester.data_loader import load_backtest_data, cal_indicator, update_data

def backtester(start_date):
    config = Config()
    api_key = config.binance_access_key
    api_secret = config.binance_secret_key
    client = Client(api_key, api_secret)

    ticker_list = config.coin_tickers.split(" ")
    future_use = bool(config.futures_use)
    if future_use:
        future_ticker_list = config.futures_coin_tickers.split(" ")

    data_dict = {}
    future_data_dict = {}

    # 초기 데이터 저장
    for symbol in ticker_list:
        data_dict[symbol] = {}
        for timeframe in ["1m", "5m", "1h"]:
            data = load_backtest_data(client, symbol, timeframe, start_date, limit=300, futures=False)
            data_dict[symbol][timeframe] = cal_indicator(data)

    if future_use:
        for symbol in future_ticker_list:
            future_data_dict[symbol] = {}
            for timeframe in ["1m", "5m", "1h"]:
                data = load_backtest_data(client, symbol, timeframe, start_date, limit=300, futures=True)
                future_data_dict[symbol][timeframe] = cal_indicator(data)

    balance = 1000
    print("초기 데이터 저장 완료. 모의투자 진행")

    while True:
        for symbol in ticker_list:
            # 1m 업데이트
            updated_data_1m = update_data(data_dict[symbol]["1m"], client, symbol, "1m", futures = False)
            data_dict[symbol]["1m"] = cal_indicator(updated_data_1m)

            # 가장 최근의 open_time 가져오기
            last_open_time = updated_data_1m.iloc[-1]["Open Time"]

            # 5분 단위 업데이트 (예: 00:05, 00:10, 00:15 ...)
            if last_open_time.minute % 5 == 0:
                updated_data_5m = update_data(data_dict[symbol]["5m"], client, symbol, "5m", futures = False)
                data_dict[symbol]["5m"] = cal_indicator(updated_data_5m)

            # 1시간 단위 업데이트 (예: 01:00, 02:00 ...)
            if last_open_time.minute == 0:
                updated_data_1h = update_data(data_dict[symbol]["1h"], client, symbol, "1h", futures = False)
                data_dict[symbol]["1h"] = cal_indicator(updated_data_1h)

            # 데이터 정제
            data_core = data_source(data_dict[symbol])
            signal = rsi_stratage(data_core)

        if future_use:
            for symbol in future_ticker_list:
                # 1m 업데이트
                updated_data_1m = update_data(future_data_dict[symbol]["1m"], client, symbol, "1m", futures = True)
                future_data_dict[symbol]["1m"] = cal_indicator(updated_data_1m)

                # 가장 최근의 open_time 가져오기
                last_open_time = updated_data_1m.iloc[-1]["Open Time"]

                # 5분 단위 업데이트 (예: 00:05, 00:10, 00:15 ...)
                if last_open_time.minute % 5 == 0:
                    updated_data_5m = update_data(future_data_dict[symbol]["5m"], client, symbol, "5m", futures = True)
                    future_data_dict[symbol]["5m"] = cal_indicator(updated_data_5m)

                # 1시간 단위 업데이트 (예: 01:00, 02:00 ...)
                if last_open_time.minute == 0:
                    updated_data_1h = update_data(future_data_dict[symbol]["1h"], client, symbol, "1h", futures = True)
                    future_data_dict[symbol]["1h"] = cal_indicator(updated_data_1h)

                # 데이터 정제
                data_core = data_source(future_data_dict[symbol])
                signal = rsi_stratage(data_core)

        print(data_dict)
        print(future_data_dict)

if __name__ == "__main__":
    backtester("2023-01-01 00:00:00")