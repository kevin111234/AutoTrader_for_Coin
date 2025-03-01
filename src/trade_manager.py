import math

class TradeManager:
    def __init__(self, order_executor, notifier, config):
        self.order = order_executor
        self.notifier = notifier
        self.config = config

    def process_spot_trade(self, ticker, signal, spot_limit_amount, buy_sell_status, symbol_info):
        try:
            if signal["signal"] == "buy":
                current_stage = buy_sell_status[ticker]["buy_stage"]
                target_stage = signal.get("weight", 1)
                if target_stage > current_stage:
                    for stage in range(current_stage + 1, target_stage + 1):
                        entry_price = signal["current_price"]
                        quantity = (int(spot_limit_amount.get(ticker, 0)) * 0.2) / entry_price
                        step_size = symbol_info["stepSize"]
                        min_qty = symbol_info["minQty"]
                        quantity = math.floor(quantity / step_size) * step_size

                        if quantity < min_qty:
                            print(f"{ticker} {stage}단계 매수 실패: 최소 주문량({min_qty}) 미만")
                            continue

                        print(f"{ticker} {stage}단계 매수 진행: 수량 {quantity}")
                        status = self.order.buy(symbol=f"{ticker}USDT", quantity=quantity)

                        if status and status.get("status") == "FILLED":
                            print(f"{ticker} {stage}단계 매수 성공")
                            message = (
                                f"매수 진행 신호 발생\n"
                                f"- 매수 비중: {signal.get('weight')}\n"
                                f"- 매수 근거: {signal.get('reason')}\n"
                                f"- 손절 퍼센트: {signal.get('stop_loss')}\n"
                                f"- 익절 퍼센트: {signal.get('take_profit')}"
                            )
                            self.notifier.send_slack_message(self.config.slack_trade_channel_id, message)
                            buy_sell_status[ticker]["buy_stage"] = stage
                            self.order.place_oco_order(
                                symbol=f"{ticker}USDT",
                                quantity=quantity,
                                entry_price=entry_price,
                                take_profit_percent=signal.get("take_profit"),
                                stop_loss_percent=signal.get("stop_loss")
                            )
                        else:
                            print(f"{ticker} {stage}단계 매수 실패: 주문 상태 미확인")
                            self.notifier.send_slack_message(
                                self.config.slack_error_channel_id,
                                f"{ticker} {stage}단계 매수 실패: 주문 상태 확인 필요"
                            )

            elif signal["signal"] == "sell":
                current_stage = buy_sell_status[ticker]["buy_stage"]
                target_stage = signal.get("weight", 1)
                if current_stage == 0:
                    print(f"{ticker}: 매도 신호 발생했으나 보유 수량 없음, 매도 스킵")
                    return

                if target_stage <= current_stage:
                    quantity = ((spot_limit_amount.get(ticker, 0) * 0.2) * target_stage) / signal["current_price"]
                    step_size = symbol_info["stepSize"]
                    min_qty = symbol_info["minQty"]
                    quantity = math.floor(quantity / step_size) * step_size

                    if quantity >= min_qty:
                        print(f"{ticker} {target_stage}단계 매도 진행: 수량 {quantity}")
                        message = (
                            f"매도 진행 신호 발생\n"
                            f"- 매도 비중: {signal.get('weight')}\n"
                            f"- 매도 근거: {signal.get('reason')}"
                        )
                        self.notifier.send_slack_message(self.config.slack_trade_channel_id, message)
                        status = self.order.sell(symbol=f"{ticker}USDT", quantity=quantity)
                        if status and status.get("status") == "FILLED":
                            buy_sell_status[ticker]["buy_stage"] -= target_stage
                            buy_sell_status[ticker]["buy_stage"] = max(0, buy_sell_status[ticker]["buy_stage"])
                    else:
                        print(f"{ticker} 매도 실패: 최소 주문량 미만")
                else:
                    quantity = self.notifier.asset_info[ticker]["free"]
                    step_size = symbol_info["stepSize"]
                    min_qty = symbol_info["minQty"]
                    quantity = math.floor(quantity / step_size) * step_size
                    if quantity >= min_qty:
                        print(f"{ticker} 전량 매도 진행: 수량 {quantity}")
                        status = self.order.sell(symbol=f"{ticker}USDT", quantity=quantity)
                        if status and status.get("status") == "FILLED":
                            buy_sell_status[ticker]["buy_stage"] = 0
                            message = f"{ticker} 전량 매도 성공"
                            print(message)
                            self.notifier.send_slack_message(self.config.slack_trade_channel_id, message)
                    else:
                        message = f"{ticker} 전량 매도 실패: 최소 주문량 미만"
                        print(message)
                        self.notifier.send_slack_message(
                            self.config.slack_error_channel_id,
                            message
                        )
            else:
                print("Hold")
        except Exception as e:
            print(f"스팟 거래 처리 중 오류 발생: {e}")

