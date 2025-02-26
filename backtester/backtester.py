import sys
import os

# 프로젝트 루트 디렉토리의 절대 경로를 구함
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from binance.client import Client
from datetime import datetime, timedelta
from src.config import Config
from src.strategy import Strategy
from backtester.backtest_engine import BacktestEngine
from backtester.data_loader import load_backtest_data, cal_indicator, update_data

def backtester(start_date, end_date):
    config = Config()
    strategy = Strategy()
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
    last_print_time = current_time  # ✅ 마지막 출력 시간 (1시간마다 출력)

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
        signal_info = strategy.signal(data_dict[symbol], False)

        if engine.last_stop_loss_trend in [4, 5, 6, 7, 8, 9, 0, -1, -2, -3, -4, -5, -6] and signal_info["trend_5m"] in [4, 5, 6, 7, 8, 9, 0, -1, -2, -3, -4, -5, -6] and engine.cooling_timer > 0:
            signal_info["signal"] = "hold"
            signal_info["weight"] = 0
            signal_info["reason"] = "쿨링 기간"
            engine.cooling_timer -= 1

        engine.execute_trade(signal_info["signal"], signal_info)

        # ✅ 1시간마다 현재 상태 출력
        if current_time >= last_print_time + timedelta(hours=12):
            total_value = engine.get_total_value(signal_info["current_price"])  # 평가 자산
            mdd = engine.get_mdd()  # 최대 손실율
            print("=" * 50)
            print(f"[{current_time.strftime('%Y-%m-%d %H:%M')}] 현재 상태")
            print(f"잔고: ${engine.balance:.2f}")
            print(f"총 평가 자산 (보유 코인 포함): ${total_value:.2f}")
            print(f"최대 손실율 (MDD): {mdd:.2f}%")
            print(f"보유 코인: {engine.total_holdings:.6f} BTC")
            if engine.entry_price:
                print(f"평균 진입 가격: ${engine.entry_price:.2f}")
            print("=" * 50)
            last_print_time = current_time  # ✅ 출력 시간 갱신

        # print(f"현재 시간: {current_time} | 잔고: {engine.balance:.2f}")

    profit_ratio = ((engine.balance - engine.initial_balance) / engine.initial_balance) * 100
    print("백테스트 종료. 최종 잔고:", engine.balance, " 수익률: {:.2f}%".format(profit_ratio))
    print("최대 손실율 (MDD): {:.2f}%".format(engine.get_mdd()))
    engine.save_trade_history("backtest_signal_maker_1.csv")


if __name__ == "__main__":
    backtester("2024-01-01 00:00:00", "2025-02-01 00:00:00")