from binance.client import Client
import time

from config import Config
from data_control import Data_Control
from notifier import Notifier
from strategy import Strategy
from order_executor import Order
import utils

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

    buy_sell_status = {ticker: {"buy_stage": 0, "sell_stage": 0} for ticker in ticker_list}
    futures_status = {ticker: {"position": None, "stage": 0} for ticker in future_ticker_list}
    for symbol in ticker_list:
        initial_data[symbol] = {}
        vp_data[symbol] = {}
        tpo_data[symbol] = {}
        spot_symbol_info[symbol] = utils.get_symbol_info(f"{ticker}USDT")

        # 1분봉, 5분봉, 1시간봉 각각 300개의 데이터 조회
        for timeframe in ["1m", "5m", "1h"]:
            data = data_control.data(client, symbol, timeframe, limit=300)
            # 각 데이터에 대한 기술적 지표 계산
            data = data_control.cal_moving_average(data)
            data = data_control.cal_rsi(data)
            data = data_control.cal_bollinger_band(data)
            data = data_control.cal_obv(data)
            data = data_control.LT_trand_check(data)

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
                future_symbol_info[symbol] = utils.get_symbol_info(f"{ticker}USDT")
                for timeframe in ["1m", "5m", "1h"]:
                    future_data = data_control.data(client, symbol, timeframe, limit=300, futures=True)
                    # 각 데이터에 대한 기술적 지표 계산
                    future_data = data_control.cal_moving_average(future_data)
                    future_data = data_control.cal_rsi(future_data)
                    future_data = data_control.cal_bollinger_band(future_data)
                    future_data = data_control.cal_obv(future_data)
                    future_data = data_control.LT_trand_check(future_data)

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

            spot_limit_amount = notifier.get_limit_amount()
            future_limit_amount = notifier.futures_get_limit_amount()

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
                    updated_data = data_control.cal_moving_average(updated_data)
                    updated_data = data_control.cal_rsi(updated_data)
                    updated_data = data_control.cal_bollinger_band(updated_data)
                    updated_data = data_control.cal_obv(updated_data)
                    updated_data = data_control.LT_trand_check(updated_data)

                    # TPO/VP 데이터 업데이트
                    initial_data[ticker][timeframe] = updated_data
                    data = initial_data[ticker][timeframe]
                    profile_df, sr_levels = data_control.cal_tpo_volume_profile(data)
                    vp_data[ticker][timeframe] = profile_df
                    tpo_data[ticker][timeframe] = sr_levels

                # -------------------------------------------------------------------------
                # 매수/매도 판단
                signal = {}
                signal = strategy.signal(initial_data[ticker])

                # 주문 진행
                try:
                    # 매수 단계별 처리
                    if signal["signal"] == "buy":
                        current_stage = buy_sell_status[ticker]["buy_stage"]
                        target_stage = signal.get("weight", 1)

                        # 진행된 단계보다 높은 단계의 매수만 실행
                        if target_stage > current_stage:
                            for stage in range(current_stage + 1, target_stage + 1):
                                entry_price = signal["last_5m"]["Close"]
                                quantity = spot_limit_amount.get(ticker, 0) / entry_price / (6 - stage)
                                # 소수점 및 최소 주문량 처리
                                symbol_info = spot_symbol_info[ticker]
                                step_size = symbol_info["stepSize"]
                                min_qty = symbol_info["minQty"]
                                quantity = (quantity // step_size) * step_size

                                if quantity < min_qty:
                                    print(f"{ticker} {stage}단계 매수 실패: 최소 주문량({min_qty}) 미만")
                                    continue

                                # 매수 진행
                                print(f"{ticker} {stage}단계 매수 진행: 수량 {quantity}")

                                status = order.buy(symbol=f"{ticker}USDT", quantity=quantity)
                                if status and status.get("status") == "FILLED":
                                    print(f"{ticker} {stage}단계 매수 성공")
                                    order.place_oco_order(
                                        symbol=f"{ticker}USDT",
                                        quantity=quantity,
                                        entry_price=entry_price,
                                        take_profit_percent=signal["take_profit"],
                                        stop_loss_percent=signal["stop_loss"]
                                    )
                                    buy_sell_status[ticker]["buy_stage"] = stage
                                else:
                                    print(f"{ticker} {stage}단계 매수 실패: 주문 상태 미확인")
                                    notifier.send_slack_message(
                                        config.slack_error_channel_id,
                                        f"{ticker} {stage}단계 매수 실패: 주문 상태 확인 필요"
                                    )

                    # 현물 매도 단계별 처리
                    if signal["signal"] == "sell":
                        current_stage = buy_sell_status[ticker]["sell_stage"]
                        target_stage = signal.get("weight", 1)

                        if target_stage > current_stage:
                            for stage in range(current_stage + 1, target_stage + 1):
                                # 매도 가능한 수량 계산
                                available_quantity = notifier.asset_info[ticker]["free"] / (6 - stage)

                                # 소수점 및 최소 주문량 처리
                                symbol_info = spot_symbol_info[ticker]
                                step_size = symbol_info["stepSize"]
                                min_qty = symbol_info["minQty"]
                                available_quantity = (available_quantity // step_size) * step_size  # stepSize에 맞게 내림
                                if available_quantity < min_qty:
                                    print(f"{ticker} {stage}단계 매도 실패: 최소 주문량({min_qty}) 미만")
                                    continue

                                # 매도 진행
                                print(f"{ticker} {stage}단계 매도 진행: 수량 {available_quantity}")
                                status = order.sell(symbol=f"{ticker}USDT", quantity=available_quantity)
                                if status and status.get("status") == "FILLED":
                                    print(f"{ticker} {stage}단계 매도 성공")
                                    buy_sell_status[ticker]["sell_stage"] = stage
                                else:
                                    print(f"{ticker} {stage}단계 매도 실패: 주문 상태 미확인")
                                    notifier.send_slack_message(
                                        config.slack_error_channel_id,
                                        f"{ticker} {stage}단계 매도 실패: 주문 상태 확인 필요"
                                    )
                except Exception as e:
                    print(f"현물 주문 중 오류: {e}")

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
                        updated_data = data_control.cal_moving_average(updated_data)
                        updated_data = data_control.cal_rsi(updated_data)
                        updated_data = data_control.cal_bollinger_band(updated_data)
                        updated_data = data_control.cal_obv(updated_data)
                        updated_data = data_control.LT_trand_check(updated_data)

                        # TPO/VP 데이터 업데이트
                        futures_data[ticker][timeframe] = updated_data
                        data = futures_data[ticker][timeframe]
                        profile_df, sr_levels = data_control.cal_tpo_volume_profile(data)
                        futures_vp_data[ticker][timeframe] = profile_df
                        futures_tpo_data[ticker][timeframe] = sr_levels

                    # -------------------------------------------------------------------------
                    # 매수/매도 판단
                    signal = {}
                    signal = strategy.signal(futures_data[ticker])

                    # 현재 상태 확인
                    current_position = futures_status[ticker]["position"]
                    current_stage = futures_status[ticker]["stage"]
                    target_stage = int(signal.get("weight", 1))  # weight를 단계로 사용

                    # 선물 롱 포지션 처리
                    try:
                        if signal["signal"] == "L_buy":
                            if current_position == "short":
                                print(f"{ticker} 숏 포지션 정리")
                                quantity = abs(futures_status[ticker]["stage"] * future_limit_amount[ticker])
                                status = order.S_sell(symbol=f"{ticker}USDT", quantity=quantity)
                                if status and status.get("status") == "FILLED":
                                    futures_status[ticker] = {"position": None, "stage": 0}
                                    print(f"{ticker} 숏 포지션 정리 성공")
                                else:
                                    print(f"{ticker} 숏 포지션 정리 실패")
                                    continue

                            if current_position != "long" or target_stage > current_stage:
                                for stage in range(current_stage + 1, target_stage + 1):
                                    entry_price = signal["last_5m"]["Close"]
                                    quantity = future_limit_amount[ticker] / entry_price / (6 - stage)
                                    symbol_info = future_symbol_info[ticker]
                                    step_size = symbol_info["stepSize"]
                                    min_qty = symbol_info["minQty"]

                                    # 소수점 처리 및 최소 주문량 확인
                                    quantity = (quantity // step_size) * step_size
                                    if quantity < min_qty:
                                        print(f"{ticker} {stage}단계 롱 포지션 실패: 최소 주문량({min_qty}) 미만")
                                        continue

                                    # 롱 포지션 진입
                                    print(f"{ticker} {stage}단계 롱 포지션 진입: 수량 {quantity}")
                                    status = order.L_buy(symbol=f"{ticker}USDT", quantity=quantity)
                                    if status and status.get("status") == "FILLED":
                                        print(f"{ticker} {stage}단계 롱 포지션 성공")
                                        order.place_oco_order(
                                            symbol=f"{ticker}USDT",
                                            quantity=quantity,
                                            entry_price=entry_price,
                                            take_profit_percent=signal["take_profit"],
                                            stop_loss_percent=signal["stop_loss"]
                                        )
                                        futures_status[ticker] = {"position": "long", "stage": stage}
                                    else:
                                        print(f"{ticker} {stage}단계 롱 포지션 실패: 주문 상태 미확인")
                                        notifier.send_slack_message(
                                            config.slack_error_channel_id,
                                            f"{ticker} {stage}단계 롱 포지션 실패: 주문 상태 확인 필요"
                                        )

                        # 선물 숏 포지션 처리
                        elif signal["signal"] == "S_buy":
                            if current_position == "long":
                                print(f"{ticker} 롱 포지션 정리")
                                quantity = futures_status[ticker]["stage"] * future_limit_amount[ticker]
                                status = order.L_sell(symbol=f"{ticker}USDT", quantity=quantity)
                                if status and status.get("status") == "FILLED":
                                    futures_status[ticker] = {"position": None, "stage": 0}
                                    print(f"{ticker} 롱 포지션 정리 성공")
                                else:
                                    print(f"{ticker} 롱 포지션 정리 실패")
                                    continue

                            if current_position != "short" or target_stage > current_stage:
                                for stage in range(current_stage + 1, target_stage + 1):
                                    entry_price = signal["last_5m"]["Close"]
                                    quantity = future_limit_amount[ticker] / entry_price / (6 - stage)
                                    symbol_info = future_symbol_info[ticker]
                                    step_size = symbol_info["stepSize"]
                                    min_qty = symbol_info["minQty"]

                                    # 소수점 처리 및 최소 주문량 확인
                                    quantity = (quantity // step_size) * step_size
                                    if quantity < min_qty:
                                        print(f"{ticker} {stage}단계 숏 포지션 실패: 최소 주문량({min_qty}) 미만")
                                        continue

                                    # 숏 포지션 진입
                                    print(f"{ticker} {stage}단계 숏 포지션 진입: 수량 {quantity}")
                                    status = order.S_buy(symbol=f"{ticker}USDT", quantity=quantity)
                                    if status and status.get("status") == "FILLED":
                                        print(f"{ticker} {stage}단계 숏 포지션 성공")
                                        order.place_oco_order(
                                            symbol=f"{ticker}USDT",
                                            quantity=quantity,
                                            entry_price=entry_price,
                                            take_profit_percent=signal["take_profit"],
                                            stop_loss_percent=signal["stop_loss"]
                                        )
                                        futures_status[ticker] = {"position": "short", "stage": stage}
                                    else:
                                        print(f"{ticker} {stage}단계 숏 포지션 실패: 주문 상태 미확인")
                                        notifier.send_slack_message(
                                            config.slack_error_channel_id,
                                            f"{ticker} {stage}단계 숏 포지션 실패: 주문 상태 확인 필요"
                                        )
                        elif signal["signal"] == "L_sell":
                            # 롱 포지션 정리
                            if current_position == "long":
                                print(f"{ticker} 롱 포지션 정리 시작")

                                # 현재 롱 포지션 수량 확인
                                quantity = futures_status[ticker]["stage"] * future_limit_amount[ticker]
                                symbol_info = future_symbol_info[ticker]
                                step_size = symbol_info["stepSize"]
                                min_qty = symbol_info["minQty"]

                                # 소수점 처리 및 최소 주문량 확인
                                quantity = (quantity // step_size) * step_size
                                if quantity < min_qty:
                                    print(f"{ticker} 롱 포지션 정리 실패: 최소 주문량({min_qty}) 미만")
                                    notifier.send_slack_message(
                                        config.slack_error_channel_id,
                                        f"{ticker} 롱 포지션 정리 실패: 최소 주문량({min_qty}) 미만"
                                    )
                                else:
                                    # 롱 포지션 정리 주문 실행
                                    status = order.L_sell(symbol=f"{ticker}USDT", quantity=quantity)
                                    if status and status.get("status") == "FILLED":
                                        print(f"{ticker} 롱 포지션 정리 성공")
                                        futures_status[ticker] = {"position": None, "stage": 0}
                                    else:
                                        print(f"{ticker} 롱 포지션 정리 실패: 주문 상태 미확인")
                                        notifier.send_slack_message(
                                            config.slack_error_channel_id,
                                            f"{ticker} 롱 포지션 정리 실패: 주문 상태 확인 필요"
                                        )

                        elif signal["signal"] == "S_sell":
                            # 숏 포지션 정리
                            if current_position == "short":
                                print(f"{ticker} 숏 포지션 정리 시작")

                                # 현재 숏 포지션 수량 확인
                                quantity = futures_status[ticker]["stage"] * future_limit_amount[ticker]
                                symbol_info = future_symbol_info[ticker]
                                step_size = symbol_info["stepSize"]
                                min_qty = symbol_info["minQty"]

                                # 소수점 처리 및 최소 주문량 확인
                                quantity = (quantity // step_size) * step_size
                                if quantity < min_qty:
                                    print(f"{ticker} 숏 포지션 정리 실패: 최소 주문량({min_qty}) 미만")
                                    notifier.send_slack_message(
                                        config.slack_error_channel_id,
                                        f"{ticker} 숏 포지션 정리 실패: 최소 주문량({min_qty}) 미만"
                                    )
                                else:
                                    # 숏 포지션 정리 주문 실행
                                    status = order.S_sell(symbol=f"{ticker}USDT", quantity=quantity)
                                    if status and status.get("status") == "FILLED":
                                        print(f"{ticker} 숏 포지션 정리 성공")
                                        futures_status[ticker] = {"position": None, "stage": 0}
                                    else:
                                        print(f"{ticker} 숏 포지션 정리 실패: 주문 상태 미확인")
                                        notifier.send_slack_message(
                                            config.slack_error_channel_id,
                                            f"{ticker} 숏 포지션 정리 실패: 주문 상태 확인 필요"
                                        )

                        else:
                            print("Hold")
                    except Exception as e:
                        print(f"선물 주문 중 오류: {e}")

                    time.sleep(1)
        except Exception as e:
            print(f"메인 루프 오류: {e}")
            # notifier.py를 통해 error 로그 전송

if __name__ == "__main__":
    main()