def process_futures_trade(self, ticker, signal, futures_limit_amount, futures_status, symbol_info):
    """
    선물 스테이징 로직을 적용하여, 단계별 진입/청산을 구현한 함수 예시입니다.
    기존 process_spot_trade 함수와 유사하게 'stage' 값을 사용해 부분매매를 합니다.

    매개변수:
      ticker               : 선물 거래 대상 티커 (예: "BTC")
      signal               : 전략에서 생성된 시그널 딕셔너리 (예: {"signal": "L_buy", "weight": 3, ...})
      futures_limit_amount : 선물 주문 가능 금액 딕셔너리 ({"BTC": 1000, ...})
      futures_status       : 선물 포지션 상태 관리용 딕셔너리 (예: {"BTC": {"position": "LONG", "stage": 2, "quantity": 0.01}})
      symbol_info          : 심볼별 스텝 사이즈, 최소 주문량 등 정보 ({"stepSize": 0.000001, "minQty": 0.0001})
    """
    try:
        current_price = signal.get("current_price", 0)
        signal_type = signal.get("signal", "")
        target_stage = signal.get("weight", 1)

        # 현재 포지션 정보
        current_pos = futures_status[ticker].get("position", None)  # "LONG", "SHORT", None
        current_stage = futures_status[ticker].get("stage", 0)
        current_quantity = futures_status[ticker].get("quantity", 0.0)

        step_size = symbol_info["stepSize"]
        min_qty = symbol_info["minQty"]

        # -------------------------------------------------------
        # 1) 선물 롱 진입 (L_buy)
        # -------------------------------------------------------
        if signal_type == "L_buy":
            # 이미 LONG 포지션이면 -> stage가 더 낮으면 추가진입(피라미딩)
            if current_pos == "LONG":
                if target_stage > current_stage:
                    for stage in range(current_stage + 1, target_stage + 1):
                        quantity = (int(futures_limit_amount.get(ticker, 0)) * 0.2) / current_price
                        quantity = math.floor(quantity / step_size) * step_size

                        if quantity < min_qty:
                            print(f"{ticker} {stage}단계 롱 추가진입 실패: 최소 주문량({min_qty}) 미만")
                            continue

                        print(f"{ticker} {stage}단계 롱 추가진입: 수량 {quantity}")
                        status = self.order.L_buy(symbol=f"{ticker}USDT", quantity=quantity)
                        if status and status.get("status") == "FILLED":
                            print(f"{ticker} {stage}단계 롱 추가진입 성공")
                            # 기존 보유량 += 새로 매수한 양
                            current_quantity += quantity
                            futures_status[ticker]["quantity"] = current_quantity
                            # 스테이지 업데이트
                            futures_status[ticker]["stage"] = stage
                            futures_status[ticker]["position"] = "LONG"
                        else:
                            print(f"{ticker} {stage}단계 롱 추가진입 실패: 주문 상태 미확인")
                else:
                    print(f"{ticker}: 이미 LONG 포지션 (stage={current_stage}), 추가 진입 없음.")
            elif current_pos == "SHORT":
                # 숏 포지션 상태에서 롱 신호가 들어온 경우 → 먼저 S_sell 등으로 숏 청산 후 롱 전환
                print(f"{ticker}: 현재 SHORT 보유 중 → 먼저 청산 처리 후에 롱 진입해야 합니다.")
            else:
                # current_pos == None
                # 스테이지별 최초 진입
                for stage in range(1, target_stage + 1):
                    quantity = (int(futures_limit_amount.get(ticker, 0)) * 0.2) / current_price
                    quantity = math.floor(quantity / step_size) * step_size

                    if quantity < min_qty:
                        print(f"{ticker} {stage}단계 롱 진입 실패: 최소 주문량({min_qty}) 미만")
                        continue

                    print(f"{ticker} {stage}단계 롱 진입: 수량 {quantity}")
                    status = self.order.L_buy(symbol=f"{ticker}USDT", quantity=quantity)
                    if status and status.get("status") == "FILLED":
                        print(f"{ticker} {stage}단계 롱 진입 성공")
                        current_quantity += quantity
                        futures_status[ticker]["position"] = "LONG"
                        futures_status[ticker]["stage"] = stage
                        futures_status[ticker]["quantity"] = current_quantity
                    else:
                        print(f"{ticker} {stage}단계 롱 진입 실패: 주문 상태 미확인")

        # -------------------------------------------------------
        # 2) 선물 롱 청산 (L_sell)
        # -------------------------------------------------------
        elif signal_type == "L_sell":
            if current_pos != "LONG":
                print(f"{ticker}: 롱 포지션이 아니므로 청산 불가.")
                return

            if current_stage == 0 or current_quantity <= 0:
                print(f"{ticker}: 롱 포지션이 없거나 이미 청산됨 (stage={current_stage}).")
                return

            # 부분 청산 or 전량 청산
            if target_stage < current_stage:
                # 부분청산 (단계 수만큼 반복)
                stages_to_sell = current_stage - target_stage
                # 1스테이지 분량
                if current_stage > 0:
                    per_stage_qty = current_quantity / current_stage
                else:
                    per_stage_qty = current_quantity

                for s in range(stages_to_sell):
                    qty = math.floor(per_stage_qty / step_size) * step_size
                    if qty < min_qty:
                        print(f"{ticker} 롱 부분청산 실패: 최소 주문량 미만")
                        continue

                    print(f"{ticker} 롱 부분청산 진행: 수량 {qty}")
                    status = self.order.L_sell(symbol=f"{ticker}USDT", quantity=qty)
                    if status and status.get("status") == "FILLED":
                        print(f"{ticker} 롱 부분청산 성공")
                        current_stage -= 1
                        current_quantity -= qty
                        futures_status[ticker]["stage"] = current_stage
                        futures_status[ticker]["quantity"] = max(0, current_quantity)
                        if current_stage == 0:
                            # 완전 청산된 경우
                            futures_status[ticker]["position"] = None
                            print(f"{ticker} 롱 포지션 완전 청산")
                            break
                    else:
                        print(f"{ticker} 롱 부분청산 실패: 주문 상태 미확인")
            else:
                # 전량 청산
                qty = math.floor(current_quantity / step_size) * step_size
                if qty < min_qty:
                    print(f"{ticker} 롱 전량청산 실패: 최소 주문량 미만")
                    return

                print(f"{ticker} 롱 전량청산 진행: 수량 {qty}")
                status = self.order.L_sell(symbol=f"{ticker}USDT", quantity=qty)
                if status and status.get("status") == "FILLED":
                    print(f"{ticker} 롱 전량청산 성공")
                    futures_status[ticker]["position"] = None
                    futures_status[ticker]["stage"] = 0
                    futures_status[ticker]["quantity"] = 0
                else:
                    print(f"{ticker} 롱 전량청산 실패: 주문 상태 미확인")

        # -------------------------------------------------------
        # 3) 선물 숏 진입 (S_buy)
        # -------------------------------------------------------
        elif signal_type == "S_buy":
            if current_pos == "SHORT":
                # 추가 숏 진입
                if target_stage > current_stage:
                    for stage in range(current_stage + 1, target_stage + 1):
                        quantity = (int(futures_limit_amount.get(ticker, 0)) * 0.2) / current_price
                        quantity = math.floor(quantity / step_size) * step_size

                        if quantity < min_qty:
                            print(f"{ticker} {stage}단계 숏 추가진입 실패: 최소 주문량({min_qty}) 미만")
                            continue

                        print(f"{ticker} {stage}단계 숏 추가진입: 수량 {quantity}")
                        status = self.order.S_buy(symbol=f"{ticker}USDT", quantity=quantity)
                        if status and status.get("status") == "FILLED":
                            print(f"{ticker} {stage}단계 숏 추가진입 성공")
                            current_quantity += quantity
                            futures_status[ticker]["stage"] = stage
                            futures_status[ticker]["quantity"] = current_quantity
                        else:
                            print(f"{ticker} {stage}단계 숏 추가진입 실패: 주문 상태 미확인")
                else:
                    print(f"{ticker}: 이미 SHORT 포지션 (stage={current_stage}), 추가 진입 없음.")
            elif current_pos == "LONG":
                print(f"{ticker}: 현재 LONG 상태 → 먼저 롱 청산 후 숏 전환 필요.")
            else:
                # position == None
                for stage in range(1, target_stage + 1):
                    quantity = (int(futures_limit_amount.get(ticker, 0)) * 0.2) / current_price
                    quantity = math.floor(quantity / step_size) * step_size

                    if quantity < min_qty:
                        print(f"{ticker} {stage}단계 숏 진입 실패: 최소 주문량({min_qty}) 미만")
                        continue

                    print(f"{ticker} {stage}단계 숏 진입: 수량 {quantity}")
                    status = self.order.S_buy(symbol=f"{ticker}USDT", quantity=quantity)
                    if status and status.get("status") == "FILLED":
                        print(f"{ticker} {stage}단계 숏 진입 성공")
                        current_quantity += quantity
                        futures_status[ticker]["position"] = "SHORT"
                        futures_status[ticker]["stage"] = stage
                        futures_status[ticker]["quantity"] = current_quantity
                    else:
                        print(f"{ticker} {stage}단계 숏 진입 실패: 주문 상태 미확인")

        # -------------------------------------------------------
        # 4) 선물 숏 청산 (S_sell)
        # -------------------------------------------------------
        elif signal_type == "S_sell":
            if current_pos != "SHORT":
                print(f"{ticker}: 숏 포지션이 아니므로 청산 불가.")
                return

            if current_stage == 0 or current_quantity <= 0:
                print(f"{ticker}: 숏 포지션이 없거나 이미 청산됨 (stage={current_stage}).")
                return

            # 부분 청산 or 전량 청산
            if target_stage < current_stage:
                stages_to_sell = current_stage - target_stage
                if current_stage > 0:
                    per_stage_qty = current_quantity / current_stage
                else:
                    per_stage_qty = current_quantity

                for s in range(stages_to_sell):
                    qty = math.floor(per_stage_qty / step_size) * step_size
                    if qty < min_qty:
                        print(f"{ticker} 숏 부분청산 실패: 최소 주문량 미만")
                        continue

                    print(f"{ticker} 숏 부분청산 진행: 수량 {qty}")
                    status = self.order.S_sell(symbol=f"{ticker}USDT", quantity=qty)
                    if status and status.get("status") == "FILLED":
                        print(f"{ticker} 숏 부분청산 성공")
                        current_stage -= 1
                        current_quantity -= qty
                        futures_status[ticker]["stage"] = current_stage
                        futures_status[ticker]["quantity"] = max(0, current_quantity)
                        if current_stage == 0:
                            futures_status[ticker]["position"] = None
                            print(f"{ticker} 숏 포지션 완전 청산")
                            break
                    else:
                        print(f"{ticker} 숏 부분청산 실패: 주문 상태 미확인")
            else:
                # 전량 청산
                qty = math.floor(current_quantity / step_size) * step_size
                if qty < min_qty:
                    print(f"{ticker} 숏 전량청산 실패: 최소 주문량 미만")
                    return

                print(f"{ticker} 숏 전량청산 진행: 수량 {qty}")
                status = self.order.S_sell(symbol=f"{ticker}USDT", quantity=qty)
                if status and status.get("status") == "FILLED":
                    print(f"{ticker} 숏 전량청산 성공")
                    futures_status[ticker]["position"] = None
                    futures_status[ticker]["stage"] = 0
                    futures_status[ticker]["quantity"] = 0
                else:
                    print(f"{ticker} 숏 전량청산 실패: 주문 상태 미확인")

        else:
            print("Hold")

    except Exception as e:
        print(f"선물 거래 처리 중 오류 발생: {e}")
