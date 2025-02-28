from binance.client import Client
import time
import math
import sys
import os

# 프로젝트 루트 디렉토리의 절대 경로를 구함
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.config import Config
from src.data_control import Data_Control
from src.notifier import Notifier
from src.strategy import Strategy
from src.order_executor import Order
from src.trade_manager import TradeManager
import src.utils

def main():
    print("투자 프로그램을 시작합니다.")
    
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
    trade_manager = TradeManager(order, notifier, config)

    # 서버 시간과 로컬 시간 동기화
    local_time = int(time.time() * 1000)
    server_time = client.get_server_time()
    time_diff = server_time['serverTime'] - local_time

    if abs(time_diff) > 1000:
        print(f"시간 차이 발생: {time_diff}ms, 시스템 시간 동기화 필요")
        time.sleep(time_diff / 1000)


    # 초기 데이터 조회 - data_control.py
    initial_data = {}
    vp_data = {}
    tpo_data = {}
    futures_data = {}
    futures_vp_data = {}
    futures_tpo_data = {}

    spot_symbol_info = {}
    future_symbol_info = {}

    buy_sell_status = {ticker: {"buy_stage": 0} for ticker in ticker_list}
    futures_status = {ticker: {"position": None, "stage": 0} for ticker in future_ticker_list}
    for symbol in ticker_list:
        initial_data[symbol] = {}
        vp_data[symbol] = {}
        tpo_data[symbol] = {}
        spot_symbol_info[symbol] = src.utils.get_symbol_info(f"{symbol}USDT", client)

        # 1분봉, 5분봉, 1시간봉 각각 300개의 데이터 조회
        for timeframe in ["1m", "5m", "1h"]:
            data = data_control.data(client, symbol, timeframe, limit=300)
            # 각 데이터에 대한 기술적 지표 계산
            data = data_control.cal_indicator(data)

            # 비어있는 값 제거
            data = data.dropna()
            
            # 데이터 길이는 140개로 제한. (120일 이평선 계산을 위함.)
            if len(data) > 140:
                data = data.iloc[-140:].reset_index(drop=True)
            initial_data[symbol][timeframe] = data
            # 남은 데이터에 대한 VP, TPO 계산
            profile_df, sr_levels = data_control.cal_tpo_volume_profile(data)
            
            vp_data[symbol][timeframe] = profile_df
            tpo_data[symbol][timeframe] = sr_levels

        if future_use:
            for symbol in future_ticker_list:
                futures_data[symbol] = {}
                futures_vp_data[symbol] = {}
                futures_tpo_data[symbol] = {}
                future_symbol_info[symbol] = src.utils.get_symbol_info(f"{symbol}USDT", client)
                for timeframe in ["1m", "5m", "1h"]:
                    future_data = data_control.data(client, symbol, timeframe, limit=300, futures=True)
                    # 각 데이터에 대한 기술적 지표 계산
                    future_data = data_control.cal_indicator(future_data)

                    # 비어있는 값 제거
                    future_data = future_data.dropna()
                    
                    # 데이터 길이는 140개로 제한. (120일 이평선 계산을 위함.)
                    if len(future_data) > 140:
                        future_data = future_data.iloc[-140:].reset_index(drop=True)
                    futures_data[symbol][timeframe] = future_data
                    # 남은 데이터에 대한 VP, TPO 계산
                    profile_df, sr_levels = data_control.cal_tpo_volume_profile(future_data)
                    
                    futures_vp_data[symbol][timeframe] = profile_df
                    futures_tpo_data[symbol][timeframe] = sr_levels

    # 초기 자산 조회 - notifier.py
    notifier.get_asset_info()
    notifier.get_futures_asset_info()
    spot_limit_amount = notifier.get_limit_amount()
    future_limit_amount = notifier.futures_get_limit_amount()

    notifier.send_asset_info(spot_limit_amount, future_limit_amount)

    # 반복문 시작
    while True:
        try:
            # 자산 정보 업데이트
            notifier.get_asset_info()
            notifier.get_futures_asset_info()

            spot_all_zero = all(
                notifier.asset_info[coin]["total_quantity"] == 0
                for coin in ticker_list
                if coin != "USDT"
            )
            # 모든 암호화폐의 보유량이 0이면 매수 한도 업데이트
            if spot_all_zero:
                spot_limit_amount = notifier.get_limit_amount()
                print("현물 매수 한도가 업데이트되었습니다.")
            # 선물 자산정보의 길이가 1이면 선물 매매 한도 업데이트
            has_positions = any(
                notifier.futures_asset_info.get(f"{symbol}USDT", {}).get("position_amt", 0) != 0
                for symbol in future_ticker_list
            )

            if not has_positions:  # ✅ 포지션이 하나도 없을 경우에만 업데이트 실행
                future_limit_amount = notifier.futures_get_limit_amount()
                print("선물 매매 한도가 업데이트되었습니다.")

            # 매수/매도 판단 로직
            for ticker in ticker_list:
                if ticker == "USDT": # USDT는 스킵
                    continue

                # 데이터 업데이트. 1분, 5분, 1시간 봉에 대한 업데이트 진행
                for timeframe in ["1m", "5m", "1h"]:
                    initial_data[ticker][timeframe] = data_control.update_data(
                        client, ticker, timeframe, initial_data[ticker][timeframe]
                    )
                    updated_data = initial_data[ticker][timeframe]
                    # 업데이트된 데이터에 대한 기술적 지표 추가
                    updated_data = data_control.cal_indicator(updated_data)
                    initial_data[ticker][timeframe] = updated_data

                # 매수/매도 판단
                signal = {}
                signal = strategy.signal(initial_data[ticker], False)

                # 주문 진행
                # 모듈화된 매매 로직 호출
                trade_manager.process_spot_trade(
                    ticker,
                    signal,
                    spot_limit_amount,
                    buy_sell_status,
                    spot_symbol_info[ticker]
                )

                # 1초 대기
                time.sleep(1)
            
            if future_use:
                for ticker in future_ticker_list:
                    if ticker == "USDT":
                        continue
                    for timeframe in ["1m", "5m", "1h"]:
                        futures_data[ticker][timeframe] = data_control.update_data(
                            client, ticker, timeframe, futures_data[ticker][timeframe], futures=True
                        )
                        updated_data = futures_data[ticker][timeframe]
                        # 업데이트된 데이터에 대한 기술적 지표 추가
                        updated_data = data_control.cal_indicator(updated_data)
                        futures_data[ticker][timeframe] = updated_data

                    # 매수/매도 판단
                    signal = {}
                    signal = strategy.signal(futures_data[ticker], True)

                if signal["signal"] == "close":
                    if futures_status[ticker].get("position") == "LONG":
                        signal["signal"] = "L_sell"
                    elif futures_status[ticker].get("position") == "SHORT":
                        signal["signal"] = "S_sell"
                    else:
                        signal["signal"] = "Hold"

                    # 모듈화된 선물 거래 로직 호출
                    trade_manager.process_futures_trade(
                        ticker,
                        signal,
                        future_limit_amount,
                        futures_status,
                        future_symbol_info[ticker]
                    )
                    
                    # 1초 대기
                    time.sleep(1)

        except Exception as e:
            print(f"메인 루프 오류: {e}")
            # notifier.py를 통해 error 로그 전송

if __name__ == "__main__":
    main()