import sys
import os

# 프로젝트 루트 디렉토리의 절대 경로를 구함
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from binance.client import Client
from datetime import datetime

from src.config import Config
from src.data_control import Data_Control
from src.utils import data_source
from backtester.test_strategy import rsi_stratage
from backtester.backtest_engine import BacktestEngine
from backtester.data_loader import load_backtest_data, cal_indicator, update_data

def backtester(start_date, end_date):
    config = Config()
    api_key = config.binance_access_key
    api_secret = config.binance_secret_key
    client = Client(api_key, api_secret)
    engine = BacktestEngine(initial_balance=100000)
    end_time = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")

    symbol = "BTC"

    data_dict = {}

    # 초기 데이터 저장
    data_dict[symbol] = {}
    for timeframe in ["1m", "5m", "1h"]:
        data = load_backtest_data(client, symbol, timeframe, start_date, limit=300, futures=False)
        data_dict[symbol][timeframe] = cal_indicator(data)

    print("초기 데이터 저장 완료. 모의투자 진행")
    current_time = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")

    while current_time < end_time:
        # 1m 업데이트
        updated_data_1m = update_data(data_dict[symbol]["1m"], client, symbol, "1m", futures = False)
        data_dict[symbol]["1m"] = cal_indicator(updated_data_1m)

        # 가장 최근의 open_time 가져오기
        last_open_time = updated_data_1m.iloc[-1]["Open Time"]
        current_time = last_open_time  # 현재 시간 업데이트

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
        signal_info = rsi_stratage(data_core)

        engine.execute_trade(signal_info["signal"], signal_info)

        # print(f"현재 시간: {current_time} | 잔고: {engine.balance:.2f}")

    print("백테스트 종료. 최종 잔고:", engine.balance)
    print(engine.get_trade_history())  

if __name__ == "__main__":
    backtester("2023-01-01 00:00:00", "2023-02-01 00:00:00")